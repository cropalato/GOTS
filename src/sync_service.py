"""Sync service for synchronizing Okta groups to Grafana teams."""
import logging
import time
from dataclasses import dataclass
from typing import Set

from src.grafana_client import GrafanaClient
from src.okta_client import OktaClient

logger = logging.getLogger(__name__)


@dataclass
class SyncMetrics:
    """Metrics for a sync operation."""

    users_added: int = 0
    users_removed: int = 0
    errors: int = 0
    duration_seconds: float = 0.0


class SyncService:
    """Service for synchronizing Okta groups to Grafana teams."""

    def __init__(
        self, okta_client: OktaClient, grafana_client: GrafanaClient, dry_run: bool = False
    ) -> None:
        """
        Initialize sync service.

        Args:
            okta_client: Okta API client
            grafana_client: Grafana API client
            dry_run: If True, log actions without executing them
        """
        self.okta_client = okta_client
        self.grafana_client = grafana_client
        self.dry_run = dry_run

    def sync_group_to_team(  # pylint: disable=too-many-locals
        self, okta_group_name: str, grafana_team_name: str
    ) -> SyncMetrics:
        """
        Sync an Okta group to a Grafana team.

        Args:
            okta_group_name: Name of Okta group
            grafana_team_name: Name of Grafana team

        Returns:
            SyncMetrics with operation results
        """
        start_time = time.time()
        metrics = SyncMetrics()

        logger.info("Starting sync: %s -> %s", okta_group_name, grafana_team_name)

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

            # Calculate diff
            to_add = okta_emails - grafana_emails
            to_remove = grafana_emails - okta_emails

            logger.info("Sync diff: %d to add, %d to remove", len(to_add), len(to_remove))

            # Add users
            for email in to_add:
                try:
                    if self.dry_run:
                        logger.info(
                            "[DRY RUN] Would add user %s to team %s",
                            email,
                            grafana_team_name,
                        )
                    else:
                        # Get or create user
                        user = self.grafana_client.get_or_create_user(email)
                        user_id = user["id"]
                        # Add user to team
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

        return metrics
