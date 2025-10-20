# Project Architecture: Grafana-Okta Team Sync Service

## Overview

A Python-based service that periodically syncs Okta group membership to Grafana teams, running in a Docker container.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│         Docker Container (Python Service)           │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │           Main Application Loop              │  │
│  │      (Scheduler - runs every N minutes)      │  │
│  └────────────────┬─────────────────────────────┘  │
│                   │                                 │
│  ┌────────────────▼─────────────────────────────┐  │
│  │          Sync Service (Core Logic)           │  │
│  │  - Compare Okta groups vs Grafana teams      │  │
│  │  - Determine add/remove operations           │  │
│  │  - Execute sync & track metrics              │  │
│  └────┬─────────────────────────────────┬───────┘  │
│       │                                 │           │
│  ┌────▼──────────┐              ┌──────▼────────┐  │
│  │ Okta Client   │              │Grafana Client │  │
│  │ - Get groups  │              │- Manage teams │  │
│  │ - Get members │              │- Manage users │  │
│  └───────────────┘              └───────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │       Configuration Manager                   │  │
│  │  (YAML + Environment Variables)              │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   Okta API                      Grafana API
 (acme.okta.com)         (your-grafana-server)
```

## Project Structure

```
grafana-okta-team-sync/
├── Dockerfile
├── docker-compose.yml          # For local testing
├── requirements.txt
├── README.md
├── .env.example
├── config.example.yaml
├── src/
│   ├── __init__.py
│   ├── main.py                # Entry point & scheduler
│   ├── okta_client.py         # Okta API wrapper
│   ├── grafana_client.py      # Grafana API wrapper
│   ├── sync_service.py        # Core sync logic
│   ├── config.py              # Configuration loader
│   └── utils.py               # Common utilities
└── tests/
    ├── __init__.py
    ├── test_okta_client.py
    ├── test_grafana_client.py
    └── test_sync_service.py
```

## Configuration Format

```yaml
okta:
  domain: acme.okta.com
  api_token: ${OKTA_API_TOKEN}

grafana:
  url: http://your-grafana-server:3000
  api_key: ${GRAFANA_API_KEY}

sync:
  interval_seconds: 300 # Run every 5 minutes
  dry_run: false # Set true to preview without changes
  mappings:
    - okta_group: "Group1"
      grafana_team: "Team1"
    - okta_group: "Group2"
      grafana_team: "Team2"
    - okta_group: "Group3"
      grafana_team: "Team3"

logging:
  level: INFO
  format: json # or 'text'
```

## Key Dependencies

- `requests` - HTTP client for API calls
- `pyyaml` - Configuration file parsing
- `python-dotenv` - Environment variable management
- `schedule` - Periodic task scheduling
- `tenacity` - Retry logic with backoff

---

# Implementation Tickets

## **TICKET-1: Project Scaffolding & Setup**

**Priority:** Critical
**Estimate:** 30 minutes

**Tasks:**

- Create directory structure (`src/`, `tests/`, root files)
- Create `requirements.txt` with initial dependencies
- Create `.env.example` with placeholder secrets
- Create `config.example.yaml` with sample mappings
- Create basic `README.md` structure
- Initialize Python package with `__init__.py` files

**Acceptance Criteria:**

- Project structure matches architecture
- Example files are properly documented
- README explains what the project does

---

## **TICKET-2: Configuration Management Module**

**Priority:** Critical
**Estimate:** 2 hours

**Tasks:**

- Implement `config.py` with `Config` class
- Load YAML configuration file
- Override with environment variables
- Validate required fields (Okta domain, tokens, mappings)
- Support both file-based and env-only config
- Add helpful error messages for missing config

**Acceptance Criteria:**

- Config loads from YAML and env vars correctly
- Missing required fields raise clear errors
- Multiple group mappings are supported
- Config object is easily accessible to other modules

---

## **TICKET-3: Okta API Client**

**Priority:** Critical
**Estimate:** 3 hours

**Tasks:**

- Create `okta_client.py` with `OktaClient` class
- Implement authentication with API token
- Method: `get_group_by_name(group_name)` → group object
- Method: `get_group_members(group_id)` → list of users
- Handle pagination for large groups
- Implement retry logic with exponential backoff
- Add structured logging for API calls
- Handle common errors (404, 401, rate limits)

**Acceptance Criteria:**

- Successfully authenticates with Okta
- Can fetch group by name
- Can fetch all members with pagination
- Retries on transient failures
- Logs all API interactions

**API Documentation:** https://developer.okta.com/docs/reference/api/groups/

---

## **TICKET-4: Grafana API Client**

**Priority:** Critical
**Estimate:** 4 hours

**Tasks:**

- Create `grafana_client.py` with `GrafanaClient` class
- Implement authentication with API key
- Method: `get_or_create_team(team_name)` → team object
- Method: `get_team_members(team_id)` → list of users
- Method: `add_user_to_team(team_id, user_email)` → success/fail
- Method: `remove_user_from_team(team_id, user_id)` → success/fail
- Method: `get_or_create_user(email, name)` → user object
- Handle case where Okta user doesn't exist in Grafana yet
- Implement retry logic
- Add structured logging

**Acceptance Criteria:**

- Successfully authenticates with Grafana
- Creates teams idempotently
- Adds/removes users from teams
- Creates users if they don't exist (from Okta SSO)
- Handles all error cases gracefully

**API Documentation:** https://grafana.com/docs/grafana/latest/developers/http_api/

---

## **TICKET-5: Sync Service Logic**

**Priority:** Critical
**Estimate:** 3 hours

**Tasks:**

- Create `sync_service.py` with `SyncService` class
- Inject OktaClient and GrafanaClient as dependencies
- Method: `sync_group_to_team(okta_group, grafana_team)`
- Compare Okta group members vs Grafana team members
- Calculate diff (users to add, users to remove)
- Execute add operations
- Execute remove operations
- Track metrics (added, removed, errors, duration)
- Support dry-run mode (log actions without executing)
- Comprehensive error handling

**Acceptance Criteria:**

- Correctly identifies members to add/remove
- Executes sync operations in correct order
- Tracks detailed metrics for each sync
- Dry-run mode works without making changes
- Sync is idempotent (can run repeatedly safely)

---

## **TICKET-6: Main Application & Scheduler**

**Priority:** Critical
**Estimate:** 2 hours

**Tasks:**

- Create `main.py` with application entry point
- Load configuration on startup
- Initialize Okta and Grafana clients
- Initialize SyncService
- Setup structured logging (JSON or text format)
- Implement sync loop using `schedule` library
- Run initial sync on startup
- Run periodic sync based on config interval
- Handle SIGTERM/SIGINT for graceful shutdown
- Add startup banner with config summary

**Acceptance Criteria:**

- Application starts successfully
- Runs initial sync on startup
- Continues to sync on schedule
- Gracefully shuts down on signals
- Logs are clear and structured

---

## **TICKET-7: Docker Containerization**

**Priority:** High
**Estimate:** 2 hours

**Tasks:**

- Create `Dockerfile` with multi-stage build
- Use `python:3.11-slim` base image
- Copy requirements and install dependencies
- Copy source code
- Create non-root user for security
- Set proper working directory
- Define CMD to run main.py
- Create `docker-compose.yml` for local testing
- Add health check (optional - simple endpoint or file)
- Optimize image size

**Acceptance Criteria:**

- Docker image builds successfully
- Image size is reasonable (<200MB)
- Container runs without root privileges
- Can pass config via environment variables
- docker-compose.yml works for local testing

**Dockerfile Example:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
RUN useradd -m -u 1000 syncuser && chown -R syncuser:syncuser /app
USER syncuser
CMD ["python", "-m", "src.main"]
```

