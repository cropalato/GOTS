"""Grafana API client for team and user management."""

import logging
from typing import Any, Dict, List, Optional

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class GrafanaAPIError(Exception):
    """Base exception for Grafana API errors."""


class GrafanaAuthenticationError(GrafanaAPIError):
    """Raised when authentication fails."""


class GrafanaNotFoundError(GrafanaAPIError):
    """Raised when a resource is not found."""


class GrafanaConflictError(GrafanaAPIError):
    """Raised when a resource already exists."""


class GrafanaClient:
    """Client for interacting with Grafana API."""

    def __init__(self, url: str, api_key: str) -> None:
        """
        Initialize Grafana client.

        Args:
            url: Grafana URL (e.g., 'https://grafana.example.com')
            api_key: Grafana API key (service account token)
        """
        self.base_url = url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _handle_response(self, response: requests.Response) -> None:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object

        Raises:
            GrafanaAuthenticationError: If authentication fails (401, 403)
            GrafanaNotFoundError: If resource not found (404)
            GrafanaConflictError: If resource already exists (409)
            GrafanaAPIError: For other API errors
        """
        if response.status_code in (200, 201):
            return

        if response.status_code in (401, 403):
            logger.error("Grafana authentication failed - check API key")
            raise GrafanaAuthenticationError("Authentication failed - invalid API key")

        if response.status_code == 404:
            logger.warning("Grafana resource not found: %s", response.url)
            raise GrafanaNotFoundError(f"Resource not found: {response.url}")

        if response.status_code == 409:
            logger.warning("Grafana resource conflict: %s", response.text)
            raise GrafanaConflictError(f"Resource already exists: {response.text}")

        logger.error("Grafana API error: %s - %s", response.status_code, response.text)
        raise GrafanaAPIError(f"API error {response.status_code}: {response.text}")

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
    )
    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make GET request to Grafana API with retry logic.

        Args:
            endpoint: API endpoint (e.g., '/api/teams')
            params: Query parameters

        Returns:
            HTTP response object
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug("GET %s params=%s", url, params)

        response = self.session.get(url, params=params, timeout=30)
        self._handle_response(response)
        return response

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
    )
    def _post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make POST request to Grafana API with retry logic.

        Args:
            endpoint: API endpoint
            json_data: JSON body data

        Returns:
            HTTP response object
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug("POST %s data=%s", url, json_data)

        response = self.session.post(url, json=json_data, timeout=30)
        self._handle_response(response)
        return response

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
    )
    def _patch(
        self, endpoint: str, json_data: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """
        Make PATCH request to Grafana API with retry logic.

        Args:
            endpoint: API endpoint
            json_data: JSON body data

        Returns:
            HTTP response object
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug("PATCH %s data=%s", url, json_data)

        response = self.session.patch(url, json=json_data, timeout=30)
        self._handle_response(response)
        return response

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
    )
    def _put(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make PUT request to Grafana API with retry logic.

        Args:
            endpoint: API endpoint
            json_data: JSON body data

        Returns:
            HTTP response object
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug("PUT %s data=%s", url, json_data)

        response = self.session.put(url, json=json_data, timeout=30)
        self._handle_response(response)
        return response

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
    )
    def _delete(self, endpoint: str) -> requests.Response:
        """
        Make DELETE request to Grafana API with retry logic.

        Args:
            endpoint: API endpoint

        Returns:
            HTTP response object
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug("DELETE %s", url)

        response = self.session.delete(url, timeout=30)
        self._handle_response(response)
        return response

    def get_team_by_name(self, team_name: str) -> Optional[Dict[str, Any]]:
        """
        Get Grafana team by name.

        Args:
            team_name: Name of the team to find

        Returns:
            Team object with 'id', 'name', 'email', etc., or None if not found
        """
        logger.debug("Searching for Grafana team: %s", team_name)

        response = self._get("/api/teams/search", params={"name": team_name})
        teams = response.json()

        # Search returns partial matches, find exact match
        if isinstance(teams, dict) and "teams" in teams:
            teams_list = teams["teams"]
        else:
            teams_list = teams

        for team in teams_list:
            if team.get("name") == team_name:
                logger.info("Found Grafana team: %s (ID: %s)", team_name, team["id"])
                return team  # type: ignore[no-any-return]

        logger.info("Grafana team not found: %s", team_name)
        return None

    def create_team(self, team_name: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new Grafana team.

        Args:
            team_name: Name of the team to create
            email: Optional team email

        Returns:
            Created team object with 'teamId', 'message'

        Raises:
            GrafanaConflictError: If team already exists
        """
        logger.info("Creating Grafana team: %s", team_name)

        data: Dict[str, Any] = {"name": team_name}
        if email:
            data["email"] = email

        response = self._post("/api/teams", json_data=data)
        result = response.json()

        logger.info("Created Grafana team: %s (ID: %s)", team_name, result.get("teamId"))
        return result  # type: ignore[no-any-return]

    def get_or_create_team(self, team_name: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        Get existing team or create new one.

        Args:
            team_name: Name of the team
            email: Optional team email (used only when creating)

        Returns:
            Team object with 'id', 'name', etc.
        """
        existing_team = self.get_team_by_name(team_name)
        if existing_team:
            return existing_team

        _ = self.create_team(team_name, email)
        # Return format is different, fetch the team to get consistent format
        team = self.get_team_by_name(team_name)
        if team:
            return team
        raise GrafanaAPIError(f"Failed to retrieve created team: {team_name}")

    def get_team_members(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get all members of a Grafana team.

        Args:
            team_id: Grafana team ID

        Returns:
            List of team member objects with 'userId', 'email', 'login', etc.
        """
        logger.info("Fetching members for Grafana team ID: %s", team_id)

        response = self._get(f"/api/teams/{team_id}/members")
        members = response.json()

        logger.info("Found %d members in team %s", len(members), team_id)
        return members  # type: ignore[no-any-return]

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get Grafana user by email.

        Uses /api/org/users endpoint instead of /api/users/lookup to work
        with service accounts that have org.users:read but not users:read permission.

        Args:
            email: User email address

        Returns:
            User object with 'id', 'email', 'login', etc., or None if not found
        """
        logger.debug("Searching for Grafana user: %s", email)

        try:
            # Use org/users endpoint which requires org.users:read permission
            # instead of /api/users/lookup which requires users:read
            response = self._get("/api/org/users")
            users = response.json()

            # Search for user by email
            for user in users:
                if user.get("email", "").lower() == email.lower():
                    logger.debug("Found Grafana user: %s (ID: %s)", email, user["userId"])
                    # Normalize the response to match the expected format
                    # org/users returns 'userId' while users/lookup returns 'id'
                    normalized_user = {
                        "id": user["userId"],
                        "email": user["email"],
                        "login": user["login"],
                        "name": user.get("name", ""),
                        "orgId": user.get("orgId"),
                        "role": user.get("role", "Viewer"),
                        "isDisabled": user.get("isDisabled", False),
                    }
                    return normalized_user  # type: ignore[no-any-return]

            logger.debug("Grafana user not found: %s", email)
            return None
        except (GrafanaNotFoundError, GrafanaAuthenticationError):
            logger.debug("Grafana user not found: %s", email)
            return None

    def create_user(
        self, email: str, login: Optional[str] = None, name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Grafana user.

        Args:
            email: User email address
            login: User login (defaults to email)
            name: User display name (defaults to email)

        Returns:
            Created user object with 'id', 'message'

        Raises:
            GrafanaConflictError: If user already exists
        """
        logger.info("Creating Grafana user: %s", email)

        data = {
            "email": email,
            "login": login or email,
            "name": name or email,
        }

        response = self._post("/api/admin/users", json_data=data)
        result = response.json()

        logger.info("Created Grafana user: %s (ID: %s)", email, result.get("id"))
        return result  # type: ignore[no-any-return]

    def get_or_create_user(
        self, email: str, login: Optional[str] = None, name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get existing user or create new one.

        Args:
            email: User email address
            login: User login (used only when creating)
            name: User display name (used only when creating)

        Returns:
            User object with 'id', 'email', 'login', etc.
        """
        existing_user = self.get_user_by_email(email)
        if existing_user:
            return existing_user

        _ = self.create_user(email, login, name)
        # Return format is different, fetch the user to get consistent format
        user = self.get_user_by_email(email)
        if user:
            return user
        raise GrafanaAPIError(f"Failed to retrieve created user: {email}")

    def add_user_to_team(self, team_id: int, user_id: int) -> Dict[str, Any]:
        """
        Add user to a Grafana team.

        Args:
            team_id: Grafana team ID
            user_id: Grafana user ID

        Returns:
            Result object with 'message'
        """
        logger.info("Adding user %s to team %s", user_id, team_id)

        data = {"userId": user_id}
        response = self._post(f"/api/teams/{team_id}/members", json_data=data)
        result = response.json()

        logger.info("Added user %s to team %s", user_id, team_id)
        return result  # type: ignore[no-any-return]

    def remove_user_from_team(self, team_id: int, user_id: int) -> Dict[str, Any]:
        """
        Remove user from a Grafana team.

        Args:
            team_id: Grafana team ID
            user_id: Grafana user ID

        Returns:
            Result object with 'message'
        """
        logger.info("Removing user %s from team %s", user_id, team_id)

        response = self._delete(f"/api/teams/{team_id}/members/{user_id}")
        result = response.json()

        logger.info("Removed user %s from team %s", user_id, team_id)
        return result  # type: ignore[no-any-return]

    def update_user_role(self, user_id: int, role: str) -> Dict[str, Any]:
        """
        Update user's organization role.

        Args:
            user_id: Grafana user ID
            role: New role (Admin, Editor, or Viewer)

        Returns:
            Result object with 'message'

        Raises:
            ValueError: If role is invalid
        """
        valid_roles = ["Admin", "Editor", "Viewer"]
        if role not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}, got: {role}")

        logger.info("Updating user %s role to %s", user_id, role)

        data = {"role": role}
        response = self._patch(f"/api/org/users/{user_id}", json_data=data)
        result = response.json()

        logger.info("Updated user %s role to %s", user_id, role)
        return result  # type: ignore[no-any-return]

    def set_user_admin_permission(self, user_id: int, is_admin: bool) -> Dict[str, Any]:
        """
        Set user's Grafana admin permission.

        This grants or revokes full Grafana admin privileges (isGrafanaAdmin flag),
        which is different from organization roles (Admin, Editor, Viewer).

        Args:
            user_id: Grafana user ID
            is_admin: True to grant admin privileges, False to revoke

        Returns:
            Result object with 'message'
        """
        logger.info("Setting Grafana admin permission for user %s to %s", user_id, is_admin)

        data = {"isGrafanaAdmin": is_admin}
        response = self._put(f"/api/admin/users/{user_id}/permissions", json_data=data)
        result = response.json()

        logger.info("Set Grafana admin permission for user %s to %s", user_id, is_admin)
        return result  # type: ignore[no-any-return]
