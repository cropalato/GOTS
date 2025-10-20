# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Grafana-Okta Team Sync (GOTS)** is a Python-based service that periodically syncs Okta group membership to Grafana teams. The service runs in a Docker container and performs scheduled synchronization to ensure Grafana team memberships match the corresponding Okta groups.

## Current Status

This repository contains the architectural design document (`grafana-okta-team-sync.md`) but the code has not been implemented yet. Follow the implementation tickets in the design document when building out the service.

## Planned Architecture

### Core Components

1. **Sync Service** (`src/sync_service.py`) - Core logic that compares Okta groups vs Grafana teams and executes add/remove operations
2. **Okta Client** (`src/okta_client.py`) - API wrapper for fetching groups and members from Okta
3. **Grafana Client** (`src/grafana_client.py`) - API wrapper for managing Grafana teams and users
4. **Configuration Manager** (`src/config.py`) - Loads YAML config and environment variables
5. **Main Application** (`src/main.py`) - Entry point with scheduler that runs sync operations

### Configuration Structure

The service uses YAML configuration with environment variable substitution:
- `okta.domain` and `okta.api_token` for Okta API access
- `grafana.url` and `grafana.api_key` for Grafana API access
- `sync.interval_seconds` for scheduling frequency
- `sync.dry_run` for testing without making changes
- `sync.mappings` array defining Okta group to Grafana team relationships

### Key Design Patterns

- **Dependency Injection**: SyncService receives client instances rather than creating them
- **Idempotent Operations**: Sync can run repeatedly without side effects
- **Retry Logic**: All API clients implement exponential backoff using `tenacity`
- **Graceful Degradation**: If one group sync fails, continue with remaining groups

## Development Commands

### Project Setup

This project uses **Poetry** for dependency management:

```bash
poetry install                  # Install all dependencies
poetry install --with dev       # Install with development dependencies
poetry shell                    # Activate virtual environment
```

### Testing

**All code must have corresponding tests.** Tests are executed using Poetry:

```bash
poetry run pytest               # Run all tests
poetry run pytest tests/test_sync_service.py  # Run specific test file
poetry run pytest -v            # Verbose output
poetry run pytest --cov=src --cov-report=term-missing  # Run with coverage report
poetry run pytest --cov=src --cov-report=html  # Generate HTML coverage report
poetry run pytest -k test_name  # Run specific test by name
```

### Code Quality

```bash
poetry run pylint src/          # Lint source code
poetry run black src/ tests/    # Format code
poetry run black --check src/ tests/  # Check formatting without changes
poetry run mypy src/            # Type checking
poetry run isort src/ tests/    # Sort imports
```

### Running Locally

```bash
poetry run python -m src.main   # Run the service directly
```

### Docker

```bash
docker build -t gots .          # Build container
docker-compose up               # Run with docker-compose for local testing
docker-compose up -d            # Run in background
docker-compose logs -f          # Follow logs
```

## Version Control and Changelog Management

### Semantic Versioning

This project adheres to **Semantic Versioning 2.0.0** (https://semver.org/spec/v2.0.0.html):

- **MAJOR version** (X.0.0): Incompatible API changes or breaking changes
- **MINOR version** (0.X.0): New functionality in a backwards-compatible manner
- **PATCH version** (0.0.X): Backwards-compatible bug fixes

Version format: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)

Additional labels for pre-release and build metadata:
- Pre-release: `1.0.0-alpha`, `1.0.0-beta.1`, `1.0.0-rc.1`
- Build metadata: `1.0.0+20130313144700`

### CHANGELOG.md Maintenance

**CRITICAL: The CHANGELOG.md file must be kept updated and clean at all times.**

The changelog follows the format specified at https://keepachangelog.com/en/1.1.0/

#### Changelog Structure

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New features go here

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes and vulnerability patches

## [1.0.0] - 2024-03-15

### Added
- Initial release
- Okta group synchronization
- Grafana team management
- Docker containerization

