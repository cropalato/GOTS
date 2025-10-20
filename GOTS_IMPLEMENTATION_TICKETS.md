# GOTS Implementation Tickets - Detailed Tasks

This document provides detailed, actionable subtasks for implementing the Grafana-Okta Team Sync (GOTS) service. Each ticket from `grafana-okta-team-sync.md` is expanded with specific tasks, file paths, code structure, and testing requirements.

---

## **TICKET-1: Project Scaffolding & Setup** ✅ COMPLETED

**Priority:** Critical
**Estimate:** 1.5 hours (updated from 30 min to include Poetry, GitHub Actions, CHANGELOG)
**Actual Time:** ~1.5 hours
**Status:** ✅ Completed

### Tasks Checklist

#### 1.1 Initialize Git Repository
- [ ] Run `git init` if not already initialized
- [ ] Create `.gitignore` file with Python-specific ignores:
  ```
  __pycache__/
  *.py[cod]
  *$py.class
  .pytest_cache/
  .coverage
  htmlcov/
  .env
  *.log
  .venv/
  venv/
  dist/
  build/
  *.egg-info/
  .mypy_cache/
  .ruff_cache/
  config.yaml
  ```

#### 1.2 Initialize Poetry Project
- [ ] Run `poetry init` to create `pyproject.toml`
  - Project name: `grafana-okta-team-sync`
  - Version: `0.1.0` (following semver)
  - Description: "Service to sync Okta group membership to Grafana teams"
  - Author: Your name/email
  - Python version: `^3.10`
  - License: Choose appropriate (e.g., MIT, Apache-2.0)

- [ ] Add runtime dependencies to `pyproject.toml`:
  ```bash
  poetry add requests pyyaml python-dotenv schedule tenacity
  ```

- [ ] Add development dependencies:
  ```bash
  poetry add --group dev pytest pytest-cov pytest-mock responses pylint black mypy isort
  ```

- [ ] Verify `poetry.lock` is generated

#### 1.3 Create Directory Structure
- [ ] Create `src/` directory
- [ ] Create `tests/` directory
- [ ] Create `.github/workflows/` directory

#### 1.4 Create Python Package Files
- [ ] Create `src/__init__.py` (empty or with version)
  ```python
  """Grafana-Okta Team Sync Service."""
  __version__ = "0.1.0"
  ```
- [ ] Create `tests/__init__.py` (empty)

#### 1.5 Create Placeholder Source Files
- [ ] Create empty `src/main.py`
- [ ] Create empty `src/config.py`
- [ ] Create empty `src/okta_client.py`
- [ ] Create empty `src/grafana_client.py`
- [ ] Create empty `src/sync_service.py`
- [ ] Create empty `src/utils.py`

#### 1.6 Create Placeholder Test Files
- [ ] Create empty `tests/test_config.py`
- [ ] Create empty `tests/test_okta_client.py`
- [ ] Create empty `tests/test_grafana_client.py`
- [ ] Create empty `tests/test_sync_service.py`
- [ ] Create empty `tests/test_main.py`
- [ ] Create empty `tests/test_utils.py`

#### 1.7 Create Configuration Examples
- [ ] Create `.env.example`:
  ```bash
  # Okta Configuration
  OKTA_DOMAIN=your-company.okta.com
  OKTA_API_TOKEN=your-okta-api-token-here

  # Grafana Configuration
  GRAFANA_URL=https://your-grafana-server.com
  GRAFANA_API_KEY=your-grafana-api-key-here

  # Sync Configuration (optional, can use config.yaml)
  SYNC_INTERVAL_SECONDS=300
  SYNC_DRY_RUN=false
  LOG_LEVEL=INFO
  LOG_FORMAT=json
  ```

- [ ] Create `config.example.yaml`:
  ```yaml
  okta:
    domain: ${OKTA_DOMAIN}  # or hardcode: your-company.okta.com
    api_token: ${OKTA_API_TOKEN}

  grafana:
    url: ${GRAFANA_URL}  # e.g., https://grafana.example.com
    api_key: ${GRAFANA_API_KEY}

  sync:
    interval_seconds: 300  # Run every 5 minutes
    dry_run: false  # Set true to preview changes without applying
    mappings:
      - okta_group: "Engineering"
        grafana_team: "Engineers"
      - okta_group: "DataScience"
        grafana_team: "Data Scientists"
      - okta_group: "SRE"
        grafana_team: "SRE Team"

  logging:
    level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: json  # json or text
  ```

#### 1.8 Create Docker Files
- [ ] Create `.dockerignore`:
  ```
  .git/
  .github/
  .pytest_cache/
  .mypy_cache/
  __pycache__/
  *.py[cod]
  .coverage
  htmlcov/
  .env
  .env.example
  config.example.yaml
  README.md
  CLAUDE.md
  CHANGELOG.md
  grafana-okta-team-sync.md
  GOTS_IMPLEMENTATION_TICKETS.md
  tests/
  *.log
  ```

#### 1.9 Initialize CHANGELOG.md
- [ ] Create `CHANGELOG.md`:
  ```markdown
  # Changelog

  All notable changes to this project will be documented in this file.

  The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
  and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

  ## [Unreleased]

  ### Added
  - Initial project scaffolding
  - Poetry dependency management
  - Configuration examples (.env.example, config.example.yaml)
  - Project directory structure

  [Unreleased]: https://github.com/cropalato/gots/compare/v0.1.0...HEAD
  ```

#### 1.10 Create GitHub Actions Workflows

- [ ] Create `.github/workflows/ci.yml`:
  ```yaml
  name: CI

  on:
    push:
      branches: [ main, develop ]
    pull_request:
      branches: [ main, develop ]

  jobs:
    test:
      runs-on: ubuntu-latest
      strategy:
        matrix:
          python-version: ['3.10', '3.11', '3.12']

      steps:
        - uses: actions/checkout@v4

        - name: Install Poetry
          run: pipx install poetry

        - uses: actions/setup-python@v5
          with:
            python-version: ${{ matrix.python-version }}
            cache: 'poetry'

        - name: Install dependencies
          run: poetry install --with dev

        - name: Run code formatting check
          run: poetry run black --check src/ tests/

        - name: Run import sorting check
          run: poetry run isort --check-only src/ tests/

        - name: Run linting
          run: poetry run pylint src/

        - name: Run type checking
          run: poetry run mypy src/

        - name: Run tests with coverage
          run: poetry run pytest --cov=src --cov-report=xml --cov-report=term-missing

        - name: Upload coverage to Codecov
          uses: codecov/codecov-action@v4
          if: matrix.python-version == '3.11'
          with:
            file: ./coverage.xml
            fail_ci_if_error: false
  ```

- [ ] Create `.github/workflows/docker.yml`:
  ```yaml
  name: Docker Build and Push

  on:
    push:
      branches: [ main ]
      tags: [ 'v*' ]

  jobs:
    docker:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4

        - name: Set up Docker Buildx
          uses: docker/setup-buildx-action@v3

        - name: Login to GitHub Container Registry
          uses: docker/login-action@v3
          with:
            registry: ghcr.io
            username: ${{ github.actor }}
            password: ${{ secrets.GITHUB_TOKEN }}

        - name: Extract metadata
          id: meta
          uses: docker/metadata-action@v5
          with:
            images: ghcr.io/${{ github.repository }}
            tags: |
              type=ref,event=branch
              type=semver,pattern={{version}}
              type=semver,pattern={{major}}.{{minor}}
              type=sha,prefix={{branch}}-

        - name: Build and push
          uses: docker/build-push-action@v5
          with:
            context: .
            push: true
            tags: ${{ steps.meta.outputs.tags }}
            labels: ${{ steps.meta.outputs.labels }}
            cache-from: type=gha
            cache-to: type=gha,mode=max
  ```

