# Grafana-Okta Team Sync (GOTS)

A Python service that automatically synchronizes Okta group membership to Grafana teams. GOTS ensures your Grafana team memberships stay in sync with your Okta groups, eliminating manual user management.

## Features

- **Bidirectional Synchronization**: Adds users from Okta groups to Grafana teams and removes users no longer in Okta
- **Periodic Sync**: Configurable sync intervals (minimum 60 seconds)
- **Dry-Run Mode**: Test sync operations without making actual changes
- **Multiple Mappings**: Sync multiple Okta groups to different Grafana teams
- **Comprehensive Error Handling**: Retry logic with exponential backoff for transient failures
- **Partial Failure Tolerance**: Continues syncing even if individual operations fail
- **Structured Logging**: JSON or text format logging with configurable levels
- **Prometheus Metrics**: Built-in metrics export for monitoring and alerting
- **Health Checks**: HTTP endpoints for Kubernetes liveness/readiness probes
- **Docker Support**: Containerized deployment with minimal image size (162MB)
- **Graceful Shutdown**: Handles SIGTERM/SIGINT signals properly

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Okta Setup](#okta-setup)
- [Grafana Setup](#grafana-setup)
- [Running the Service](#running-the-service)
- [Docker Deployment](#docker-deployment)
- [Monitoring & Observability](#monitoring--observability)
- [How Sync Works](#how-sync-works)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Prerequisites

- **Python 3.10+** (for local development)
- **Docker** (optional, for containerized deployment)
- **Okta API Token** with group read permissions
- **Grafana API Key** with admin permissions (to create teams and users)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/cropalato/gots.git
cd gots
```

### 2. Install Dependencies

```bash
# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 3. Configure Credentials

```bash
# Copy configuration templates
cp .env.example .env
cp config.example.yaml config.yaml

# Edit .env with your Okta and Grafana credentials
nano .env

# Edit config.yaml to define your group mappings
nano config.yaml
```

### 4. Test with Dry-Run Mode

```bash
# Set dry_run: true in config.yaml first
poetry run python -m src.main
```

### 5. Run the Service

```bash
# After verifying dry-run results, set dry_run: false
poetry run python -m src.main
```

## Configuration

GOTS uses a YAML configuration file combined with environment variables. Environment variables take precedence over YAML settings.

### Configuration File Structure

**config.yaml:**

```yaml
okta:
  domain: ${OKTA_DOMAIN}        # Okta domain (e.g., company.okta.com)
  api_token: ${OKTA_API_TOKEN}  # Okta API token

grafana:
  url: ${GRAFANA_URL}           # Grafana URL (e.g., https://grafana.example.com)
  api_key: ${GRAFANA_API_KEY}   # Grafana API key

sync:
  interval_seconds: 300          # Sync frequency (minimum 60 seconds)
  dry_run: false                 # true = preview changes, false = apply changes
  mappings:
    - okta_group: "Engineering"  # Exact Okta group name
      grafana_team: "Engineers"  # Grafana team name (created if doesn't exist)
    - okta_group: "DataScience"
      grafana_team: "Data Scientists"

logging:
  level: INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: json                   # json or text
```

### Environment Variables

All configuration options can be set via environment variables:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OKTA_DOMAIN` | Okta domain (without https://) | Yes | - |
| `OKTA_AUTH_METHOD` | Okta auth method (api_token or oauth) | No | api_token |
| `OKTA_API_TOKEN` | Okta API token (for api_token method) | Conditional | - |
| `OKTA_CLIENT_ID` | OAuth client ID (for oauth method) | Conditional | - |
| `OKTA_CLIENT_SECRET` | OAuth client secret (for oauth method) | Conditional | - |
| `OKTA_SCOPES` | OAuth scopes, comma-separated (for oauth method) | Conditional | - |
| `GRAFANA_URL` | Grafana server URL | Yes | - |
| `GRAFANA_API_KEY` | Grafana API key | Yes | - |
| `SYNC_INTERVAL_SECONDS` | Sync frequency in seconds | No | 300 |
| `SYNC_DRY_RUN` | Dry-run mode (true/false) | No | false |
| `LOG_LEVEL` | Logging level | No | INFO |
| `LOG_FORMAT` | Log format (json/text) | No | json |
| `METRICS_ENABLED` | Enable Prometheus metrics (true/false) | No | false |
| `METRICS_PORT` | Metrics HTTP server port | No | 8000 |
| `METRICS_HOST` | Metrics server bind address | No | 0.0.0.0 |

### Variable Expansion

The YAML configuration supports `${VAR_NAME}` syntax for environment variable expansion:

```yaml
okta:
  domain: ${OKTA_DOMAIN}  # Expands to value of OKTA_DOMAIN env var
  api_token: ${OKTA_API_TOKEN}
```

## Okta Setup

GOTS supports two authentication methods for connecting to Okta: **API Token** (default) and **OAuth 2.0** (recommended for production). Choose the method that best fits your security requirements.

### Authentication Methods

#### Option 1: API Token Authentication (Default)

Simple setup using an API token. Suitable for testing and smaller deployments.

**Steps:**

1. Log into your Okta Admin Console
2. Navigate to **Security** → **API** → **Tokens**
3. Click **Create Token**
4. Name it (e.g., "Grafana Team Sync")
5. Copy the token immediately (it won't be shown again)
6. Set `OKTA_API_TOKEN` to this value in your `.env` file

**Configuration:**
```yaml
okta:
  domain: ${OKTA_DOMAIN}
  auth_method: api_token  # Default
  api_token: ${OKTA_API_TOKEN}
```

#### Option 2: OAuth 2.0 Authentication (Recommended)

More secure with automatic token rotation. Recommended for production environments.

**Benefits:**
- Short-lived access tokens (automatically refreshed)
- Better security posture with granular scopes
- No need for manual token rotation
- Appears in Okta audit logs as OAuth app activity

**Steps:**

1. **Create OAuth 2.0 Application in Okta:**
   - Log into Okta Admin Console
   - Navigate to **Applications** → **Applications**
   - Click **Create App Integration**
   - Select **API Services** (for M2M communication)
   - Name it (e.g., "Grafana Team Sync OAuth")
   - Click **Save**

2. **Note Client Credentials:**
   - Copy the **Client ID**
   - Copy the **Client Secret** (shown only once)
   - Set `OKTA_CLIENT_ID` and `OKTA_CLIENT_SECRET` in your `.env` file

3. **Grant Required Scopes:**
   - In the Okta Admin Console, go to **Security** → **API** → **Authorization Servers**
   - Select your authorization server (usually "default")
   - Go to the **Scopes** tab
   - Ensure these scopes exist (create if needed):
     - `okta.groups.read` - Read group information
     - `okta.users.read` - Read user information
   - Navigate to **Applications** → Your OAuth app → **Okta API Scopes**
   - Grant the following scopes:
     - `okta.groups.read`
     - `okta.users.read`

4. **Assign Admin Role (Critical!):**
   - In the same OAuth application, go to the **Admin Roles** tab
   - Click **Add Role** or **Grant**
   - Select **Group Administrator** (recommended for least privilege)
   - Click **Save**
   - **Note**: This step is required! Scopes alone are not sufficient for OAuth for Okta. See [OKTA_ADMIN_ROLE_SETUP.md](OKTA_ADMIN_ROLE_SETUP.md) for details.

**Configuration:**
```yaml
okta:
  domain: ${OKTA_DOMAIN}
  auth_method: oauth
  oauth:
    client_id: ${OKTA_CLIENT_ID}
    client_secret: ${OKTA_CLIENT_SECRET}
    scopes:
      - okta.groups.read
      - okta.users.read
```

**Environment Variables:**
```bash
OKTA_AUTH_METHOD=oauth
OKTA_CLIENT_ID=your-client-id-here
OKTA_CLIENT_SECRET=your-client-secret-here
OKTA_SCOPES=okta.groups.read,okta.users.read
```

### Find Your Okta Domain

Your Okta domain is the subdomain in your Okta URL:
- If your Okta URL is `https://company.okta.com`
- Your domain is `company.okta.com`
- Set `OKTA_DOMAIN=company.okta.com`

### Find Group Names

1. In Okta Admin Console, go to **Directory** → **Groups**
2. Find the groups you want to sync
3. Note the **exact group names** (case-sensitive)
4. Use these exact names in the `okta_group` field in config.yaml

### Required Permissions

**API Token Method:**
- The API token needs **read-only** access to groups and users
- Default token permissions are sufficient

**OAuth Method:**
- Requires `okta.groups.read` and `okta.users.read` scopes
- Scopes must be granted to the OAuth application

## Grafana Setup

### 1. Create an API Key

1. Log into Grafana as an admin
2. Navigate to **Configuration** → **API Keys** (or **Service Accounts** in Grafana 9+)
3. Click **Add API Key** (or **Add service account**)
4. Name it (e.g., "Okta Team Sync")
5. Role: **Admin** (required to create teams and users)
6. Set `GRAFANA_API_KEY` to the generated key

**Note:** Admin role is required because GOTS needs to:
- Create teams (if they don't exist)
- Create users (if they don't exist in Grafana)
- Add/remove users from teams

### 2. Get Your Grafana URL

Set `GRAFANA_URL` to your Grafana server URL:
- Example: `https://grafana.company.com`
- Include the protocol (`https://` or `http://`)

### SSL/TLS Certificates

If your Grafana instance uses a self-signed certificate:

```bash
# Option 1: Set CA bundle path
export REQUESTS_CA_BUNDLE=/path/to/ca-certificates.crt

# Option 2: In Docker, mount the certificate
volumes:
  - /etc/ssl/certs:/app/certs:ro
environment:
  - REQUESTS_CA_BUNDLE=/app/certs/ca-certificates.crt
```

## Running the Service

### Local Execution

```bash
# Run with default config.yaml
poetry run python -m src.main

# Run with custom config file
poetry run python -m src.main /path/to/custom-config.yaml
```

### First Run Recommendations

1. **Start with dry-run mode** (`dry_run: true`)
2. Check the logs to verify what changes would be made
3. If everything looks correct, set `dry_run: false`
4. Monitor the first few syncs to ensure expected behavior

### Logs

The service outputs structured logs showing:
- Sync operations (users added/removed)
- API interactions
- Errors and warnings
- Sync metrics (duration, counts)

Example log output (text format):
```
2025-01-20 10:00:00 - INFO - Starting sync: Engineering -> Engineers
2025-01-20 10:00:01 - INFO - Found 25 members in Okta group 'Engineering'
2025-01-20 10:00:01 - INFO - Found 23 members in Grafana team 'Engineers'
2025-01-20 10:00:01 - INFO - Sync diff: 2 to add, 0 to remove
2025-01-20 10:00:02 - INFO - Added user john.doe@company.com to team Engineers
2025-01-20 10:00:02 - INFO - Added user jane.smith@company.com to team Engineers
2025-01-20 10:00:02 - INFO - Sync completed: +2 users, -0 users, 0 errors, 1.50s
```

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Create docker-compose.yml:**

```yaml
version: '3.8'

services:
  gots:
    image: ghcr.io/cropalato/gots:latest  # or build locally: build: .
    container_name: gots
    env_file:
      - .env
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    restart: unless-stopped
```

2. **Create .env file with credentials:**

```bash
OKTA_DOMAIN=company.okta.com
OKTA_API_TOKEN=your-token-here
GRAFANA_URL=https://grafana.example.com
GRAFANA_API_KEY=your-api-key-here
SYNC_DRY_RUN=false
LOG_LEVEL=INFO
LOG_FORMAT=json
```

3. **Run the service:**

```bash
docker-compose up -d
```

4. **View logs:**

```bash
docker-compose logs -f
```

### Using Docker Directly

```bash
# Build the image
docker build -t gots:latest .

# Run the container
docker run -d --name gots \
  --env-file .env \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  gots:latest

# View logs
docker logs -f gots
```

### Docker Environment

- Base image: `python:3.11-slim`
- Final image size: **162MB**
- Runs as non-root user (`syncuser`, UID 1000)
- Config file location: `/app/config.yaml`

## Monitoring & Observability

GOTS includes comprehensive monitoring and observability features for production deployments.

### Prometheus Metrics

Enable Prometheus metrics export to track sync operations, errors, and performance:

**Configuration:**

```yaml
metrics:
  enabled: true      # Enable metrics export
  port: 8000         # HTTP server port
  host: 0.0.0.0      # Bind address
```

Or via environment variables:
```bash
METRICS_ENABLED=true
METRICS_PORT=8000
METRICS_HOST=0.0.0.0
```

**Exported Metrics:**

- `gots_sync_duration_seconds` - Histogram of sync operation durations
- `gots_users_added_total` - Counter of users added to Grafana teams
- `gots_users_removed_total` - Counter of users removed from Grafana teams
- `gots_sync_errors_total` - Counter of sync errors
- `gots_last_sync_timestamp` - Timestamp of last sync completion
- `gots_last_sync_success` - Success/failure status of last sync (1=success, 0=failure)

All metrics include labels for `okta_group` and `grafana_team` to track per-mapping statistics.

### Health Endpoints

When metrics are enabled, GOTS exposes two HTTP endpoints:

- **`/health`** - Health check endpoint (returns JSON status)
- **`/metrics`** - Prometheus metrics endpoint (Prometheus text format)

Access them at `http://localhost:8000/health` and `http://localhost:8000/metrics`.

### Kubernetes Integration

**Health Probes:**

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

**Prometheus ServiceMonitor:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: gots
spec:
  selector:
    matchLabels:
      app: gots
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```

### Production Monitoring

For comprehensive production monitoring setup, see **[MONITORING.md](MONITORING.md)**, which includes:

- Complete Prometheus alert rules (18 alerts for critical/warning/info scenarios)
- AlertManager configuration with severity-based routing
- Grafana dashboard recommendations with example queries
- Troubleshooting runbooks for common issues
- Best practices for alert management and SLO monitoring

**Quick Links:**
- [Prometheus Alert Rules](prometheus-alerts.yaml) - Production-ready alert definitions
- [AlertManager Config Example](alertmanager-config-example.yaml) - Notification routing and templates
- [Monitoring Guide](MONITORING.md) - Complete monitoring and alerting documentation

## How Sync Works

### Sync Process

For each mapping in your configuration:

1. **Fetch Okta Group Members**: Retrieves all users in the Okta group
2. **Get or Create Grafana Team**: Creates the team if it doesn't exist
3. **Fetch Grafana Team Members**: Retrieves current team members
4. **Calculate Diff**:
   - Users to add: In Okta but not in Grafana
   - Users to remove: In Grafana but not in Okta
5. **Execute Operations**:
   - Add missing users (creates Grafana user if needed)
   - Remove extra users from the team
6. **Track Metrics**: Records users added/removed, errors, duration

### Sync Behavior

- **Idempotent**: Running the same sync multiple times produces the same result
- **Case-Insensitive**: Email matching is case-insensitive
- **Partial Failure Tolerant**: If adding/removing one user fails, other operations continue
- **Team Creation**: Grafana teams are created automatically if they don't exist
- **User Creation**: Grafana users are created automatically if they don't exist

### What Gets Synced

- ✅ **User membership**: Users added to/removed from teams
- ❌ **User attributes**: Names, roles, etc. are NOT synced
- ❌ **Team settings**: Team permissions and settings are NOT modified

### Frequency

- Sync runs immediately on startup
- Then runs on the configured interval (default: 5 minutes)
- Minimum interval: 60 seconds

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/cropalato/gots.git
cd gots

# Install dependencies including dev tools
poetry install --with dev

# Activate virtual environment
poetry shell
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=src --cov-report=term-missing

# Run with HTML coverage report
poetry run pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser

# Run specific test file
poetry run pytest tests/test_sync_service.py -v

# Run specific test
poetry run pytest tests/test_sync_service.py::TestSyncService::test_sync_with_users_to_add -v
```

### Code Quality Checks

```bash
# Format code (auto-fix)
poetry run black src/ tests/

# Sort imports (auto-fix)
poetry run isort src/ tests/

# Lint code
poetry run pylint src/

# Type checking
poetry run mypy src/

# Run all checks
poetry run black src/ tests/ && \
poetry run isort src/ tests/ && \
poetry run pylint src/ && \
poetry run mypy src/
```

### Project Structure

```
.
├── src/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── okta_client.py       # Okta API client
│   ├── grafana_client.py    # Grafana API client
│   └── sync_service.py      # Core sync logic
├── tests/
│   ├── test_main.py
│   ├── test_config.py
│   ├── test_okta_client.py
│   ├── test_grafana_client.py
│   └── test_sync_service.py
├── pyproject.toml           # Poetry configuration
├── Dockerfile
├── docker-compose.yml
├── config.example.yaml
└── .env.example
```

### Making Changes

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Run code quality checks
5. Update CHANGELOG.md
6. Submit a pull request

## Troubleshooting

### Common Issues

#### "Authentication failed - invalid API token"

**Cause**: Invalid Okta API token or expired token

**Solution**:
- Verify `OKTA_API_TOKEN` is correct
- Check token hasn't expired in Okta Admin Console
- Create a new token if needed

#### "Group not found: GroupName"

**Cause**: Okta group name doesn't match exactly

**Solution**:
- Group names are **case-sensitive**
- Verify exact group name in Okta Admin Console
- Check for extra spaces or special characters

#### "SSL Certificate verification failed"

**Cause**: Self-signed certificate or corporate proxy

**Solution**:
```bash
# Set CA bundle path
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt

# Or in Docker
environment:
  - REQUESTS_CA_BUNDLE=/app/certs/ca-certificates.crt
volumes:
  - /etc/ssl/certs:/app/certs:ro
```

#### "Rate limit exceeded"

**Cause**: Too many API requests to Okta

**Solution**:
- The service automatically retries with exponential backoff
- Increase `interval_seconds` to reduce request frequency
- Wait for rate limit reset (shown in logs)

#### Users not being added to Grafana

**Cause**: Insufficient Grafana API key permissions

**Solution**:
- Ensure API key has **Admin** role
- In Grafana 9+, use Service Accounts with Admin permissions

#### Sync completes but some users fail

**Cause**: Individual user operations can fail (e.g., invalid email)

**Solution**:
- Check logs for specific error messages
- The sync continues for other users
- Errors are tracked in metrics
- Fix the underlying issue (e.g., user email format)

### Debugging

Enable debug logging for detailed information:

```yaml
logging:
  level: DEBUG
  format: text  # More readable than json for debugging
```

Or via environment variable:
```bash
export LOG_LEVEL=DEBUG
export LOG_FORMAT=text
```

### Getting Help

- Check logs first (look for ERROR or WARNING messages)
- Review this troubleshooting section
- Check [GitHub Issues](https://github.com/cropalato/gots/issues)
- Create a new issue with:
  - GOTS version
  - Error message and logs
  - Configuration (redact credentials!)
  - Steps to reproduce

## Contributing

Contributions are welcome! Please follow these guidelines:

### Reporting Issues

- Use the GitHub issue tracker
- Include version, error messages, and steps to reproduce
- Redact all credentials and sensitive information

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`poetry run pytest`)
6. Run code quality checks
7. Update CHANGELOG.md under `[Unreleased]`
8. Commit your changes
9. Push to your fork
10. Create a Pull Request

### Development Guidelines

- Follow existing code style (enforced by black/pylint)
- Add docstrings to all public functions/classes
- Write tests for new features (aim for >80% coverage)
- Update documentation as needed
- Keep commits atomic and write clear commit messages

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Poetry](https://python-poetry.org/)
- Uses [Tenacity](https://github.com/jd/tenacity) for retry logic
- Scheduled with [schedule](https://github.com/dbader/schedule)
- Containerized with Docker

---

**Maintained by**: Ricardo Melo ([@cropalato](https://github.com/cropalato))

**Project**: [https://github.com/cropalato/gots](https://github.com/cropalato/gots)
