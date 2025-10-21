"""Tests for configuration module."""
import os
import tempfile
from pathlib import Path

import pytest

from src.config import (
    Config,
    ConfigLoader,
    GrafanaConfig,
    GroupMapping,
    LoggingConfig,
    MetricsConfig,
    OktaConfig,
    SyncConfig,
)


class TestOktaConfig:
    """Test OktaConfig dataclass."""

    def test_valid_config(self) -> None:
        """Test valid Okta configuration."""
        config = OktaConfig(domain="example.okta.com", api_token="test-token")
        assert config.domain == "example.okta.com"
        assert config.api_token == "test-token"

    def test_removes_https_from_domain(self) -> None:
        """Test that https:// is stripped from domain."""
        config = OktaConfig(domain="https://example.okta.com", api_token="token")
        assert config.domain == "example.okta.com"

    def test_removes_http_from_domain(self) -> None:
        """Test that http:// is stripped from domain."""
        config = OktaConfig(domain="http://example.okta.com", api_token="token")
        assert config.domain == "example.okta.com"

    def test_missing_domain(self) -> None:
        """Test error when domain is missing."""
        with pytest.raises(ValueError, match="Okta domain is required"):
            OktaConfig(domain="", api_token="token")

    def test_missing_token(self) -> None:
        """Test error when API token is missing."""
        with pytest.raises(ValueError, match="Okta API token is required"):
            OktaConfig(domain="example.okta.com", api_token="")


class TestGrafanaConfig:
    """Test GrafanaConfig dataclass."""

    def test_valid_config(self) -> None:
        """Test valid Grafana configuration."""
        config = GrafanaConfig(url="https://grafana.example.com", api_key="test-key")
        assert config.url == "https://grafana.example.com"
        assert config.api_key == "test-key"

    def test_adds_https_to_url(self) -> None:
        """Test that https:// is added if missing."""
        config = GrafanaConfig(url="grafana.example.com", api_key="key")
        assert config.url == "https://grafana.example.com"

    def test_preserves_http_url(self) -> None:
        """Test that http:// URLs are preserved."""
        config = GrafanaConfig(url="http://localhost:3000", api_key="key")
        assert config.url == "http://localhost:3000"

    def test_preserves_https_url(self) -> None:
        """Test that https:// URLs are preserved."""
        config = GrafanaConfig(url="https://grafana.example.com", api_key="key")
        assert config.url == "https://grafana.example.com"

    def test_missing_url(self) -> None:
        """Test error when URL is missing."""
        with pytest.raises(ValueError, match="Grafana URL is required"):
            GrafanaConfig(url="", api_key="key")

    def test_missing_api_key(self) -> None:
        """Test error when API key is missing."""
        with pytest.raises(ValueError, match="Grafana API key is required"):
            GrafanaConfig(url="https://grafana.example.com", api_key="")


class TestGroupMapping:
    """Test GroupMapping dataclass."""

    def test_valid_mapping(self) -> None:
        """Test valid group mapping."""
        mapping = GroupMapping(okta_group="Engineering", grafana_team="Engineers")
        assert mapping.okta_group == "Engineering"
        assert mapping.grafana_team == "Engineers"

    def test_missing_okta_group(self) -> None:
        """Test error when Okta group is missing."""
        with pytest.raises(ValueError, match="Okta group name is required"):
            GroupMapping(okta_group="", grafana_team="Team")

    def test_missing_grafana_team(self) -> None:
        """Test error when Grafana team is missing."""
        with pytest.raises(ValueError, match="Grafana team name is required"):
            GroupMapping(okta_group="Group", grafana_team="")


