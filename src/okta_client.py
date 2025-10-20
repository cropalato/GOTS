"""Okta API client for group and user management."""
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class OktaAPIError(Exception):
    """Base exception for Okta API errors."""


class OktaAuthenticationError(OktaAPIError):
    """Raised when authentication fails."""


class OktaNotFoundError(OktaAPIError):
    """Raised when a resource is not found."""


class OktaRateLimitError(OktaAPIError):
    """Raised when rate limit is exceeded."""


class OktaClient:
    """Client for interacting with Okta API."""

    def __init__(self, domain: str, api_token: str) -> None:
        """
        Initialize Okta client.

        Args:
            domain: Okta domain (e.g., 'example.okta.com')
            api_token: Okta API token
        """
        self.domain = domain.replace("https://", "").replace("http://", "")
        self.base_url = f"https://{self.domain}"
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _handle_response(self, response: requests.Response) -> None:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object

        Raises:
            OktaAuthenticationError: If authentication fails (401)
            OktaNotFoundError: If resource not found (404)
            OktaRateLimitError: If rate limit exceeded (429)
            OktaAPIError: For other API errors
        """
        if response.status_code == 200:
            return

        if response.status_code == 401:
            logger.error("Okta authentication failed - check API token")
            raise OktaAuthenticationError("Authentication failed - invalid API token")

        if response.status_code == 404:
            logger.warning("Okta resource not found: %s", response.url)
            raise OktaNotFoundError(f"Resource not found: {response.url}")

        if response.status_code == 429:
            reset_time = response.headers.get("X-Rate-Limit-Reset", "unknown")
            logger.warning("Okta rate limit exceeded. Resets at: %s", reset_time)
            raise OktaRateLimitError(f"Rate limit exceeded. Resets at: {reset_time}")

        logger.error("Okta API error: %s - %s", response.status_code, response.text)
        raise OktaAPIError(f"API error {response.status_code}: {response.text}")

    @retry(
        retry=retry_if_exception_type((requests.RequestException, OktaRateLimitError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
    )
    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make GET request to Okta API with retry logic.

        Args:
            endpoint: API endpoint (e.g., '/api/v1/groups')
            params: Query parameters

        Returns:
            HTTP response object
        """
        url = urljoin(self.base_url, endpoint)
        logger.debug("GET %s params=%s", url, params)

        response = self.session.get(url, params=params, timeout=30)
        self._handle_response(response)

        # Log rate limit status
        limit = response.headers.get("X-Rate-Limit-Limit")
        remaining = response.headers.get("X-Rate-Limit-Remaining")
        if limit and remaining:
            logger.debug("Rate limit: %s/%s remaining", remaining, limit)

        return response

    def _get_paginated(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all results from a paginated endpoint.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            List of all results
        """
        all_results: List[Dict[str, Any]] = []
        current_url = endpoint
        current_params = params or {}

        while True:
            response = self._get(current_url, current_params)
            results = response.json()
            all_results.extend(results)

            # Check for next page in Link header
            link_header = response.headers.get("Link", "")
            next_link = self._parse_next_link(link_header)

            if not next_link:
                break

            # Parse next URL
            parsed = urlparse(next_link)
            current_url = parsed.path
            current_params = parse_qs(parsed.query)
            # Convert lists to single values
            current_params = {
                k: v[0] if isinstance(v, list) and len(v) == 1 else v
                for k, v in current_params.items()
            }

        logger.info("Retrieved %d total results from %s", len(all_results), endpoint)
        return all_results

    @staticmethod
    def _parse_next_link(link_header: str) -> Optional[str]:
        """
        Parse 'next' link from Link header.

        Args:
            link_header: Link header value

        Returns:
            Next page URL or None
        """
        if not link_header:
            return None

        # Link header format: <url>; rel="next", <url>; rel="self"
        links = link_header.split(",")
        for link in links:
            parts = link.split(";")
            if len(parts) == 2:
                url = parts[0].strip().strip("<>")
                rel = parts[1].strip()
                if 'rel="next"' in rel:
                    return url
        return None

    def get_group_by_name(self, group_name: str) -> Dict[str, Any]:
        """
        Get Okta group by name.

        Args:
            group_name: Name of the group to find

        Returns:
            Group object with 'id', 'profile' (with 'name'), etc.

        Raises:
            OktaNotFoundError: If group not found
            OktaAPIError: For other API errors
        """
        logger.info("Searching for Okta group: %s", group_name)

        response = self._get("/api/v1/groups", params={"q": group_name})
        groups = response.json()

        # Find exact match (search is case-insensitive partial match)
        for group in groups:
            if group.get("profile", {}).get("name") == group_name:
                logger.info("Found Okta group: %s (ID: %s)", group_name, group["id"])
                return group  # type: ignore[no-any-return]

        logger.warning("Okta group not found: %s", group_name)
        raise OktaNotFoundError(f"Group not found: {group_name}")

    def get_group_members(self, group_id: str) -> List[Dict[str, Any]]:
        """
        Get all members of an Okta group.

        Args:
            group_id: Okta group ID

        Returns:
            List of user objects with 'id', 'profile' (with 'email', 'firstName', 'lastName'), etc.
        """
        logger.info("Fetching members for Okta group ID: %s", group_id)

        endpoint = f"/api/v1/groups/{group_id}/users"
        members = self._get_paginated(endpoint)

        logger.info("Found %d members in group %s", len(members), group_id)
        return members

    def get_group_members_by_name(self, group_name: str) -> List[Dict[str, Any]]:
        """
        Get all members of an Okta group by group name.

        Convenience method that combines get_group_by_name and get_group_members.

        Args:
            group_name: Name of the Okta group

        Returns:
            List of user objects

        Raises:
            OktaNotFoundError: If group not found
        """
        group = self.get_group_by_name(group_name)
        return self.get_group_members(group["id"])
