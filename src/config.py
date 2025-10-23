"""Configuration management for GOTS."""
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv


@dataclass
class OktaOAuthConfig:
    """Okta OAuth 2.0 configuration."""

    client_id: str
    scopes: List[str]
    client_secret: Optional[str] = None  # For client_secret_basic/post methods
    private_key_path: Optional[str] = None  # For private_key_jwt method
    token_endpoint_auth_method: str = "client_secret_basic"  # or "private_key_jwt"

    def __post_init__(self) -> None:
        """Validate OAuth configuration."""
        if not self.client_id:
            raise ValueError("OAuth client_id is required")
        if not self.scopes:
            raise ValueError("At least one OAuth scope is required")

        # Validate auth method and required credentials
        valid_methods = ["client_secret_basic", "client_secret_post", "private_key_jwt"]
        if self.token_endpoint_auth_method not in valid_methods:
            raise ValueError(
                f"token_endpoint_auth_method must be one of {valid_methods}, "
                f"got: {self.token_endpoint_auth_method}"
            )

        if self.token_endpoint_auth_method in ["client_secret_basic", "client_secret_post"]:
            if not self.client_secret:
                raise ValueError(f"client_secret is required for {self.token_endpoint_auth_method}")
        elif self.token_endpoint_auth_method == "private_key_jwt":
            if not self.private_key_path:
                raise ValueError("private_key_path is required for private_key_jwt")


@dataclass
class OktaConfig:
    """Okta API configuration."""

    domain: str
    auth_method: str = "api_token"  # "api_token" or "oauth"
    api_token: Optional[str] = None
    oauth: Optional[OktaOAuthConfig] = None

    def __post_init__(self) -> None:
        """Validate Okta configuration."""
        if not self.domain:
            raise ValueError("Okta domain is required")

        # Remove protocol if present
        self.domain = self.domain.replace("https://", "").replace("http://", "")

        # Validate auth method
        valid_auth_methods = ["api_token", "oauth"]
        if self.auth_method not in valid_auth_methods:
            raise ValueError(
                f"auth_method must be one of {valid_auth_methods}, got: {self.auth_method}"
            )

        # Validate credentials based on auth method
        if self.auth_method == "api_token":
            if not self.api_token:
                raise ValueError("Okta API token is required when using api_token auth method")
        elif self.auth_method == "oauth":
            if not self.oauth:
                raise ValueError("OAuth configuration is required when using oauth auth method")


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
    grafana_role: str = "Viewer"  # Admin, Editor, or Viewer

    def __post_init__(self) -> None:
        """Validate group mapping."""
        if not self.okta_group:
            raise ValueError("Okta group name is required")
        if not self.grafana_team:
            raise ValueError("Grafana team name is required")

        # Validate and normalize role
        valid_roles = ["Admin", "Editor", "Viewer"]
        if self.grafana_role not in valid_roles:
            raise ValueError(f"grafana_role must be one of {valid_roles}, got: {self.grafana_role}")


@dataclass
class SyncConfig:
    """Synchronization configuration."""

    interval_seconds: int = 300
    dry_run: bool = False
    mappings: Optional[List[GroupMapping]] = None
    admin_groups: Optional[List[str]] = None  # Okta groups for Grafana admin privileges

    def __post_init__(self) -> None:
        """Validate sync configuration."""
        if self.mappings is None:
            self.mappings = []
        if self.admin_groups is None:
            self.admin_groups = []
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
class MetricsConfig:
    """Metrics server configuration."""

    enabled: bool = False
    port: int = 8000
    host: str = "0.0.0.0"

    def __post_init__(self) -> None:
        """Validate metrics configuration."""
        if self.port < 1 or self.port > 65535:
            raise ValueError("Metrics port must be between 1 and 65535")


@dataclass
class Config:
    """Main configuration class."""

    okta: OktaConfig
    grafana: GrafanaConfig
    sync: SyncConfig
    logging: Optional[LoggingConfig] = None
    metrics: Optional[MetricsConfig] = None

    def __post_init__(self) -> None:
        """Set defaults."""
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.metrics is None:
            self.metrics = MetricsConfig()


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
        okta_dict = config_dict.get("okta", {})
        auth_method = os.getenv("OKTA_AUTH_METHOD", okta_dict.get("auth_method", "api_token"))

        # Build OAuth config if using oauth auth method
        oauth_config = None
        if auth_method == "oauth":
            oauth_dict = okta_dict.get("oauth", {})
            client_id = os.getenv("OKTA_CLIENT_ID", oauth_dict.get("client_id", ""))
            client_secret = os.getenv("OKTA_CLIENT_SECRET", oauth_dict.get("client_secret", ""))
            private_key_path = os.getenv(
                "OKTA_PRIVATE_KEY_PATH", oauth_dict.get("private_key_path", "")
            )
            token_endpoint_auth_method = os.getenv(
                "OKTA_TOKEN_ENDPOINT_AUTH_METHOD",
                oauth_dict.get("token_endpoint_auth_method", "client_secret_basic"),
            )

            # Parse scopes - can be comma-separated string from env or list from YAML
            scopes_env = os.getenv("OKTA_SCOPES", "")
            if scopes_env:
                scopes = [s.strip() for s in scopes_env.split(",")]
            else:
                scopes = oauth_dict.get("scopes", [])

            # Convert empty strings to None for optional fields
            client_secret = client_secret if client_secret else None
            private_key_path = private_key_path if private_key_path else None

            oauth_config = OktaOAuthConfig(
                client_id=client_id,
                client_secret=client_secret,
                private_key_path=private_key_path,
                token_endpoint_auth_method=token_endpoint_auth_method,
                scopes=scopes,
            )

        # Get api_token, convert empty string to None for optional field
        api_token_value = os.getenv("OKTA_API_TOKEN", okta_dict.get("api_token", ""))
        api_token = api_token_value if api_token_value else None

        okta_config = OktaConfig(
            domain=os.getenv("OKTA_DOMAIN", okta_dict.get("domain", "")),
            auth_method=auth_method,
            api_token=api_token,
            oauth=oauth_config,
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
                GroupMapping(
                    okta_group=mapping["okta_group"],
                    grafana_team=mapping["grafana_team"],
                    grafana_role=mapping.get("grafana_role", "Viewer"),
                )
            )

        admin_groups = sync_dict.get("admin_groups", [])

        sync_config = SyncConfig(
            interval_seconds=interval, dry_run=dry_run, mappings=mappings, admin_groups=admin_groups
        )

        # Logging config
        logging_dict = config_dict.get("logging", {})
        logging_config = LoggingConfig(
            level=os.getenv("LOG_LEVEL", logging_dict.get("level", "INFO")),
            format=os.getenv("LOG_FORMAT", logging_dict.get("format", "json")),
        )

        # Metrics config
        metrics_dict = config_dict.get("metrics", {})
        metrics_enabled = (
            os.getenv("METRICS_ENABLED", str(metrics_dict.get("enabled", False))).lower() == "true"
        )
        metrics_port = int(os.getenv("METRICS_PORT", metrics_dict.get("port", 8000)))
        metrics_host = os.getenv("METRICS_HOST", metrics_dict.get("host", "0.0.0.0"))
        metrics_config = MetricsConfig(
            enabled=metrics_enabled, port=metrics_port, host=metrics_host
        )

        return Config(
            okta=okta_config,
            grafana=grafana_config,
            sync=sync_config,
            logging=logging_config,
            metrics=metrics_config,
        )