[Unreleased]: https://github.com/username/repo/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/username/repo/releases/tag/v1.0.0
```

#### When to Update CHANGELOG.md

**Update the changelog with EVERY git commit** that includes meaningful changes:

1. **Before committing code**, add an entry to the `[Unreleased]` section under the appropriate category:
   - `Added` for new features
   - `Changed` for changes in existing functionality
   - `Deprecated` for soon-to-be removed features
   - `Removed` for now removed features
   - `Fixed` for any bug fixes
   - `Security` for vulnerability fixes

2. **When creating a release**:
   - Move all `[Unreleased]` changes to a new version section
   - Add the version number and release date: `## [X.Y.Z] - YYYY-MM-DD`
   - Update the comparison links at the bottom
   - Create a git tag: `git tag -a vX.Y.Z -m "Release version X.Y.Z"`

3. **Changelog entry format**:
   - Use present tense ("Add feature" not "Added feature")
   - Be concise but descriptive
   - Reference issue/PR numbers when applicable: `Fix sync error for large groups (#42)`
   - Group related changes together

#### Example Workflow

```bash
# 1. Make code changes
vim src/okta_client.py

# 2. Update CHANGELOG.md BEFORE committing
vim CHANGELOG.md
# Add entry under [Unreleased] > [Added]:
# - Add retry logic for Okta API rate limits

# 3. Stage both files
git add src/okta_client.py CHANGELOG.md

# 4. Commit with semantic message
git commit -m "feat: add retry logic for Okta API rate limits

Implements exponential backoff when Okta returns 429 status.
Configurable max retries via config.yaml.

Refs #123"

# 5. When ready to release (e.g., v1.1.0)
# - Move [Unreleased] changes to [1.1.0] section in CHANGELOG.md
# - Update version in pyproject.toml
# - Commit: git commit -m "chore: release version 1.1.0"
# - Tag: git tag -a v1.1.0 -m "Release version 1.1.0"
# - Push: git push && git push --tags
```

### Git Commit Message Format

Follow conventional commit format for clear history:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature (triggers MINOR version bump)
- `fix`: Bug fix (triggers PATCH version bump)
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependency updates
- `ci`: CI/CD pipeline changes

**Breaking changes:** Add `BREAKING CHANGE:` in footer or `!` after type (triggers MAJOR version bump)

**Examples:**
```bash
feat(okta): add support for nested group membership
fix(sync): handle empty Grafana teams correctly
docs: update installation instructions in README
chore: bump dependencies to latest versions
feat(grafana)!: change team API to v2 (BREAKING CHANGE)
```

## Testing Requirements

### Coverage Expectations

- **All modules must have tests**: Every file in `src/` should have a corresponding test file in `tests/`
- **Minimum coverage target**: 80% code coverage
- **Critical paths**: 100% coverage for sync logic and API clients

### Test Organization

```
tests/
├── __init__.py
├── test_okta_client.py         # Test Okta API wrapper
├── test_grafana_client.py      # Test Grafana API wrapper
├── test_sync_service.py        # Test core sync logic
├── test_config.py              # Test configuration loading
├── test_main.py                # Test application entry point
└── test_utils.py               # Test utility functions
```

### Testing Approach

- Use `pytest` as the test framework
- Use `responses` library to mock HTTP API calls
- Use `pytest-mock` for mocking dependencies
- Test both success and failure scenarios
- Test edge cases (empty groups, missing users, API errors, rate limits)
- Test dry-run mode functionality
- Test retry logic and error handling

## GitHub Actions CI/CD Pipeline

The project is hosted on GitHub and uses GitHub Actions for CI/CD. The pipeline should be defined in `.github/workflows/`.

### Required Workflows

#### 1. CI Workflow (`.github/workflows/ci.yml`)

Runs on every push and pull request:

```yaml
name: CI

on: [push, pull_request]

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
      - name: Run linting
        run: |
          poetry run black --check src/ tests/
          poetry run pylint src/
          poetry run mypy src/
      - name: Run tests with coverage
        run: poetry run pytest --cov=src --cov-report=xml --cov-report=term
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.11'
```

#### 2. Docker Build Workflow (`.github/workflows/docker.yml`)

Builds and pushes Docker images:

```yaml
name: Docker Build

on:
  push:
    branches: [main]
    tags: ['v*']

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
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.sha }}
```

#### 3. Release Workflow (`.github/workflows/release.yml`)