- [ ] Create `.github/workflows/release.yml`:
  ```yaml
  name: Release

  on:
    push:
      tags:
        - 'v*'

  jobs:
    release:
      runs-on: ubuntu-latest
      permissions:
        contents: write
      steps:
        - uses: actions/checkout@v4

        - name: Create Release
          uses: softprops/action-gh-release@v1
          with:
            generate_release_notes: true
            body_path: CHANGELOG.md
  ```

#### 1.11 Create README.md Skeleton
- [ ] Create `README.md` with basic structure:
  ```markdown
  # Grafana-Okta Team Sync (GOTS)

  A Python service that automatically synchronizes Okta group membership to Grafana teams.

  ## Features

  - Periodic synchronization of Okta groups to Grafana teams
  - Configurable sync intervals
  - Dry-run mode for testing
  - Docker containerized deployment
  - Comprehensive logging and error handling

  ## Prerequisites

  - Python 3.10+
  - Okta API token with group read permissions
  - Grafana API key with team admin permissions
  - Docker (optional, for containerized deployment)

  ## Quick Start

  *(To be completed in TICKET-9)*

  ## Configuration

  *(To be completed in TICKET-9)*

  ## Development

  *(To be completed in TICKET-9)*

  ## License

  *(Specify your license)*
  ```

#### 1.12 Configure Development Tools
- [ ] Create `pyproject.toml` additions for tool configuration:
  ```toml
  [tool.black]
  line-length = 100
  target-version = ['py310', 'py311', 'py312']
  include = '\.pyi?$'

  [tool.isort]
  profile = "black"
  line_length = 100

  [tool.pylint.messages_control]
  max-line-length = 100
  disable = ["C0111"]  # Adjust as needed

  [tool.mypy]
  python_version = "3.10"
  warn_return_any = true
  warn_unused_configs = true
  disallow_untyped_defs = true

  [tool.pytest.ini_options]
  testpaths = ["tests"]
  python_files = "test_*.py"
  python_functions = "test_*"
  addopts = "-v --cov=src --cov-report=term-missing"

  [tool.coverage.run]
  source = ["src"]
  omit = ["tests/*", "**/__init__.py"]

  [tool.coverage.report]
  exclude_lines = [
      "pragma: no cover",
      "def __repr__",
      "raise AssertionError",
      "raise NotImplementedError",
      "if __name__ == .__main__.:",
  ]
  ```

#### 1.13 Verify Setup
- [ ] Run `poetry install` to verify dependencies install correctly
- [ ] Run `poetry run black --version` to verify dev tools work
- [ ] Run `poetry run pytest --version` to verify test framework

#### 1.14 Initial Commit
- [ ] Stage all files: `git add .`
- [ ] Commit with message:
  ```
  feat: initial project scaffolding

  - Set up Poetry for dependency management
  - Create project directory structure
  - Add configuration examples
  - Set up GitHub Actions CI/CD workflows
  - Initialize CHANGELOG.md
  - Configure development tools (black, pylint, mypy, pytest)
  ```

### Acceptance Criteria
- [x] Project structure matches CLAUDE.md specification
- [x] `poetry install` runs successfully
- [x] All example files are properly documented
- [x] GitHub Actions workflows are present
- [x] CHANGELOG.md is initialized
- [x] Development tools are configured

**Implementation Notes:**
- Complete project scaffolding with Poetry, GitHub Actions, and tooling
- All configuration examples created
- Directory structure established
- Commit: `096e15b feat: initial project scaffolding`

---

## **TICKET-2: Configuration Management Module** ✅ COMPLETED

**Priority:** Critical
**Estimate:** 3 hours (includes tests and documentation)
**Actual Time:** ~3 hours
**Status:** ✅ Completed

### Tasks Checklist

#### 2.1 Design Configuration Classes
- [ ] Define configuration data structure in `src/config.py`

#### 2.2 Implement Configuration Module
- [ ] Create `src/config.py`:
  ```python
  """Configuration management for GOTS."""
  import os
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
          self.domain = self.domain.replace('https://', '').replace('http://', '')


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
          if not self.url.startswith(('http://', 'https://')):
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
      mappings: List[GroupMapping] = None

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
      logging: LoggingConfig = None

      def __post_init__(self) -> None:
          """Set defaults."""
          if self.logging is None:
              self.logging = LoggingConfig()


  class ConfigLoader:
      """Load configuration from YAML file and environment variables."""

      @staticmethod
      def _expand_env_vars(value: Any) -> Any:
          """Recursively expand environment variables in configuration values."""
          if isinstance(value, str):
              # Replace ${VAR_NAME} with environment variable value
              import re
              pattern = r'\$\{([^}]+)\}'
              matches = re.findall(pattern, value)
              for match in matches:
                  env_value = os.getenv(match, '')
                  value = value.replace(f'${{{match}}}', env_value)
              return value
          elif isinstance(value, dict):
              return {k: ConfigLoader._expand_env_vars(v) for k, v in value.items()}
          elif isinstance(value, list):
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

              with open(path, 'r', encoding='utf-8') as f:
                  config_dict = yaml.safe_load(f) or {}

              # Expand environment variables in config
              config_dict = ConfigLoader._expand_env_vars(config_dict)

          # Override with environment variables
          okta_config = OktaConfig(
              domain=os.getenv('OKTA_DOMAIN', config_dict.get('okta', {}).get('domain', '')),
              api_token=os.getenv('OKTA_API_TOKEN', config_dict.get('okta', {}).get('api_token', ''))
          )

          grafana_config = GrafanaConfig(
              url=os.getenv('GRAFANA_URL', config_dict.get('grafana', {}).get('url', '')),
              api_key=os.getenv('GRAFANA_API_KEY', config_dict.get('grafana', {}).get('api_key', ''))
          )

          # Sync config
          sync_dict = config_dict.get('sync', {})
          interval = int(os.getenv('SYNC_INTERVAL_SECONDS', sync_dict.get('interval_seconds', 300)))
          dry_run = os.getenv('SYNC_DRY_RUN', str(sync_dict.get('dry_run', False))).lower() == 'true'

          mappings = []
          for mapping in sync_dict.get('mappings', []):
              mappings.append(GroupMapping(
                  okta_group=mapping['okta_group'],
                  grafana_team=mapping['grafana_team']
              ))

          sync_config = SyncConfig(
              interval_seconds=interval,
              dry_run=dry_run,
              mappings=mappings
          )

          # Logging config
          logging_dict = config_dict.get('logging', {})
          logging_config = LoggingConfig(
              level=os.getenv('LOG_LEVEL', logging_dict.get('level', 'INFO')),
              format=os.getenv('LOG_FORMAT', logging_dict.get('format', 'json'))
          )

          return Config(
              okta=okta_config,
              grafana=grafana_config,
              sync=sync_config,
              logging=logging_config
          )
  ```

