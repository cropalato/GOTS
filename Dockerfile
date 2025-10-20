# Multi-stage build for smaller image
FROM python:3.11-slim AS builder

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.2

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry to create virtualenv in project
# Install dependencies (only main, no dev dependencies)
RUN poetry config virtualenvs.in-project true && \
    poetry install --only main --no-root --no-interaction --no-ansi

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY src/ ./src/

# Create non-root user for security
RUN useradd -m -u 1000 syncuser && \
    chown -R syncuser:syncuser /app

# Switch to non-root user
USER syncuser

# Add virtualenv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set Python to run in unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Default command - can be overridden in docker-compose or docker run
CMD ["python", "-m", "src.main", "config.yaml"]
