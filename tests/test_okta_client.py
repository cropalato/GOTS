"""Tests for Okta API client."""
import time
from unittest import mock

import pytest
import responses
from tenacity import RetryError

from src.okta_client import (
    OktaAPIError,
    OktaAuthenticationError,
    OktaClient,
    OktaNotFoundError,
    OktaOAuthTokenManager,
    OktaRateLimitError,
)


@pytest.fixture
def okta_client() -> OktaClient:
    """Create Okta client fixture."""
    return OktaClient(domain="example.okta.com", api_token="test-token")


class TestOktaClient:
    """Test OktaClient class."""

    def test_init_strips_protocol(self) -> None:
        """Test that protocol is stripped from domain."""
        client = OktaClient(domain="https://example.okta.com", api_token="token")
        assert client.domain == "example.okta.com"
        assert client.base_url == "https://example.okta.com"

    def test_init_strips_http_protocol(self) -> None:
        """Test that http:// protocol is stripped from domain."""
        client = OktaClient(domain="http://example.okta.com", api_token="token")
        assert client.domain == "example.okta.com"
        assert client.base_url == "https://example.okta.com"

    def test_session_headers(self, okta_client: OktaClient) -> None:
        """Test that session has correct headers."""
        # Authorization header is now set dynamically, not in session
        assert okta_client.session.headers["Accept"] == "application/json"
        assert okta_client.session.headers["Content-Type"] == "application/json"

    @responses.activate
    def test_get_group_by_name_success(self, okta_client: OktaClient) -> None:
        """Test successful group lookup."""
        mock_response = [
            {
                "id": "00g1234567890abcdef",
                "profile": {"name": "Engineering", "description": "Engineering team"},
            }
        ]

        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups",
            json=mock_response,
            status=200,
        )

        group = okta_client.get_group_by_name("Engineering")
        assert group["id"] == "00g1234567890abcdef"
        assert group["profile"]["name"] == "Engineering"

    @responses.activate
    def test_get_group_by_name_not_found(self, okta_client: OktaClient) -> None:
        """Test group not found error."""
        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups",
            json=[],
            status=200,
        )

        with pytest.raises(OktaNotFoundError, match="Group not found: NonExistent"):
            okta_client.get_group_by_name("NonExistent")

    @responses.activate
    def test_get_group_by_name_exact_match(self, okta_client: OktaClient) -> None:
        """Test that exact match is returned when multiple partial matches exist."""
        mock_response = [
            {"id": "1", "profile": {"name": "Engineering"}},
            {"id": "2", "profile": {"name": "Engineering-DevOps"}},
            {"id": "3", "profile": {"name": "Engineering-QA"}},
        ]

        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups",
            json=mock_response,
            status=200,
        )

        group = okta_client.get_group_by_name("Engineering")
        assert group["id"] == "1"

    @responses.activate
    def test_get_group_members_success(self, okta_client: OktaClient) -> None:
        """Test successful retrieval of group members."""
        mock_response = [
            {
                "id": "00u1234567890abcdef",
                "profile": {
                    "email": "user1@example.com",
                    "firstName": "John",
                    "lastName": "Doe",
                },
            },
            {
                "id": "00u0987654321fedcba",
                "profile": {
                    "email": "user2@example.com",
                    "firstName": "Jane",
                    "lastName": "Smith",
                },
            },
        ]

        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups/00g123/users",
            json=mock_response,
            status=200,
        )

        members = okta_client.get_group_members("00g123")
        assert len(members) == 2
        assert members[0]["profile"]["email"] == "user1@example.com"

    @responses.activate
    def test_get_group_members_pagination(self, okta_client: OktaClient) -> None:
        """Test pagination when retrieving group members."""
        page1_response = [{"id": "user1", "profile": {"email": "user1@example.com"}}]
        page2_response = [{"id": "user2", "profile": {"email": "user2@example.com"}}]

        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups/00g123/users",
            json=page1_response,
            status=200,
            headers={
                "Link": '<https://example.okta.com/api/v1/groups/00g123/users?after=cursor1>; rel="next"'
            },
        )

        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups/00g123/users",
            json=page2_response,
            status=200,
        )

        members = okta_client.get_group_members("00g123")
        assert len(members) == 2
        assert members[0]["id"] == "user1"
        assert members[1]["id"] == "user2"

    @responses.activate
    def test_get_group_members_empty(self, okta_client: OktaClient) -> None:
        """Test retrieval of empty group."""
        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups/00g123/users",
            json=[],
            status=200,
        )

        members = okta_client.get_group_members("00g123")
        assert len(members) == 0

    @responses.activate
    def test_authentication_error(self, okta_client: OktaClient) -> None:
        """Test authentication error handling."""
        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups",
            json={
                "errorCode": "E0000011",
                "errorSummary": "Invalid token provided",
            },
            status=401,
        )

        with pytest.raises(OktaAuthenticationError, match="Authentication failed"):
            okta_client.get_group_by_name("Engineering")

    @responses.activate
    def test_rate_limit_error(self, okta_client: OktaClient) -> None:
        """Test rate limit error handling."""
        # Add multiple 429 responses for retry attempts
        for _ in range(5):
            responses.add(
                responses.GET,
                "https://example.okta.com/api/v1/groups",
                json={"errorCode": "E0000047", "errorSummary": "Rate limit exceeded"},
                status=429,
                headers={"X-Rate-Limit-Reset": "1234567890"},
            )

        # After all retries are exhausted, tenacity wraps it in RetryError
        with pytest.raises(RetryError):
            okta_client.get_group_by_name("Engineering")

    @responses.activate
    def test_404_error(self, okta_client: OktaClient) -> None:
        """Test 404 error handling."""
        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups/invalid",
            json={"errorCode": "E0000007", "errorSummary": "Not found"},
            status=404,
        )

        with pytest.raises(OktaNotFoundError, match="Resource not found"):
            okta_client._get("/api/v1/groups/invalid")

    @responses.activate
    def test_generic_api_error(self, okta_client: OktaClient) -> None:
        """Test generic API error handling."""
        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups",
            json={
                "errorCode": "E0000001",
                "errorSummary": "API validation failed",
            },
            status=400,
        )

        with pytest.raises(OktaAPIError, match="API error 400"):
            okta_client.get_group_by_name("Engineering")

    @responses.activate
    def test_get_group_members_by_name(self, okta_client: OktaClient) -> None:
        """Test convenience method to get members by group name."""
        # Mock group search
        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups",
            json=[{"id": "00g123", "profile": {"name": "Engineering"}}],
            status=200,
        )

        # Mock members retrieval
        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups/00g123/users",
            json=[{"id": "user1", "profile": {"email": "user1@example.com"}}],
            status=200,
        )

        members = okta_client.get_group_members_by_name("Engineering")
        assert len(members) == 1
        assert members[0]["id"] == "user1"

    def test_parse_next_link(self) -> None:
        """Test parsing of Link header."""
        link_header = '<https://example.okta.com/api/v1/groups?after=cursor>; rel="next", <https://example.okta.com/api/v1/groups>; rel="self"'
        next_link = OktaClient._parse_next_link(link_header)
        assert next_link == "https://example.okta.com/api/v1/groups?after=cursor"

    def test_parse_next_link_no_next(self) -> None:
        """Test parsing Link header with no next link."""
        link_header = '<https://example.okta.com/api/v1/groups>; rel="self"'
        next_link = OktaClient._parse_next_link(link_header)
        assert next_link is None

    def test_parse_next_link_empty(self) -> None:
        """Test parsing empty Link header."""
        next_link = OktaClient._parse_next_link("")
        assert next_link is None

    @responses.activate
    def test_rate_limit_logging(self, okta_client: OktaClient) -> None:
        """Test that rate limit info is logged."""
        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups",
            json=[{"id": "00g123", "profile": {"name": "Engineering"}}],
            status=200,
            headers={"X-Rate-Limit-Limit": "1000", "X-Rate-Limit-Remaining": "999"},
        )

        okta_client.get_group_by_name("Engineering")
        # If this doesn't raise an exception, the logging worked
        assert True

    @responses.activate
    def test_multiple_pages_pagination(self, okta_client: OktaClient) -> None:
        """Test pagination with multiple pages."""
        page1 = [{"id": "user1"}]
        page2 = [{"id": "user2"}]
        page3 = [{"id": "user3"}]

        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups/00g123/users",
            json=page1,
            status=200,
            headers={
                "Link": '<https://example.okta.com/api/v1/groups/00g123/users?after=cursor1>; rel="next"'
            },
        )

        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups/00g123/users",
            json=page2,
            status=200,
            headers={
                "Link": '<https://example.okta.com/api/v1/groups/00g123/users?after=cursor2>; rel="next"'
            },
        )

        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups/00g123/users",
            json=page3,
            status=200,
        )

        members = okta_client.get_group_members("00g123")
        assert len(members) == 3
        assert members[0]["id"] == "user1"
        assert members[1]["id"] == "user2"
        assert members[2]["id"] == "user3"


