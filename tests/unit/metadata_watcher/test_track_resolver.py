"""Unit tests for track resolver."""

import pytest
from pathlib import Path
from unittest.mock import Mock
from metadata_watcher.track_resolver import TrackResolver
from metadata_watcher.config import Config


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock configuration for testing."""
    # Create directory structure
    loops_path = tmp_path / "loops"
    tracks_dir = loops_path / "tracks"
    tracks_dir.mkdir(parents=True)

    # Create default loop
    default_loop = loops_path / "default.mp4"
    default_loop.write_bytes(b"default video data")

    config = Mock(spec=Config)
    config.loops_path = loops_path
    config.default_loop = default_loop

    return config


@pytest.fixture
def resolver(mock_config):
    """Create a TrackResolver instance."""
    return TrackResolver(mock_config)


class TestTrackResolver:
    """Test track resolution logic."""

    def test_normalize_track_key(self, resolver):
        """Test track key normalization."""
        key = resolver._normalize_track_key("Test Artist", "Test Title")
        assert key == "test artist - test title"

    def test_normalize_with_special_chars(self, resolver):
        """Test normalization removes special characters."""
        key = resolver._normalize_track_key("Artist/Name", 'Song: "Title"')
        assert "/" not in key
        assert ":" not in key
        assert '"' not in key
        assert key == "artistname - song title"

    def test_normalize_with_whitespace(self, resolver):
        """Test normalization handles extra whitespace."""
        key = resolver._normalize_track_key("  Artist  Name  ", "  Song   Title  ")
        assert key == "artist name - song title"

    def test_resolve_loop_with_track_key(self, resolver, mock_config):
        """Test resolving loop by track key."""
        # Create a track-specific loop
        tracks_dir = mock_config.loops_path / "tracks"
        track_loop = tracks_dir / "test_artist_-_test_title.mp4"
        track_loop.write_bytes(b"track video data")

        result = resolver.resolve_loop("Test Artist", "Test Title")

        assert result == track_loop
        assert result.exists()

    def test_resolve_loop_with_song_id(self, resolver, mock_config):
        """Test resolving loop by song ID."""
        tracks_dir = mock_config.loops_path / "tracks"
        song_loop = tracks_dir / "track_123_loop.mp4"
        song_loop.write_bytes(b"song video data")

        result = resolver.resolve_loop("Unknown Artist", "Unknown Title", song_id="123")

        assert result == song_loop
        assert result.exists()

    def test_resolve_loop_fallback_to_default(self, resolver, mock_config):
        """Test falling back to default loop."""
        result = resolver.resolve_loop("Nonexistent Artist", "Nonexistent Title")

        assert result == mock_config.default_loop
        assert result.exists()

    def test_is_valid_loop_exists(self, resolver, tmp_path):
        """Test valid loop file detection."""
        loop_path = tmp_path / "valid.mp4"
        loop_path.write_bytes(b"video data")

        assert resolver._is_valid_loop(loop_path) is True

    def test_is_valid_loop_missing(self, resolver, tmp_path):
        """Test detection of missing file."""
        loop_path = tmp_path / "nonexistent.mp4"

        assert resolver._is_valid_loop(loop_path) is False

    def test_is_valid_loop_empty(self, resolver, tmp_path):
        """Test detection of empty file."""
        loop_path = tmp_path / "empty.mp4"
        loop_path.write_bytes(b"")

        assert resolver._is_valid_loop(loop_path) is False

    def test_is_valid_loop_invalid_extension(self, resolver, tmp_path):
        """Test detection of invalid file extension."""
        loop_path = tmp_path / "video.txt"
        loop_path.write_bytes(b"not a video")

        assert resolver._is_valid_loop(loop_path) is False

    def test_is_valid_loop_directory(self, resolver, tmp_path):
        """Test detection when path is a directory."""
        loop_path = tmp_path / "loops.mp4"
        loop_path.mkdir()

        assert resolver._is_valid_loop(loop_path) is False

    def test_get_default_loop(self, resolver, mock_config):
        """Test getting default loop."""
        result = resolver.get_default_loop()

        assert result == mock_config.default_loop
        assert result.exists()

    def test_get_default_loop_missing(self, resolver, mock_config):
        """Test error when default loop is missing."""
        mock_config.default_loop.unlink()

        with pytest.raises(FileNotFoundError, match="Default loop file not found"):
            resolver.get_default_loop()

    def test_find_loop_in_root_directory(self, resolver, mock_config):
        """Test finding loop in root loops directory."""
        # Create loop in root (not in tracks subdirectory)
        root_loop = mock_config.loops_path / "artist_-_title.mp4"
        root_loop.write_bytes(b"root video data")

        result = resolver.resolve_loop("Artist", "Title")

        assert result == root_loop

    def test_find_loop_prefers_tracks_subdirectory(self, resolver, mock_config):
        """Test that tracks subdirectory is preferred over root."""
        # Create loops in both locations
        tracks_dir = mock_config.loops_path / "tracks"
        tracks_loop = tracks_dir / "artist_-_title.mp4"
        tracks_loop.write_bytes(b"tracks video data")

        root_loop = mock_config.loops_path / "artist_-_title.mp4"
        root_loop.write_bytes(b"root video data")

        result = resolver.resolve_loop("Artist", "Title")

        # Should prefer tracks subdirectory
        assert result == tracks_loop

    def test_resolve_loop_with_album(self, resolver, mock_config, caplog):
        """Test that album parameter is accepted (used for logging)."""
        import logging
        caplog.set_level(logging.INFO)

        result = resolver.resolve_loop(
            "Test Artist",
            "Test Title",
            song_id="123",
            album="Test Album"
        )

        # Should return default since no specific loop exists
        assert result == mock_config.default_loop




