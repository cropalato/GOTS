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

[Unreleased]: https://github.com/cropalato/gots/compare/v0.1.0...HEAD