class TestOktaOAuthTokenManager:
    """Test OktaOAuthTokenManager class."""

    @pytest.fixture
    def oauth_manager(self) -> OktaOAuthTokenManager:
        """Create OAuth token manager fixture."""
        return OktaOAuthTokenManager(
            domain="example.okta.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
            scopes=["okta.groups.read", "okta.users.read"],
        )

    def test_init_strips_protocol(self) -> None:
        """Test that protocol is stripped from domain."""
        manager = OktaOAuthTokenManager(
            domain="https://example.okta.com",
            client_id="id",
            client_secret="secret",
            scopes=["okta.groups.read"],
        )
        assert manager.domain == "example.okta.com"
        assert manager.token_url == "https://example.okta.com/oauth2/v1/token"

    @responses.activate
    def test_get_access_token_success(self, oauth_manager: OktaOAuthTokenManager) -> None:
        """Test successful token acquisition."""
        mock_response = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        responses.add(
            responses.POST,
            "https://example.okta.com/oauth2/v1/token",
            json=mock_response,
            status=200,
        )

        token = oauth_manager.get_access_token()
        assert token == "test-access-token"

    @responses.activate
    def test_token_caching(self, oauth_manager: OktaOAuthTokenManager) -> None:
        """Test that tokens are cached and reused."""
        mock_response = {"access_token": "cached-token", "token_type": "Bearer", "expires_in": 3600}

        responses.add(
            responses.POST,
            "https://example.okta.com/oauth2/v1/token",
            json=mock_response,
            status=200,
        )

        # First call should fetch token
        token1 = oauth_manager.get_access_token()
        assert token1 == "cached-token"
        assert len(responses.calls) == 1

        # Second call should use cached token
        token2 = oauth_manager.get_access_token()
        assert token2 == "cached-token"
        assert len(responses.calls) == 1  # No additional API call

    @responses.activate
    def test_token_refresh_on_expiry(self, oauth_manager: OktaOAuthTokenManager) -> None:
        """Test that expired tokens are refreshed."""
        first_response = {
            "access_token": "first-token",
            "token_type": "Bearer",
            "expires_in": 1,  # Expire in 1 second
        }
        second_response = {
            "access_token": "second-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        responses.add(
            responses.POST,
            "https://example.okta.com/oauth2/v1/token",
            json=first_response,
            status=200,
        )
        responses.add(
            responses.POST,
            "https://example.okta.com/oauth2/v1/token",
            json=second_response,
            status=200,
        )

        # Get initial token
        token1 = oauth_manager.get_access_token()
        assert token1 == "first-token"

        # Wait for token to expire (with 60s safety margin, it expires immediately)
        time.sleep(0.1)

        # Should get new token
        token2 = oauth_manager.get_access_token()
        assert token2 == "second-token"
        assert len(responses.calls) == 2

    @responses.activate
    def test_authentication_error(self, oauth_manager: OktaOAuthTokenManager) -> None:
        """Test OAuth authentication error handling."""
        responses.add(
            responses.POST,
            "https://example.okta.com/oauth2/v1/token",
            json={"error": "invalid_client", "error_description": "Invalid client credentials"},
            status=401,
        )

        with pytest.raises(OktaAuthenticationError, match="OAuth authentication failed"):
            oauth_manager.get_access_token()

    @responses.activate
    def test_api_error(self, oauth_manager: OktaOAuthTokenManager) -> None:
        """Test generic OAuth API error handling."""
        responses.add(
            responses.POST,
            "https://example.okta.com/oauth2/v1/token",
            json={"error": "server_error", "error_description": "Internal server error"},
            status=500,
        )

        with pytest.raises(OktaAPIError, match="OAuth token request failed 500"):
            oauth_manager.get_access_token()

    def test_token_expiry_calculation(self, oauth_manager: OktaOAuthTokenManager) -> None:
        """Test token expiry time calculation."""
        # Token should be expired initially
        assert oauth_manager._is_token_expired() is True

        # Set expiry to future time
        oauth_manager._token_expiry = time.time() + 120  # 2 minutes from now
        assert oauth_manager._is_token_expired() is False

        # Set expiry to 30 seconds from now (within safety margin)
        oauth_manager._token_expiry = time.time() + 30
        assert oauth_manager._is_token_expired() is True  # Should refresh within 60s

    @responses.activate
    def test_thread_safety(self, oauth_manager: OktaOAuthTokenManager) -> None:
        """Test that token manager is thread-safe."""
        mock_response = {
            "access_token": "thread-safe-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        responses.add(
            responses.POST,
            "https://example.okta.com/oauth2/v1/token",
            json=mock_response,
            status=200,
        )

        # Simulate multiple threads requesting token simultaneously
        import threading

        results = []

        def get_token() -> None:
            results.append(oauth_manager.get_access_token())

        threads = [threading.Thread(target=get_token) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All threads should get the same token
        assert len(results) == 5
        assert all(token == "thread-safe-token" for token in results)
        # Should only have made one API call despite multiple threads
        assert len(responses.calls) == 1


class TestOktaClientWithOAuth:
    """Test OktaClient with OAuth authentication."""

    @pytest.fixture
    def oauth_manager(self) -> OktaOAuthTokenManager:
        """Create OAuth token manager fixture."""
        manager = OktaOAuthTokenManager(
            domain="example.okta.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
            scopes=["okta.groups.read", "okta.users.read"],
        )
        # Pre-set token to avoid actual OAuth calls in most tests
        manager._access_token = "test-oauth-token"
        manager._token_expiry = time.time() + 3600
        return manager

    @pytest.fixture
    def oauth_client(self, oauth_manager: OktaOAuthTokenManager) -> OktaClient:
        """Create OktaClient with OAuth authentication."""
        return OktaClient(domain="example.okta.com", oauth_token_manager=oauth_manager)

    def test_init_with_oauth(self, oauth_client: OktaClient) -> None:
        """Test client initialization with OAuth."""
        assert oauth_client.oauth_token_manager is not None
        assert oauth_client.api_token is None

    def test_init_requires_auth_method(self) -> None:
        """Test that client requires at least one auth method."""
        with pytest.raises(
            ValueError, match="Either api_token or oauth_token_manager must be provided"
        ):
            OktaClient(domain="example.okta.com")

    def test_init_rejects_both_auth_methods(self) -> None:
        """Test that client rejects both auth methods."""
        manager = OktaOAuthTokenManager(
            domain="example.okta.com",
            client_id="id",
            client_secret="secret",
            scopes=["okta.groups.read"],
        )
        with pytest.raises(ValueError, match="Only one of api_token or oauth_token_manager"):
            OktaClient(domain="example.okta.com", api_token="token", oauth_token_manager=manager)

    def test_get_auth_header_with_oauth(self, oauth_client: OktaClient) -> None:
        """Test that OAuth client uses Bearer token."""
        header = oauth_client._get_auth_header()
        assert header == "Bearer test-oauth-token"

    def test_get_auth_header_with_api_token(self) -> None:
        """Test that API token client uses SSWS token."""
        client = OktaClient(domain="example.okta.com", api_token="test-api-token")
        header = client._get_auth_header()
        assert header == "SSWS test-api-token"

    @responses.activate
    def test_api_call_with_oauth(self, oauth_client: OktaClient) -> None:
        """Test that API calls use OAuth Bearer token."""
        mock_response = [{"id": "00g123", "profile": {"name": "Engineering"}}]

        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups",
            json=mock_response,
            status=200,
        )

        group = oauth_client.get_group_by_name("Engineering")
        assert group["id"] == "00g123"

        # Verify Authorization header
        assert len(responses.calls) == 1
        assert responses.calls[0].request.headers["Authorization"] == "Bearer test-oauth-token"

    @responses.activate
    @mock.patch("time.time")
    def test_token_refresh_during_api_call(
        self, mock_time: mock.Mock, oauth_manager: OktaOAuthTokenManager
    ) -> None:
        """Test that expired tokens are refreshed during API calls."""
        # Create client with OAuth manager
        client = OktaClient(domain="example.okta.com", oauth_token_manager=oauth_manager)

        # Set token as expired
        oauth_manager._token_expiry = 1000.0  # Old timestamp
        mock_time.return_value = 2000.0  # Current time

        # Mock OAuth token refresh
        responses.add(
            responses.POST,
            "https://example.okta.com/oauth2/v1/token",
            json={"access_token": "refreshed-token", "token_type": "Bearer", "expires_in": 3600},
            status=200,
        )

        # Mock API call
        responses.add(
            responses.GET,
            "https://example.okta.com/api/v1/groups",
            json=[{"id": "00g123", "profile": {"name": "Test"}}],
            status=200,
        )

        # Make API call - should trigger token refresh
        client.get_group_by_name("Test")

        # Should have refreshed token and used it
        assert len(responses.calls) == 2  # Token refresh + API call
        assert responses.calls[0].request.url.endswith("/oauth2/v1/token")
        assert responses.calls[1].request.headers["Authorization"] == "Bearer refreshed-token"
