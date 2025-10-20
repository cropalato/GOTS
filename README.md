# Grafana-Okta Team Sync (GOTS)

A Python service that automatically synchronizes Okta group membership to Grafana teams.

## Features

- Periodic synchronization of Okta groups to Grafana teams
- Configurable sync intervals
- Dry-run mode for testing
- Docker containerized deployment
- Comprehensive logging and error handling
- Automatic retry logic with exponential backoff
- Support for multiple group mappings

## Prerequisites

- Python 3.10+
- Okta API token with group read permissions
- Grafana API key with team admin permissions
- Docker (optional, for containerized deployment)

## Quick Start

*(To be completed in TICKET-9)*

### Installation

```bash
# Clone the repository
git clone https://github.com/cropalato/gots.git
cd gots

# Install dependencies with Poetry
poetry install

# Copy configuration examples
cp .env.example .env
cp config.example.yaml config.yaml

# Edit .env and config.yaml with your credentials
```

### Running Locally

```bash
# Run with Poetry
poetry run python -m src.main
```

### Running with Docker

```bash
# Build the image
docker build -t gots:latest .

# Run the container
docker run -d --name gots \
  --env-file .env \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  gots:latest
```

## Configuration

*(To be completed in TICKET-9)*

See `config.example.yaml` and `.env.example` for configuration options.

## Development

*(To be completed in TICKET-9)*

### Running Tests

```bash
poetry run pytest
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Sort imports
poetry run isort src/ tests/

# Lint code
poetry run pylint src/

# Type check
poetry run mypy src/
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
