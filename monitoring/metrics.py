"""Prometheus metrics exporter for radio stream monitoring."""

import logging
import time
from typing import Dict, Optional

from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY

logger = logging.getLogger(__name__)


class MetricsExporter:
    """Prometheus metrics exporter for 24/7 radio stream.

    Provides counters, gauges, and histograms for tracking stream health,
    FFmpeg process status, and operational metrics.
    """

    def __init__(self):
        """Initialize Prometheus metrics."""
        # Counters
        self.tracks_played_total = Counter(
            "radio_tracks_played_total",
            "Total number of tracks played",
        )

        self.ffmpeg_restarts_total = Counter(
            "radio_ffmpeg_restarts_total",
            "Total number of FFmpeg process restarts",
        )

        self.errors_total = Counter(
            "radio_errors_total",
            "Total number of errors",
            ["severity"],  # error, critical
        )

        # Gauges
        self.ffmpeg_status = Gauge(
            "radio_ffmpeg_status",
            "FFmpeg process status (1=running, 0=stopped, -1=crashed)",
            ["status"],  # running, stopped, crashed
        )

        self.stream_uptime_seconds = Gauge(
            "radio_stream_uptime_seconds",
            "Current stream uptime in seconds",
        )

        self.current_track_duration_seconds = Gauge(
            "radio_current_track_duration_seconds",
            "Current track playback duration in seconds",
        )

        self.ffmpeg_cpu_usage_percent = Gauge(
            "radio_ffmpeg_cpu_usage_percent",
            "FFmpeg process CPU usage percentage",
        )

        self.ffmpeg_memory_mb = Gauge(
            "radio_ffmpeg_memory_mb",
            "FFmpeg process memory usage in MB",
        )

        self.audio_stream_available = Gauge(
            "radio_audio_stream_available",
            "Audio stream availability (1=available, 0=unavailable)",
        )

        self.rtmp_connection_status = Gauge(
            "radio_rtmp_connection_status",
            "RTMP connection status (1=connected, 0=disconnected)",
        )

        # Histograms
        self.track_switch_duration_seconds = Histogram(
            "radio_track_switch_duration_seconds",
            "Track switch duration in seconds",
            buckets=(0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0),
        )

        logger.info("Prometheus metrics initialized")

    def record_track_played(self) -> None:
        """Increment tracks played counter."""
        self.tracks_played_total.inc()
        logger.debug("Track played counter incremented")

    def record_ffmpeg_restart(self) -> None:
        """Increment FFmpeg restart counter."""
        self.ffmpeg_restarts_total.inc()
        logger.debug("FFmpeg restart counter incremented")

    def record_error(self, severity: str = "error") -> None:
        """Record an error event.

        Args:
            severity: Error severity level ("error" or "critical")
        """
        self.errors_total.labels(severity=severity).inc()
        logger.debug(f"Error recorded with severity: {severity}")

    def update_ffmpeg_status(self, status: str) -> None:
        """Update FFmpeg process status gauge.

        Args:
            status: Process status ("running", "stopped", "crashed")
        """
        # Reset all status labels
        for state in ["running", "stopped", "crashed"]:
            self.ffmpeg_status.labels(status=state).set(0)

        # Set current status
        if status == "running":
            self.ffmpeg_status.labels(status="running").set(1)
        elif status == "stopped":
            self.ffmpeg_status.labels(status="stopped").set(1)
        elif status == "crashed":
            self.ffmpeg_status.labels(status="crashed").set(1)

        logger.debug(f"FFmpeg status updated: {status}")

    def update_stream_uptime(self, uptime_seconds: float) -> None:
        """Update stream uptime gauge.

        Args:
            uptime_seconds: Current uptime in seconds
        """
        self.stream_uptime_seconds.set(uptime_seconds)

    def update_track_duration(self, duration_seconds: float) -> None:
        """Update current track duration gauge.

        Args:
            duration_seconds: Current track duration in seconds
        """
        self.current_track_duration_seconds.set(duration_seconds)

    def update_ffmpeg_cpu(self, cpu_percent: float) -> None:
        """Update FFmpeg CPU usage gauge.

        Args:
            cpu_percent: CPU usage percentage
        """
        self.ffmpeg_cpu_usage_percent.set(cpu_percent)

    def update_ffmpeg_memory(self, memory_mb: float) -> None:
        """Update FFmpeg memory usage gauge.

        Args:
            memory_mb: Memory usage in megabytes
        """
        self.ffmpeg_memory_mb.set(memory_mb)

    def update_audio_stream_status(self, available: bool) -> None:
        """Update audio stream availability gauge.

        Args:
            available: True if audio stream is available
        """
        self.audio_stream_available.set(1 if available else 0)

    def update_rtmp_connection_status(self, connected: bool) -> None:
        """Update RTMP connection status gauge.

        Args:
            connected: True if RTMP is connected
        """
        self.rtmp_connection_status.set(1 if connected else 0)

    def record_track_switch_duration(self, duration_seconds: float) -> None:
        """Record track switch duration histogram.

        Args:
            duration_seconds: Duration of track switch in seconds
        """
        self.track_switch_duration_seconds.observe(duration_seconds)
        logger.debug(f"Track switch duration recorded: {duration_seconds:.3f}s")

    def update_from_ffmpeg_status(self, status_dict: Dict) -> None:
        """Update metrics from FFmpeg process status dictionary.

        Args:
            status_dict: Status dictionary from FFmpegProcessManager.get_status()
        """
        # Update process status
        state = str(status_dict.get("state", "stopped"))
        if state in ["running", "starting"]:
            self.update_ffmpeg_status("running")
        elif state == "crashed":
            self.update_ffmpeg_status("crashed")
        else:
            self.update_ffmpeg_status("stopped")

        # Update uptime
        uptime = status_dict.get("uptime_seconds", 0)
        self.update_stream_uptime(uptime)

        # Update metrics if available
        metrics = status_dict.get("metrics", {})
        if metrics:
            # Update CPU/memory if available
            if "cpu_percent" in metrics:
                self.update_ffmpeg_cpu(metrics["cpu_percent"])
            if "memory_mb" in metrics:
                self.update_ffmpeg_memory(metrics["memory_mb"])

    def get_metrics(self) -> bytes:
        """Generate Prometheus metrics output.

        Returns:
            Prometheus metrics in text format
        """
        return generate_latest(REGISTRY)

    def get_metrics_summary(self) -> Dict:
        """Get current metrics summary as dictionary.

        Returns:
            Dictionary with current metric values
        """
        return {
            "tracks_played": self.tracks_played_total._value.get(),
            "ffmpeg_restarts": self.ffmpeg_restarts_total._value.get(),
            "errors": {
                "error": self.errors_total.labels(severity="error")._value.get(),
                "critical": self.errors_total.labels(severity="critical")._value.get(),
            },
            "stream_uptime_seconds": self.stream_uptime_seconds._value.get(),
            "current_track_duration_seconds": self.current_track_duration_seconds._value.get(),
            "cpu_usage_percent": self.ffmpeg_cpu_usage_percent._value.get(),
            "memory_mb": self.ffmpeg_memory_mb._value.get(),
            "audio_stream_available": bool(self.audio_stream_available._value.get()),
            "rtmp_connected": bool(self.rtmp_connection_status._value.get()),
        }