#### 2.3 Create Comprehensive Tests
- [ ] Create `tests/test_config.py`:
  ```python
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
      OktaConfig,
      SyncConfig,
  )


  class TestOktaConfig:
      """Test OktaConfig dataclass."""

      def test_valid_config(self):
          """Test valid Okta configuration."""
          config = OktaConfig(domain="example.okta.com", api_token="test-token")
          assert config.domain == "example.okta.com"
          assert config.api_token == "test-token"

      def test_removes_https_from_domain(self):
          """Test that https:// is stripped from domain."""
          config = OktaConfig(domain="https://example.okta.com", api_token="token")
          assert config.domain == "example.okta.com"

      def test_missing_domain(self):
          """Test error when domain is missing."""
          with pytest.raises(ValueError, match="Okta domain is required"):
              OktaConfig(domain="", api_token="token")

      def test_missing_token(self):
          """Test error when API token is missing."""
          with pytest.raises(ValueError, match="Okta API token is required"):
              OktaConfig(domain="example.okta.com", api_token="")


  class TestGrafanaConfig:
      """Test GrafanaConfig dataclass."""

      def test_valid_config(self):
          """Test valid Grafana configuration."""
          config = GrafanaConfig(url="https://grafana.example.com", api_key="test-key")
          assert config.url == "https://grafana.example.com"
          assert config.api_key == "test-key"

      def test_adds_https_to_url(self):
          """Test that https:// is added if missing."""
          config = GrafanaConfig(url="grafana.example.com", api_key="key")
          assert config.url == "https://grafana.example.com"

      def test_preserves_http_url(self):
          """Test that http:// URLs are preserved."""
          config = GrafanaConfig(url="http://localhost:3000", api_key="key")
          assert config.url == "http://localhost:3000"

      def test_missing_url(self):
          """Test error when URL is missing."""
          with pytest.raises(ValueError, match="Grafana URL is required"):
              GrafanaConfig(url="", api_key="key")

      def test_missing_api_key(self):
          """Test error when API key is missing."""
          with pytest.raises(ValueError, match="Grafana API key is required"):
              GrafanaConfig(url="https://grafana.example.com", api_key="")


  class TestGroupMapping:
      """Test GroupMapping dataclass."""

      def test_valid_mapping(self):
          """Test valid group mapping."""
          mapping = GroupMapping(okta_group="Engineering", grafana_team="Engineers")
          assert mapping.okta_group == "Engineering"
          assert mapping.grafana_team == "Engineers"

      def test_missing_okta_group(self):
          """Test error when Okta group is missing."""
          with pytest.raises(ValueError, match="Okta group name is required"):
              GroupMapping(okta_group="", grafana_team="Team")

      def test_missing_grafana_team(self):
          """Test error when Grafana team is missing."""
          with pytest.raises(ValueError, match="Grafana team name is required"):
              GroupMapping(okta_group="Group", grafana_team="")


  class TestSyncConfig:
      """Test SyncConfig dataclass."""

      def test_valid_config(self):
          """Test valid sync configuration."""
          mappings = [GroupMapping(okta_group="Group1", grafana_team="Team1")]
          config = SyncConfig(interval_seconds=300, dry_run=False, mappings=mappings)
          assert config.interval_seconds == 300
          assert config.dry_run is False
          assert len(config.mappings) == 1

      def test_interval_too_short(self):
          """Test error when interval is less than 60 seconds."""
          mappings = [GroupMapping(okta_group="Group1", grafana_team="Team1")]
          with pytest.raises(ValueError, match="at least 60 seconds"):
              SyncConfig(interval_seconds=30, mappings=mappings)

      def test_no_mappings(self):
          """Test error when no mappings provided."""
          with pytest.raises(ValueError, match="At least one group mapping is required"):
              SyncConfig(interval_seconds=300, mappings=[])


  class TestLoggingConfig:
      """Test LoggingConfig dataclass."""

      def test_default_config(self):
          """Test default logging configuration."""
          config = LoggingConfig()
          assert config.level == "INFO"
          assert config.format == "json"

      def test_valid_config(self):
          """Test valid logging configuration."""
          config = LoggingConfig(level="DEBUG", format="text")
          assert config.level == "DEBUG"
          assert config.format == "text"

      def test_normalizes_level_case(self):
          """Test that log level is normalized to uppercase."""
          config = LoggingConfig(level="debug")
          assert config.level == "DEBUG"

      def test_invalid_level(self):
          """Test error with invalid log level."""
          with pytest.raises(ValueError, match="Log level must be one of"):
              LoggingConfig(level="INVALID")

      def test_invalid_format(self):
          """Test error with invalid log format."""
          with pytest.raises(ValueError, match="Log format must be one of"):
              LoggingConfig(format="xml")


  class TestConfigLoader:
      """Test ConfigLoader class."""

      def test_load_from_yaml(self):
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

          with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
              f.write(yaml_content)
              config_path = f.name

          try:
              config = ConfigLoader.load(config_path)
              assert config.okta.domain == "example.okta.com"
              assert config.grafana.url == "https://grafana.example.com"
              assert config.sync.interval_seconds == 300
              assert len(config.sync.mappings) == 1
              assert config.logging.level == "DEBUG"
          finally:
              Path(config_path).unlink()

      def test_expand_env_vars(self):
          """Test environment variable expansion."""
          os.environ['TEST_OKTA_DOMAIN'] = 'env.okta.com'
          os.environ['TEST_OKTA_TOKEN'] = 'env-token'

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

          with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
              f.write(yaml_content)
              config_path = f.name

          try:
              config = ConfigLoader.load(config_path)
              assert config.okta.domain == "env.okta.com"
              assert config.okta.api_token == "env-token"
          finally:
              Path(config_path).unlink()
              del os.environ['TEST_OKTA_DOMAIN']
              del os.environ['TEST_OKTA_TOKEN']

      def test_env_vars_override_yaml(self):
          """Test that environment variables override YAML config."""
          os.environ['OKTA_DOMAIN'] = 'override.okta.com'

          yaml_content = """
          okta:
            domain: original.okta.com
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

          with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
              f.write(yaml_content)
              config_path = f.name

          try:
              config = ConfigLoader.load(config_path)
              assert config.okta.domain == "override.okta.com"
          finally:
              Path(config_path).unlink()
              del os.environ['OKTA_DOMAIN']

      def test_missing_config_file(self):
          """Test error when config file doesn't exist."""
          with pytest.raises(FileNotFoundError):
              ConfigLoader.load("/nonexistent/config.yaml")

      def test_invalid_yaml(self):
          """Test error with invalid YAML."""
          with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
              f.write("invalid: yaml: content: [")
              config_path = f.name

          try:
              with pytest.raises(Exception):  # yaml.YAMLError
                  ConfigLoader.load(config_path)
          finally:
              Path(config_path).unlink()
  ```

#### 2.4 Update CHANGELOG.md
- [ ] Add entry to CHANGELOG.md under `[Unreleased]` > `[Added]`:
  ```
  - Configuration management module with YAML and environment variable support
  - Configuration validation with clear error messages
  - Support for multiple Okta-to-Grafana group mappings
  ```

#### 2.5 Verify Tests Pass
- [ ] Run tests: `poetry run pytest tests/test_config.py -v`
- [ ] Run coverage: `poetry run pytest tests/test_config.py --cov=src.config --cov-report=term-missing`
- [ ] Ensure coverage is above 90% for config.py

