"""Tests for Grafana API client."""
import pytest
import responses

from src.grafana_client import (
    GrafanaAPIError,
    GrafanaAuthenticationError,
    GrafanaClient,
    GrafanaConflictError,
    GrafanaNotFoundError,
)


@pytest.fixture
def grafana_client() -> GrafanaClient:
    """Create Grafana client fixture."""
    return GrafanaClient(url="https://grafana.example.com", api_key="test-api-key")


class TestGrafanaClient:
    """Test GrafanaClient class."""

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from URL."""
        client = GrafanaClient(url="https://grafana.example.com/", api_key="key")
        assert client.base_url == "https://grafana.example.com"

    def test_session_headers(self, grafana_client: GrafanaClient) -> None:
        """Test that session has correct headers."""
        assert grafana_client.session.headers["Authorization"] == "Bearer test-api-key"
        assert grafana_client.session.headers["Content-Type"] == "application/json"
        assert grafana_client.session.headers["Accept"] == "application/json"

    @responses.activate
    def test_get_team_by_name_success(self, grafana_client: GrafanaClient) -> None:
        """Test successful team lookup."""
        mock_response = {
            "teams": [
                {
                    "id": 1,
                    "name": "Engineering",
                    "email": "eng@example.com",
                    "avatarUrl": "/avatar/abc",
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json=mock_response,
            status=200,
        )

        team = grafana_client.get_team_by_name("Engineering")
        assert team is not None
        assert team["id"] == 1
        assert team["name"] == "Engineering"

    @responses.activate
    def test_get_team_by_name_not_found(self, grafana_client: GrafanaClient) -> None:
        """Test team not found."""
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json={"teams": []},
            status=200,
        )

        team = grafana_client.get_team_by_name("NonExistent")
        assert team is None

    @responses.activate
    def test_get_team_by_name_exact_match(self, grafana_client: GrafanaClient) -> None:
        """Test that exact match is returned when multiple partial matches exist."""
        mock_response = {
            "teams": [
                {"id": 1, "name": "Engineering"},
                {"id": 2, "name": "Engineering-DevOps"},
                {"id": 3, "name": "Engineering-QA"},
            ]
        }

        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json=mock_response,
            status=200,
        )

        team = grafana_client.get_team_by_name("Engineering")
        assert team is not None
        assert team["id"] == 1

    @responses.activate
    def test_get_team_by_name_list_response(self, grafana_client: GrafanaClient) -> None:
        """Test team lookup when API returns a list instead of dict with teams key."""
        mock_response = [
            {"id": 1, "name": "Engineering"},
            {"id": 2, "name": "DevOps"},
        ]

        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json=mock_response,
            status=200,
        )

        team = grafana_client.get_team_by_name("Engineering")
        assert team is not None
        assert team["id"] == 1

    @responses.activate
    def test_create_team_success(self, grafana_client: GrafanaClient) -> None:
        """Test successful team creation."""
        mock_response = {"teamId": 42, "message": "Team created"}

        responses.add(
            responses.POST,
            "https://grafana.example.com/api/teams",
            json=mock_response,
            status=200,
        )

        result = grafana_client.create_team("NewTeam", "team@example.com")
        assert result["teamId"] == 42
        assert result["message"] == "Team created"

    @responses.activate
    def test_create_team_without_email(self, grafana_client: GrafanaClient) -> None:
        """Test team creation without email."""
        mock_response = {"teamId": 42, "message": "Team created"}

        responses.add(
            responses.POST,
            "https://grafana.example.com/api/teams",
            json=mock_response,
            status=200,
        )

        result = grafana_client.create_team("NewTeam")
        assert result["teamId"] == 42

    @responses.activate
    def test_create_team_conflict(self, grafana_client: GrafanaClient) -> None:
        """Test team creation when team already exists."""
        responses.add(
            responses.POST,
            "https://grafana.example.com/api/teams",
            json={"message": "Team name taken"},
            status=409,
        )

        with pytest.raises(GrafanaConflictError, match="Resource already exists"):
            grafana_client.create_team("ExistingTeam")

    @responses.activate
    def test_get_or_create_team_existing(self, grafana_client: GrafanaClient) -> None:
        """Test get_or_create_team when team exists."""
        mock_response = {"teams": [{"id": 1, "name": "Engineering"}]}

        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json=mock_response,
            status=200,
        )

        team = grafana_client.get_or_create_team("Engineering")
        assert team["id"] == 1

    @responses.activate
    def test_get_or_create_team_new(self, grafana_client: GrafanaClient) -> None:
        """Test get_or_create_team when team doesn't exist."""
        # First call: team not found
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json={"teams": []},
            status=200,
        )

        # Second call: create team
        responses.add(
            responses.POST,
            "https://grafana.example.com/api/teams",
            json={"teamId": 42, "message": "Team created"},
            status=200,
        )

        # Third call: get created team
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json={"teams": [{"id": 42, "name": "NewTeam"}]},
            status=200,
        )

        team = grafana_client.get_or_create_team("NewTeam")
        assert team["id"] == 42

    @responses.activate
    def test_get_or_create_team_creation_failed(self, grafana_client: GrafanaClient) -> None:
        """Test get_or_create_team when creation succeeds but retrieval fails."""
        # First call: team not found
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json={"teams": []},
            status=200,
        )

        # Second call: create team
        responses.add(
            responses.POST,
            "https://grafana.example.com/api/teams",
            json={"teamId": 42, "message": "Team created"},
            status=200,
        )

        # Third call: failed to retrieve created team
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json={"teams": []},
            status=200,
        )

        with pytest.raises(GrafanaAPIError, match="Failed to retrieve created team"):
            grafana_client.get_or_create_team("NewTeam")

    @responses.activate
    def test_get_team_members_success(self, grafana_client: GrafanaClient) -> None:
        """Test successful retrieval of team members."""
        mock_response = [
            {
                "userId": 1,
                "email": "user1@example.com",
                "login": "user1",
                "avatarUrl": "/avatar/1",
            },
            {
                "userId": 2,
                "email": "user2@example.com",
                "login": "user2",
                "avatarUrl": "/avatar/2",
            },
        ]

        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/1/members",
            json=mock_response,
            status=200,
        )

        members = grafana_client.get_team_members(1)
        assert len(members) == 2
        assert members[0]["email"] == "user1@example.com"
        assert members[1]["email"] == "user2@example.com"

    @responses.activate
    def test_get_team_members_empty(self, grafana_client: GrafanaClient) -> None:
        """Test retrieval of empty team."""
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/1/members",
            json=[],
            status=200,
        )

        members = grafana_client.get_team_members(1)
        assert len(members) == 0

    @responses.activate
    def test_get_user_by_email_success(self, grafana_client: GrafanaClient) -> None:
        """Test successful user lookup."""
        # Mock /api/org/users endpoint (returns list of org users)
        mock_response = [
            {
                "userId": 123,
                "email": "user@example.com",
                "login": "user",
                "name": "Test User",
                "orgId": 1,
                "role": "Editor",
            }
        ]

        responses.add(
            responses.GET,
            "https://grafana.example.com/api/org/users",
            json=mock_response,
            status=200,
        )

        user = grafana_client.get_user_by_email("user@example.com")
        assert user is not None
        assert user["id"] == 123  # Normalized from userId
        assert user["email"] == "user@example.com"

    @responses.activate
    def test_get_user_by_email_not_found(self, grafana_client: GrafanaClient) -> None:
        """Test user not found."""
        # Return empty list when user doesn't exist
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/org/users",
            json=[],
            status=200,
        )

        user = grafana_client.get_user_by_email("nonexistent@example.com")
        assert user is None

    @responses.activate
    def test_create_user_success(self, grafana_client: GrafanaClient) -> None:
        """Test successful user creation."""
        mock_response = {"id": 456, "message": "User created"}

        responses.add(
            responses.POST,
            "https://grafana.example.com/api/admin/users",
            json=mock_response,
            status=200,
        )

        result = grafana_client.create_user(
            email="newuser@example.com", login="newuser", name="New User"
        )
        assert result["id"] == 456

    @responses.activate
    def test_create_user_with_defaults(self, grafana_client: GrafanaClient) -> None:
        """Test user creation with default login and name."""
        mock_response = {"id": 456, "message": "User created"}

        responses.add(
            responses.POST,
            "https://grafana.example.com/api/admin/users",
            json=mock_response,
            status=200,
        )

        result = grafana_client.create_user(email="newuser@example.com")
        assert result["id"] == 456

    @responses.activate
    def test_create_user_conflict(self, grafana_client: GrafanaClient) -> None:
        """Test user creation when user already exists."""
        responses.add(
            responses.POST,
            "https://grafana.example.com/api/admin/users",
            json={"message": "User already exists"},
            status=409,
        )

        with pytest.raises(GrafanaConflictError, match="Resource already exists"):
            grafana_client.create_user("existing@example.com")

    @responses.activate
    def test_get_or_create_user_existing(self, grafana_client: GrafanaClient) -> None:
        """Test get_or_create_user when user exists."""
        # Mock org/users endpoint
        mock_response = [
            {"userId": 123, "email": "user@example.com", "login": "user", "role": "Viewer"}
        ]

        responses.add(
            responses.GET,
            "https://grafana.example.com/api/org/users",
            json=mock_response,
            status=200,
        )

        user = grafana_client.get_or_create_user("user@example.com")
        assert user["id"] == 123

    @responses.activate
    def test_get_or_create_user_new(self, grafana_client: GrafanaClient) -> None:
        """Test get_or_create_user when user doesn't exist."""
        # First call: user not found (empty list)
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/org/users",
            json=[],
            status=200,
        )

        # Second call: create user
        responses.add(
            responses.POST,
            "https://grafana.example.com/api/admin/users",
            json={"id": 456, "message": "User created"},
            status=200,
        )

        # Third call: get created user (now exists)
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/org/users",
            json=[{"userId": 456, "email": "newuser@example.com", "login": "newuser", "role": "Viewer"}],
            status=200,
        )

        user = grafana_client.get_or_create_user("newuser@example.com")
        assert user["id"] == 456

    @responses.activate
    def test_get_or_create_user_creation_failed(self, grafana_client: GrafanaClient) -> None:
        """Test get_or_create_user when creation succeeds but retrieval fails."""
        # First call: user not found (empty list)
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/org/users",
            json=[],
            status=200,
        )

        # Second call: create user
        responses.add(
            responses.POST,
            "https://grafana.example.com/api/admin/users",
            json={"id": 456, "message": "User created"},
            status=200,
        )

        # Third call: failed to retrieve created user (still empty list)
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/org/users",
            json=[],
            status=200,
        )

        with pytest.raises(GrafanaAPIError, match="Failed to retrieve created user"):
            grafana_client.get_or_create_user("newuser@example.com")

    @responses.activate
    def test_add_user_to_team_success(self, grafana_client: GrafanaClient) -> None:
        """Test adding user to team."""
        mock_response = {"message": "Member added to Team"}

        responses.add(
            responses.POST,
            "https://grafana.example.com/api/teams/1/members",
            json=mock_response,
            status=200,
        )

        result = grafana_client.add_user_to_team(team_id=1, user_id=123)
        assert result["message"] == "Member added to Team"

    @responses.activate
    def test_remove_user_from_team_success(self, grafana_client: GrafanaClient) -> None:
        """Test removing user from team."""
        mock_response = {"message": "Team Member removed"}

        responses.add(
            responses.DELETE,
            "https://grafana.example.com/api/teams/1/members/123",
            json=mock_response,
            status=200,
        )

        result = grafana_client.remove_user_from_team(team_id=1, user_id=123)
        assert result["message"] == "Team Member removed"

    @responses.activate
    def test_authentication_error_401(self, grafana_client: GrafanaClient) -> None:
        """Test authentication error handling (401)."""
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json={"message": "Invalid API key"},
            status=401,
        )

        with pytest.raises(GrafanaAuthenticationError, match="Authentication failed"):
            grafana_client.get_team_by_name("Engineering")

    @responses.activate
    def test_authentication_error_403(self, grafana_client: GrafanaClient) -> None:
        """Test authentication error handling (403)."""
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json={"message": "Access denied"},
            status=403,
        )

        with pytest.raises(GrafanaAuthenticationError, match="Authentication failed"):
            grafana_client.get_team_by_name("Engineering")

    @responses.activate
    def test_404_error(self, grafana_client: GrafanaClient) -> None:
        """Test 404 error handling."""
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/999",
            json={"message": "Team not found"},
            status=404,
        )

        with pytest.raises(GrafanaNotFoundError, match="Resource not found"):
            grafana_client._get("/api/teams/999")

    @responses.activate
    def test_generic_api_error(self, grafana_client: GrafanaClient) -> None:
        """Test generic API error handling."""
        responses.add(
            responses.GET,
            "https://grafana.example.com/api/teams/search",
            json={"message": "Internal server error"},
            status=500,
        )

        with pytest.raises(GrafanaAPIError, match="API error 500"):
            grafana_client.get_team_by_name("Engineering")

    @responses.activate
    def test_201_created_response(self, grafana_client: GrafanaClient) -> None:
        """Test that 201 Created is handled as success."""
        mock_response = {"teamId": 42, "message": "Team created"}

        responses.add(
            responses.POST,
            "https://grafana.example.com/api/teams",
            json=mock_response,
            status=201,
        )

        result = grafana_client.create_team("NewTeam")
        assert result["teamId"] == 42

    @responses.activate
    def test_update_user_role_success(self, grafana_client: GrafanaClient) -> None:
        """Test successful user role update."""
        mock_response = {"message": "Organization user updated"}

        responses.add(
            responses.PATCH,
            "https://grafana.example.com/api/org/users/123",
            json=mock_response,
            status=200,
        )

        result = grafana_client.update_user_role(user_id=123, role="Editor")
        assert result["message"] == "Organization user updated"

    def test_update_user_role_invalid_role(self, grafana_client: GrafanaClient) -> None:
        """Test error when updating with invalid role."""
        with pytest.raises(ValueError, match="Role must be one of"):
            grafana_client.update_user_role(user_id=123, role="InvalidRole")

    @responses.activate
    def test_set_user_admin_permission_grant(self, grafana_client: GrafanaClient) -> None:
        """Test granting Grafana admin permission."""
        mock_response = {"message": "User permissions updated"}

        responses.add(
            responses.PUT,
            "https://grafana.example.com/api/admin/users/123/permissions",
            json=mock_response,
            status=200,
        )

        result = grafana_client.set_user_admin_permission(user_id=123, is_admin=True)
        assert result["message"] == "User permissions updated"

    @responses.activate
    def test_set_user_admin_permission_revoke(self, grafana_client: GrafanaClient) -> None:
        """Test revoking Grafana admin permission."""
        mock_response = {"message": "User permissions updated"}

        responses.add(
            responses.PUT,
            "https://grafana.example.com/api/admin/users/123/permissions",
            json=mock_response,
            status=200,
        )

        result = grafana_client.set_user_admin_permission(user_id=123, is_admin=False)
        assert result["message"] == "User permissions updated"
