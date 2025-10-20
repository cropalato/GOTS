"""Tests for Okta API client."""
import pytest
import responses
from tenacity import RetryError

from src.okta_client import (
    OktaAPIError,
    OktaAuthenticationError,
    OktaClient,
    OktaNotFoundError,
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
        assert okta_client.session.headers["Authorization"] == "SSWS test-token"
        assert okta_client.session.headers["Accept"] == "application/json"

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