#### 2.6 Run Code Quality Checks
- [ ] Format code: `poetry run black src/config.py tests/test_config.py`
- [ ] Sort imports: `poetry run isort src/config.py tests/test_config.py`
- [ ] Lint code: `poetry run pylint src/config.py`
- [ ] Type check: `poetry run mypy src/config.py`

#### 2.7 Commit Changes
- [ ] Stage files: `git add src/config.py tests/test_config.py CHANGELOG.md`
- [ ] Commit with message:
  ```
  feat(config): implement configuration management module

  - Add OktaConfig, GrafanaConfig, SyncConfig, LoggingConfig dataclasses
  - Implement ConfigLoader with YAML and environment variable support
  - Add environment variable expansion (${VAR_NAME} syntax)
  - Add comprehensive validation with clear error messages
  - Add 95%+ test coverage with 15+ test cases
  ```

### Acceptance Criteria
- [x] Config loads from YAML file correctly
- [x] Environment variables override YAML settings
- [x] ${VAR_NAME} expansion works in YAML
- [x] Missing required fields raise clear ValueError exceptions
- [x] Multiple group mappings are supported
- [x] All tests pass with 100% coverage
- [x] Code passes linting and type checking

**Implementation Notes:**
- Implemented src/config.py (225 lines) with full validation
- Created 36 comprehensive test cases (441 lines)
- Achieved 100% code coverage (109 statements, 0 missed)
- All code quality checks passed (pylint 10/10, mypy, black, isort)
- Commit: `01f02dd feat(config): implement configuration management module`

---

## **TICKET-3: Okta API Client** ✅ COMPLETED

**Priority:** Critical
**Estimate:** 4 hours (includes tests, error handling, pagination)
**Actual Time:** ~4 hours
**Status:** ✅ Completed

### Tasks Checklist

#### 3.1 Research Okta API
- [ ] Review Okta Groups API documentation: https://developer.okta.com/docs/reference/api/groups/
- [ ] Identify required endpoints:
  - `GET /api/v1/groups?q={name}` - Search groups by name
  - `GET /api/v1/groups/{groupId}/users` - Get group members
- [ ] Note pagination mechanism (Link headers)
- [ ] Note rate limit headers (X-Rate-Limit-*)

#### 3.2 Implement Okta Client
- [ ] Create `src/okta_client.py`:
  ```python
  """Okta API client for group and user management."""
  import logging
  from typing import Any, Dict, List, Optional
  from urllib.parse import urljoin, urlparse, parse_qs

  import requests
  from tenacity import (
      retry,
      retry_if_exception_type,
      stop_after_attempt,
      wait_exponential,
  )

  logger = logging.getLogger(__name__)


  class OktaAPIError(Exception):
      """Base exception for Okta API errors."""
      pass


  class OktaAuthenticationError(OktaAPIError):
      """Raised when authentication fails."""
      pass


  class OktaNotFoundError(OktaAPIError):
      """Raised when a resource is not found."""
      pass


  class OktaRateLimitError(OktaAPIError):
      """Raised when rate limit is exceeded."""
      pass


  class OktaClient:
      """Client for interacting with Okta API."""

      def __init__(self, domain: str, api_token: str) -> None:
          """
          Initialize Okta client.

          Args:
              domain: Okta domain (e.g., 'example.okta.com')
              api_token: Okta API token
          """
          self.domain = domain.replace('https://', '').replace('http://', '')
          self.base_url = f"https://{self.domain}"
          self.api_token = api_token
          self.session = requests.Session()
          self.session.headers.update({
              'Authorization': f'SSWS {api_token}',
              'Accept': 'application/json',
              'Content-Type': 'application/json',
          })

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
              logger.warning(f"Okta resource not found: {response.url}")
              raise OktaNotFoundError(f"Resource not found: {response.url}")

          if response.status_code == 429:
              reset_time = response.headers.get('X-Rate-Limit-Reset', 'unknown')
              logger.warning(f"Okta rate limit exceeded. Resets at: {reset_time}")
              raise OktaRateLimitError(f"Rate limit exceeded. Resets at: {reset_time}")

          logger.error(f"Okta API error: {response.status_code} - {response.text}")
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
          logger.debug(f"GET {url} params={params}")

          response = self.session.get(url, params=params)
          self._handle_response(response)

          # Log rate limit status
          limit = response.headers.get('X-Rate-Limit-Limit')
          remaining = response.headers.get('X-Rate-Limit-Remaining')
          if limit and remaining:
              logger.debug(f"Rate limit: {remaining}/{limit} remaining")

          return response

      def _get_paginated(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
          """
          Get all results from a paginated endpoint.

          Args:
              endpoint: API endpoint
              params: Query parameters

          Returns:
              List of all results
          """
          all_results = []
          current_url = endpoint
          current_params = params or {}

          while True:
              response = self._get(current_url, current_params)
              results = response.json()
              all_results.extend(results)

              # Check for next page in Link header
              link_header = response.headers.get('Link', '')
              next_link = self._parse_next_link(link_header)

              if not next_link:
                  break

              # Parse next URL
              parsed = urlparse(next_link)
              current_url = parsed.path
              current_params = parse_qs(parsed.query)
              # Convert lists to single values
              current_params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v
                                for k, v in current_params.items()}

          logger.info(f"Retrieved {len(all_results)} total results from {endpoint}")
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
          links = link_header.split(',')
          for link in links:
              parts = link.split(';')
              if len(parts) == 2:
                  url = parts[0].strip().strip('<>')
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
          logger.info(f"Searching for Okta group: {group_name}")

          response = self._get('/api/v1/groups', params={'q': group_name})
          groups = response.json()

          # Find exact match (search is case-insensitive partial match)
          for group in groups:
              if group.get('profile', {}).get('name') == group_name:
                  logger.info(f"Found Okta group: {group_name} (ID: {group['id']})")
                  return group

          logger.warning(f"Okta group not found: {group_name}")
          raise OktaNotFoundError(f"Group not found: {group_name}")

      def get_group_members(self, group_id: str) -> List[Dict[str, Any]]:
          """
          Get all members of an Okta group.

          Args:
              group_id: Okta group ID

          Returns:
              List of user objects with 'id', 'profile' (with 'email', 'firstName', 'lastName'), etc.
          """
          logger.info(f"Fetching members for Okta group ID: {group_id}")

          endpoint = f'/api/v1/groups/{group_id}/users'
          members = self._get_paginated(endpoint)

          logger.info(f"Found {len(members)} members in group {group_id}")
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
          return self.get_group_members(group['id'])
  ```

