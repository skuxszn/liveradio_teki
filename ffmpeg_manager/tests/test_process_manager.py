"""
Tests for FFmpeg process manager.

Note: These tests mock subprocess calls to avoid spawning actual FFmpeg processes.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from ffmpeg_manager.config import FFmpegConfig
from ffmpeg_manager.process_manager import (
    FFmpegProcessManager,
    ProcessInfo,
    ProcessState,
)


class TestProcessState:
    """Test ProcessState enum."""

    def test_states_exist(self):
        """Test that all process states exist."""
        assert ProcessState.STOPPED
        assert ProcessState.STARTING
        assert ProcessState.RUNNING
        assert ProcessState.STOPPING
        assert ProcessState.CRASHED
        assert ProcessState.RESTARTING


class TestProcessInfo:
    """Test ProcessInfo dataclass."""

    def test_process_info_creation(self):
        """Test creating process info."""
        info = ProcessInfo(
            pid=12345,
            state=ProcessState.RUNNING,
            loop_path="/path/to/loop.mp4",
            started_at=datetime.now(),
        )

        assert info.pid == 12345
        assert info.state == ProcessState.RUNNING
        assert info.restart_count == 0


class TestFFmpegProcessManager:
    """Test FFmpeg process manager."""

    def test_initialization(self, test_config: FFmpegConfig):
        """Test process manager initialization."""
        manager = FFmpegProcessManager(config=test_config)

        assert manager.config == test_config
        assert manager.command_builder is not None
        assert manager._current_process is None

    def test_initialization_with_defaults(self):
        """Test initialization with default config."""
        manager = FFmpegProcessManager()

        assert manager.config is not None
        assert manager.command_builder is not None

    @pytest.mark.asyncio
    async def test_start_stream_success(
        self, process_manager: FFmpegProcessManager, test_loop_file
    ):
        """Test starting a stream successfully."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock successful FFmpeg process
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None  # Process is running
            mock_process.stderr = MagicMock()
            mock_popen.return_value = mock_process

            success = await process_manager.start_stream(str(test_loop_file))

            assert success is True
            assert process_manager._current_process is not None
            assert process_manager._current_process.pid == 12345
            assert process_manager._current_process.state == ProcessState.RUNNING

    @pytest.mark.asyncio
    async def test_start_stream_failure(
        self, process_manager: FFmpegProcessManager, test_loop_file
    ):
        """Test starting a stream that fails immediately."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock failed FFmpeg process
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.poll.return_value = 1  # Process exited
            mock_process.stderr.read.return_value = b"Error message"
            mock_popen.return_value = mock_process

            success = await process_manager.start_stream(str(test_loop_file))

            assert success is False
            assert process_manager._current_process.state == ProcessState.CRASHED

    @pytest.mark.asyncio
    async def test_switch_track(
        self, process_manager: FFmpegProcessManager, test_loop_file, temp_dir
    ):
        """Test switching tracks."""
        new_loop = temp_dir / "new_loop.mp4"
        new_loop.touch()

        with patch("subprocess.Popen") as mock_popen:
            # Mock successful processes
            mock_process1 = MagicMock()
            mock_process1.pid = 12345
            mock_process1.poll.return_value = None
            mock_process1.stderr = MagicMock()
            mock_process1.terminate = MagicMock()
            mock_process1.wait = MagicMock()

            mock_process2 = MagicMock()
            mock_process2.pid = 67890
            mock_process2.poll.return_value = None
            mock_process2.stderr = MagicMock()

            mock_popen.side_effect = [mock_process1, mock_process2]

            # Start initial stream
            await process_manager.start_stream(str(test_loop_file))

            # Switch to new track
            success = await process_manager.switch_track(str(new_loop))

            assert success is True
            assert process_manager._current_process.pid == 67890
            mock_process1.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_stream(self, process_manager: FFmpegProcessManager, test_loop_file):
        """Test stopping a stream."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock process
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.poll.side_effect = [None, None, None]  # Running
            mock_process.stderr = MagicMock()
            mock_process.terminate = MagicMock()
            mock_process.wait = MagicMock()
            mock_popen.return_value = mock_process

            # Start stream
            await process_manager.start_stream(str(test_loop_file))

            # Stop stream
            success = await process_manager.stop_stream()

            assert success is True
            assert process_manager._current_process is None
            # Process.terminate() should be called when stopping
            assert mock_process.terminate.called or mock_process.kill.called

    @pytest.mark.asyncio
    async def test_stop_stream_force(self, process_manager: FFmpegProcessManager, test_loop_file):
        """Test force stopping a stream."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock process
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.poll.side_effect = [None, None, None]
            mock_process.stderr = MagicMock()
            mock_process.kill = MagicMock()
            mock_process.wait = MagicMock()
            mock_popen.return_value = mock_process

            # Start stream
            await process_manager.start_stream(str(test_loop_file))

            # Force stop
            success = await process_manager.stop_stream(force=True)

            assert success is True
            # Process.kill() should be called when force stopping
            assert mock_process.kill.called or mock_process.terminate.called

    @pytest.mark.asyncio
    async def test_restart_stream(self, process_manager: FFmpegProcessManager, test_loop_file):
        """Test restarting a stream."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock processes
            mock_process1 = MagicMock()
            mock_process1.pid = 12345
            mock_process1.poll.side_effect = [None, None, 0]
            mock_process1.stderr = MagicMock()
            mock_process1.terminate = MagicMock()
            mock_process1.wait = MagicMock()

            mock_process2 = MagicMock()
            mock_process2.pid = 67890
            mock_process2.poll.return_value = None
            mock_process2.stderr = MagicMock()

            mock_popen.side_effect = [mock_process1, mock_process2]

            # Start stream
            await process_manager.start_stream(str(test_loop_file))

            # Restart
            success = await process_manager.restart_stream()

            assert success is True
            assert process_manager._current_process.pid == 67890

    @pytest.mark.asyncio
    async def test_cleanup(self, process_manager: FFmpegProcessManager, test_loop_file):
        """Test cleanup of process manager."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock process
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.poll.side_effect = [None, 0]
            mock_process.stderr = MagicMock()
            mock_process.kill = MagicMock()
            mock_process.wait = MagicMock()
            mock_popen.return_value = mock_process

            # Start stream
            await process_manager.start_stream(str(test_loop_file))

            # Cleanup
            await process_manager.cleanup()

            assert process_manager._should_monitor is False
            assert process_manager._current_process is None

    def test_get_status_no_process(self, process_manager: FFmpegProcessManager):
        """Test getting status with no active process."""
        status = process_manager.get_status()

        assert status["state"] == ProcessState.STOPPED
        assert status["pid"] is None
        assert status["loop_path"] is None

    @pytest.mark.asyncio
    async def test_get_status_with_process(
        self, process_manager: FFmpegProcessManager, test_loop_file
    ):
        """Test getting status with active process."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock process
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_process.stderr = MagicMock()
            mock_popen.return_value = mock_process

            await process_manager.start_stream(str(test_loop_file))

            status = process_manager.get_status()

            assert status["state"] == ProcessState.RUNNING
            assert status["pid"] == 12345
            assert status["loop_path"] == str(test_loop_file)
            assert "uptime_seconds" in status

    def test_is_running_false(self, process_manager: FFmpegProcessManager):
        """Test is_running with no process."""
        assert process_manager.is_running() is False

    @pytest.mark.asyncio
    async def test_is_running_true(self, process_manager: FFmpegProcessManager, test_loop_file):
        """Test is_running with active process."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_process.stderr = MagicMock()
            mock_popen.return_value = mock_process

            await process_manager.start_stream(str(test_loop_file))

            assert process_manager.is_running() is True


class TestProcessRecovery:
    """Test process recovery and auto-restart logic."""

    @pytest.mark.asyncio
    async def test_max_restart_attempts(
        self, process_manager: FFmpegProcessManager, test_loop_file
    ):
        """Test that max restart attempts are respected."""
        with patch("subprocess.Popen") as mock_popen:
            # Mock process that keeps crashing
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.poll.return_value = 1  # Crashed
            mock_process.stderr.read.return_value = b"Error"
            mock_popen.return_value = mock_process

            # Create process info
            process_info = ProcessInfo(
                pid=12345,
                state=ProcessState.CRASHED,
                loop_path=str(test_loop_file),
                started_at=datetime.now(),
                restart_count=3,  # Already at max
            )

            # Try to recover
            success = await process_manager._recover_process(process_info)

            assert success is False
