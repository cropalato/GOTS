"""Main application entry point and scheduler."""

import json
import logging
import signal
import sys
import time
from typing import NoReturn, Optional

import schedule

from src.config import ConfigLoader
from src.grafana_client import GrafanaClient
from src.metrics_server import MetricsCollector, MetricsServer
from src.okta_client import OktaClient, OktaOAuthTokenManager
from src.sync_service import SyncService

# Global flag for graceful shutdown
shutdown_requested = False
# Global metrics server for graceful shutdown
metrics_server: Optional[MetricsServer] = None


def setup_logging(log_level: str, log_format: str) -> None:
    """
    Setup logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
    """
    level = getattr(logging, log_level.upper())

    if log_format == "json":
        # JSON format for structured logging
        class JsonFormatter(logging.Formatter):
            """Custom JSON formatter for structured logging."""

            def format(self, record: logging.LogRecord) -> str:
                """Format log record as JSON."""
                log_data = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_data)

        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logging.root.handlers = [handler]
    else:
        # Text format for human-readable logging
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    logging.root.setLevel(level)


def signal_handler(signum: int, _frame) -> None:  # type: ignore[no-untyped-def]
    """
    Handle shutdown signals gracefully.

    Args:
        signum: Signal number
        _frame: Current stack frame (unused)
    """
    global shutdown_requested  # pylint: disable=global-statement

    if shutdown_requested:
        # Second signal - force exit immediately
        logging.warning("Forcing immediate shutdown...")
        sys.exit(1)

    signal_name = signal.Signals(signum).name
    logging.info("Received signal %s, initiating graceful shutdown...", signal_name)
    shutdown_requested = True

    # Raise KeyboardInterrupt to break out of blocking operations
    raise KeyboardInterrupt()


def print_banner(dry_run: bool) -> None:
    """
    Print startup banner.

    Args:
        dry_run: Whether running in dry-run mode
    """
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   Grafana-Okta Team Sync (GOTS)                           ║
║   Automated team synchronization service                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)
    if dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made")
        print()


def run_sync(
    sync_service: SyncService,
    okta_group: str,
    grafana_team: str,
    grafana_role: str,
    desired_roles: dict,  # type: ignore[type-arg]
) -> None:
    """
    Run a single sync operation.

    Args:
        sync_service: Initialized SyncService instance
        okta_group: Okta group name
        grafana_team: Grafana team name
        grafana_role: Grafana organization role (Admin, Editor, or Viewer)
        desired_roles: Shared dict tracking desired roles across all groups

    Raises:
        KeyboardInterrupt: Re-raised to allow graceful shutdown
    """
    try:
        logging.info("Starting sync: %s -> %s (role: %s)", okta_group, grafana_team, grafana_role)
        metrics = sync_service.sync_group_to_team(
            okta_group, grafana_team, grafana_role, desired_roles
        )
        logging.info(
            "Sync completed: +%d users, -%d users, %d errors, %.2fs",
            metrics.users_added,
            metrics.users_removed,
            metrics.errors,
            metrics.duration_seconds,
        )
    except KeyboardInterrupt:
        logging.info("Sync interrupted by user")
        raise
    except Exception as e:  # pylint: disable=broad-except
        logging.error(
            "Sync failed for %s -> %s: %s",
            okta_group,
            grafana_team,
            str(e),
            exc_info=True,
        )