#### 3.3 Create Comprehensive Tests
- [ ] Create `tests/test_okta_client.py`:
  ```python
  """Tests for Okta API client."""
  import pytest
  import responses
  from requests.exceptions import RequestException

  from src.okta_client import (
      OktaAPIError,
      OktaAuthenticationError,
      OktaClient,
      OktaNotFoundError,
      OktaRateLimitError,
  )


  @pytest.fixture
  def okta_client():
      """Create Okta client fixture."""
      return OktaClient(domain="example.okta.com", api_token="test-token")


  class TestOktaClient:
      """Test OktaClient class."""

      def test_init_strips_protocol(self):
          """Test that protocol is stripped from domain."""
          client = OktaClient(domain="https://example.okta.com", api_token="token")
          assert client.domain == "example.okta.com"
          assert client.base_url == "https://example.okta.com"

      def test_session_headers(self, okta_client):
          """Test that session has correct headers."""
          assert okta_client.session.headers['Authorization'] == 'SSWS test-token'
          assert okta_client.session.headers['Accept'] == 'application/json'

      @responses.activate
      def test_get_group_by_name_success(self, okta_client):
          """Test successful group lookup."""
          mock_response = [
              {
                  "id": "00g1234567890abcdef",
                  "profile": {
                      "name": "Engineering",
                      "description": "Engineering team"
                  }
              }
          ]

          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups",
              json=mock_response,
              status=200
          )

          group = okta_client.get_group_by_name("Engineering")
          assert group['id'] == "00g1234567890abcdef"
          assert group['profile']['name'] == "Engineering"

      @responses.activate
      def test_get_group_by_name_not_found(self, okta_client):
          """Test group not found error."""
          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups",
              json=[],
              status=200
          )

          with pytest.raises(OktaNotFoundError, match="Group not found: NonExistent"):
              okta_client.get_group_by_name("NonExistent")

      @responses.activate
      def test_get_group_by_name_exact_match(self, okta_client):
          """Test that exact match is returned when multiple partial matches exist."""
          mock_response = [
              {"id": "1", "profile": {"name": "Engineering"}},
              {"id": "2", "profile": {"name": "Engineering-DevOps"}},
              {"id": "3", "profile": {"name": "Engineering-QA"}},
          ]

          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups",
              json=mock_response,
              status=200
          )

          group = okta_client.get_group_by_name("Engineering")
          assert group['id'] == "1"

      @responses.activate
      def test_get_group_members_success(self, okta_client):
          """Test successful retrieval of group members."""
          mock_response = [
              {
                  "id": "00u1234567890abcdef",
                  "profile": {
                      "email": "user1@example.com",
                      "firstName": "John",
                      "lastName": "Doe"
                  }
              },
              {
                  "id": "00u0987654321fedcba",
                  "profile": {
                      "email": "user2@example.com",
                      "firstName": "Jane",
                      "lastName": "Smith"
                  }
              }
          ]

          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups/00g123/users",
              json=mock_response,
              status=200
          )

          members = okta_client.get_group_members("00g123")
          assert len(members) == 2
          assert members[0]['profile']['email'] == "user1@example.com"

      @responses.activate
      def test_get_group_members_pagination(self, okta_client):
          """Test pagination when retrieving group members."""
          page1_response = [{"id": "user1", "profile": {"email": "user1@example.com"}}]
          page2_response = [{"id": "user2", "profile": {"email": "user2@example.com"}}]

          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups/00g123/users",
              json=page1_response,
              status=200,
              headers={
                  'Link': '<https://example.okta.com/api/v1/groups/00g123/users?after=cursor1>; rel="next"'
              }
          )

          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups/00g123/users",
              json=page2_response,
              status=200
          )

          members = okta_client.get_group_members("00g123")
          assert len(members) == 2
          assert members[0]['id'] == "user1"
          assert members[1]['id'] == "user2"

      @responses.activate
      def test_get_group_members_empty(self, okta_client):
          """Test retrieval of empty group."""
          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups/00g123/users",
              json=[],
              status=200
          )

          members = okta_client.get_group_members("00g123")
          assert len(members) == 0

      @responses.activate
      def test_authentication_error(self, okta_client):
          """Test authentication error handling."""
          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups",
              json={"errorCode": "E0000011", "errorSummary": "Invalid token provided"},
              status=401
          )

          with pytest.raises(OktaAuthenticationError, match="Authentication failed"):
              okta_client.get_group_by_name("Engineering")

      @responses.activate
      def test_rate_limit_error(self, okta_client):
          """Test rate limit error handling."""
          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups",
              json={"errorCode": "E0000047", "errorSummary": "Rate limit exceeded"},
              status=429,
              headers={'X-Rate-Limit-Reset': '1234567890'}
          )

          # Note: Retry decorator will retry, so we need to add multiple responses
          for _ in range(5):
              responses.add(
                  responses.GET,
                  "https://example.okta.com/api/v1/groups",
                  json={"errorCode": "E0000047"},
                  status=429,
                  headers={'X-Rate-Limit-Reset': '1234567890'}
              )

          with pytest.raises(OktaRateLimitError, match="Rate limit exceeded"):
              okta_client.get_group_by_name("Engineering")

      @responses.activate
      def test_404_error(self, okta_client):
          """Test 404 error handling."""
          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups/invalid",
              json={"errorCode": "E0000007", "errorSummary": "Not found"},
              status=404
          )

          with pytest.raises(OktaNotFoundError, match="Resource not found"):
              okta_client._get('/api/v1/groups/invalid')

      @responses.activate
      def test_generic_api_error(self, okta_client):
          """Test generic API error handling."""
          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups",
              json={"errorCode": "E0000001", "errorSummary": "API validation failed"},
              status=400
          )

          with pytest.raises(OktaAPIError, match="API error 400"):
              okta_client.get_group_by_name("Engineering")

      @responses.activate
      def test_get_group_members_by_name(self, okta_client):
          """Test convenience method to get members by group name."""
          # Mock group search
          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups",
              json=[{"id": "00g123", "profile": {"name": "Engineering"}}],
              status=200
          )

          # Mock members retrieval
          responses.add(
              responses.GET,
              "https://example.okta.com/api/v1/groups/00g123/users",
              json=[{"id": "user1", "profile": {"email": "user1@example.com"}}],
              status=200
          )

          members = okta_client.get_group_members_by_name("Engineering")
          assert len(members) == 1
          assert members[0]['id'] == "user1"

      def test_parse_next_link(self):
          """Test parsing of Link header."""
          link_header = '<https://example.okta.com/api/v1/groups?after=cursor>; rel="next", <https://example.okta.com/api/v1/groups>; rel="self"'
          next_link = OktaClient._parse_next_link(link_header)
          assert next_link == "https://example.okta.com/api/v1/groups?after=cursor"

      def test_parse_next_link_no_next(self):
          """Test parsing Link header with no next link."""
          link_header = '<https://example.okta.com/api/v1/groups>; rel="self"'
          next_link = OktaClient._parse_next_link(link_header)
          assert next_link is None

      def test_parse_next_link_empty(self):
          """Test parsing empty Link header."""
          next_link = OktaClient._parse_next_link("")
          assert next_link is None
  ```

#### 3.4 Update CHANGELOG.md
- [ ] Add to `[Unreleased]` > `[Added]`:
  ```
  - Okta API client with group and member retrieval
  - Automatic pagination support for large Okta groups
  - Retry logic with exponential backoff for transient failures
  - Comprehensive error handling (401, 404, 429, 5xx)
  ```

#### 3.5 Verify Tests and Coverage
- [ ] Run tests: `poetry run pytest tests/test_okta_client.py -v`
- [ ] Check coverage: `poetry run pytest tests/test_okta_client.py --cov=src.okta_client --cov-report=term-missing`
- [ ] Ensure coverage >90%

#### 3.6 Code Quality
- [ ] Format: `poetry run black src/okta_client.py tests/test_okta_client.py`
- [ ] Sort imports: `poetry run isort src/okta_client.py tests/test_okta_client.py`
- [ ] Lint: `poetry run pylint src/okta_client.py`
- [ ] Type check: `poetry run mypy src/okta_client.py`

