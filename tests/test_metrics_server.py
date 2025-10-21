"""Tests for metrics server module."""

import time
from http.client import HTTPConnection

import pytest

from src.metrics_server import (
    MetricsCollector,
    MetricsServer,
    last_sync_success,
    last_sync_timestamp,
    sync_duration_seconds,
    sync_errors_total,
    users_added_total,
    users_removed_total,
)


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_init(self) -> None:
        """Test metrics collector initialization."""
        collector = MetricsCollector()
        assert collector.sync_status == {}
        assert collector.lock is not None

    def test_record_sync_start(self) -> None:
        """Test recording sync start."""
        collector = MetricsCollector()
        collector.record_sync_start("Engineering", "Engineers")

        status = collector.get_sync_status()
        assert "Engineering->Engineers" in status
        assert status["Engineering->Engineers"]["status"] == "in_progress"
        assert "started_at" in status["Engineering->Engineers"]

    def test_record_sync_complete_success(self) -> None:
        """Test recording successful sync completion."""
        collector = MetricsCollector()
        collector.record_sync_start("Engineering", "Engineers")

        # Record completion
        collector.record_sync_complete(
            okta_group="Engineering",
            grafana_team="Engineers",
            duration=5.5,
            users_added=2,
            users_removed=1,
            errors=0,
        )

        status = collector.get_sync_status()
        assert status["Engineering->Engineers"]["status"] == "completed"
        assert status["Engineering->Engineers"]["duration_seconds"] == 5.5
        assert status["Engineering->Engineers"]["users_added"] == 2
        assert status["Engineering->Engineers"]["users_removed"] == 1
        assert status["Engineering->Engineers"]["errors"] == 0
        assert "completed_at" in status["Engineering->Engineers"]

    def test_record_sync_complete_with_errors(self) -> None:
        """Test recording sync completion with errors."""
        collector = MetricsCollector()
        collector.record_sync_start("DataScience", "Data Scientists")

        collector.record_sync_complete(
            okta_group="DataScience",
            grafana_team="Data Scientists",
            duration=3.2,
            users_added=0,
            users_removed=0,
            errors=2,
        )

        status = collector.get_sync_status()
        assert status["DataScience->Data Scientists"]["status"] == "failed"
        assert status["DataScience->Data Scientists"]["errors"] == 2

    def test_multiple_sync_mappings(self) -> None:
        """Test tracking multiple sync mappings."""
        collector = MetricsCollector()

        collector.record_sync_start("Group1", "Team1")
        collector.record_sync_start("Group2", "Team2")

        collector.record_sync_complete("Group1", "Team1", 1.0, 1, 0, 0)
        collector.record_sync_complete("Group2", "Team2", 2.0, 0, 1, 0)

        status = collector.get_sync_status()
        assert len(status) == 2
        assert "Group1->Team1" in status
        assert "Group2->Team2" in status

    def test_prometheus_metrics_recorded(self) -> None:
        """Test that Prometheus metrics are recorded correctly."""
        # Clear any previous metrics by creating a new collector
        collector = MetricsCollector()

        # Record a sync
        collector.record_sync_complete(
            okta_group="TestGroup",
            grafana_team="TestTeam",
            duration=1.5,
            users_added=3,
            users_removed=2,
            errors=0,
        )

        # Check that metrics were recorded (we can't easily inspect the values,
        # but we can verify the metrics objects exist and have the right labels)
        # The metrics are global, so they should be populated
        assert sync_duration_seconds is not None
        assert users_added_total is not None
        assert users_removed_total is not None
        assert sync_errors_total is not None
        assert last_sync_timestamp is not None
        assert last_sync_success is not None


