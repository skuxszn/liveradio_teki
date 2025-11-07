"""Tests for auto-recovery functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from monitoring.config import MonitoringConfig
from monitoring.auto_recovery import AutoRecovery, RecoveryAction


class TestAutoRecovery:
    """Test cases for AutoRecovery."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return MonitoringConfig(
            enable_auto_recovery=True,
            max_restart_attempts=3,
            restart_cooldown=60.0,
            audio_stream_retry_interval=30.0,
            audio_stream_max_retries=10,
        )

    @pytest.fixture
    def recovery(self, config):
        """Create AutoRecovery instance."""
        return AutoRecovery(config)

    @pytest.mark.asyncio
    async def test_handle_ffmpeg_crash_disabled(self):
        """Test FFmpeg crash handling when auto-recovery is disabled."""
        config = MonitoringConfig(enable_auto_recovery=False)
        recovery = AutoRecovery(config)

        action = await recovery.handle_ffmpeg_crash("Test error")

        assert action == RecoveryAction.NONE

    @pytest.mark.asyncio
    async def test_handle_ffmpeg_crash_first_attempt(self, recovery):
        """Test first FFmpeg crash recovery attempt."""
        restart_callback = AsyncMock()
        alert_callback = AsyncMock()

        recovery.set_restart_callback(restart_callback)
        recovery.set_alert_callback(alert_callback)

        action = await recovery.handle_ffmpeg_crash("Test error")

        assert action == RecoveryAction.RESTART_FFMPEG
        assert recovery._restart_count == 1
        restart_callback.assert_called_once()
        alert_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_ffmpeg_crash_cooldown(self, recovery):
        """Test FFmpeg crash handling during cooldown period."""
        restart_callback = AsyncMock()
        recovery.set_restart_callback(restart_callback)

        # First crash
        await recovery.handle_ffmpeg_crash("Error 1")

        # Immediate second crash (within cooldown)
        action = await recovery.handle_ffmpeg_crash("Error 2")

        assert action == RecoveryAction.NONE
        assert recovery._restart_count == 1  # Should not increment

    @pytest.mark.asyncio
    async def test_handle_ffmpeg_crash_max_attempts(self, recovery):
        """Test FFmpeg crash handling when max attempts reached."""
        restart_callback = AsyncMock()
        alert_callback = AsyncMock()

        recovery.set_restart_callback(restart_callback)
        recovery.set_alert_callback(alert_callback)

        # Exhaust restart attempts
        recovery._restart_count = 3
        recovery._last_restart_time = datetime.now() - timedelta(seconds=120)

        action = await recovery.handle_ffmpeg_crash("Final error")

        assert action == RecoveryAction.ESCALATE_ALERT
        # Should have sent critical alert
        assert alert_callback.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_ffmpeg_crash_failed_restart(self, recovery):
        """Test FFmpeg crash handling when restart fails."""
        restart_callback = AsyncMock(side_effect=Exception("Restart failed"))
        alert_callback = AsyncMock()

        recovery.set_restart_callback(restart_callback)
        recovery.set_alert_callback(alert_callback)

        action = await recovery.handle_ffmpeg_crash("Test error")

        assert action == RecoveryAction.ESCALATE_ALERT
        # Should have sent critical alert
        assert any("critical" in str(call) for call in alert_callback.call_args_list)

    @pytest.mark.asyncio
    async def test_handle_audio_stream_unavailable(self, recovery):
        """Test audio stream unavailability handling."""
        alert_callback = AsyncMock()
        recovery.set_alert_callback(alert_callback)

        action = await recovery.handle_audio_stream_unavailable()

        assert action == RecoveryAction.RETRY_AUDIO_STREAM
        assert recovery._audio_retry_count == 1

    @pytest.mark.asyncio
    async def test_handle_audio_stream_retry_cooldown(self, recovery):
        """Test audio stream retry during cooldown."""
        # First retry
        await recovery.handle_audio_stream_unavailable()

        # Immediate second retry (within cooldown)
        action = await recovery.handle_audio_stream_unavailable()

        assert action == RecoveryAction.NONE
        assert recovery._audio_retry_count == 1  # Should not increment

    @pytest.mark.asyncio
    async def test_handle_audio_stream_max_retries(self, recovery):
        """Test audio stream retry when max retries reached."""
        alert_callback = AsyncMock()
        recovery.set_alert_callback(alert_callback)

        # Exhaust retries
        recovery._audio_retry_count = 10
        recovery._last_audio_retry_time = datetime.now() - timedelta(seconds=60)

        action = await recovery.handle_audio_stream_unavailable()

        assert action == RecoveryAction.ESCALATE_ALERT
        # Should have sent critical alert
        assert alert_callback.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_rtmp_connection_lost(self, recovery):
        """Test RTMP connection loss handling."""
        restart_callback = AsyncMock()
        alert_callback = AsyncMock()

        recovery.set_restart_callback(restart_callback)
        recovery.set_alert_callback(alert_callback)

        action = await recovery.handle_rtmp_connection_lost()

        assert action == RecoveryAction.RECONNECT_RTMP
        restart_callback.assert_called_once()
        alert_callback.assert_called_once()

    def test_reset_restart_counter(self, recovery):
        """Test resetting restart counter."""
        recovery._restart_count = 2
        recovery._last_restart_time = datetime.now()

        recovery.reset_restart_counter()

        assert recovery._restart_count == 0
        assert recovery._last_restart_time is None

    def test_reset_audio_retry_counter(self, recovery):
        """Test resetting audio retry counter."""
        recovery._audio_retry_count = 5
        recovery._last_audio_retry_time = datetime.now()

        recovery.reset_audio_retry_counter()

        assert recovery._audio_retry_count == 0
        assert recovery._last_audio_retry_time is None

    def test_get_recovery_stats(self, recovery):
        """Test getting recovery statistics."""
        recovery._restart_count = 2
        recovery._audio_retry_count = 3

        stats = recovery.get_recovery_stats()

        assert stats["restart_count"] == 2
        assert stats["audio_retry_count"] == 3
        assert stats["auto_recovery_enabled"] is True
        assert "recent_attempts" in stats
        assert "total_attempts" in stats

    @pytest.mark.asyncio
    async def test_get_recovery_history(self, recovery):
        """Test getting recovery history."""
        restart_callback = AsyncMock()
        recovery.set_restart_callback(restart_callback)

        # Generate some recovery attempts
        await recovery.handle_ffmpeg_crash("Error 1")
        recovery._last_restart_time = datetime.now() - timedelta(seconds=120)
        await recovery.handle_ffmpeg_crash("Error 2")

        history = recovery.get_recovery_history(limit=10)

        assert len(history) >= 1
        assert all("action" in attempt for attempt in history)
        assert all("timestamp" in attempt for attempt in history)
        assert all("success" in attempt for attempt in history)

    @pytest.mark.asyncio
    async def test_send_alert_no_callback(self, recovery):
        """Test sending alert when no callback is configured."""
        # Should not raise exception
        await recovery._send_alert("info", "Test message")

    @pytest.mark.asyncio
    async def test_send_alert_with_callback(self, recovery):
        """Test sending alert with configured callback."""
        alert_callback = AsyncMock()
        recovery.set_alert_callback(alert_callback)

        await recovery._send_alert("warning", "Test warning")

        alert_callback.assert_called_once_with("warning", "Test warning")

    def test_set_restart_callback(self, recovery):
        """Test setting restart callback."""
        callback = AsyncMock()
        recovery.set_restart_callback(callback)

        assert recovery._restart_callback == callback

    def test_set_alert_callback(self, recovery):
        """Test setting alert callback."""
        callback = AsyncMock()
        recovery.set_alert_callback(callback)

        assert recovery._alert_callback == callback
