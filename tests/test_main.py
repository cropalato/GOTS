"""Tests for main application entry point."""
import json
import logging
import signal
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.config import Config, GrafanaConfig, GroupMapping, LoggingConfig, OktaConfig, SyncConfig
from src.main import print_banner, run_sync, setup_logging, signal_handler
from src.sync_service import SyncMetrics


@pytest.fixture
def mock_config() -> Config:
    """Create mock configuration."""
    return Config(
        okta=OktaConfig(domain="test.okta.com", api_token="test-token"),
        grafana=GrafanaConfig(url="https://grafana.test", api_key="test-key"),
        sync=SyncConfig(
            interval_seconds=60,
            dry_run=True,
            mappings=[
                GroupMapping(okta_group="Group1", grafana_team="Team1"),
                GroupMapping(okta_group="Group2", grafana_team="Team2"),
            ],
        ),
        logging=LoggingConfig(level="INFO", format="text"),
    )


@pytest.fixture
def mock_sync_service() -> Mock:
    """Create mock sync service."""
    service = MagicMock()
    service.sync_group_to_team.return_value = SyncMetrics(
        users_added=5, users_removed=2, errors=0, duration_seconds=1.5
    )
    return service


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_text_format(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test text format logging setup."""
        setup_logging("INFO", "text")

        # Log a test message
        logger = logging.getLogger("test")
        logger.info("Test message")

        # Verify log level
        assert logging.root.level == logging.INFO

        # Verify message was logged
        assert "Test message" in caplog.text

    def test_setup_logging_json_format(self, capsys: pytest.CaptureFixture) -> None:
        """Test JSON format logging setup."""
        setup_logging("DEBUG", "json")

        # Log a test message
        logger = logging.getLogger("test")
        logger.debug("Test JSON message")

        # Verify log level
        assert logging.root.level == logging.DEBUG

        # Verify JSON format in stderr
        captured = capsys.readouterr()
        assert "Test JSON message" in captured.err
        # Check it's valid JSON by attempting to parse a line
        lines = [line for line in captured.err.strip().split("\n") if line]
        if lines:
            log_entry = json.loads(lines[-1])
            assert log_entry["message"] == "Test JSON message"
            assert log_entry["level"] == "DEBUG"

    def test_setup_logging_different_levels(self) -> None:
        """Test different log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            setup_logging(level, "text")
            assert logging.root.level == getattr(logging, level)

    def test_json_formatter_with_exception(self, capsys: pytest.CaptureFixture) -> None:
        """Test JSON formatter handles exceptions."""
        setup_logging("ERROR", "json")

        logger = logging.getLogger("test")
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.error("Error occurred", exc_info=True)

        # Verify exception was logged in JSON format
        captured = capsys.readouterr()
        assert "Error occurred" in captured.err
        # Check exception is in JSON
        lines = [line for line in captured.err.strip().split("\n") if line]
        if lines:
            log_entry = json.loads(lines[-1])
            assert log_entry["message"] == "Error occurred"
            assert "exception" in log_entry
            assert "ValueError: Test error" in log_entry["exception"]


class TestSignalHandler:
    """Test signal_handler function."""

    def test_signal_handler_first_call(self) -> None:
        """Test signal handler on first call raises KeyboardInterrupt."""
        # Import shutdown_requested
        import src.main  # pylint: disable=import-outside-toplevel

        src.main.shutdown_requested = False

        # Call signal handler and expect KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            signal_handler(signal.SIGINT, None)

        # Verify shutdown was requested
        assert src.main.shutdown_requested is True

    def test_signal_handler_second_call(self) -> None:
        """Test signal handler on second call forces exit."""
        import src.main  # pylint: disable=import-outside-toplevel

        src.main.shutdown_requested = True

        # Call signal handler and expect sys.exit
        with pytest.raises(SystemExit) as exc_info:
            signal_handler(signal.SIGTERM, None)

        # Verify exit code
        assert exc_info.value.code == 1

    def test_signal_handler_logs_signal_name(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test signal handler logs signal name."""
        import src.main  # pylint: disable=import-outside-toplevel

        src.main.shutdown_requested = False

        with caplog.at_level(logging.INFO):
            with pytest.raises(KeyboardInterrupt):
                signal_handler(signal.SIGTERM, None)

        # Verify signal name was logged
        assert "SIGTERM" in caplog.text
        assert "graceful shutdown" in caplog.text


class TestPrintBanner:
    """Test print_banner function."""

    def test_print_banner_normal_mode(self, capsys: pytest.CaptureFixture) -> None:
        """Test banner in normal mode."""
        print_banner(dry_run=False)

        captured = capsys.readouterr()
        assert "Grafana-Okta Team Sync (GOTS)" in captured.out
        assert "DRY RUN MODE" not in captured.out

    def test_print_banner_dry_run_mode(self, capsys: pytest.CaptureFixture) -> None:
        """Test banner in dry-run mode."""
        print_banner(dry_run=True)

        captured = capsys.readouterr()
        assert "Grafana-Okta Team Sync (GOTS)" in captured.out
        assert "DRY RUN MODE" in captured.out


class TestRunSync:
    """Test run_sync function."""

    def test_run_sync_success(
        self, mock_sync_service: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test successful sync operation."""
        with caplog.at_level(logging.INFO):
            run_sync(mock_sync_service, "TestGroup", "TestTeam")

        # Verify sync was called
        mock_sync_service.sync_group_to_team.assert_called_once_with("TestGroup", "TestTeam")

        # Verify logging
        assert "Starting sync: TestGroup -> TestTeam" in caplog.text
        assert "Sync completed: +5 users, -2 users, 0 errors" in caplog.text

    def test_run_sync_keyboard_interrupt(
        self, mock_sync_service: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test sync interrupted by user."""
        mock_sync_service.sync_group_to_team.side_effect = KeyboardInterrupt()

        with caplog.at_level(logging.INFO):
            with pytest.raises(KeyboardInterrupt):
                run_sync(mock_sync_service, "TestGroup", "TestTeam")

        # Verify interrupt was logged
        assert "Sync interrupted by user" in caplog.text

    def test_run_sync_error(
        self, mock_sync_service: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test sync with error."""
        mock_sync_service.sync_group_to_team.side_effect = Exception("API error")

        with caplog.at_level(logging.ERROR):
            run_sync(mock_sync_service, "TestGroup", "TestTeam")

        # Verify error was logged
        assert "Sync failed for TestGroup -> TestTeam" in caplog.text
        assert "API error" in caplog.text


class TestMain:
    """Test main function."""

    @patch("src.main.SyncService")
    @patch("src.main.GrafanaClient")
    @patch("src.main.OktaClient")
    @patch("src.main.ConfigLoader.load")
    @patch("src.main.schedule")
    @patch("src.main.signal.signal")
    @patch("src.main.time.sleep")
    def test_main_successful_run(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        mock_sleep: Mock,
        mock_signal: Mock,
        mock_schedule: Mock,
        mock_config_load: Mock,
        mock_okta_client_class: Mock,
        mock_grafana_client_class: Mock,
        mock_sync_service_class: Mock,
        mock_config: Config,
    ) -> None:
        """Test main function successful run."""
        # Reset shutdown flag from previous tests
        import src.main  # pylint: disable=import-outside-toplevel

        src.main.shutdown_requested = False

        # Setup mocks
        mock_config_load.return_value = mock_config
        mock_okta_client = MagicMock()
        mock_grafana_client = MagicMock()
        mock_sync_service = MagicMock()

        mock_okta_client_class.return_value = mock_okta_client
        mock_grafana_client_class.return_value = mock_grafana_client
        mock_sync_service_class.return_value = mock_sync_service

        mock_sync_service.sync_group_to_team.return_value = SyncMetrics(
            users_added=2, users_removed=1, errors=0, duration_seconds=0.5
        )

        # Setup schedule mock
        mock_job = MagicMock()
        mock_schedule.every.return_value.seconds.do.return_value = mock_job
        mock_schedule.run_pending.return_value = None

        # Make sleep raise KeyboardInterrupt after first call to exit loop
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            from src.main import main  # pylint: disable=import-outside-toplevel

            main()

        # Verify exit code
        assert exc_info.value.code == 0

        # Verify clients were initialized
        mock_okta_client_class.assert_called_once_with("test.okta.com", "test-token")
        mock_grafana_client_class.assert_called_once_with("https://grafana.test", "test-key")

        # Verify sync service was created
        mock_sync_service_class.assert_called_once_with(
            okta_client=mock_okta_client,
            grafana_client=mock_grafana_client,
            dry_run=True,
        )

        # Verify signal handlers were registered
        assert mock_signal.call_count >= 2

        # Verify initial sync was run (2 mappings)
        assert mock_sync_service.sync_group_to_team.call_count >= 2

    @patch("src.main.ConfigLoader.load")
    def test_main_config_file_not_found(self, mock_config_load: Mock) -> None:
        """Test main with missing config file."""
        mock_config_load.side_effect = FileNotFoundError("Config not found")

        with pytest.raises(SystemExit) as exc_info:
            from src.main import main  # pylint: disable=import-outside-toplevel

            main()

        assert exc_info.value.code == 1

    @patch("src.main.ConfigLoader.load")
    def test_main_config_validation_error(self, mock_config_load: Mock) -> None:
        """Test main with invalid configuration."""
        mock_config_load.side_effect = ValueError("Invalid config")

        with pytest.raises(SystemExit) as exc_info:
            from src.main import main  # pylint: disable=import-outside-toplevel

            main()

        assert exc_info.value.code == 1

    @patch("src.main.SyncService")
    @patch("src.main.GrafanaClient")
    @patch("src.main.OktaClient")
    @patch("src.main.ConfigLoader.load")
    def test_main_fatal_error(  # pylint: disable=too-many-arguments
        self,
        mock_config_load: Mock,
        mock_okta_client_class: Mock,
        _mock_grafana_client_class: Mock,
        _mock_sync_service_class: Mock,
        mock_config: Config,
    ) -> None:
        """Test main with fatal error during execution."""
        mock_config_load.return_value = mock_config
        mock_okta_client_class.side_effect = Exception("Connection failed")

        with pytest.raises(SystemExit) as exc_info:
            from src.main import main  # pylint: disable=import-outside-toplevel

            main()

        assert exc_info.value.code == 1

    @patch("src.main.SyncService")
    @patch("src.main.GrafanaClient")
    @patch("src.main.OktaClient")
    @patch("src.main.ConfigLoader.load")
    @patch("src.main.schedule")
    @patch("src.main.signal.signal")
    @patch("src.main.time.sleep")
    def test_main_respects_shutdown_flag(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        _mock_sleep: Mock,
        _mock_signal: Mock,
        mock_schedule: Mock,
        mock_config_load: Mock,
        _mock_okta_client_class: Mock,
        _mock_grafana_client_class: Mock,
        mock_sync_service_class: Mock,
        mock_config: Config,
    ) -> None:
        """Test main respects shutdown_requested flag during sync."""
        import src.main  # pylint: disable=import-outside-toplevel

        # Setup mocks
        mock_config_load.return_value = mock_config
        mock_sync_service = MagicMock()
        mock_sync_service_class.return_value = mock_sync_service

        # Setup schedule
        mock_schedule.every.return_value.seconds.do.return_value = MagicMock()
        mock_schedule.run_pending.return_value = None

        # Simulate shutdown requested during initial sync
        def set_shutdown(*_args: object, **_kwargs: object) -> SyncMetrics:
            src.main.shutdown_requested = True
            return SyncMetrics()

        mock_sync_service.sync_group_to_team.side_effect = set_shutdown

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            from src.main import main  # pylint: disable=import-outside-toplevel

            main()

        # Verify graceful shutdown
        assert exc_info.value.code == 0

    @patch("sys.argv", ["main.py", "custom_config.yaml"])
    @patch("src.main.ConfigLoader.load")
    def test_main_custom_config_path(self, mock_config_load: Mock) -> None:
        """Test main with custom config file path from CLI."""
        mock_config_load.side_effect = FileNotFoundError()

        with pytest.raises(SystemExit):
            from src.main import main  # pylint: disable=import-outside-toplevel

            main()

        # Verify custom config path was used
        mock_config_load.assert_called_once_with("custom_config.yaml")
