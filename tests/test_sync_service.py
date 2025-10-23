"""Tests for sync service."""
from unittest.mock import MagicMock, Mock

import pytest

from src.grafana_client import GrafanaAPIError
from src.okta_client import OktaAPIError
from src.sync_service import SyncMetrics, SyncService


@pytest.fixture
def mock_okta_client() -> Mock:
    """Create mock Okta client."""
    return MagicMock()


@pytest.fixture
def mock_grafana_client() -> Mock:
    """Create mock Grafana client."""
    return MagicMock()


@pytest.fixture
def sync_service(mock_okta_client: Mock, mock_grafana_client: Mock) -> SyncService:
    """Create SyncService with mock clients."""
    return SyncService(
        okta_client=mock_okta_client,
        grafana_client=mock_grafana_client,
        dry_run=False,
    )


@pytest.fixture
def sync_service_dry_run(mock_okta_client: Mock, mock_grafana_client: Mock) -> SyncService:
    """Create SyncService in dry-run mode."""
    return SyncService(
        okta_client=mock_okta_client,
        grafana_client=mock_grafana_client,
        dry_run=True,
    )


class TestSyncMetrics:
    """Test SyncMetrics dataclass."""

    def test_default_values(self) -> None:
        """Test default metric values."""
        metrics = SyncMetrics()
        assert metrics.users_added == 0
        assert metrics.users_removed == 0
        assert metrics.errors == 0
        assert metrics.duration_seconds == 0.0

    def test_custom_values(self) -> None:
        """Test custom metric values."""
        metrics = SyncMetrics(users_added=5, users_removed=3, errors=1, duration_seconds=10.5)
        assert metrics.users_added == 5
        assert metrics.users_removed == 3
        assert metrics.errors == 1
        assert metrics.duration_seconds == 10.5


