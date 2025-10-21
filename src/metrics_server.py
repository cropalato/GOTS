"""Metrics server for Prometheus monitoring."""

import logging
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional

from prometheus_client import REGISTRY, Counter, Gauge, Histogram, generate_latest

logger = logging.getLogger(__name__)


# Define Prometheus metrics
sync_duration_seconds = Histogram(
    "gots_sync_duration_seconds",
    "Duration of sync operations in seconds",
    ["okta_group", "grafana_team"],
    buckets=(1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

users_added_total = Counter(
    "gots_users_added_total",
    "Total number of users added to Grafana teams",
    ["okta_group", "grafana_team"],
)

users_removed_total = Counter(
    "gots_users_removed_total",
    "Total number of users removed from Grafana teams",
    ["okta_group", "grafana_team"],
)

sync_errors_total = Counter(
    "gots_sync_errors_total",
    "Total number of sync errors",
    ["okta_group", "grafana_team"],
)

last_sync_timestamp = Gauge(
    "gots_last_sync_timestamp",
    "Timestamp of last successful sync",
    ["okta_group", "grafana_team"],
)

last_sync_success = Gauge(
    "gots_last_sync_success",
    "Whether the last sync was successful (1=success, 0=failure)",
    ["okta_group", "grafana_team"],
)


class MetricsCollector:
    """Collector for sync metrics."""

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self.sync_status: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def record_sync_start(self, okta_group: str, grafana_team: str) -> None:
        """
        Record the start of a sync operation.

        Args:
            okta_group: Name of Okta group
            grafana_team: Name of Grafana team
        """
        with self.lock:
            key = f"{okta_group}->{grafana_team}"
            self.sync_status[key] = {
                "status": "in_progress",
                "started_at": datetime.now(timezone.utc).isoformat(),
            }

    def record_sync_complete(
        self,
        okta_group: str,
        grafana_team: str,
        duration: float,
        users_added: int,
        users_removed: int,
        errors: int,
    ) -> None:
        """
        Record the completion of a sync operation.

        Args:
            okta_group: Name of Okta group
            grafana_team: Name of Grafana team
            duration: Duration in seconds
            users_added: Number of users added
            users_removed: Number of users removed
            errors: Number of errors encountered
        """
        labels = {"okta_group": okta_group, "grafana_team": grafana_team}

        # Record metrics
        sync_duration_seconds.labels(**labels).observe(duration)
        users_added_total.labels(**labels).inc(users_added)
        users_removed_total.labels(**labels).inc(users_removed)

        if errors > 0:
            sync_errors_total.labels(**labels).inc(errors)

        # Update last sync timestamp
        last_sync_timestamp.labels(**labels).set(time.time())

        # Record success/failure
        success = 1 if errors == 0 else 0
        last_sync_success.labels(**labels).set(success)

        # Update sync status
        with self.lock:
            key = f"{okta_group}->{grafana_team}"
            self.sync_status[key] = {
                "status": "completed" if errors == 0 else "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": duration,
                "users_added": users_added,
                "users_removed": users_removed,
                "errors": errors,
            }

    def get_sync_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current sync status for all mappings.

        Returns:
            Dictionary of sync status by mapping key
        """
        with self.lock:
            return self.sync_status.copy()


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks and metrics."""

    metrics_collector: Optional[MetricsCollector] = None

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/metrics":
            self._handle_metrics()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def _handle_health(self) -> None:
        """Handle health check endpoint."""
        health_data: Dict[str, Any] = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.metrics_collector:
            health_data["sync_status"] = self.metrics_collector.get_sync_status()

        response = str(health_data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _handle_metrics(self) -> None:
        """Handle Prometheus metrics endpoint."""
        metrics_data = generate_latest(REGISTRY)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(metrics_data)))
        self.end_headers()
        self.wfile.write(metrics_data)

    def log_message(self, format: str, *args) -> None:  # type: ignore[no-untyped-def]
        """Override to use Python logging instead of stderr."""
        logger.debug(f"{self.address_string()} - {format % args}")


class MetricsServer:
    """HTTP server for exposing metrics and health checks."""

    def __init__(
        self, metrics_collector: MetricsCollector, port: int = 8000, host: str = "0.0.0.0"
    ) -> None:
        """
        Initialize metrics server.

        Args:
            metrics_collector: MetricsCollector instance
            port: Port to listen on
            host: Host to bind to
        """
        self.port = port
        self.host = host
        self.metrics_collector = metrics_collector
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the metrics server in a background thread."""
        # Set the metrics collector on the handler class
        HealthCheckHandler.metrics_collector = self.metrics_collector

        self.server = HTTPServer((self.host, self.port), HealthCheckHandler)
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

        logger.info(f"Metrics server started on http://{self.host}:{self.port}")
        logger.info(f"Health endpoint: http://{self.host}:{self.port}/health")
        logger.info(f"Metrics endpoint: http://{self.host}:{self.port}/metrics")

    def _run_server(self) -> None:
        """Run the HTTP server (runs in background thread)."""
        if self.server:
            try:
                self.server.serve_forever()
            except Exception as e:
                logger.error(f"Metrics server error: {e}")

    def stop(self) -> None:
        """Stop the metrics server."""
        if self.server:
            logger.info("Stopping metrics server...")
            self.server.shutdown()
            self.server.server_close()

        if self.thread:
            self.thread.join(timeout=5)

        logger.info("Metrics server stopped")