class TestSyncConfig:
    """Test SyncConfig dataclass."""

    def test_valid_config(self) -> None:
        """Test valid sync configuration."""
        mappings = [GroupMapping(okta_group="Group1", grafana_team="Team1")]
        config = SyncConfig(interval_seconds=300, dry_run=False, mappings=mappings)
        assert config.interval_seconds == 300
        assert config.dry_run is False
        assert len(config.mappings) == 1

    def test_default_values(self) -> None:
        """Test default sync configuration values."""
        mappings = [GroupMapping(okta_group="Group1", grafana_team="Team1")]
        config = SyncConfig(mappings=mappings)
        assert config.interval_seconds == 300
        assert config.dry_run is False

    def test_interval_too_short(self) -> None:
        """Test error when interval is less than 60 seconds."""
        mappings = [GroupMapping(okta_group="Group1", grafana_team="Team1")]
        with pytest.raises(ValueError, match="at least 60 seconds"):
            SyncConfig(interval_seconds=30, mappings=mappings)

    def test_no_mappings(self) -> None:
        """Test error when no mappings provided."""
        with pytest.raises(ValueError, match="At least one group mapping is required"):
            SyncConfig(interval_seconds=300, mappings=[])

    def test_none_mappings(self) -> None:
        """Test error when mappings is None."""
        with pytest.raises(ValueError, match="At least one group mapping is required"):
            SyncConfig(interval_seconds=300)

    def test_admin_groups(self) -> None:
        """Test admin groups configuration."""
        mappings = [GroupMapping(okta_group="Group1", grafana_team="Team1")]
        admin_groups = ["Grafana-Admins", "Platform-Team"]
        config = SyncConfig(mappings=mappings, admin_groups=admin_groups)
        assert config.admin_groups == admin_groups
        assert len(config.admin_groups) == 2

    def test_admin_groups_default_empty(self) -> None:
        """Test that admin_groups defaults to empty list."""
        mappings = [GroupMapping(okta_group="Group1", grafana_team="Team1")]
        config = SyncConfig(mappings=mappings)
        assert config.admin_groups == []


class TestLoggingConfig:
    """Test LoggingConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default logging configuration."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "json"

    def test_valid_config(self) -> None:
        """Test valid logging configuration."""
        config = LoggingConfig(level="DEBUG", format="text")
        assert config.level == "DEBUG"
        assert config.format == "text"

    def test_normalizes_level_case(self) -> None:
        """Test that log level is normalized to uppercase."""
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"

    def test_normalizes_format_case(self) -> None:
        """Test that log format is normalized to lowercase."""
        config = LoggingConfig(format="JSON")
        assert config.format == "json"

    def test_invalid_level(self) -> None:
        """Test error with invalid log level."""
        with pytest.raises(ValueError, match="Log level must be one of"):
            LoggingConfig(level="INVALID")

    def test_invalid_format(self) -> None:
        """Test error with invalid log format."""
        with pytest.raises(ValueError, match="Log format must be one of"):
            LoggingConfig(format="xml")

    def test_all_valid_levels(self) -> None:
        """Test all valid log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level


class TestMetricsConfig:
    """Test MetricsConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default metrics configuration."""
        config = MetricsConfig()
        assert config.enabled is False
        assert config.port == 8000
        assert config.host == "0.0.0.0"

    def test_valid_config(self) -> None:
        """Test valid metrics configuration."""
        config = MetricsConfig(enabled=True, port=9090, host="127.0.0.1")
        assert config.enabled is True
        assert config.port == 9090
        assert config.host == "127.0.0.1"

    def test_invalid_port_too_low(self) -> None:
        """Test error with port number too low."""
        with pytest.raises(ValueError, match="Metrics port must be between 1 and 65535"):
            MetricsConfig(port=0)

    def test_invalid_port_too_high(self) -> None:
        """Test error with port number too high."""
        with pytest.raises(ValueError, match="Metrics port must be between 1 and 65535"):
            MetricsConfig(port=65536)

    def test_valid_port_boundaries(self) -> None:
        """Test valid port boundaries."""
        config1 = MetricsConfig(port=1)
        assert config1.port == 1
        config2 = MetricsConfig(port=65535)
        assert config2.port == 65535


