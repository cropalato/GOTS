"""Sync service for synchronizing Okta groups to Grafana teams."""

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from src.grafana_client import GrafanaClient
from src.okta_client import OktaClient

if TYPE_CHECKING:
    from src.metrics_server import MetricsCollector

logger = logging.getLogger(__name__)

# Role hierarchy: Admin > Editor > Viewer
ROLE_HIERARCHY = {"Admin": 3, "Editor": 2, "Viewer": 1}


def get_highest_role(role1: str, role2: str) -> str:
    """
    Compare two roles and return the one with highest permission.

    Args:
        role1: First role (Admin, Editor, or Viewer)
        role2: Second role (Admin, Editor, or Viewer)

    Returns:
        The role with higher permission level
    """
    return role1 if ROLE_HIERARCHY.get(role1, 0) > ROLE_HIERARCHY.get(role2, 0) else role2


@dataclass
class SyncMetrics:
    """Metrics for a sync operation."""

    users_added: int = 0
    users_removed: int = 0
    roles_updated: int = 0
    errors: int = 0
    duration_seconds: float = 0.0


class SyncService:
    """Service for synchronizing Okta groups to Grafana teams."""

    def __init__(
        self,
        okta_client: OktaClient,
        grafana_client: GrafanaClient,
        dry_run: bool = False,
        metrics_collector: Optional["MetricsCollector"] = None,
    ) -> None:
        """
        Initialize sync service.

        Args:
            okta_client: Okta API client
            grafana_client: Grafana API client
            dry_run: If True, log actions without executing them
            metrics_collector: Optional metrics collector for monitoring
        """
        self.okta_client = okta_client
        self.grafana_client = grafana_client
        self.dry_run = dry_run
        self.metrics_collector = metrics_collector

    def sync_group_to_team(  # pylint: disable=too-many-locals
        self,
        okta_group_name: str,
        grafana_team_name: str,
        grafana_role: str = "Viewer",
        desired_roles: Optional[Dict[str, str]] = None,
    ) -> SyncMetrics:
        """
        Sync an Okta group to a Grafana team.

        Args:
            okta_group_name: Name of Okta group
            grafana_team_name: Name of Grafana team
            grafana_role: Grafana organization role for members (Admin, Editor, or Viewer)
            desired_roles: Dict to track desired roles for users across all groups

        Returns:
            SyncMetrics with operation results
        """
        if desired_roles is None:
            desired_roles = {}
        start_time = time.time()
        metrics = SyncMetrics()

        logger.info("Starting sync: %s -> %s", okta_group_name, grafana_team_name)

        # Record metrics start
        if self.metrics_collector:
            self.metrics_collector.record_sync_start(okta_group_name, grafana_team_name)

        try:
            # Fetch Okta group members
            okta_members = self.okta_client.get_group_members_by_name(okta_group_name)
            okta_emails: Set[str] = {m["profile"]["email"].lower() for m in okta_members}
            logger.info(
                "Found %d members in Okta group '%s'",
                len(okta_emails),
                okta_group_name,
            )

            # Get or create Grafana team
            team = self.grafana_client.get_or_create_team(grafana_team_name)
            team_id = team["id"]

            # Fetch Grafana team members
            grafana_members = self.grafana_client.get_team_members(team_id)
            grafana_emails: Set[str] = {m["email"].lower() for m in grafana_members}
            logger.info(
                "Found %d members in Grafana team '%s'",
                len(grafana_emails),
                grafana_team_name,
            )

            # Track desired roles for all Okta group members
            for email in okta_emails:
                # Track the highest role this user should have
                current_desired = desired_roles.get(email, "Viewer")
                desired_roles[email] = get_highest_role(current_desired, grafana_role)

            # Calculate diff
            to_add = okta_emails - grafana_emails
            to_remove = grafana_emails - okta_emails

            logger.info("Sync diff: %d to add, %d to remove", len(to_add), len(to_remove))

            # Add users
            for email in to_add:
                try:
                    # Get user (don't create - users should be auto-provisioned via Okta)
                    user = self.grafana_client.get_user_by_email(email)
                    if user is None:
                        logger.debug(
                            "Skipping user %s - not found in Grafana. "
                            "User must login via Okta first.",
                            email,
                        )
                        continue

                    if self.dry_run:
                        logger.info(
                            "[DRY RUN] Would add user %s to team %s",
                            email,
                            grafana_team_name,
                        )
                    else:
                        user_id = user["id"]
                        # Add user to team (role will be updated later)
                        self.grafana_client.add_user_to_team(team_id, user_id)
                        logger.info("Added user %s to team %s", email, grafana_team_name)
                    metrics.users_added += 1
                except Exception as e:  # pylint: disable=broad-except
                    logger.error("Failed to add user %s: %s", email, e)
                    metrics.errors += 1

            # Remove users
            for email in to_remove:
                try:
                    # Find user ID
                    member = next(m for m in grafana_members if m["email"].lower() == email)
                    user_id = member["userId"]

                    if self.dry_run:
                        logger.info(
                            "[DRY RUN] Would remove user %s from team %s",
                            email,
                            grafana_team_name,
                        )
                    else:
                        self.grafana_client.remove_user_from_team(team_id, user_id)
                        logger.info("Removed user %s from team %s", email, grafana_team_name)
                    metrics.users_removed += 1
                except Exception as e:  # pylint: disable=broad-except
                    logger.error("Failed to remove user %s: %s", email, e)
                    metrics.errors += 1

        except Exception as e:
            logger.error("Sync failed for %s -> %s: %s", okta_group_name, grafana_team_name, e)
            metrics.errors += 1
            raise
        finally:
            metrics.duration_seconds = time.time() - start_time
            logger.info(
                "Sync completed in %.2fs: +%d, -%d, errors=%d",
                metrics.duration_seconds,
                metrics.users_added,
                metrics.users_removed,
                metrics.errors,
            )

            # Record metrics completion
            if self.metrics_collector:
                self.metrics_collector.record_sync_complete(
                    okta_group_name,
                    grafana_team_name,
                    metrics.duration_seconds,
                    metrics.users_added,
                    metrics.users_removed,
                    metrics.errors,
                )

        return metrics

    def update_user_roles(self, desired_roles: Dict[str, str]) -> int:
        """
        Update user roles based on desired roles collected from all group mappings.

        Ensures users get the highest role they're entitled to across all groups.

        Args:
            desired_roles: Dict mapping email to desired role

        Returns:
            Number of roles updated
        """
        roles_updated = 0

        logger.info("Checking roles for %d users", len(desired_roles))

        for email, desired_role in desired_roles.items():
            try:
                user = self.grafana_client.get_user_by_email(email)
                if user is None:
                    logger.debug("Skipping role update for %s - user not found", email)
                    continue

                current_role = user.get("role", "Viewer")
                user_id = user["id"]

                # Only update if roles differ
                if current_role != desired_role:
                    if self.dry_run:
                        logger.info(
                            "[DRY RUN] Would update role for %s: %s -> %s",
                            email,
                            current_role,
                            desired_role,
                        )
                    else:
                        self.grafana_client.update_user_role(user_id, desired_role)
                        logger.info(
                            "Updated role for %s: %s -> %s", email, current_role, desired_role
                        )
                    roles_updated += 1
                else:
                    logger.debug("User %s already has correct role: %s", email, current_role)

            except Exception as e:  # pylint: disable=broad-except
                logger.error("Failed to update role for %s: %s", email, e)

        logger.info("Role updates completed: %d roles updated", roles_updated)
        return roles_updated

    def sync_admin_privileges(self, admin_groups: List[str]) -> int:
        """
        Sync Grafana admin privileges based on Okta admin groups.

        Users who are members of any admin group will be granted Grafana admin privileges.
        Users who are not members of any admin group will have admin privileges revoked.

        Args:
            admin_groups: List of Okta group names whose members should be Grafana admins

        Returns:
            Number of admin permissions updated
        """
        if not admin_groups:
            logger.debug("No admin groups configured, skipping admin privilege sync")
            return 0

        admins_updated = 0
        admin_emails: Set[str] = set()

        logger.info("Syncing Grafana admin privileges from %d Okta groups", len(admin_groups))

        # Collect all users who should be admins from Okta groups
        for group_name in admin_groups:
            try:
                members = self.okta_client.get_group_members_by_name(group_name)
                group_emails = {m["profile"]["email"].lower() for m in members}
                admin_emails.update(group_emails)
                logger.info(
                    "Found %d members in Okta admin group '%s'", len(group_emails), group_name
                )
            except Exception as e:  # pylint: disable=broad-except
                logger.error("Failed to fetch members from Okta group %s: %s", group_name, e)

        logger.info("Total unique admin emails from Okta: %d", len(admin_emails))

        # Get all Grafana users and update admin privileges
        try:
            # Fetch all organization users
            response = self.grafana_client._get(
                "/api/org/users"
            )  # pylint: disable=protected-access
            all_users = response.json()

            logger.info("Checking admin privileges for %d Grafana users", len(all_users))

            for user in all_users:
                email = user.get("email", "").lower()
                user_id = user.get("userId")
                current_is_admin = user.get("isGrafanaAdmin", False)

                # Determine desired admin status
                should_be_admin = email in admin_emails

                # Only update if status needs to change
                if current_is_admin != should_be_admin:
                    try:
                        if self.dry_run:
                            logger.info(
                                "[DRY RUN] Would update Grafana admin for %s: %s -> %s",
                                email,
                                current_is_admin,
                                should_be_admin,
                            )
                        else:
                            self.grafana_client.set_user_admin_permission(user_id, should_be_admin)
                            logger.info(
                                "Updated Grafana admin for %s: %s -> %s",
                                email,
                                current_is_admin,
                                should_be_admin,
                            )
                        admins_updated += 1
                    except Exception as e:  # pylint: disable=broad-except
                        logger.error("Failed to update admin privilege for %s: %s", email, e)
                else:
                    logger.debug(
                        "User %s already has correct admin status: %s", email, current_is_admin
                    )

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to fetch Grafana users for admin sync: %s", e)

        logger.info("Admin privilege sync completed: %d permissions updated", admins_updated)
        return admins_updated