#### 3.7 Commit
- [ ] Commit with message:
  ```
  feat(okta): implement Okta API client

  - Add OktaClient with group search and member retrieval
  - Implement automatic pagination for large groups
  - Add retry logic with exponential backoff using tenacity
  - Handle authentication errors (401), not found (404), rate limits (429)
  - Add custom exception types for different error cases
  - Add 95%+ test coverage with mocked HTTP responses
  ```

### Acceptance Criteria
- [x] Successfully authenticates with Okta API
- [x] Can fetch group by exact name match
- [x] Can fetch all group members with pagination
- [x] Retries on transient failures (network errors, rate limits)
- [x] Logs all API interactions at appropriate levels
- [x] Raises specific exceptions for different error types
- [x] All tests pass with 100% coverage

**Implementation Notes:**
- Implemented src/okta_client.py (247 lines) with pagination and retry logic
- Created 19 comprehensive test cases (322 lines)
- Achieved 100% code coverage (93 statements, 0 missed)
- All code quality checks passed (pylint 10/10, mypy, black, isort)
- Commit: `9167b8d feat(okta): implement Okta API client`

---

## **TICKET-4: Grafana API Client** ✅ COMPLETED

**Priority:** Critical
**Estimate:** 5 hours (complex API interactions, user/team management)
**Actual Time:** ~5 hours
**Status:** ✅ Completed

### Tasks Checklist

#### 4.1 Research Grafana API
- [x] Review Grafana HTTP API documentation
- [x] Identify required endpoints:
  - `GET /api/teams/search?name={name}` - Search teams
  - `POST /api/teams` - Create team
  - `GET /api/teams/{id}/members` - Get team members
  - `POST /api/teams/{id}/members` - Add user to team
  - `DELETE /api/teams/{id}/members/{userId}` - Remove user from team
  - `GET /api/users/lookup?loginOrEmail={email}` - Find user
  - `POST /api/admin/users` - Create user (admin API)

#### 4.2 Implement Grafana Client
- [x] Create `src/grafana_client.py` with:
  - GrafanaClient class
  - Custom exception types (GrafanaAPIError, GrafanaAuthenticationError, etc.)
  - get_or_create_team() method
  - get_team_members() method
  - add_user_to_team() method
  - remove_user_from_team() method
  - get_or_create_user() method
  - Retry logic with tenacity
  - Structured logging

*✅ Implemented: 357 lines with complete functionality*

#### 4.3 Create Comprehensive Tests
- [x] Create `tests/test_grafana_client.py` with:
  - Test initialization and headers
  - Test team creation (new and existing)
  - Test team member retrieval
  - Test adding user to team
  - Test removing user from team
  - Test user creation (new and existing)
  - Test authentication errors
  - Test not found errors
  - Test generic API errors
  - Test retry logic
  - Test idempotent operations

*✅ Implemented: 29 test cases, 100% coverage*

#### 4.4 Update CHANGELOG.md
- [x] Add to `[Unreleased]` > `[Added]`:
  ```
  - Grafana API client with team and user management
  - Team operations: search, create, and get-or-create with automatic retrieval
  - User operations: lookup, create, and get-or-create with email-based search
  - Team membership operations: add and remove users from teams
  - Retry logic with exponential backoff for HTTP requests
  - Comprehensive error handling (401, 403, 404, 409, 5xx errors)
  - Support for both 200 OK and 201 Created success responses
  - Comprehensive test suite for Grafana client (29 test cases, 100% coverage)
  ```

#### 4.5 Verify and Commit
- [x] Run tests with coverage (100% achieved)
- [x] Run code quality checks (pylint 10/10, mypy clean, black/isort formatted)
- [x] Commit with descriptive message (commit 9278098)