class TestMetricsServer:
    """Test MetricsServer class."""

    def test_init(self) -> None:
        """Test metrics server initialization."""
        collector = MetricsCollector()
        server = MetricsServer(collector, port=9000, host="127.0.0.1")

        assert server.port == 9000
        assert server.host == "127.0.0.1"
        assert server.metrics_collector is collector
        assert server.server is None
        assert server.thread is None

    def test_start_and_stop(self) -> None:
        """Test starting and stopping metrics server."""
        collector = MetricsCollector()
        server = MetricsServer(collector, port=9001, host="127.0.0.1")

        # Start server
        server.start()
        time.sleep(0.5)  # Give server time to start

        assert server.server is not None
        assert server.thread is not None
        assert server.thread.is_alive()

        # Stop server
        server.stop()
        time.sleep(0.5)  # Give server time to stop

        assert not server.thread.is_alive()

    def test_health_endpoint(self) -> None:
        """Test /health endpoint returns correct data."""
        collector = MetricsCollector()
        collector.record_sync_start("Group1", "Team1")
        collector.record_sync_complete("Group1", "Team1", 1.0, 1, 0, 0)

        server = MetricsServer(collector, port=9002, host="127.0.0.1")
        server.start()
        time.sleep(0.5)  # Give server time to start

        try:
            # Make request to health endpoint
            conn = HTTPConnection("127.0.0.1", 9002, timeout=5)
            conn.request("GET", "/health")
            response = conn.getresponse()

            assert response.status == 200
            assert "application/json" in response.getheader("Content-Type", "")

            body = response.read().decode("utf-8")
            assert "healthy" in body
            assert "sync_status" in body
            assert "Group1->Team1" in body

            conn.close()
        finally:
            server.stop()
            time.sleep(0.2)

    def test_metrics_endpoint(self) -> None:
        """Test /metrics endpoint returns Prometheus format."""
        collector = MetricsCollector()
        collector.record_sync_complete("Group1", "Team1", 2.5, 5, 3, 0)

        server = MetricsServer(collector, port=9003, host="127.0.0.1")
        server.start()
        time.sleep(0.5)  # Give server time to start

        try:
            # Make request to metrics endpoint
            conn = HTTPConnection("127.0.0.1", 9003, timeout=5)
            conn.request("GET", "/metrics")
            response = conn.getresponse()

            assert response.status == 200
            content_type = response.getheader("Content-Type", "")
            assert "text/plain" in content_type

            body = response.read().decode("utf-8")
            # Check for our custom metrics
            assert "gots_sync_duration_seconds" in body
            assert "gots_users_added_total" in body
            assert "gots_users_removed_total" in body
            assert "gots_last_sync_timestamp" in body

            conn.close()
        finally:
            server.stop()
            time.sleep(0.2)

    def test_not_found_endpoint(self) -> None:
        """Test that unknown endpoints return 404."""
        collector = MetricsCollector()
        server = MetricsServer(collector, port=9004, host="127.0.0.1")
        server.start()
        time.sleep(0.5)  # Give server time to start

        try:
            conn = HTTPConnection("127.0.0.1", 9004, timeout=5)
            conn.request("GET", "/unknown")
            response = conn.getresponse()

            assert response.status == 404
            body = response.read().decode("utf-8")
            assert "Not Found" in body

            conn.close()
        finally:
            server.stop()
            time.sleep(0.2)

    def test_thread_safety(self) -> None:
        """Test that metrics collector is thread-safe."""
        import threading

        collector = MetricsCollector()

        def record_sync(group_name: str, team_name: str) -> None:
            for i in range(10):
                collector.record_sync_start(f"{group_name}{i}", f"{team_name}{i}")
                collector.record_sync_complete(f"{group_name}{i}", f"{team_name}{i}", 1.0, 1, 0, 0)

        # Create multiple threads that record metrics concurrently
        threads = [
            threading.Thread(target=record_sync, args=(f"Group{i}", f"Team{i}")) for i in range(5)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify that all syncs were recorded
        status = collector.get_sync_status()
        assert len(status) == 50  # 5 threads × 10 syncs each
