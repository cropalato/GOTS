"""Configuration management for GOTS."""
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv


@dataclass
class OktaConfig:
    """Okta API configuration."""

    domain: str
    api_token: str

    def __post_init__(self) -> None:
        """Validate Okta configuration."""
        if not self.domain:
            raise ValueError("Okta domain is required")
        if not self.api_token:
            raise ValueError("Okta API token is required")
        # Remove protocol if present
        self.domain = self.domain.replace("https://", "").replace("http://", "")


@dataclass
class GrafanaConfig:
    """Grafana API configuration."""

    url: str
    api_key: str

    def __post_init__(self) -> None:
        """Validate Grafana configuration."""
        if not self.url:
            raise ValueError("Grafana URL is required")
        if not self.api_key:
            raise ValueError("Grafana API key is required")
        # Ensure URL has protocol
        if not self.url.startswith(("http://", "https://")):
            self.url = f"https://{self.url}"


@dataclass
class GroupMapping:
    """Mapping between Okta group and Grafana team."""

    okta_group: str
    grafana_team: str

    def __post_init__(self) -> None:
        """Validate group mapping."""
        if not self.okta_group:
            raise ValueError("Okta group name is required")
        if not self.grafana_team:
            raise ValueError("Grafana team name is required")


@dataclass
class SyncConfig:
    """Synchronization configuration."""

    interval_seconds: int = 300
    dry_run: bool = False
    mappings: Optional[List[GroupMapping]] = None

    def __post_init__(self) -> None:
        """Validate sync configuration."""
        if self.mappings is None:
            self.mappings = []
        if self.interval_seconds < 60:
            raise ValueError("Sync interval must be at least 60 seconds")
        if not self.mappings:
            raise ValueError("At least one group mapping is required")


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"  # json or text

    def __post_init__(self) -> None:
        """Validate logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        self.level = self.level.upper()

        valid_formats = ["json", "text"]
        if self.format.lower() not in valid_formats:
            raise ValueError(f"Log format must be one of: {valid_formats}")
        self.format = self.format.lower()


@dataclass
class Config:
    """Main configuration class."""

    okta: OktaConfig
    grafana: GrafanaConfig
    sync: SyncConfig
    logging: Optional[LoggingConfig] = None

    def __post_init__(self) -> None:
        """Set defaults."""
        if self.logging is None:
            self.logging = LoggingConfig()


class ConfigLoader:
    """Load configuration from YAML file and environment variables."""

    @staticmethod
    def _expand_env_vars(value: Any) -> Any:
        """
        Recursively expand environment variables in configuration values.

        Args:
            value: Configuration value to expand

        Returns:
            Value with environment variables expanded
        """
        if isinstance(value, str):
            # Replace ${VAR_NAME} with environment variable value
            pattern = r"\$\{([^}]+)\}"
            matches = re.findall(pattern, value)
            for match in matches:
                env_value = os.getenv(match, "")
                value = value.replace(f"${{{match}}}", env_value)
            return value
        if isinstance(value, dict):
            return {k: ConfigLoader._expand_env_vars(v) for k, v in value.items()}
        if isinstance(value, list):
            return [ConfigLoader._expand_env_vars(item) for item in value]
        return value

    @staticmethod
    def load(config_path: Optional[str] = None) -> Config:
        """
        Load configuration from YAML file and environment variables.

        Environment variables take precedence over file configuration.

        Args:
            config_path: Path to YAML configuration file. Defaults to ./config.yaml

        Returns:
            Config object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        # Load .env file if present
        load_dotenv()

        # Load YAML config if path provided
        config_dict: Dict[str, Any] = {}
        if config_path:
            path = Path(config_path)
            if not path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

            with open(path, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f) or {}

            # Expand environment variables in config
            config_dict = ConfigLoader._expand_env_vars(config_dict)

        # Override with environment variables
        okta_config = OktaConfig(
            domain=os.getenv("OKTA_DOMAIN", config_dict.get("okta", {}).get("domain", "")),
            api_token=os.getenv("OKTA_API_TOKEN", config_dict.get("okta", {}).get("api_token", "")),
        )

        grafana_config = GrafanaConfig(
            url=os.getenv("GRAFANA_URL", config_dict.get("grafana", {}).get("url", "")),
            api_key=os.getenv("GRAFANA_API_KEY", config_dict.get("grafana", {}).get("api_key", "")),
        )

        # Sync config
        sync_dict = config_dict.get("sync", {})
        interval = int(os.getenv("SYNC_INTERVAL_SECONDS", sync_dict.get("interval_seconds", 300)))
        dry_run = os.getenv("SYNC_DRY_RUN", str(sync_dict.get("dry_run", False))).lower() == "true"

        mappings = []
        for mapping in sync_dict.get("mappings", []):
            mappings.append(
                GroupMapping(okta_group=mapping["okta_group"], grafana_team=mapping["grafana_team"])
            )

        sync_config = SyncConfig(interval_seconds=interval, dry_run=dry_run, mappings=mappings)

        # Logging config
        logging_dict = config_dict.get("logging", {})
        logging_config = LoggingConfig(
            level=os.getenv("LOG_LEVEL", logging_dict.get("level", "INFO")),
            format=os.getenv("LOG_FORMAT", logging_dict.get("format", "json")),
        )

        return Config(
            okta=okta_config,
            grafana=grafana_config,
            sync=sync_config,
            logging=logging_config,
        )
