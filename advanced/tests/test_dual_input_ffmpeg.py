"""Tests for dual-input FFmpeg manager."""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import pytest

from advanced.config import AdvancedConfig
from advanced.dual_input_ffmpeg import DualInputFFmpegManager, StreamState


@pytest.fixture
def config():
    """Create test configuration."""
    return AdvancedConfig(
        audio_url="http://test:8000/audio",
        rtmp_endpoint="rtmp://test:1935/stream",
        crossfade_duration=1.0,
        process_timeout=5,
        max_restart_attempts=2,
    )


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_video(temp_dir):
    """Create a test video file."""
    video_path = os.path.join(temp_dir, "test.mp4")
    Path(video_path).touch()
    return video_path


@pytest.fixture
def manager(config, temp_dir):
    """Create dual-input FFmpeg manager."""
    config.hls_temp_dir = temp_dir
    return DualInputFFmpegManager(config)


class TestDualInputFFmpegManager:
    """Test suite for DualInputFFmpegManager."""

    def test_init(self, config):
        """Test initialization."""
        manager = DualInputFFmpegManager(config)

        assert manager.config == config
        assert manager._state == StreamState.STOPPED
        assert manager._process is None
        assert manager._switch_count == 0

    def test_init_default_config(self):
        """Test initialization with default config."""
        manager = DualInputFFmpegManager()

        assert manager.config is not None
        assert isinstance(manager.config, AdvancedConfig)

    @pytest.mark.asyncio
    async def test_start_stream_not_stopped(self, manager, test_video):
        """Test starting stream when not in STOPPED state."""
        manager._state = StreamState.RUNNING

        success = await manager.start_stream(test_video)

        assert success is False

    @pytest.mark.asyncio
    @patch("subprocess.Popen")
    async def test_start_stream_success(self, mock_popen, manager, test_video):
        """Test starting stream successfully."""
        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        mock_process.stderr = Mock()
        mock_popen.return_value = mock_process

        success = await manager.start_stream(test_video)

        assert success is True
        assert manager._state == StreamState.RUNNING
        assert manager._process == mock_process
        assert manager._current_loop == test_video

    @pytest.mark.asyncio
    @patch("subprocess.Popen")
    async def test_start_stream_process_dies(self, mock_popen, manager, test_video):
        """Test starting stream when process dies immediately."""
        # Mock process that dies
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = b"Error message"
        mock_popen.return_value = mock_process

        success = await manager.start_stream(test_video)

        assert success is False
        assert manager._state == StreamState.ERROR

    @pytest.mark.asyncio
    async def test_switch_track_not_running(self, manager, test_video):
        """Test switching track when not running."""
        success = await manager.switch_track(test_video)

        assert success is False

    @pytest.mark.asyncio
    async def test_stop_stream_already_stopped(self, manager):
        """Test stopping stream when already stopped."""
        success = await manager.stop_stream()

        assert success is True
        assert manager._state == StreamState.STOPPED

    @pytest.mark.asyncio
    async def test_stop_stream_force(self, manager):
        """Test force stopping stream."""
        mock_process = Mock()
        mock_process.wait = Mock()
        manager._process = mock_process
        manager._state = StreamState.RUNNING

        success = await manager.stop_stream(force=True)

        assert success is True
        assert manager._state == StreamState.STOPPED
        assert manager._process is None
        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_stream_max_attempts(self, manager):
        """Test restart fails after max attempts."""
        manager._restart_count = 3
        manager.config.max_restart_attempts = 2

        success = await manager.restart_stream()

        assert success is False

    def test_build_command(self, manager, test_video):
        """Test building FFmpeg command."""
        cmd = manager._build_command(
            test_video,
            test_video,
            "http://audio",
            "rtmp://output",
        )

        assert isinstance(cmd, list)
        assert cmd[0] == manager.config.ffmpeg_binary
        assert "-i" in cmd
        assert "http://audio" in cmd
        assert "rtmp://output" in cmd
        assert "-filter_complex" in cmd

    def test_get_status(self, manager):
        """Test getting status."""
        status = manager.get_status()

        assert isinstance(status, dict)
        assert "state" in status
        assert "pid" in status
        assert "current_loop" in status
        assert "uptime_seconds" in status
        assert "switch_count" in status
        assert status["state"] == StreamState.STOPPED.value

    def test_is_running(self, manager):
        """Test checking if running."""
        assert manager.is_running() is False

        manager._state = StreamState.RUNNING
        assert manager.is_running() is True

        manager._state = StreamState.SWITCHING
        assert manager.is_running() is False

    @pytest.mark.asyncio
    async def test_cleanup(self, manager):
        """Test cleanup."""
        await manager.cleanup()

        assert manager._state == StreamState.STOPPED
        assert manager._process is None


class TestStreamState:
    """Test StreamState enum."""

    def test_states_exist(self):
        """Test that all expected states exist."""
        assert StreamState.STOPPED == "stopped"
        assert StreamState.STARTING == "starting"
        assert StreamState.RUNNING == "running"
        assert StreamState.SWITCHING == "switching"
        assert StreamState.STOPPING == "stopping"
        assert StreamState.ERROR == "error"
