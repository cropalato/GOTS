# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffolding
- Poetry dependency management setup
- Configuration examples (.env.example, config.example.yaml)
- Project directory structure (src/, tests/, .github/workflows/)
- Placeholder modules for core functionality
- GitHub Actions CI/CD workflows
- Development tool configuration (black, pylint, mypy, pytest, isort)
- Configuration management module with YAML and environment variable support
- Configuration validation with clear error messages
- Support for multiple Okta-to-Grafana group mappings
- Environment variable expansion (${VAR_NAME} syntax) in YAML configuration
- Comprehensive test suite for configuration module (36 test cases, 100% coverage)
- Okta API client with group search and member retrieval
- Automatic pagination support for large Okta groups
- Retry logic with exponential backoff for transient failures
- Comprehensive error handling (401, 404, 429, 5xx errors)
- Custom exception types for different error scenarios
- Rate limit tracking and logging
- Comprehensive test suite for Okta client (19 test cases with mocked HTTP responses)
- Grafana API client with team and user management
- Team operations: search, create, and get-or-create with automatic retrieval
- User operations: lookup, create, and get-or-create with email-based search
- Team membership operations: add and remove users from teams
- Retry logic with exponential backoff for HTTP requests
- Comprehensive error handling (401, 403, 404, 409, 5xx errors)
- Support for both 200 OK and 201 Created success responses
- Comprehensive test suite for Grafana client (29 test cases, 100% coverage)
- Core sync service with bidirectional member synchronization
- Dry-run mode for testing sync operations without making changes
- Sync metrics tracking (users added, users removed, errors, duration)
- Case-insensitive email matching for user synchronization
- Partial failure handling (continues sync even if individual operations fail)
- Comprehensive test suite for sync service (16 test cases, 100% coverage)
- Main application entry point with command-line interface
- Periodic sync scheduler using the schedule library
- Structured logging with JSON and text format support
- Graceful shutdown handling (SIGTERM, SIGINT)
- Startup banner with dry-run mode indicator
- Initial sync on startup followed by periodic syncs
- Configuration loading from YAML files with CLI argument support
- Docker containerization with multi-stage build for minimal image size (162MB)
- Docker Compose configuration for local testing and deployment
- Non-root container execution for improved security
- Environment variable configuration support in Docker
- Volume mounting support for configuration files and CA certificates
- Verified comprehensive error handling and resilience across all modules
- HTTP request timeouts set to 30 seconds across all API clients
- Exponential backoff configured (2-60 seconds, 5 retry attempts)
- Extensive test coverage for all failure scenarios (network, auth, rate limits, partial failures)
- Comprehensive README.md documentation with setup guides, troubleshooting, and examples
- Complete Okta and Grafana setup instructions
- Docker deployment guide with docker-compose examples
- Development guide with testing and code quality instructions
- Troubleshooting section for common issues
- Environment variables reference table
- Detailed sync behavior explanation

[Unreleased]: https://github.com/cropalato/gots/compare/v0.1.0...HEAD