class TestConfig:
    """Test Config dataclass."""

    def test_valid_config(self) -> None:
        """Test valid configuration."""
        okta = OktaConfig(domain="example.okta.com", api_token="token")
        grafana = GrafanaConfig(url="https://grafana.example.com", api_key="key")
        mappings = [GroupMapping(okta_group="Group1", grafana_team="Team1")]
        sync = SyncConfig(mappings=mappings)

        config = Config(okta=okta, grafana=grafana, sync=sync)
        assert config.okta.domain == "example.okta.com"
        assert config.grafana.url == "https://grafana.example.com"
        assert len(config.sync.mappings) == 1

    def test_default_logging_config(self) -> None:
        """Test that logging config is set to default if not provided."""
        okta = OktaConfig(domain="example.okta.com", api_token="token")
        grafana = GrafanaConfig(url="https://grafana.example.com", api_key="key")
        mappings = [GroupMapping(okta_group="Group1", grafana_team="Team1")]
        sync = SyncConfig(mappings=mappings)

        config = Config(okta=okta, grafana=grafana, sync=sync)
        assert config.logging is not None
        assert config.logging.level == "INFO"
        assert config.logging.format == "json"

    def test_default_metrics_config(self) -> None:
        """Test that metrics config is set to default if not provided."""
        okta = OktaConfig(domain="example.okta.com", api_token="token")
        grafana = GrafanaConfig(url="https://grafana.example.com", api_key="key")
        mappings = [GroupMapping(okta_group="Group1", grafana_team="Team1")]
        sync = SyncConfig(mappings=mappings)

        config = Config(okta=okta, grafana=grafana, sync=sync)
        assert config.metrics is not None
        assert config.metrics.enabled is False
        assert config.metrics.port == 8000
        assert config.metrics.host == "0.0.0.0"


class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_load_from_yaml(self) -> None:
        """Test loading configuration from YAML file."""
        yaml_content = """
okta:
  domain: example.okta.com
  api_token: test-token

grafana:
  url: https://grafana.example.com
  api_key: test-key

sync:
  interval_seconds: 300
  dry_run: false
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"

logging:
  level: DEBUG
  format: text
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert config.okta.domain == "example.okta.com"
            assert config.okta.api_token == "test-token"
            assert config.grafana.url == "https://grafana.example.com"
            assert config.grafana.api_key == "test-key"
            assert config.sync.interval_seconds == 300
            assert config.sync.dry_run is False
            assert len(config.sync.mappings) == 1
            assert config.sync.mappings[0].okta_group == "Group1"
            assert config.sync.mappings[0].grafana_team == "Team1"
            assert config.logging.level == "DEBUG"
            assert config.logging.format == "text"
        finally:
            Path(config_path).unlink()

    def test_expand_env_vars(self) -> None:
        """Test environment variable expansion."""
        os.environ["TEST_OKTA_DOMAIN"] = "env.okta.com"
        os.environ["TEST_OKTA_TOKEN"] = "env-token"

        yaml_content = """
okta:
  domain: ${TEST_OKTA_DOMAIN}
  api_token: ${TEST_OKTA_TOKEN}

grafana:
  url: https://grafana.example.com
  api_key: test-key

sync:
  interval_seconds: 300
  dry_run: false
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert config.okta.domain == "env.okta.com"
            assert config.okta.api_token == "env-token"
        finally:
            Path(config_path).unlink()
            del os.environ["TEST_OKTA_DOMAIN"]
            del os.environ["TEST_OKTA_TOKEN"]

    def test_env_vars_override_yaml(self) -> None:
        """Test that environment variables override YAML config."""
        os.environ["OKTA_DOMAIN"] = "override.okta.com"
        os.environ["GRAFANA_API_KEY"] = "override-key"

        yaml_content = """
okta:
  domain: original.okta.com
  api_token: test-token

grafana:
  url: https://grafana.example.com
  api_key: original-key

sync:
  interval_seconds: 300
  dry_run: false
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert config.okta.domain == "override.okta.com"
            assert config.grafana.api_key == "override-key"
        finally:
            Path(config_path).unlink()
            del os.environ["OKTA_DOMAIN"]
            del os.environ["GRAFANA_API_KEY"]

    def test_missing_config_file(self) -> None:
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load("/nonexistent/config.yaml")

    def test_invalid_yaml(self) -> None:
        """Test error with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name

        try:
            with pytest.raises(Exception):  # yaml.YAMLError
                ConfigLoader.load(config_path)
        finally:
            Path(config_path).unlink()

    def test_multiple_mappings(self) -> None:
        """Test loading multiple group mappings."""
        yaml_content = """
okta:
  domain: example.okta.com
  api_token: test-token

grafana:
  url: https://grafana.example.com
  api_key: test-key

sync:
  interval_seconds: 300
  dry_run: false
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"
    - okta_group: "Group2"
      grafana_team: "Team2"
    - okta_group: "Group3"
      grafana_team: "Team3"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert len(config.sync.mappings) == 3
            assert config.sync.mappings[0].okta_group == "Group1"
            assert config.sync.mappings[1].okta_group == "Group2"
            assert config.sync.mappings[2].okta_group == "Group3"
        finally:
            Path(config_path).unlink()

    def test_dry_run_from_env(self) -> None:
        """Test dry_run configuration from environment variable."""
        os.environ["SYNC_DRY_RUN"] = "true"

        yaml_content = """
