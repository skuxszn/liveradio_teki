"""Unit tests for FFmpeg process manager."""

import asyncio
import pytest
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from metadata_watcher.ffmpeg_manager import FFmpegManager, FFmpegProcess
from metadata_watcher.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.azuracast_audio_url = "http://test:8000/radio"
    config.rtmp_endpoint = "rtmp://test:1935/live/stream"
    config.video_resolution = "1280:720"
    config.video_bitrate = "3000k"
    config.audio_bitrate = "192k"
    config.video_encoder = "libx264"
    config.ffmpeg_preset = "veryfast"
    config.fade_duration = 1.0
    config.track_overlap_duration = 2.0
    config.max_restart_attempts = 3
    config.restart_cooldown_seconds = 60
    config.ffmpeg_log_level = "info"
    return config


@pytest.fixture
def manager(mock_config):
    """Create an FFmpegManager instance."""
    return FFmpegManager(mock_config)


class TestFFmpegProcess:
    """Test FFmpegProcess wrapper class."""

    def test_init(self):
        """Test FFmpegProcess initialization."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345

        ffmpeg_process = FFmpegProcess(
            process=mock_process,
            track_key="test - track",
            loop_path=Path("/test/loop.mp4"),
            started_at=datetime.now()
        )

        assert ffmpeg_process.pid == 12345
        assert ffmpeg_process.track_key == "test - track"
        assert ffmpeg_process.loop_path == Path("/test/loop.mp4")

    def test_is_running_true(self):
        """Test is_running when process is active."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Still running

        ffmpeg_process = FFmpegProcess(
            process=mock_process,
            track_key="test - track",
            loop_path=Path("/test/loop.mp4"),
            started_at=datetime.now()
        )

        assert ffmpeg_process.is_running is True

    def test_is_running_false(self):
        """Test is_running when process has exited."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # Exited

        ffmpeg_process = FFmpegProcess(
            process=mock_process,
            track_key="test - track",
            loop_path=Path("/test/loop.mp4"),
            started_at=datetime.now()
        )

        assert ffmpeg_process.is_running is False

    def test_terminate(self):
        """Test terminating process."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        ffmpeg_process = FFmpegProcess(
            process=mock_process,
            track_key="test - track",
            loop_path=Path("/test/loop.mp4"),
            started_at=datetime.now()
        )

        ffmpeg_process.terminate()
        mock_process.terminate.assert_called_once()

    def test_kill(self):
        """Test killing process."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        ffmpeg_process = FFmpegProcess(
            process=mock_process,
            track_key="test - track",
            loop_path=Path("/test/loop.mp4"),
            started_at=datetime.now()
        )

        ffmpeg_process.kill()
        mock_process.kill.assert_called_once()


class TestFFmpegManager:
    """Test FFmpegManager functionality."""

    def test_init(self, mock_config):
        """Test FFmpegManager initialization."""
        manager = FFmpegManager(mock_config)

        assert manager.config == mock_config
        assert manager.current_process is None
        assert isinstance(manager.process_lock, asyncio.Lock)

    def test_build_ffmpeg_command(self, manager):
        """Test FFmpeg command building."""
        loop_path = Path("/test/loop.mp4")
        cmd = manager._build_ffmpeg_command(loop_path, "Test Artist", "Test Title")

        # Check basic structure
        assert "ffmpeg" in cmd
        assert "-re" in cmd
        assert "-stream_loop" in cmd
        assert "-1" in cmd
        assert str(loop_path) in cmd
        assert manager.config.azuracast_audio_url in cmd
        assert manager.config.rtmp_endpoint in cmd

        # Check encoding settings
        assert "-c:v" in cmd
        assert manager.config.video_encoder in cmd
        assert "-b:v" in cmd
        assert manager.config.video_bitrate in cmd
        assert "-b:a" in cmd
        assert manager.config.audio_bitrate in cmd

    def test_build_ffmpeg_command_with_filters(self, manager):
        """Test that video filters are included."""
        loop_path = Path("/test/loop.mp4")
        cmd = manager._build_ffmpeg_command(loop_path, "Artist", "Title")

        cmd_str = " ".join(cmd)
        assert "fade=t=in" in cmd_str
        assert "scale=1280:720" in cmd_str
        assert "format=yuv420p" in cmd_str
        assert "afade=t=in" in cmd_str

    @pytest.mark.asyncio
    async def test_spawn_process_success(self, manager):
        """Test successful process spawning."""
        with patch('metadata_watcher.ffmpeg_manager.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None  # Running
            mock_process.stderr = Mock()
            mock_popen.return_value = mock_process

            loop_path = Path("/test/loop.mp4")
            cmd = ["ffmpeg", "-i", "test"]

            result = await manager._spawn_process("test - track", loop_path, cmd)

            assert result is not None
            assert result.pid == 12345
            assert result.track_key == "test - track"
            mock_popen.assert_called_once()

    @pytest.mark.asyncio
    async def test_spawn_process_immediate_exit(self, manager):
        """Test handling of process that exits immediately."""
        with patch('metadata_watcher.ffmpeg_manager.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = 1  # Already exited
            mock_process.stderr = Mock()
            mock_process.stderr.read.return_value = b"Error message"
            mock_popen.return_value = mock_process

            loop_path = Path("/test/loop.mp4")
            cmd = ["ffmpeg", "-i", "test"]

            result = await manager._spawn_process("test - track", loop_path, cmd)

            assert result is None

    @pytest.mark.asyncio
    async def test_spawn_process_max_attempts(self, manager):
        """Test that max restart attempts are enforced."""
        track_key = "test - track"
        manager.restart_attempts[track_key] = 3  # Max reached

        loop_path = Path("/test/loop.mp4")
        cmd = ["ffmpeg", "-i", "test"]

        result = await manager._spawn_process(track_key, loop_path, cmd)

        assert result is None

    def test_check_restart_cooldown_first_attempt(self, manager):
        """Test cooldown check for first attempt."""
        assert manager._check_restart_cooldown("new - track") is True

    def test_check_restart_cooldown_active(self, manager):
        """Test cooldown check when cooldown is active."""
        import time

        track_key = "test - track"
        manager.last_restart_time[track_key] = time.time()

        assert manager._check_restart_cooldown(track_key) is False

    def test_check_restart_cooldown_expired(self, manager):
        """Test cooldown check when cooldown has expired."""
        import time

        track_key = "test - track"
        manager.last_restart_time[track_key] = time.time() - 100  # 100 seconds ago
        manager.restart_attempts[track_key] = 1

        result = manager._check_restart_cooldown(track_key)

        assert result is True
        assert manager.restart_attempts[track_key] == 0  # Reset

    def test_get_status_no_process(self, manager):
        """Test status when no process is running."""
        status = manager.get_status()

        assert status["status"] == "stopped"
        assert status["process"] is None

    def test_get_status_with_running_process(self, manager):
        """Test status with running process."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        manager.current_process = FFmpegProcess(
            process=mock_process,
            track_key="test - track",
            loop_path=Path("/test/loop.mp4"),
            started_at=datetime.now()
        )

        status = manager.get_status()

        assert status["status"] == "running"
        assert status["process"]["pid"] == 12345
        assert status["process"]["track_key"] == "test - track"

    @pytest.mark.asyncio
    async def test_cleanup_no_process(self, manager):
        """Test cleanup with no active process."""
        await manager.cleanup()
        # Should not raise

    @pytest.mark.asyncio
    async def test_cleanup_with_running_process(self, manager):
        """Test cleanup terminates running process."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0

        manager.current_process = FFmpegProcess(
            process=mock_process,
            track_key="test - track",
            loop_path=Path("/test/loop.mp4"),
            started_at=datetime.now()
        )

        await manager.cleanup()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called()

    @pytest.mark.asyncio
    async def test_switch_track_success(self, manager):
        """Test successful track switching."""
        with patch.object(manager, '_spawn_process') as mock_spawn:
            # Create a mock FFmpegProcess
            mock_process = Mock(spec=subprocess.Popen)
            mock_process.pid = 12345
            mock_process.poll.return_value = None

            new_ffmpeg_process = FFmpegProcess(
                process=mock_process,
                track_key="new - track",
                loop_path=Path("/test/new.mp4"),
                started_at=datetime.now()
            )
            mock_spawn.return_value = new_ffmpeg_process

            # Reduce overlap for faster test
            manager.config.track_overlap_duration = 0.1

            result = await manager.switch_track(
                track_key="new - track",
                artist="New Artist",
                title="New Title",
                loop_path=Path("/test/new.mp4")
            )

            assert result is True
            assert manager.current_process == new_ffmpeg_process
            mock_spawn.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_track_spawn_failure(self, manager):
        """Test track switching when spawn fails."""
        with patch.object(manager, '_spawn_process') as mock_spawn:
            mock_spawn.return_value = None  # Spawn failed

            result = await manager.switch_track(
                track_key="new - track",
                artist="New Artist",
                title="New Title",
                loop_path=Path("/test/new.mp4")
            )

            assert result is False
            assert manager.current_process is None

