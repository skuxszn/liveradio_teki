"""Tests for HLS alternative manager."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from advanced.config import AdvancedConfig
from advanced.hls_alternative import HLSManager


@pytest.fixture
def config():
    """Create test configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield AdvancedConfig(
            audio_url="http://test:8000/audio",
            rtmp_endpoint="rtmp://test:1935/stream",
            hls_temp_dir=tmpdir,
            hls_segment_duration=2,
            hls_playlist_size=5,
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
def manager(config):
    """Create HLS manager."""
    return HLSManager(config)


class TestHLSManager:
    """Test suite for HLSManager."""
    
    def test_init(self, config):
        """Test initialization."""
        manager = HLSManager(config)
        
        assert manager.config == config
        assert manager.hls_dir.exists()
        assert manager.segments_dir.exists()
        assert manager._encoder_process is None
        assert manager._streamer_process is None
    
    def test_init_default_config(self):
        """Test initialization with default config."""
        manager = HLSManager()
        
        assert manager.config is not None
        assert isinstance(manager.config, AdvancedConfig)
    
    def test_setup_directories(self, manager):
        """Test directory setup."""
        assert manager.hls_dir.exists()
        assert manager.segments_dir.exists()
        assert manager.playlist_path.parent.exists()
    
    @pytest.mark.asyncio
    @patch("subprocess.Popen")
    async def test_start_encoder_success(self, mock_popen, manager, test_video):
        """Test starting encoder successfully."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        success = await manager._start_encoder(test_video)
        
        assert success is True
        assert manager._encoder_process == mock_process
    
    @pytest.mark.asyncio
    @patch("subprocess.Popen")
    async def test_start_encoder_fails(self, mock_popen, manager, test_video):
        """Test starting encoder when it fails immediately."""
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process died
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = b"Error"
        mock_popen.return_value = mock_process
        
        success = await manager._start_encoder(test_video)
        
        assert success is False
    
    @pytest.mark.asyncio
    @patch("subprocess.Popen")
    async def test_start_streamer_success(self, mock_popen, manager):
        """Test starting streamer successfully."""
        # Create dummy playlist
        manager.playlist_path.touch()
        
        mock_process = Mock()
        mock_process.pid = 12346
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        success = await manager._start_streamer()
        
        assert success is True
        assert manager._streamer_process == mock_process
    
    @pytest.mark.asyncio
    async def test_stop_encoder(self, manager):
        """Test stopping encoder."""
        mock_process = Mock()
        mock_process.wait = Mock()
        manager._encoder_process = mock_process
        
        success = await manager._stop_encoder()
        
        assert success is True
        assert manager._encoder_process is None
        mock_process.terminate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_encoder_force_kill(self, manager):
        """Test force killing encoder on timeout."""
        mock_process = Mock()
        
        import subprocess
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired("cmd", 5),
            None,
        ]
        manager._encoder_process = mock_process
        
        success = await manager._stop_encoder()
        
        assert success is True
        mock_process.kill.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_streamer(self, manager):
        """Test stopping streamer."""
        mock_process = Mock()
        mock_process.wait = Mock()
        manager._streamer_process = mock_process
        
        success = await manager._stop_streamer()
        
        assert success is True
        assert manager._streamer_process is None
        mock_process.terminate.assert_called_once()
    
    def test_cleanup_segments(self, manager):
        """Test cleaning up segments."""
        # Create dummy segments
        (manager.segments_dir / "segment_001.ts").touch()
        (manager.segments_dir / "segment_002.ts").touch()
        manager.playlist_path.touch()
        
        manager._cleanup_segments()
        
        assert not (manager.segments_dir / "segment_001.ts").exists()
        assert not (manager.segments_dir / "segment_002.ts").exists()
        assert not manager.playlist_path.exists()
    
    def test_get_status(self, manager):
        """Test getting status."""
        status = manager.get_status()
        
        assert isinstance(status, dict)
        assert "encoder_running" in status
        assert "streamer_running" in status
        assert "encoder_pid" in status
        assert "streamer_pid" in status
        assert "current_loop" in status
        assert "hls_directory" in status
        assert "playlist_exists" in status
    
    def test_is_running(self, manager):
        """Test checking if running."""
        assert manager.is_running() is False
        
        # Mock running processes
        mock_encoder = Mock()
        mock_encoder.poll.return_value = None
        mock_streamer = Mock()
        mock_streamer.poll.return_value = None
        
        manager._encoder_process = mock_encoder
        manager._streamer_process = mock_streamer
        
        assert manager.is_running() is True
    
    @pytest.mark.asyncio
    async def test_cleanup(self, manager):
        """Test cleanup."""
        # Create some files
        manager.hls_dir.mkdir(exist_ok=True)
        (manager.hls_dir / "test.txt").touch()
        
        await manager.cleanup()
        
        # HLS directory should be removed
        assert not manager.hls_dir.exists()