Creates releases when tags are pushed:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true
```

## Implementation Guidelines

### API Client Implementation

When implementing API clients (`okta_client.py`, `grafana_client.py`):
- Use `requests` library for HTTP calls
- Implement retry logic with `tenacity` decorator
- Add structured logging for all API calls
- Handle pagination for large result sets (especially Okta groups)
- Raise custom exceptions for different error types (auth, not found, rate limit)
- **All client methods must have corresponding unit tests with mocked responses**

### Sync Service Logic

The sync process for each mapping:
1. Fetch Okta group members by group name
2. Get or create corresponding Grafana team
3. Fetch current Grafana team members
4. Calculate diff (members to add, members to remove)
5. For each new member: get or create Grafana user, then add to team
6. For each removed member: remove from Grafana team
7. Track metrics (users added/removed, errors, duration)

### Error Handling

- Transient failures (network errors, timeouts) should retry with exponential backoff
- Permanent failures (404, invalid credentials) should log and skip
- Individual sync failures should not stop the entire process
- All exceptions must be logged with full context for debugging

### Docker Best Practices

- Use multi-stage builds to minimize image size
- Run as non-root user (`syncuser`)
- Support configuration via environment variables
- Use `python:3.11-slim` as base image
- Handle SIGTERM for graceful shutdown
- Copy only necessary files (use `.dockerignore`)

## Key Dependencies

### Runtime Dependencies
- `requests` - HTTP client for Okta and Grafana APIs
- `pyyaml` - Configuration file parsing
- `python-dotenv` - Environment variable management
- `schedule` - Periodic task scheduling
- `tenacity` - Retry logic with exponential backoff

### Development Dependencies
- `pytest` - Testing framework
- `pytest-cov` - Code coverage reporting
- `pytest-mock` - Mocking support
- `responses` - HTTP response mocking
- `pylint` - Code linting
- `black` - Code formatting
- `mypy` - Static type checking
- `isort` - Import sorting

## Project Files Structure

When implementing, create these files:

```
.
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI pipeline
│       ├── docker.yml          # Docker build and push
│       └── release.yml         # Release workflow
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point & scheduler
│   ├── okta_client.py          # Okta API wrapper
│   ├── grafana_client.py       # Grafana API wrapper
│   ├── sync_service.py         # Core sync logic
│   ├── config.py               # Configuration loader
│   └── utils.py                # Common utilities
├── tests/
│   ├── __init__.py
│   ├── test_okta_client.py     # Tests for Okta client
│   ├── test_grafana_client.py  # Tests for Grafana client
│   ├── test_sync_service.py    # Tests for sync service
│   ├── test_config.py          # Tests for config
│   ├── test_main.py            # Tests for main
│   └── test_utils.py           # Tests for utils
├── pyproject.toml              # Poetry configuration
├── poetry.lock                 # Poetry lock file
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Local testing setup
├── .dockerignore               # Docker build exclusions
├── .gitignore                  # Git exclusions
├── config.example.yaml         # Example configuration
├── .env.example                # Example environment variables
├── CHANGELOG.md                # Project changelog (Keep a Changelog format)
├── README.md                   # Project documentation
└── CLAUDE.md                   # This file
```

## API Documentation References

- Okta Groups API: https://developer.okta.com/docs/reference/api/groups/
- Grafana HTTP API: https://grafana.com/docs/grafana/latest/developers/http_api/

## Implementation Order

Follow the ticket sequence in `grafana-okta-team-sync.md`:
1. TICKET-1: Project scaffolding (include Poetry setup, GitHub Actions, and initialize CHANGELOG.md)
2. TICKET-2: Configuration management (with tests, update CHANGELOG.md)
3. TICKET-3: Okta API client (with comprehensive tests, update CHANGELOG.md)
4. TICKET-4: Grafana API client (with comprehensive tests, update CHANGELOG.md)
5. TICKET-5: Sync service logic (with comprehensive tests, update CHANGELOG.md)
6. TICKET-6: Main application and scheduler (with tests, update CHANGELOG.md)
7. TICKET-7: Docker containerization (update CHANGELOG.md)
8. TICKET-8: Error handling and resilience (with failure scenario tests, update CHANGELOG.md)
9. TICKET-9: Documentation (update CHANGELOG.md)
10. TICKET-10: Ensure 80%+ test coverage and all edge cases covered
11. TICKET-11: Monitoring and observability (optional, update CHANGELOG.md if implemented)

**Important reminders:**
- **Testing is mandatory, not optional.** Every ticket that involves code must include corresponding tests.
- **CHANGELOG.md must be updated with every meaningful commit.** Add entries to the [Unreleased] section before committing.
- **Follow Semantic Versioning** for all releases and version tags.