---

## **TICKET-8: Error Handling & Resilience**

**Priority:** High
**Estimate:** 2 hours

**Tasks:**

- Add retry logic to API clients using `tenacity`
- Implement exponential backoff for retries
- Handle rate limiting from Okta/Grafana
- Catch and log all exceptions properly
- Continue syncing other groups if one fails
- Add circuit breaker pattern for repeated failures (optional)
- Log stack traces for debugging

**Acceptance Criteria:**

- Transient failures are retried automatically
- Permanent failures are logged and skipped
- Service continues running despite individual sync failures
- Clear error messages for troubleshooting

---

## **TICKET-9: Comprehensive Documentation**

**Priority:** High
**Estimate:** 2 hours

**Tasks:**

- Complete README.md with:
  - Project overview and architecture
  - Prerequisites (Okta API token, Grafana API key)
  - Configuration guide with examples
  - Okta setup instructions (create API token, find group names)
  - Grafana setup instructions (create API key with Team Admin role)
  - Docker run commands
  - docker-compose usage
  - Environment variables reference
  - Troubleshooting common issues
  - Sync behavior explanation
- Document code with docstrings
- Add inline comments for complex logic

**Acceptance Criteria:**

- README is comprehensive and easy to follow
- Someone unfamiliar can set up and run the service
- All configuration options are documented
- API setup steps are clear

---

## **TICKET-10: Testing (Optional but Recommended)**

**Priority:** Medium
**Estimate:** 3 hours

**Tasks:**

- Create unit tests for `okta_client.py` with mocked responses
- Create unit tests for `grafana_client.py` with mocked responses
- Create unit tests for `sync_service.py` with mock clients
- Use `pytest` and `responses` library for HTTP mocking
- Test edge cases (empty groups, API errors, etc.)
- Aim for >70% code coverage

**Acceptance Criteria:**

- All critical paths are tested
- Tests run with `pytest`
- Mock data represents real API responses
- Tests are fast and don't require real APIs

---

## **TICKET-11: Monitoring & Observability (Optional Enhancement)**

**Priority:** Low
**Estimate:** 2 hours

**Tasks:**

- Add metrics export (Prometheus format)
- Track: sync duration, users added/removed, errors
- Add health check HTTP endpoint
- Log sync summary after each run
- Optional: Send alerts on consecutive failures

**Acceptance Criteria:**

- Metrics are available for monitoring
- Health check responds correctly
- Easy to see sync status from logs

---

# Total Estimated Effort

- **Critical tickets (1-6):** ~14 hours
- **High priority (7-8):** ~4 hours
- **Documentation (9):** ~2 hours
- **Optional (10-11):** ~5 hours

**Minimum Viable Product:** Tickets 1-7 + 9 = ~20 hours

---

# Recommended Implementation Order

1. TICKET-1 → TICKET-2 (Setup foundation)
2. TICKET-3 → TICKET-4 (Build API clients)
3. TICKET-5 (Core sync logic)
4. TICKET-6 (Make it run)
5. TICKET-7 (Containerize)
6. TICKET-8 (Harden)
7. TICKET-9 (Document)
8. TICKET-10, 11 (If time permits)
