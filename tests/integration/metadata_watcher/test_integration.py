"""Integration tests for metadata watcher service.

These tests verify the complete workflow from webhook to FFmpeg spawning.
"""

import pytest
import asyncio
import os
import signal
import time
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
from metadata_watcher.config import Config
from metadata_watcher.ffmpeg_manager import FFmpegManager
from metadata_watcher.track_resolver import TrackResolver


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration."""
    # Create test directories
    loops_path = tmp_path / "loops"
    tracks_dir = loops_path / "tracks"
    tracks_dir.mkdir(parents=True)

    # Create default loop
    default_loop = loops_path / "default.mp4"
    default_loop.write_bytes(b"default video data" * 1000)

    # Create test loop
    test_loop = tracks_dir / "test_artist_-_test_song.mp4"
    test_loop.write_bytes(b"test video data" * 1000)

    # Set environment variables
    env_vars = {
        "AZURACAST_URL": "http://test.example.com",
        "AZURACAST_API_KEY": "test-key",
        "AZURACAST_AUDIO_URL": "http://test.example.com:8000/radio",
        "POSTGRES_PASSWORD": "test-password",
        "LOOPS_PATH": str(loops_path),
        "DEFAULT_LOOP": str(default_loop),
        "ENVIRONMENT": "testing",
        "VIDEO_RESOLUTION": "1280:720",
        "VIDEO_ENCODER": "libx264",
        "TRACK_OVERLAP_DURATION": "0.5",  # Short for testing
        "MAX_RESTART_ATTEMPTS": "3",
        "RESTART_COOLDOWN_SECONDS": "5",
    }

    for key, value in env_vars.items():
        os.environ[key] = value

    config = Config.from_env()
    yield config

    # Cleanup
    for key in env_vars:
        os.environ.pop(key, None)


@pytest.fixture
def track_resolver(test_config):
    """Create a TrackResolver instance."""
    return TrackResolver(test_config)


@pytest.fixture
def ffmpeg_manager(test_config):
    """Create an FFmpegManager instance."""
    return FFmpegManager(test_config)


class TestTrackResolverIntegration:
    """Integration tests for track resolver."""

    def test_resolve_existing_track(self, track_resolver, test_config):
        """Test resolving an existing track."""
        result = track_resolver.resolve_loop("Test Artist", "Test Song")

        expected_path = test_config.loops_path / "tracks" / "test_artist_-_test_song.mp4"
        assert result == expected_path
        assert result.exists()

    def test_resolve_nonexistent_track(self, track_resolver, test_config):
        """Test resolving a non-existent track falls back to default."""
        result = track_resolver.resolve_loop("Unknown", "Unknown")

        assert result == test_config.default_loop
        assert result.exists()

    def test_multiple_resolutions(self, track_resolver, test_config):
        """Test multiple consecutive resolutions."""
        # Should work multiple times without issues
        for _ in range(5):
            result = track_resolver.resolve_loop("Test Artist", "Test Song")
            assert result.exists()


class TestFFmpegManagerIntegration:
    """Integration tests for FFmpeg manager (with mocked subprocess)."""

    @pytest.mark.asyncio
    async def test_spawn_process_lifecycle(self, ffmpeg_manager, test_config):
        """Test spawning and managing a process."""
        with patch("metadata_watcher.ffmpeg_manager.subprocess.Popen") as mock_popen:
            # Mock a successful FFmpeg process
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None  # Running
            mock_process.stderr = Mock()
            mock_process.stderr.read.return_value = b""
            mock_process.terminate.return_value = None
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            # Switch to a track
            loop_path = test_config.loops_path / "tracks" / "test_artist_-_test_song.mp4"
            success = await ffmpeg_manager.switch_track(
                track_key="test artist - test song",
                artist="Test Artist",
                title="Test Song",
                loop_path=loop_path,
            )

            assert success is True
            assert ffmpeg_manager.current_process is not None
            assert ffmpeg_manager.current_process.pid == 12345

            # Check status
            status = ffmpeg_manager.get_status()
            assert status["status"] == "running"
            assert status["process"]["pid"] == 12345

    @pytest.mark.asyncio
    async def test_track_switching_with_overlap(self, ffmpeg_manager, test_config):
        """Test switching between tracks with overlap."""
        with patch("metadata_watcher.ffmpeg_manager.subprocess.Popen") as mock_popen:
            # Create two mock processes
            mock_process1 = Mock()
            mock_process1.pid = 11111
            mock_process1.poll.return_value = None
            mock_process1.stderr = Mock()
            mock_process1.stderr.read.return_value = b""
            mock_process1.terminate.return_value = None
            mock_process1.wait.return_value = 0

            mock_process2 = Mock()
            mock_process2.pid = 22222
            mock_process2.poll.return_value = None
            mock_process2.stderr = Mock()
            mock_process2.stderr.read.return_value = b""
            mock_process2.terminate.return_value = None
            mock_process2.wait.return_value = 0

            mock_popen.side_effect = [mock_process1, mock_process2]

            # Switch to first track
            loop_path = test_config.loops_path / "tracks" / "test_artist_-_test_song.mp4"
            success1 = await ffmpeg_manager.switch_track(
                track_key="track 1", artist="Artist 1", title="Song 1", loop_path=loop_path
            )
            assert success1 is True
            assert ffmpeg_manager.current_process.pid == 11111

            # Switch to second track (should terminate first)
            success2 = await ffmpeg_manager.switch_track(
                track_key="track 2", artist="Artist 2", title="Song 2", loop_path=loop_path
            )
            assert success2 is True
            assert ffmpeg_manager.current_process.pid == 22222

            # Verify first process was terminated
            mock_process1.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup(self, ffmpeg_manager, test_config):
        """Test cleanup terminates active processes."""
        with patch("metadata_watcher.ffmpeg_manager.subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_process.stderr = Mock()
            mock_process.stderr.read.return_value = b""
            mock_process.terminate.return_value = None
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            # Spawn a process
            loop_path = test_config.loops_path / "tracks" / "test_artist_-_test_song.mp4"
            await ffmpeg_manager.switch_track(
                track_key="test track", artist="Test", title="Track", loop_path=loop_path
            )

            # Cleanup
            await ffmpeg_manager.cleanup()

            # Verify process was terminated
            mock_process.terminate.assert_called()


class TestEndToEndWorkflow:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_complete_track_change_workflow(
        self, test_config, track_resolver, ffmpeg_manager
    ):
        """Test complete workflow from track resolution to FFmpeg spawn."""
        with patch("metadata_watcher.ffmpeg_manager.subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_process.stderr = Mock()
            mock_process.stderr.read.return_value = b""
            mock_process.terminate.return_value = None
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            # Step 1: Resolve track to loop
            loop_path = track_resolver.resolve_loop("Test Artist", "Test Song")
            assert loop_path.exists()

            # Step 2: Normalize track key
            track_key = track_resolver._normalize_track_key("Test Artist", "Test Song")
            assert track_key == "test artist - test song"

            # Step 3: Switch FFmpeg process
            success = await ffmpeg_manager.switch_track(
                track_key=track_key, artist="Test Artist", title="Test Song", loop_path=loop_path
            )
            assert success is True

            # Step 4: Verify process is running
            status = ffmpeg_manager.get_status()
            assert status["status"] == "running"
            assert status["process"]["track_key"] == track_key

            # Step 5: Cleanup
            await ffmpeg_manager.cleanup()
            mock_process.terminate.assert_called()

    @pytest.mark.asyncio
    async def test_multiple_track_changes(self, test_config, track_resolver, ffmpeg_manager):
        """Test multiple consecutive track changes."""
        with patch("metadata_watcher.ffmpeg_manager.subprocess.Popen") as mock_popen:
            # Create multiple mock processes
            processes = []
            for i in range(3):
                mock_process = Mock()
                mock_process.pid = 10000 + i
                mock_process.poll.return_value = None
                mock_process.stderr = Mock()
                mock_process.stderr.read.return_value = b""
                mock_process.terminate.return_value = None
                mock_process.wait.return_value = 0
                processes.append(mock_process)

            mock_popen.side_effect = processes

            tracks = [
                ("Artist 1", "Song 1"),
                ("Artist 2", "Song 2"),
                ("Artist 3", "Song 3"),
            ]

            for i, (artist, title) in enumerate(tracks):
                loop_path = track_resolver.resolve_loop(artist, title)
                track_key = track_resolver._normalize_track_key(artist, title)

                success = await ffmpeg_manager.switch_track(
                    track_key=track_key, artist=artist, title=title, loop_path=loop_path
                )

                assert success is True
                assert ffmpeg_manager.current_process.pid == 10000 + i

                # Verify previous process was terminated (except first)
                if i > 0:
                    processes[i - 1].terminate.assert_called_once()

            # Final cleanup
            await ffmpeg_manager.cleanup()


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    @pytest.mark.asyncio
    async def test_missing_default_loop(self, test_config, track_resolver):
        """Test behavior when default loop is missing."""
        # Remove default loop
        test_config.default_loop.unlink()

        # Should raise error when trying to get default
        with pytest.raises(FileNotFoundError):
            track_resolver.get_default_loop()

    @pytest.mark.asyncio
    async def test_restart_cooldown(self, ffmpeg_manager, test_config):
        """Test restart cooldown mechanism."""
        with patch("metadata_watcher.ffmpeg_manager.subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_process.stderr = Mock()
            mock_process.stderr.read.return_value = b""
            mock_popen.return_value = mock_process

            loop_path = test_config.default_loop
            track_key = "test - track"

            # First spawn should work
            result1 = await ffmpeg_manager._spawn_process(track_key, loop_path, ["test"])
            assert result1 is not None

            # Immediate second spawn should be blocked by cooldown
            result2 = await ffmpeg_manager._spawn_process(track_key, loop_path, ["test"])
            assert result2 is None
