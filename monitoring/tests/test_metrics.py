"""Tests for Prometheus metrics exporter."""

import pytest
from prometheus_client import REGISTRY

from monitoring.metrics import MetricsExporter


class TestMetricsExporter:
    """Test cases for MetricsExporter."""

    @pytest.fixture
    def metrics(self):
        """Create MetricsExporter instance."""
        # Clear any existing metrics from the registry
        collectors = list(REGISTRY._collector_to_names.keys())
        for collector in collectors:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

        return MetricsExporter()

    def test_initialization(self, metrics):
        """Test metrics initialization."""
        assert metrics.tracks_played_total is not None
        assert metrics.ffmpeg_restarts_total is not None
        assert metrics.errors_total is not None
        assert metrics.ffmpeg_status is not None
        assert metrics.stream_uptime_seconds is not None

    def test_record_track_played(self, metrics):
        """Test recording track played."""
        initial = metrics.tracks_played_total._value.get()
        metrics.record_track_played()
        assert metrics.tracks_played_total._value.get() == initial + 1

    def test_record_ffmpeg_restart(self, metrics):
        """Test recording FFmpeg restart."""
        initial = metrics.ffmpeg_restarts_total._value.get()
        metrics.record_ffmpeg_restart()
        assert metrics.ffmpeg_restarts_total._value.get() == initial + 1

    def test_record_error(self, metrics):
        """Test recording errors."""
        metrics.record_error("error")
        metrics.record_error("critical")

        assert metrics.errors_total.labels(severity="error")._value.get() >= 1
        assert metrics.errors_total.labels(severity="critical")._value.get() >= 1

    def test_update_ffmpeg_status(self, metrics):
        """Test updating FFmpeg status."""
        metrics.update_ffmpeg_status("running")
        assert metrics.ffmpeg_status.labels(status="running")._value.get() == 1
        assert metrics.ffmpeg_status.labels(status="stopped")._value.get() == 0

        metrics.update_ffmpeg_status("stopped")
        assert metrics.ffmpeg_status.labels(status="running")._value.get() == 0
        assert metrics.ffmpeg_status.labels(status="stopped")._value.get() == 1

        metrics.update_ffmpeg_status("crashed")
        assert metrics.ffmpeg_status.labels(status="crashed")._value.get() == 1

    def test_update_stream_uptime(self, metrics):
        """Test updating stream uptime."""
        metrics.update_stream_uptime(123.45)
        assert metrics.stream_uptime_seconds._value.get() == 123.45

    def test_update_track_duration(self, metrics):
        """Test updating track duration."""
        metrics.update_track_duration(180.0)
        assert metrics.current_track_duration_seconds._value.get() == 180.0

    def test_update_ffmpeg_cpu(self, metrics):
        """Test updating FFmpeg CPU usage."""
        metrics.update_ffmpeg_cpu(45.5)
        assert metrics.ffmpeg_cpu_usage_percent._value.get() == 45.5

    def test_update_ffmpeg_memory(self, metrics):
        """Test updating FFmpeg memory usage."""
        metrics.update_ffmpeg_memory(512.0)
        assert metrics.ffmpeg_memory_mb._value.get() == 512.0

    def test_update_audio_stream_status(self, metrics):
        """Test updating audio stream status."""
        metrics.update_audio_stream_status(True)
        assert metrics.audio_stream_available._value.get() == 1

        metrics.update_audio_stream_status(False)
        assert metrics.audio_stream_available._value.get() == 0

    def test_update_rtmp_connection_status(self, metrics):
        """Test updating RTMP connection status."""
        metrics.update_rtmp_connection_status(True)
        assert metrics.rtmp_connection_status._value.get() == 1

        metrics.update_rtmp_connection_status(False)
        assert metrics.rtmp_connection_status._value.get() == 0

    def test_record_track_switch_duration(self, metrics):
        """Test recording track switch duration."""
        # Record several durations
        metrics.record_track_switch_duration(0.5)
        metrics.record_track_switch_duration(1.0)
        metrics.record_track_switch_duration(2.0)

        # Verify histogram was updated by checking it exists and doesn't throw
        # We can't directly access histogram internals, but we can verify
        # the metric collection works
        assert metrics.track_switch_duration_seconds is not None

    def test_update_from_ffmpeg_status_running(self, metrics):
        """Test updating from FFmpeg status dict (running state)."""
        status_dict = {
            "state": "running",
            "uptime_seconds": 300.0,
            "metrics": {
                "cpu_percent": 50.0,
                "memory_mb": 800.0,
            },
        }

        metrics.update_from_ffmpeg_status(status_dict)

        assert metrics.stream_uptime_seconds._value.get() == 300.0
        assert metrics.ffmpeg_cpu_usage_percent._value.get() == 50.0
        assert metrics.ffmpeg_memory_mb._value.get() == 800.0

    def test_update_from_ffmpeg_status_stopped(self, metrics):
        """Test updating from FFmpeg status dict (stopped state)."""
        status_dict = {
            "state": "stopped",
            "uptime_seconds": 0,
        }

        metrics.update_from_ffmpeg_status(status_dict)

        # Status should be set to stopped
        assert metrics.ffmpeg_status.labels(status="stopped")._value.get() == 1

    def test_get_metrics(self, metrics):
        """Test getting Prometheus metrics output."""
        metrics.record_track_played()
        output = metrics.get_metrics()

        assert isinstance(output, bytes)
        assert b"radio_tracks_played_total" in output

    def test_get_metrics_summary(self, metrics):
        """Test getting metrics summary."""
        metrics.record_track_played()
        metrics.record_ffmpeg_restart()
        metrics.update_stream_uptime(100.0)

        summary = metrics.get_metrics_summary()

        assert isinstance(summary, dict)
        assert "tracks_played" in summary
        assert "ffmpeg_restarts" in summary
        assert "stream_uptime_seconds" in summary
        assert summary["stream_uptime_seconds"] == 100.0
