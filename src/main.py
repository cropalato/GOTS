"""Main application entry point and scheduler."""
import json
import logging
import signal
import sys
import time
from typing import NoReturn

import schedule

from src.config import ConfigLoader
from src.grafana_client import GrafanaClient
from src.okta_client import OktaClient
from src.sync_service import SyncService

# Global flag for graceful shutdown
shutdown_requested = False


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
    signal_name = signal.Signals(signum).name
    logging.info("Received signal %s, initiating graceful shutdown...", signal_name)
    shutdown_requested = True


def print_banner(dry_run: bool) -> None:
    """
    Print startup banner.

    Args:
        dry_run: Whether running in dry-run mode
    """
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   Grafana-Okta Team Sync (GOTS)                          ║
║   Automated team synchronization service                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)
    if dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made")
        print()


def run_sync(sync_service: SyncService, okta_group: str, grafana_team: str) -> None:
    """
    Run a single sync operation.

    Args:
        sync_service: Initialized SyncService instance
        okta_group: Okta group name
        grafana_team: Grafana team name
    """
    try:
        logging.info("Starting sync: %s -> %s", okta_group, grafana_team)
        metrics = sync_service.sync_group_to_team(okta_group, grafana_team)
        logging.info(
            "Sync completed: +%d users, -%d users, %d errors, %.2fs",
            metrics.users_added,
            metrics.users_removed,
            metrics.errors,
            metrics.duration_seconds,
        )
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

        # Initialize API clients
        logging.info("Initializing API clients...")
        okta_client = OktaClient(config.okta.domain, config.okta.api_token)
        grafana_client = GrafanaClient(config.grafana.url, config.grafana.api_key)

        # Initialize sync service
        sync_service = SyncService(
            okta_client=okta_client,
            grafana_client=grafana_client,
            dry_run=config.sync.dry_run,
        )

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Define sync job
        def sync_job() -> None:
            """Run all configured sync operations."""
            # SyncConfig.__post_init__ ensures mappings is never None
            assert config.sync.mappings is not None
            for mapping in config.sync.mappings:
                if shutdown_requested:
                    break
                run_sync(sync_service, mapping.okta_group, mapping.grafana_team)

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