def main() -> NoReturn:
    """Main application entry point."""
    # Parse command line arguments for config path
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"

    try:
        # Load configuration
        logging.info("Loading configuration from: %s", config_path)
        config = ConfigLoader.load(config_path)

        # Setup logging with config
        # Config.__post_init__ ensures logging is never None
        assert config.logging is not None
        setup_logging(config.logging.level, config.logging.format)

        # Print banner
        print_banner(config.sync.dry_run)

        # Log configuration summary
        logging.info("Configuration loaded successfully")
        logging.info("Okta domain: %s", config.okta.domain)
        logging.info("Grafana URL: %s", config.grafana.url)
        logging.info("Sync interval: %d seconds", config.sync.interval_seconds)
        logging.info("Dry run mode: %s", config.sync.dry_run)
        # SyncConfig.__post_init__ ensures mappings is never None
        assert config.sync.mappings is not None
        logging.info("Number of mappings: %d", len(config.sync.mappings))
        if config.sync.admin_groups:
            logging.info("Admin groups: %s", ", ".join(config.sync.admin_groups))
        else:
            logging.info("Admin groups: None configured")

        # Initialize API clients
        logging.info("Initializing API clients...")
        logging.info("Okta auth method: %s", config.okta.auth_method)

        # Create OktaClient based on auth method
        if config.okta.auth_method == "oauth":
            assert config.okta.oauth is not None
            oauth_token_manager = OktaOAuthTokenManager(
                domain=config.okta.domain,
                client_id=config.okta.oauth.client_id,
                scopes=config.okta.oauth.scopes,
                client_secret=config.okta.oauth.client_secret,
                private_key_path=config.okta.oauth.private_key_path,
                token_endpoint_auth_method=config.okta.oauth.token_endpoint_auth_method,
            )
            okta_client = OktaClient(domain=config.okta.domain, oauth_token_manager=oauth_token_manager)
        else:  # api_token
            assert config.okta.api_token is not None
            okta_client = OktaClient(domain=config.okta.domain, api_token=config.okta.api_token)

        grafana_client = GrafanaClient(config.grafana.url, config.grafana.api_key)

        # Initialize metrics if enabled
        metrics_collector = None
        global metrics_server  # pylint: disable=global-statement
        assert config.metrics is not None
        if config.metrics.enabled:
            logging.info("Metrics enabled, starting metrics server...")
            metrics_collector = MetricsCollector()
            metrics_server = MetricsServer(
                metrics_collector, port=config.metrics.port, host=config.metrics.host
            )
            metrics_server.start()
        else:
            logging.info("Metrics disabled")

        # Initialize sync service
        sync_service = SyncService(
            okta_client=okta_client,
            grafana_client=grafana_client,
            dry_run=config.sync.dry_run,
            metrics_collector=metrics_collector,
        )

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Define sync job
        def sync_job() -> None:
            """Run all configured sync operations."""
            # SyncConfig.__post_init__ ensures mappings is never None
            assert config.sync.mappings is not None

            # Track desired roles across all group mappings
            desired_roles: dict = {}  # type: ignore[type-arg]

            # Run all group syncs
            for mapping in config.sync.mappings:
                if shutdown_requested:
                    break
                run_sync(
                    sync_service,
                    mapping.okta_group,
                    mapping.grafana_team,
                    mapping.grafana_role,
                    desired_roles,
                )

            # Update all user roles based on highest permission across all groups
            if not shutdown_requested and desired_roles:
                logging.info("Applying role updates for %d users...", len(desired_roles))
                roles_updated = sync_service.update_user_roles(desired_roles)
                logging.info("Role update completed: %d roles updated", roles_updated)

            # Sync Grafana admin privileges based on admin groups
            if not shutdown_requested and config.sync.admin_groups:
                logging.info("Syncing Grafana admin privileges...")
                admins_updated = sync_service.sync_admin_privileges(config.sync.admin_groups)
                logging.info("Admin privilege sync completed: %d permissions updated", admins_updated)

        # Schedule periodic sync
        schedule.every(config.sync.interval_seconds).seconds.do(sync_job)

        # Run initial sync immediately
        logging.info("Running initial sync...")
        sync_job()

        # Main loop
        logging.info(
            "Entering main loop. Syncing every %d seconds. Press Ctrl+C to stop.",
            config.sync.interval_seconds,
        )

        while not shutdown_requested:
            schedule.run_pending()
            time.sleep(1)

        # Graceful shutdown
        if metrics_server:
            metrics_server.stop()
        logging.info("Shutdown complete. Goodbye!")
        sys.exit(0)

    except FileNotFoundError as e:
        logging.error("Configuration file not found: %s", e)
        sys.exit(1)
    except ValueError as e:
        logging.error("Configuration error: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Interrupted by user. Shutting down...")
        sys.exit(0)
    except Exception as e:  # pylint: disable=broad-except
        logging.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