okta:
  domain: example.okta.com
  api_token: test-token

grafana:
  url: https://grafana.example.com
  api_key: test-key

sync:
  interval_seconds: 300
  dry_run: false
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert config.sync.dry_run is True
        finally:
            Path(config_path).unlink()
            del os.environ["SYNC_DRY_RUN"]

    def test_interval_from_env(self) -> None:
        """Test interval configuration from environment variable."""
        os.environ["SYNC_INTERVAL_SECONDS"] = "600"

        yaml_content = """
okta:
  domain: example.okta.com
  api_token: test-token

grafana:
  url: https://grafana.example.com
  api_key: test-key

sync:
  interval_seconds: 300
  dry_run: false
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert config.sync.interval_seconds == 600
        finally:
            Path(config_path).unlink()
            del os.environ["SYNC_INTERVAL_SECONDS"]

    def test_metrics_from_yaml(self) -> None:
        """Test loading metrics configuration from YAML."""
        yaml_content = """
okta:
  domain: example.okta.com
  api_token: test-token

grafana:
  url: https://grafana.example.com
  api_key: test-key

sync:
  interval_seconds: 300
  dry_run: false
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"

metrics:
  enabled: true
  port: 9090
  host: 127.0.0.1
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert config.metrics is not None
            assert config.metrics.enabled is True
            assert config.metrics.port == 9090
            assert config.metrics.host == "127.0.0.1"
        finally:
            Path(config_path).unlink()

    def test_metrics_from_env(self) -> None:
        """Test loading metrics configuration from environment variables."""
        os.environ["METRICS_ENABLED"] = "true"
        os.environ["METRICS_PORT"] = "9999"
        os.environ["METRICS_HOST"] = "localhost"

        yaml_content = """
okta:
  domain: example.okta.com
  api_token: test-token

grafana:
  url: https://grafana.example.com
  api_key: test-key

sync:
  interval_seconds: 300
  dry_run: false
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert config.metrics.enabled is True
            assert config.metrics.port == 9999
            assert config.metrics.host == "localhost"
        finally:
            Path(config_path).unlink()
            del os.environ["METRICS_ENABLED"]
            del os.environ["METRICS_PORT"]
            del os.environ["METRICS_HOST"]

    def test_admin_groups_from_yaml(self) -> None:
        """Test loading admin groups from YAML."""
        yaml_content = """
okta:
  domain: example.okta.com
  api_token: test-token

grafana:
  url: https://grafana.example.com
  api_key: test-key

sync:
  interval_seconds: 300
  dry_run: false
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"
  admin_groups:
    - "Grafana-Admins"
    - "Platform-Team"
    - "SRE"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert config.sync.admin_groups is not None
            assert len(config.sync.admin_groups) == 3
            assert "Grafana-Admins" in config.sync.admin_groups
            assert "Platform-Team" in config.sync.admin_groups
            assert "SRE" in config.sync.admin_groups
        finally:
            Path(config_path).unlink()

    def test_admin_groups_empty_when_not_specified(self) -> None:
        """Test that admin_groups defaults to empty list when not in YAML."""
        yaml_content = """
okta:
  domain: example.okta.com
  api_token: test-token

grafana:
  url: https://grafana.example.com
  api_key: test-key

sync:
  interval_seconds: 300
  dry_run: false
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert config.sync.admin_groups == []
        finally:
            Path(config_path).unlink()
