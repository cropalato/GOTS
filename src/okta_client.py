"""Okta API client for group and user management."""
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

import jwt
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


class OktaOAuthTokenManager:
    """Manages OAuth 2.0 access token lifecycle for Okta API."""

    def __init__(
        self,
        domain: str,
        client_id: str,
        scopes: List[str],
        client_secret: Optional[str] = None,
        private_key_path: Optional[str] = None,
        token_endpoint_auth_method: str = "client_secret_basic",
    ) -> None:
        """
        Initialize OAuth token manager.

        Args:
            domain: Okta domain (e.g., 'example.okta.com')
            client_id: OAuth client ID
            scopes: List of OAuth scopes (e.g., ['okta.groups.read', 'okta.users.read'])
            client_secret: OAuth client secret (for client_secret_* methods)
            private_key_path: Path to private key PEM file (for private_key_jwt)
            token_endpoint_auth_method: Authentication method (client_secret_basic, private_key_jwt)
        """
        self.domain = domain.replace("https://", "").replace("http://", "")
        self.token_url = f"https://{self.domain}/oauth2/v1/token"
        self.client_id = client_id
        self.client_secret = client_secret
        self.private_key_path = private_key_path
        self.token_endpoint_auth_method = token_endpoint_auth_method
        self.scopes = scopes
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        self._lock = threading.Lock()
        self._private_key: Optional[str] = None

        # Load private key if using private_key_jwt
        if self.token_endpoint_auth_method == "private_key_jwt":
            self._load_private_key()

    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid OAuth access token

        Raises:
            OktaAuthenticationError: If token acquisition fails
        """
        with self._lock:
            if self._access_token and not self._is_token_expired():
                logger.debug("Using cached OAuth token")
                return self._access_token

            logger.info("Acquiring new OAuth token from Okta")
            return self._refresh_token()

    def _is_token_expired(self) -> bool:
        """
        Check if the current token is expired or about to expire.

        Returns:
            True if token is expired or will expire in the next 60 seconds
        """
        if self._token_expiry is None:
            return True

        # Refresh token 60 seconds before expiry to avoid race conditions
        return time.time() >= (self._token_expiry - 60)

    def _load_private_key(self) -> None:
        """Load private key from file for private_key_jwt authentication."""
        if not self.private_key_path:
            raise ValueError("private_key_path is required for private_key_jwt authentication")

        key_path = Path(self.private_key_path)
        if not key_path.exists():
            raise FileNotFoundError(f"Private key file not found: {self.private_key_path}")

        with open(key_path, "r", encoding="utf-8") as f:
            self._private_key = f.read()

        logger.info("Private key loaded from %s", self.private_key_path)

    def _create_client_assertion(self) -> str:
        """
        Create a JWT client assertion for private_key_jwt authentication.

        Returns:
            Signed JWT assertion string

        Raises:
            ValueError: If private key is not loaded
        """
        if not self._private_key:
            raise ValueError("Private key not loaded")

        now = int(time.time())
        claims = {
            "iss": self.client_id,  # Issuer: the client_id
            "sub": self.client_id,  # Subject: the client_id
            "aud": self.token_url,  # Audience: the token endpoint
            "exp": now + 300,  # Expiration: 5 minutes from now
            "iat": now,  # Issued at: now
            "jti": str(uuid.uuid4()),  # JWT ID: unique identifier
        }

        # Sign the JWT with RS256 algorithm and include kid in header
        headers = {
            "kid": "eadE2YW30tucVX8l61Re-cNXAfeQVxq9U_LJ6SXpW00",  # Key ID from Okta JWKSet
            "alg": "RS256",
            "typ": "JWT",
        }
        assertion = jwt.encode(claims, self._private_key, algorithm="RS256", headers=headers)

        logger.debug("Created client assertion JWT for %s", self.client_id)
        logger.debug("JWT claims: %s", claims)
        return assertion

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
    )
    def _refresh_token(self) -> str:
        """
        Exchange client credentials for a new access token.

        Returns:
            New OAuth access token

        Raises:
            OktaAuthenticationError: If authentication fails
            OktaAPIError: For other API errors
        """
        payload: Dict[str, str] = {
            "grant_type": "client_credentials",
            "scope": " ".join(self.scopes),
        }

        headers = {"Accept": "application/json"}
        auth: Optional[Tuple[str, str]] = None

        # Choose authentication method based on configuration
        if self.token_endpoint_auth_method == "private_key_jwt":
            # Use client_assertion for private_key_jwt
            client_assertion = self._create_client_assertion()
            payload[
                "client_assertion_type"
            ] = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
            payload["client_assertion"] = client_assertion
            payload["client_id"] = self.client_id
            logger.debug("Using private_key_jwt authentication")
            logger.debug("Token endpoint: %s", self.token_url)
            logger.debug("Client ID: %s", self.client_id)
            # Decode JWT to log claims without exposing the signature
            decoded = jwt.decode(client_assertion, options={"verify_signature": False})
            logger.debug("JWT assertion claims: %s", decoded)
        elif self.token_endpoint_auth_method == "client_secret_post":
            # Send client credentials in POST body
            payload["client_id"] = self.client_id
            if self.client_secret is None:
                raise ValueError("client_secret is required for client_secret_post")
            payload["client_secret"] = self.client_secret
            logger.debug("Using client_secret_post authentication")
        else:  # client_secret_basic (default)
            # Send client credentials via HTTP Basic Auth
            if self.client_secret is None:
                raise ValueError("client_secret is required for client_secret_basic")
            auth = (self.client_id, self.client_secret)
            logger.debug("Using client_secret_basic authentication")

        logger.debug("Requesting OAuth token from %s", self.token_url)

        try:
            response = requests.post(
                self.token_url,
                auth=auth,
                data=payload,
                headers=headers,
                timeout=30,
            )
        except requests.RequestException as e:
            logger.error("Failed to connect to Okta OAuth endpoint: %s", e)
            raise

        if response.status_code == 200:
            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
            self._token_expiry = time.time() + expires_in

            # Decode token to see what scopes were granted (for debugging)
            try:
                decoded_token = jwt.decode(self._access_token, options={"verify_signature": False})
                granted_scopes = decoded_token.get("scp", [])
                logger.info("OAuth token acquired successfully, expires in %d seconds", expires_in)
                logger.info("Granted scopes: %s", granted_scopes)
                logger.debug("Full token payload: %s", decoded_token)
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("Could not decode access token: %s", e)
                logger.info("OAuth token acquired successfully, expires in %d seconds", expires_in)

            return self._access_token

        if response.status_code == 401:
            logger.error("OAuth authentication failed - invalid client credentials")
            logger.error("Response body: %s", response.text)
            logger.error("Response headers: %s", dict(response.headers))
            try:
                error_data = response.json()
                logger.error("Error details: %s", error_data)
            except Exception:  # pylint: disable=broad-except
                pass
            raise OktaAuthenticationError(
                "OAuth authentication failed - invalid client credentials"
            )

        logger.error("OAuth token request failed: %s - %s", response.status_code, response.text)
        raise OktaAPIError(f"OAuth token request failed {response.status_code}: {response.text}")


class OktaClient:
    """Client for interacting with Okta API."""

    def __init__(
        self,
        domain: str,
        api_token: Optional[str] = None,
        oauth_token_manager: Optional[OktaOAuthTokenManager] = None,
    ) -> None:
        """
        Initialize Okta client.

        Args:
            domain: Okta domain (e.g., 'example.okta.com')
            api_token: Okta API token (for api_token auth method)
            oauth_token_manager: OAuth token manager (for oauth auth method)

        Raises:
            ValueError: If neither or both auth methods are provided
        """
        if api_token is None and oauth_token_manager is None:
            raise ValueError("Either api_token or oauth_token_manager must be provided")
        if api_token is not None and oauth_token_manager is not None:
            raise ValueError("Only one of api_token or oauth_token_manager should be provided")

        self.domain = domain.replace("https://", "").replace("http://", "")
        self.base_url = f"https://{self.domain}"
        self.api_token = api_token
        self.oauth_token_manager = oauth_token_manager
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _get_auth_header(self) -> str:
        """
        Get the appropriate Authorization header value.

        Returns:
            Authorization header value

        Raises:
            OktaAuthenticationError: If OAuth token acquisition fails
        """
        if self.oauth_token_manager:
            token = self.oauth_token_manager.get_access_token()
            # Debug: Log token format (first 20 chars to verify it's a JWT)
            logger.debug("Access token format: %s...", token[:20] if len(token) > 20 else token)
            return f"Bearer {token}"
        return f"SSWS {self.api_token}"

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

        # Get fresh auth header (important for OAuth token refresh)
        auth_header = self._get_auth_header()
        headers = {"Authorization": auth_header}

        # Log auth type (but not the actual token)
        auth_type = "OAuth Bearer" if self.oauth_token_manager else "SSWS API Token"
        logger.debug("Using auth type: %s", auth_type)

        response = self.session.get(url, params=params, headers=headers, timeout=30)
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