### Acceptance Criteria
- [x] Creates teams idempotently (doesn't fail if exists)
- [x] Adds/removes users from teams
- [x] Creates users if they don't exist
- [x] Handles all error cases gracefully
- [x] Retries on transient failures
- [x] All tests pass with 100% coverage

**Implementation Notes:**
- Implemented full Grafana API client with 357 lines of code
- Created 29 comprehensive test cases (527 lines)
- Achieved 100% code coverage (126 statements, 0 missed)
- All code quality checks passed (pylint 10/10, mypy, black, isort)
- Commit: `9278098 feat(grafana): implement Grafana API client`

---

## **TICKET-5: Sync Service Logic** ✅ COMPLETED

**Priority:** Critical
**Estimate:** 4 hours (core business logic, metrics tracking)
**Actual Time:** ~4 hours
**Status:** ✅ Completed

### Tasks Checklist

#### 5.1 Design Sync Algorithm
- [ ] Document sync process flow:
  1. Fetch Okta group members
  2. Fetch Grafana team members
  3. Calculate members to add (in Okta but not in Grafana)
  4. Calculate members to remove (in Grafana but not in Okta)
  5. Execute add operations
  6. Execute remove operations
  7. Track metrics

#### 5.2 Implement Sync Service
- [ ] Create `src/sync_service.py`:
  ```python
  """Sync service for synchronizing Okta groups to Grafana teams."""
  import logging
  import time
  from dataclasses import dataclass
  from typing import List, Set

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
          self,
          okta_client: OktaClient,
          grafana_client: GrafanaClient,
          dry_run: bool = False
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

      def sync_group_to_team(
          self,
          okta_group_name: str,
          grafana_team_name: str
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

          logger.info(f"Starting sync: {okta_group_name} -> {grafana_team_name}")

          try:
              # Fetch Okta group members
              okta_members = self.okta_client.get_group_members_by_name(okta_group_name)
              okta_emails = {m['profile']['email'].lower() for m in okta_members}
              logger.info(f"Found {len(okta_emails)} members in Okta group '{okta_group_name}'")

              # Get or create Grafana team
              team = self.grafana_client.get_or_create_team(grafana_team_name)
              team_id = team['id']

              # Fetch Grafana team members
              grafana_members = self.grafana_client.get_team_members(team_id)
              grafana_emails = {m['email'].lower() for m in grafana_members}
              logger.info(f"Found {len(grafana_emails)} members in Grafana team '{grafana_team_name}'")

              # Calculate diff
              to_add = okta_emails - grafana_emails
              to_remove = grafana_emails - okta_emails

              logger.info(f"Sync diff: {len(to_add)} to add, {len(to_remove)} to remove")

              # Add users
              for email in to_add:
                  try:
                      if self.dry_run:
                          logger.info(f"[DRY RUN] Would add user {email} to team {grafana_team_name}")
                      else:
                          self.grafana_client.add_user_to_team(team_id, email)
                          logger.info(f"Added user {email} to team {grafana_team_name}")
                      metrics.users_added += 1
                  except Exception as e:
                      logger.error(f"Failed to add user {email}: {e}")
                      metrics.errors += 1

              # Remove users
              for email in to_remove:
                  try:
                      # Find user ID
                      member = next(m for m in grafana_members if m['email'].lower() == email)
                      user_id = member['userId']

                      if self.dry_run:
                          logger.info(f"[DRY RUN] Would remove user {email} from team {grafana_team_name}")
                      else:
                          self.grafana_client.remove_user_from_team(team_id, user_id)
                          logger.info(f"Removed user {email} from team {grafana_team_name}")
                      metrics.users_removed += 1
                  except Exception as e:
                      logger.error(f"Failed to remove user {email}: {e}")
                      metrics.errors += 1

          except Exception as e:
              logger.error(f"Sync failed for {okta_group_name} -> {grafana_team_name}: {e}")
              metrics.errors += 1
              raise
          finally:
              metrics.duration_seconds = time.time() - start_time
              logger.info(
                  f"Sync completed in {metrics.duration_seconds:.2f}s: "
                  f"+{metrics.users_added}, -{metrics.users_removed}, "
                  f"errors={metrics.errors}"
              )

          return metrics
  ```

#### 5.3 Create Comprehensive Tests
- [ ] Create `tests/test_sync_service.py`:
  - Test sync with users to add
  - Test sync with users to remove
  - Test sync with both add and remove
  - Test sync with no changes (idempotent)
  - Test dry-run mode
  - Test error handling (Okta failure, Grafana failure)
  - Test metrics tracking
  - Test case-insensitive email matching
  - Test partial failure (some users succeed, some fail)

#### 5.4 Update CHANGELOG.md
- [ ] Add to `[Unreleased]` > `[Added]`:
  ```
  - Core sync service with bidirectional member synchronization
  - Dry-run mode for testing without making changes
  - Sync metrics tracking (added, removed, errors, duration)
  - Case-insensitive email matching
  ```

#### 5.5 Verify and Commit
- [ ] Run all tests
- [ ] Check coverage (>85%)
- [ ] Commit changes

### Acceptance Criteria
- [x] Correctly identifies members to add/remove
- [x] Executes sync operations in correct order
- [x] Tracks detailed metrics
- [x] Dry-run mode works without making changes
- [x] Sync is idempotent
- [x] Handles partial failures gracefully

**Implementation Notes:**
- Implemented src/sync_service.py (151 lines) with bidirectional sync
- Created 16 comprehensive test cases (485 lines)
- Achieved 100% code coverage (65 statements, 0 missed)
- All code quality checks passed (pylint 10/10, mypy clean, black/isort formatted)
- Commit: `7314862 feat(sync): implement sync service with bidirectional synchronization`

---

## **TICKET-6: Main Application & Scheduler** ✅ COMPLETED

**Priority:** Critical
**Estimate:** 3 hours
**Actual Time:** ~3 hours
**Status:** ✅ Completed

### Tasks Checklist

#### 6.1 Design Application Flow
- [x] Document application lifecycle:
  1. Load configuration
  2. Setup logging
  3. Initialize clients
  4. Run initial sync
  5. Schedule periodic syncs
  6. Handle shutdown signals

#### 6.2 Implement Main Application
- [x] Create `src/main.py`:
  - Setup logging (JSON or text format)
  - Load configuration using ConfigLoader
  - Initialize OktaClient and GrafanaClient
  - Initialize SyncService
  - Implement scheduler using `schedule` library
  - Handle SIGTERM/SIGINT for graceful shutdown
  - Add startup banner
  - Run initial sync
  - Run periodic syncs

#### 6.3 Implement Logging Setup
- [x] Add structured logging configuration
- [x] Support both JSON and text formats
- [x] Include appropriate log levels

#### 6.4 Create Tests
- [x] Create `tests/test_main.py`:
  - Test logging setup
  - Test configuration loading
  - Test client initialization
  - Test sync execution
  - Mock schedule library

#### 6.5 Update CHANGELOG.md
- [x] Add entry for main application and scheduler

#### 6.6 Test Manually
- [x] Create test config.yaml
- [x] Run locally: `poetry run python -m src.main`
- [x] Verify logs
- [x] Test with dry_run: true

#### 6.7 Commit
- [x] Commit all changes

### Acceptance Criteria
- [x] Application starts successfully
- [x] Runs initial sync on startup
- [x] Continues to sync on schedule
- [x] Gracefully shuts down on SIGTERM/SIGINT
- [x] Logs are clear and structured

**Implementation Notes:**
- Implemented src/main.py (231 lines) with full application lifecycle
- Created 18 comprehensive test cases (397 lines) with 100% coverage
- Achieved 100% code coverage (98 statements, 0 missed)
- Features implemented:
  - Structured logging with JSON and text formats
  - Periodic scheduler using schedule library
  - Graceful shutdown handling (SIGTERM/SIGINT)
  - Force exit on second Ctrl+C
  - Startup banner with dry-run indicator
  - Initial sync followed by periodic syncs
  - CLI argument support for custom config file path
  - Comprehensive error handling for all failure scenarios
- All code quality checks passed (pylint 9.46/10, mypy clean, black/isort formatted)
- Manual testing completed successfully with 26 users synced
- SSL certificate issue resolved using environment variables (REQUESTS_CA_BUNDLE)

---

## **TICKET-7: Docker Containerization** ✅ COMPLETED

**Priority:** High
**Estimate:** 2 hours
**Actual Time:** ~1 hour
**Status:** ✅ Completed

### Tasks Checklist

#### 7.1 Create Dockerfile
- [x] Create `Dockerfile`:
  ```dockerfile
  # Multi-stage build for smaller image
  FROM python:3.11-slim as builder

  # Install Poetry
  RUN pip install --no-cache-dir poetry==1.7.1

  # Copy dependency files
  WORKDIR /app
  COPY pyproject.toml poetry.lock ./

  # Install dependencies to a virtual environment
  RUN poetry config virtualenvs.in-project true && \
      poetry install --only main --no-root

  # Final stage
  FROM python:3.11-slim

  WORKDIR /app

  # Copy virtual environment from builder
  COPY --from=builder /app/.venv /app/.venv

  # Copy application code
  COPY src/ ./src/

  # Create non-root user
  RUN useradd -m -u 1000 syncuser && \
      chown -R syncuser:syncuser /app

  USER syncuser

  # Add venv to PATH
  ENV PATH="/app/.venv/bin:$PATH"

  CMD ["python", "-m", "src.main"]
  ```

#### 7.2 Create docker-compose.yml
- [x] Create `docker-compose.yml` for local testing:
  ```yaml
  version: '3.8'

  services:
    gots:
      build: .
      container_name: gots
      environment:
        - OKTA_DOMAIN=${OKTA_DOMAIN}
        - OKTA_API_TOKEN=${OKTA_API_TOKEN}
        - GRAFANA_URL=${GRAFANA_URL}
        - GRAFANA_API_KEY=${GRAFANA_API_KEY}
        - SYNC_DRY_RUN=true
        - LOG_LEVEL=DEBUG
        - LOG_FORMAT=text
      volumes:
        - ./config.yaml:/app/config.yaml:ro
      restart: unless-stopped
  ```

#### 7.3 Test Docker Build
- [x] Build image: `docker build -t gots:latest .`
- [x] Check image size (should be <200MB)
- [x] Verify non-root user: `docker run --rm gots:latest id`

#### 7.4 Test Docker Run
- [x] Create `.env` file with test credentials
- [x] Run: `docker-compose up`
- [x] Verify logs
- [x] Test graceful shutdown

#### 7.5 Update CHANGELOG.md
- [x] Add Docker containerization entry

#### 7.6 Commit
- [x] Commit Dockerfile and docker-compose.yml

### Acceptance Criteria
- [x] Docker image builds successfully
- [x] Image size <200MB (162MB achieved)
- [x] Container runs without root privileges
- [x] Can pass config via environment variables
- [x] docker-compose works for local testing

**Implementation Notes:**
- Created mult-stage Dockerfile using python:3.11-slim base image
- Final image size: 162MB (well under the 200MB target)
- Non-root user 'syncuser' (UID 1000) for security
- Multi-stage build reduces image size significantly
- Docker Compose configured with:
  - Environment variable support for all configuration options
  - Volume mounting for config files and CA certificates
  - Resource limits (optional, commented out)
  - Restart policy for production use
- Tested Docker build and verified non-root execution
- Updated CHANGELOG.md with Docker containerization features

---

## **TICKET-8: Error Handling & Resilience** ✅ COMPLETED

**Priority:** High
**Estimate:** 2 hours
**Actual Time:** ~1 hour (verification only - features already implemented)
**Status:** ✅ Completed

### Tasks Checklist

#### 8.1 Review Current Error Handling
- [x] Review all modules for error handling gaps
- [x] Identify areas needing improvement

#### 8.2 Enhance Error Handling
- [x] Ensure all API clients have retry logic
- [x] Verify exponential backoff is properly configured
- [x] Add rate limit handling
- [x] Ensure sync service continues on individual failures
- [x] Add proper exception logging with stack traces

#### 8.3 Create Failure Scenario Tests
- [x] Test network timeout handling
- [x] Test rate limit recovery
- [x] Test partial group sync failure
- [x] Test authentication failure handling
- [x] Test service continues after individual sync failure

#### 8.4 Update CHANGELOG.md
- [x] Add error handling improvements

#### 8.5 Commit
- [x] Commit enhancements

### Acceptance Criteria
- [x] Transient failures are retried automatically
- [x] Permanent failures are logged and skipped
- [x] Service continues running despite individual sync failures
- [x] Clear error messages for troubleshooting

**Implementation Notes:**
All error handling and resilience features were comprehensively implemented during TICKETS 3-6. Verification confirmed:

**Error Handling Implementation:**
- okta_client.py (lines 70-104): Retry logic with exponential backoff (5 attempts, 2-60s), HTTP timeout 30s, custom exceptions (OktaAPIError, OktaAuthenticationError, OktaNotFoundError, OktaRateLimitError)
- grafana_client.py (lines 70-104): Retry logic with exponential backoff (5 attempts, 2-60s), HTTP timeout 30s, custom exceptions (GrafanaAPIError, GrafanaAuthenticationError, GrafanaNotFoundError, GrafanaConflictError)
- sync_service.py (lines 105-107, 126-128): Partial failure handling - individual user operations can fail without stopping the entire sync
- main.py (lines 216-227): Comprehensive error handling for configuration errors, fatal errors, and graceful shutdown

**Test Coverage for Error Scenarios:**
- test_okta_client.py: Tests for 401, 404, 429 errors, retry exhaustion, pagination
- test_grafana_client.py: Tests for 401, 403, 404, 409, 500 errors, creation failures
- test_sync_service.py: Tests for partial failures (lines 332-411), API failures, metric tracking during errors
- test_main.py: Tests for config errors, fatal errors, signal handling, keyboard interrupts

All TICKET-8 requirements were satisfied during previous implementation. No additional code changes needed.

---

## **TICKET-9: Comprehensive Documentation**

**Priority:** High
**Estimate:** 3 hours

### Tasks Checklist

#### 9.1 Complete README.md
- [ ] Add project overview
- [ ] Document prerequisites
- [ ] Add installation instructions
- [ ] Add configuration guide with examples
- [ ] Document Okta setup (API token creation, finding group names)
- [ ] Document Grafana setup (API key creation, permissions needed)
- [ ] Add Docker run examples
- [ ] Add docker-compose usage
- [ ] Create environment variables reference table
- [ ] Add troubleshooting section
- [ ] Explain sync behavior
- [ ] Add development guide
- [ ] Add contributing guidelines

#### 9.2 Add Code Docstrings
- [ ] Review all modules for missing docstrings
- [ ] Add module-level docstrings
- [ ] Ensure all classes have docstrings
- [ ] Ensure all public methods have docstrings with Args/Returns/Raises

#### 9.3 Add Inline Comments
- [ ] Add comments for complex logic
- [ ] Explain non-obvious decisions

#### 9.4 Update CHANGELOG.md
- [ ] Add documentation entry

#### 9.5 Commit
- [ ] Commit all documentation

### Acceptance Criteria
- [ ] README is comprehensive and easy to follow
- [ ] Someone unfamiliar can set up and run the service
- [ ] All configuration options are documented
- [ ] API setup steps are clear
- [ ] Code is well-documented

---

## **TICKET-10: Testing - Ensure Complete Coverage**

**Priority:** Critical (not optional!)
**Estimate:** 2 hours

### Tasks Checklist

#### 10.1 Run Coverage Report
- [ ] Run: `poetry run pytest --cov=src --cov-report=html --cov-report=term-missing`
- [ ] Open `htmlcov/index.html` in browser
- [ ] Identify files/lines with missing coverage

#### 10.2 Add Missing Tests
- [ ] Add tests for any uncovered code paths
- [ ] Add edge case tests
- [ ] Add integration-style tests if needed

#### 10.3 Verify Coverage Target
- [ ] Ensure overall coverage is >80%
- [ ] Ensure critical modules (sync_service, clients) have >90%

#### 10.4 Create Test Documentation
- [ ] Document how to run tests
- [ ] Document test structure
- [ ] Add to README.md

#### 10.5 Update CHANGELOG.md
- [ ] Add comprehensive test coverage entry

#### 10.6 Commit
- [ ] Commit any new tests

### Acceptance Criteria
- [ ] All modules have tests
- [ ] Overall coverage >80%
- [ ] Critical paths have >90% coverage
- [ ] All tests pass in CI

---

## **TICKET-11: Monitoring & Observability (Optional)**

**Priority:** Low
**Estimate:** 3 hours

### Tasks Checklist

#### 11.1 Add Metrics Export
- [ ] Choose metrics library (prometheus_client recommended)
- [ ] Add metrics:
  - sync_duration_seconds (histogram)
  - users_added_total (counter)
  - users_removed_total (counter)
  - sync_errors_total (counter)
  - last_sync_timestamp (gauge)

#### 11.2 Add HTTP Health Check Endpoint
- [ ] Add optional HTTP server with /health endpoint
- [ ] Return sync status and metrics

#### 11.3 Enhance Logging
- [ ] Add sync summary logs after each run
- [ ] Include metrics in summary

#### 11.4 Add Tests
- [ ] Test metrics collection
- [ ] Test health endpoint

#### 11.5 Update Documentation
- [ ] Document metrics endpoint
- [ ] Document health check

#### 11.6 Update CHANGELOG.md and Commit

### Acceptance Criteria
- [ ] Metrics are available in Prometheus format
- [ ] Health check responds correctly
- [ ] Easy to see sync status from logs
- [ ] Metrics can be scraped for monitoring

---

## Summary

This document provides detailed, actionable tasks for implementing GOTS. Follow the tickets in order for best results. Remember to:

- Update CHANGELOG.md with every commit
- Follow semantic versioning
- Ensure >80% test coverage
- Run code quality checks before committing
- Write clear commit messages

**Estimated Total Effort:** 30-35 hours for full implementation with comprehensive testing and documentation.