class TestSyncService:
    """Test SyncService class."""

    def test_init(self, mock_okta_client: Mock, mock_grafana_client: Mock) -> None:
        """Test SyncService initialization."""
        service = SyncService(mock_okta_client, mock_grafana_client, dry_run=True)
        assert service.okta_client == mock_okta_client
        assert service.grafana_client == mock_grafana_client
        assert service.dry_run is True

    def test_sync_with_users_to_add(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test sync when users need to be added."""
        # Setup Okta members
        mock_okta_client.get_group_members_by_name.return_value = [
            {"profile": {"email": "user1@example.com"}},
            {"profile": {"email": "user2@example.com"}},
        ]

        # Setup Grafana team
        mock_grafana_client.get_or_create_team.return_value = {
            "id": 1,
            "name": "Engineers",
        }

        # Setup Grafana members (empty team)
        mock_grafana_client.get_team_members.return_value = []

        # Setup user creation
        mock_grafana_client.get_or_create_user.side_effect = [
            {"id": 101, "email": "user1@example.com"},
            {"id": 102, "email": "user2@example.com"},
        ]

        # Execute sync
        metrics = sync_service.sync_group_to_team("Engineering", "Engineers")

        # Verify metrics
        assert metrics.users_added == 2
        assert metrics.users_removed == 0
        assert metrics.errors == 0
        assert metrics.duration_seconds > 0

        # Verify API calls
        mock_okta_client.get_group_members_by_name.assert_called_once_with("Engineering")
        mock_grafana_client.get_or_create_team.assert_called_once_with("Engineers")
        assert mock_grafana_client.get_or_create_user.call_count == 2
        assert mock_grafana_client.add_user_to_team.call_count == 2

    def test_sync_with_users_to_remove(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test sync when users need to be removed."""
        # Setup Okta members (empty group)
        mock_okta_client.get_group_members_by_name.return_value = []

        # Setup Grafana team
        mock_grafana_client.get_or_create_team.return_value = {
            "id": 1,
            "name": "Engineers",
        }

        # Setup Grafana members
        mock_grafana_client.get_team_members.return_value = [
            {"userId": 101, "email": "user1@example.com"},
            {"userId": 102, "email": "user2@example.com"},
        ]

        # Execute sync
        metrics = sync_service.sync_group_to_team("Engineering", "Engineers")

        # Verify metrics
        assert metrics.users_added == 0
        assert metrics.users_removed == 2
        assert metrics.errors == 0
        assert metrics.duration_seconds > 0

        # Verify API calls
        assert mock_grafana_client.remove_user_from_team.call_count == 2
        mock_grafana_client.remove_user_from_team.assert_any_call(1, 101)
        mock_grafana_client.remove_user_from_team.assert_any_call(1, 102)

    def test_sync_with_both_add_and_remove(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test sync with both additions and removals."""
        # Setup Okta members
        mock_okta_client.get_group_members_by_name.return_value = [
            {"profile": {"email": "user1@example.com"}},
            {"profile": {"email": "user2@example.com"}},
        ]

        # Setup Grafana team
        mock_grafana_client.get_or_create_team.return_value = {
            "id": 1,
            "name": "Engineers",
        }

        # Setup Grafana members (user3 should be removed)
        mock_grafana_client.get_team_members.return_value = [
            {"userId": 103, "email": "user3@example.com"},
        ]

        # Setup user creation
        mock_grafana_client.get_or_create_user.side_effect = [
            {"id": 101, "email": "user1@example.com"},
            {"id": 102, "email": "user2@example.com"},
        ]

        # Execute sync
        metrics = sync_service.sync_group_to_team("Engineering", "Engineers")

        # Verify metrics
        assert metrics.users_added == 2
        assert metrics.users_removed == 1
        assert metrics.errors == 0

        # Verify add operations
        assert mock_grafana_client.add_user_to_team.call_count == 2

        # Verify remove operations
        mock_grafana_client.remove_user_from_team.assert_called_once_with(1, 103)

    def test_sync_no_changes_idempotent(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test sync with no changes (idempotent)."""
        # Setup Okta members
        mock_okta_client.get_group_members_by_name.return_value = [
            {"profile": {"email": "user1@example.com"}},
            {"profile": {"email": "user2@example.com"}},
        ]

        # Setup Grafana team
        mock_grafana_client.get_or_create_team.return_value = {
            "id": 1,
            "name": "Engineers",
        }

        # Setup Grafana members (already in sync)
        mock_grafana_client.get_team_members.return_value = [
            {"userId": 101, "email": "user1@example.com"},
            {"userId": 102, "email": "user2@example.com"},
        ]

        # Execute sync
        metrics = sync_service.sync_group_to_team("Engineering", "Engineers")

        # Verify metrics
        assert metrics.users_added == 0
        assert metrics.users_removed == 0
        assert metrics.errors == 0

        # Verify no modifications
        mock_grafana_client.add_user_to_team.assert_not_called()
        mock_grafana_client.remove_user_from_team.assert_not_called()

    def test_sync_dry_run_mode(
        self,
        sync_service_dry_run: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test sync in dry-run mode."""
        # Setup Okta members
        mock_okta_client.get_group_members_by_name.return_value = [
            {"profile": {"email": "user1@example.com"}},
        ]

        # Setup Grafana team
        mock_grafana_client.get_or_create_team.return_value = {
            "id": 1,
            "name": "Engineers",
        }

        # Setup Grafana members
        mock_grafana_client.get_team_members.return_value = [
            {"userId": 102, "email": "user2@example.com"},
        ]

        # Execute sync in dry-run mode
        metrics = sync_service_dry_run.sync_group_to_team("Engineering", "Engineers")

        # Verify metrics show what would happen
        assert metrics.users_added == 1
        assert metrics.users_removed == 1
        assert metrics.errors == 0

        # Verify NO actual modifications
        mock_grafana_client.get_or_create_user.assert_not_called()
        mock_grafana_client.add_user_to_team.assert_not_called()
        mock_grafana_client.remove_user_from_team.assert_not_called()

    def test_sync_case_insensitive_email_matching(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test case-insensitive email matching."""
        # Setup Okta members (uppercase email)
        mock_okta_client.get_group_members_by_name.return_value = [
            {"profile": {"email": "USER1@EXAMPLE.COM"}},
        ]

        # Setup Grafana team
        mock_grafana_client.get_or_create_team.return_value = {
            "id": 1,
            "name": "Engineers",
        }

        # Setup Grafana members (lowercase email)
        mock_grafana_client.get_team_members.return_value = [
            {"userId": 101, "email": "user1@example.com"},
        ]

        # Execute sync
        metrics = sync_service.sync_group_to_team("Engineering", "Engineers")

        # Verify no changes (emails match case-insensitively)
        assert metrics.users_added == 0
        assert metrics.users_removed == 0
        assert metrics.errors == 0

    def test_sync_okta_api_error(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
    ) -> None:
        """Test error handling when Okta API fails."""
        # Setup Okta to raise error
        mock_okta_client.get_group_members_by_name.side_effect = OktaAPIError("Okta API error")

        # Execute sync and expect exception
        with pytest.raises(OktaAPIError, match="Okta API error"):
            sync_service.sync_group_to_team("Engineering", "Engineers")

    def test_sync_grafana_team_creation_error(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test error handling when Grafana team creation fails."""
        # Setup Okta members
        mock_okta_client.get_group_members_by_name.return_value = [
            {"profile": {"email": "user1@example.com"}},
        ]

        # Setup Grafana to raise error
        mock_grafana_client.get_or_create_team.side_effect = GrafanaAPIError("Team creation failed")

        # Execute sync and expect exception
        with pytest.raises(GrafanaAPIError, match="Team creation failed"):
            sync_service.sync_group_to_team("Engineering", "Engineers")

    def test_sync_partial_failure_add_users(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test partial failure when adding users (some succeed, some fail)."""
        # Setup Okta members
        mock_okta_client.get_group_members_by_name.return_value = [
            {"profile": {"email": "user1@example.com"}},
            {"profile": {"email": "user2@example.com"}},
            {"profile": {"email": "user3@example.com"}},
        ]

        # Setup Grafana team
        mock_grafana_client.get_or_create_team.return_value = {
            "id": 1,
            "name": "Engineers",
        }

        # Setup Grafana members (empty)
        mock_grafana_client.get_team_members.return_value = []

        # Setup user creation (user2 fails)
        def get_or_create_side_effect(email: str):
            if email == "user2@example.com":
                raise GrafanaAPIError("User creation failed")
            return {"id": 101, "email": email}

        mock_grafana_client.get_or_create_user.side_effect = get_or_create_side_effect

        # Execute sync
        metrics = sync_service.sync_group_to_team("Engineering", "Engineers")

        # Verify metrics
        assert metrics.users_added == 2  # user1 and user3 succeeded
        assert metrics.users_removed == 0
        assert metrics.errors == 1  # user2 failed

        # Verify add_user_to_team was called only for successful users
        assert mock_grafana_client.add_user_to_team.call_count == 2

    def test_sync_partial_failure_remove_users(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test partial failure when removing users."""
        # Setup Okta members (empty)
        mock_okta_client.get_group_members_by_name.return_value = []

        # Setup Grafana team
        mock_grafana_client.get_or_create_team.return_value = {
            "id": 1,
            "name": "Engineers",
        }

        # Setup Grafana members
        mock_grafana_client.get_team_members.return_value = [
            {"userId": 101, "email": "user1@example.com"},
            {"userId": 102, "email": "user2@example.com"},
            {"userId": 103, "email": "user3@example.com"},
        ]

        # Setup removal (user2 fails)
        def remove_side_effect(team_id: int, user_id: int):
            if user_id == 102:
                raise GrafanaAPIError("Remove failed")

        mock_grafana_client.remove_user_from_team.side_effect = remove_side_effect

        # Execute sync
        metrics = sync_service.sync_group_to_team("Engineering", "Engineers")

        # Verify metrics
        assert metrics.users_added == 0
        assert metrics.users_removed == 2  # user1 and user3 succeeded
        assert metrics.errors == 1  # user2 failed

    def test_sync_metrics_duration_tracked(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test that sync duration is tracked."""
        # Setup minimal sync
        mock_okta_client.get_group_members_by_name.return_value = []
        mock_grafana_client.get_or_create_team.return_value = {"id": 1, "name": "Engineers"}
        mock_grafana_client.get_team_members.return_value = []

        # Execute sync
        metrics = sync_service.sync_group_to_team("Engineering", "Engineers")

        # Verify duration is tracked
        assert metrics.duration_seconds > 0

    def test_sync_empty_okta_group(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test sync with empty Okta group."""
        # Setup empty Okta group
        mock_okta_client.get_group_members_by_name.return_value = []

        # Setup Grafana team
        mock_grafana_client.get_or_create_team.return_value = {"id": 1, "name": "Engineers"}

        # Setup empty Grafana team
        mock_grafana_client.get_team_members.return_value = []

        # Execute sync
        metrics = sync_service.sync_group_to_team("Engineering", "Engineers")

        # Verify no operations
        assert metrics.users_added == 0
        assert metrics.users_removed == 0
        assert metrics.errors == 0

    def test_sync_creates_team_if_not_exists(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test that sync creates Grafana team if it doesn't exist."""
        # Setup Okta members
        mock_okta_client.get_group_members_by_name.return_value = []

        # Setup Grafana team creation
        mock_grafana_client.get_or_create_team.return_value = {
            "id": 42,
            "name": "NewTeam",
        }

        # Setup empty team
        mock_grafana_client.get_team_members.return_value = []

        # Execute sync
        sync_service.sync_group_to_team("Engineering", "NewTeam")

        # Verify team creation was called
        mock_grafana_client.get_or_create_team.assert_called_once_with("NewTeam")

    def test_sync_admin_privileges_grant_and_revoke(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test syncing admin privileges with grants and revokes."""
        # Setup Okta admin group members
        mock_okta_client.get_group_members_by_name.return_value = [
            {"profile": {"email": "admin1@example.com"}},
            {"profile": {"email": "admin2@example.com"}},
        ]

        # Mock the _get method to return all Grafana users
        class MockResponse:
            def json(self):
                return [
                    {
                        "userId": 1,
                        "email": "admin1@example.com",
                        "isGrafanaAdmin": False,  # Needs to be granted
                    },
                    {
                        "userId": 2,
                        "email": "admin2@example.com",
                        "isGrafanaAdmin": True,  # Already admin
                    },
                    {
                        "userId": 3,
                        "email": "user@example.com",
                        "isGrafanaAdmin": True,  # Needs to be revoked
                    },
                ]

        mock_grafana_client._get.return_value = MockResponse()

        # Execute admin sync
        admins_updated = sync_service.sync_admin_privileges(["Grafana-Admins"])

        # Verify results
        assert admins_updated == 2  # admin1 granted, user revoked

        # Verify Okta API was called
        mock_okta_client.get_group_members_by_name.assert_called_once_with("Grafana-Admins")

        # Verify Grafana API calls
        assert mock_grafana_client.set_user_admin_permission.call_count == 2
        mock_grafana_client.set_user_admin_permission.assert_any_call(1, True)
        mock_grafana_client.set_user_admin_permission.assert_any_call(3, False)

    def test_sync_admin_privileges_empty_list(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test sync admin privileges with empty admin groups list."""
        admins_updated = sync_service.sync_admin_privileges([])

        # Verify no API calls made
        assert admins_updated == 0
        mock_okta_client.get_group_members_by_name.assert_not_called()
        mock_grafana_client._get.assert_not_called()

    def test_sync_admin_privileges_multiple_groups(
        self,
        sync_service: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test syncing admin privileges from multiple groups."""

        # Setup Okta groups
        def get_group_members_side_effect(group_name: str):
            if group_name == "Grafana-Admins":
                return [{"profile": {"email": "admin1@example.com"}}]
            elif group_name == "Platform-Team":
                return [
                    {"profile": {"email": "admin2@example.com"}},
                    {"profile": {"email": "admin1@example.com"}},  # Duplicate
                ]
            return []

        mock_okta_client.get_group_members_by_name.side_effect = get_group_members_side_effect

        # Mock Grafana users
        class MockResponse:
            def json(self):
                return [
                    {"userId": 1, "email": "admin1@example.com", "isGrafanaAdmin": False},
                    {"userId": 2, "email": "admin2@example.com", "isGrafanaAdmin": False},
                ]

        mock_grafana_client._get.return_value = MockResponse()

        # Execute admin sync with multiple groups
        admins_updated = sync_service.sync_admin_privileges(["Grafana-Admins", "Platform-Team"])

        # Verify both groups were queried
        assert mock_okta_client.get_group_members_by_name.call_count == 2

        # Verify both users granted admin (no duplicates)
        assert admins_updated == 2
        assert mock_grafana_client.set_user_admin_permission.call_count == 2

    def test_sync_admin_privileges_dry_run(
        self,
        sync_service_dry_run: SyncService,
        mock_okta_client: Mock,
        mock_grafana_client: Mock,
    ) -> None:
        """Test admin privilege sync in dry-run mode."""
        # Setup Okta admin group
        mock_okta_client.get_group_members_by_name.return_value = [
            {"profile": {"email": "admin@example.com"}}
        ]

        # Mock Grafana users
        class MockResponse:
            def json(self):
                return [{"userId": 1, "email": "admin@example.com", "isGrafanaAdmin": False}]

        mock_grafana_client._get.return_value = MockResponse()

        # Execute admin sync in dry-run mode
        admins_updated = sync_service_dry_run.sync_admin_privileges(["Grafana-Admins"])

        # Verify result counted but no actual changes made
        assert admins_updated == 1
        mock_grafana_client.set_user_admin_permission.assert_not_called()
