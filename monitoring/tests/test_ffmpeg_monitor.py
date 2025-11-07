"""Tests for FFmpeg process monitoring."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from monitoring.config import MonitoringConfig
from monitoring.ffmpeg_monitor import FFmpegMonitor, FFmpegHealthStatus


class TestFFmpegMonitor:
    """Test cases for FFmpegMonitor."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return MonitoringConfig(
            cpu_threshold_percent=80.0,
            memory_threshold_mb=1024.0,
            stream_freeze_timeout=30.0,
        )

    @pytest.fixture
    def monitor(self, config):
        """Create FFmpegMonitor instance."""
        return FFmpegMonitor(config)

    @pytest.mark.asyncio
    async def test_check_process_health_not_running(self, monitor):
        """Test health check when process is not running."""
        report = await monitor.check_process_health(
            pid=None, uptime_seconds=0, process_state="stopped"
        )

        assert report.status == FFmpegHealthStatus.CRITICAL
        assert "not running" in report.warnings[0]
        assert report.pid is None
        assert report.cpu_percent == 0.0
        assert report.memory_mb == 0.0

    @pytest.mark.asyncio
    async def test_check_process_health_running_healthy(self, monitor):
        """Test health check when process is running and healthy."""
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 50.0
        mock_process.memory_info.return_value.rss = 512 * 1024 * 1024  # 512MB
        mock_process.status.return_value = "running"

        with patch("psutil.Process", return_value=mock_process):
            report = await monitor.check_process_health(
                pid=12345, uptime_seconds=100, process_state="running"
            )

            assert report.status == FFmpegHealthStatus.HEALTHY
            assert report.pid == 12345
            assert report.cpu_percent == 50.0
            assert report.memory_mb == 512.0
            assert len(report.warnings) == 0

    @pytest.mark.asyncio
    async def test_check_process_health_high_cpu(self, monitor):
        """Test health check with high CPU usage."""
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 95.0  # Above threshold
        mock_process.memory_info.return_value.rss = 512 * 1024 * 1024
        mock_process.status.return_value = "running"

        with patch("psutil.Process", return_value=mock_process):
            report = await monitor.check_process_health(
                pid=12345, uptime_seconds=100, process_state="running"
            )

            assert report.status == FFmpegHealthStatus.WARNING
            assert any("CPU usage high" in w for w in report.warnings)

    @pytest.mark.asyncio
    async def test_check_process_health_high_memory(self, monitor):
        """Test health check with high memory usage."""
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 50.0
        mock_process.memory_info.return_value.rss = 2048 * 1024 * 1024  # 2GB
        mock_process.status.return_value = "running"

        with patch("psutil.Process", return_value=mock_process):
            report = await monitor.check_process_health(
                pid=12345, uptime_seconds=100, process_state="running"
            )

            assert report.status == FFmpegHealthStatus.WARNING
            assert any("Memory usage high" in w for w in report.warnings)

    @pytest.mark.asyncio
    async def test_check_process_health_zombie(self, monitor):
        """Test health check when process is zombie."""
        import psutil

        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 0.0
        mock_process.memory_info.return_value.rss = 0
        mock_process.status.return_value = psutil.STATUS_ZOMBIE

        with patch("psutil.Process", return_value=mock_process):
            report = await monitor.check_process_health(
                pid=12345, uptime_seconds=100, process_state="running"
            )

            assert report.status == FFmpegHealthStatus.WARNING
            assert any("zombie" in w.lower() for w in report.warnings)

    @pytest.mark.asyncio
    async def test_check_process_health_no_such_process(self, monitor):
        """Test health check when process doesn't exist."""
        import psutil

        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(12345)):
            report = await monitor.check_process_health(
                pid=12345, uptime_seconds=100, process_state="running"
            )

            assert report.status == FFmpegHealthStatus.CRITICAL
            assert any("not found" in w for w in report.warnings)

    @pytest.mark.asyncio
    async def test_check_stream_freeze_first_check(self, monitor):
        """Test stream freeze detection on first check."""
        is_frozen = await monitor.check_stream_freeze(current_frame_count=100)

        assert is_frozen is False
        assert monitor._last_frame_count == 100
        assert monitor._last_frame_time is not None

    @pytest.mark.asyncio
    async def test_check_stream_freeze_frames_increasing(self, monitor):
        """Test stream freeze detection when frames are increasing."""
        # First check
        await monitor.check_stream_freeze(current_frame_count=100)

        # Second check with more frames
        is_frozen = await monitor.check_stream_freeze(current_frame_count=150)

        assert is_frozen is False
        assert monitor._last_frame_count == 150

    @pytest.mark.asyncio
    async def test_check_stream_freeze_detected(self, monitor):
        """Test stream freeze detection when stream is frozen."""
        import asyncio
        from datetime import datetime, timedelta

        # First check
        await monitor.check_stream_freeze(current_frame_count=100)

        # Manually set last frame time to past
        monitor._last_frame_time = datetime.now() - timedelta(seconds=60)

        # Second check with same frame count (frozen)
        is_frozen = await monitor.check_stream_freeze(current_frame_count=100)

        assert is_frozen is True

    @pytest.mark.asyncio
    async def test_check_bitrate_drop_first_check(self, monitor):
        """Test bitrate drop detection on first check."""
        has_dropped = await monitor.check_bitrate_drop(current_bitrate_kbps=3000.0)

        assert has_dropped is False
        assert monitor._last_bitrate == 3000.0

    @pytest.mark.asyncio
    async def test_check_bitrate_drop_normal(self, monitor):
        """Test bitrate drop detection with normal variation."""
        # First check
        await monitor.check_bitrate_drop(current_bitrate_kbps=3000.0)

        # Second check with small drop (< 50%)
        has_dropped = await monitor.check_bitrate_drop(current_bitrate_kbps=2800.0)

        assert has_dropped is False

    @pytest.mark.asyncio
    async def test_check_bitrate_drop_significant(self, monitor):
        """Test bitrate drop detection with significant drop."""
        # First check
        await monitor.check_bitrate_drop(current_bitrate_kbps=3000.0)

        # Second check with large drop (> 50%)
        has_dropped = await monitor.check_bitrate_drop(current_bitrate_kbps=1000.0)

        assert has_dropped is True

    def test_get_health_summary(self, monitor):
        """Test getting health report summary."""
        from monitoring.ffmpeg_monitor import FFmpegHealthReport

        report = FFmpegHealthReport(
            status=FFmpegHealthStatus.HEALTHY,
            pid=12345,
            cpu_percent=45.5,
            memory_mb=512.3,
            uptime_seconds=300.7,
            frame_count=9000,
            bitrate_kbps=3000.5,
            warnings=[],
            timestamp=datetime.now(),
        )

        summary = monitor.get_health_summary(report)

        assert summary["status"] == FFmpegHealthStatus.HEALTHY
        assert summary["pid"] == 12345
        assert summary["cpu_percent"] == 45.5
        assert summary["memory_mb"] == 512.3
        assert isinstance(summary["timestamp"], str)

    def test_reset_tracking(self, monitor):
        """Test resetting tracking state."""
        # Set some state
        monitor._last_frame_count = 1000
        monitor._last_frame_time = datetime.now()
        monitor._last_bitrate = 3000.0

        # Reset
        monitor.reset_tracking()

        assert monitor._last_frame_count == 0
        assert monitor._last_frame_time is None
        assert monitor._last_bitrate == 0.0



