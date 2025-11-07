"""
Tests for the manager module.
"""

import os
from pathlib import Path

import pytest

from asset_manager.config import AssetConfig
from asset_manager.manager import AssetManager


def test_asset_manager_initialization(test_config: AssetConfig):
    """Test AssetManager initialization."""
    manager = AssetManager(test_config)
    assert manager.config == test_config
    assert manager.validator is not None
    assert manager.overlay_generator is not None


def test_validate_loop_wrapper(test_config: AssetConfig, test_video_path: str):
    """Test validate_loop wrapper method."""
    manager = AssetManager(test_config)
    result = manager.validate_loop(test_video_path)

    assert result.valid is True
    assert result.file_path == test_video_path


def test_get_loop_metadata_wrapper(test_config: AssetConfig, test_video_path: str):
    """Test get_loop_metadata wrapper method."""
    manager = AssetManager(test_config)
    metadata = manager.get_loop_metadata(test_video_path)

    assert isinstance(metadata, dict)
    assert metadata["width"] == 1280
    assert metadata["height"] == 720


def test_get_loop_metadata_invalid_file(test_config: AssetConfig):
    """Test get_loop_metadata with invalid file."""
    manager = AssetManager(test_config)

    with pytest.raises(RuntimeError):
        manager.get_loop_metadata("/nonexistent/file.mp4")


def test_generate_overlay_wrapper(test_config: AssetConfig):
    """Test generate_overlay wrapper method."""
    manager = AssetManager(test_config)
    overlay_path = manager.generate_overlay(
        artist="Test Artist",
        title="Test Title",
    )

    assert os.path.exists(overlay_path)


def test_cleanup_old_overlays_wrapper(test_config: AssetConfig):
    """Test cleanup_old_overlays wrapper method."""
    manager = AssetManager(test_config)

    # Create a test overlay
    test_overlay = os.path.join(test_config.overlays_path, "test.png")
    Path(test_overlay).touch()

    # Clean up (shouldn't delete fresh overlay)
    manager.cleanup_old_overlays(older_than_hours=1)
    assert os.path.exists(test_overlay)


def test_ensure_default_loop_exists_missing(test_config: AssetConfig):
    """Test ensure_default_loop_exists with missing default."""
    manager = AssetManager(test_config)
    result = manager.ensure_default_loop_exists()

    assert result is False


def test_ensure_default_loop_exists_valid(test_config: AssetConfig, test_video_path: str):
    """Test ensure_default_loop_exists with valid default."""
    # Set default loop to test video
    test_config.default_loop_path = test_video_path

    manager = AssetManager(test_config)
    result = manager.ensure_default_loop_exists()

    assert result is True


def test_ensure_default_loop_exists_invalid(
    test_config: AssetConfig, test_video_wrong_resolution: str
):
    """Test ensure_default_loop_exists with invalid default."""
    # Set default loop to invalid video
    test_config.default_loop_path = test_video_wrong_resolution

    manager = AssetManager(test_config)
    result = manager.ensure_default_loop_exists()

    assert result is False


def test_get_loop_or_default_valid(test_config: AssetConfig, test_video_path: str):
    """Test get_loop_or_default with valid loop."""
    test_config.default_loop_path = test_video_path

    manager = AssetManager(test_config)
    result_path = manager.get_loop_or_default(test_video_path)

    assert result_path == test_video_path


def test_get_loop_or_default_nonexistent(test_config: AssetConfig, test_video_path: str):
    """Test get_loop_or_default with non-existent loop."""
    test_config.default_loop_path = test_video_path

    manager = AssetManager(test_config)
    result_path = manager.get_loop_or_default("/nonexistent/file.mp4")

    assert result_path == test_config.default_loop_path


def test_get_loop_or_default_invalid(
    test_config: AssetConfig,
    test_video_path: str,
    test_video_wrong_resolution: str,
):
    """Test get_loop_or_default with invalid loop."""
    test_config.default_loop_path = test_video_path

    manager = AssetManager(test_config)
    result_path = manager.get_loop_or_default(test_video_wrong_resolution)

    # Should fall back to default
    assert result_path == test_config.default_loop_path


def test_validate_all_loops_in_directory(
    test_config: AssetConfig, test_video_path: str, temp_dir: str
):
    """Test validating all loops in a directory."""
    # Create tracks directory
    tracks_dir = os.path.join(test_config.loops_base_path, "tracks")
    os.makedirs(tracks_dir, exist_ok=True)

    # Copy test video to tracks directory
    import shutil

    shutil.copy(test_video_path, os.path.join(tracks_dir, "track1.mp4"))

    # Also create an invalid file
    invalid_file = os.path.join(tracks_dir, "invalid.mp4")
    Path(invalid_file).touch()

    manager = AssetManager(test_config)
    results = manager.validate_all_loops_in_directory()

    assert results["total"] == 2
    assert results["valid"] == 1
    assert results["invalid"] == 1


def test_validate_all_loops_nonexistent_directory(test_config: AssetConfig):
    """Test validating loops in non-existent directory."""
    manager = AssetManager(test_config)
    results = manager.validate_all_loops_in_directory("/nonexistent/directory")

    assert results["total"] == 0
    assert results["valid"] == 0
    assert results["invalid"] == 0


def test_get_storage_stats(test_config: AssetConfig, test_video_path: str):
    """Test getting storage statistics."""
    # Copy test video to loops directory
    import shutil

    shutil.copy(test_video_path, os.path.join(test_config.loops_base_path, "test.mp4"))

    # Create test overlay
    test_overlay = os.path.join(test_config.overlays_path, "test.png")
    Path(test_overlay).touch()

    manager = AssetManager(test_config)
    stats = manager.get_storage_stats()

    assert stats["loops_count"] == 1
    assert stats["overlays_count"] == 1
    assert stats["loops_size_mb"] > 0
    assert stats["total_size_mb"] > 0


def test_get_storage_stats_empty(test_config: AssetConfig):
    """Test getting storage statistics for empty directories."""
    manager = AssetManager(test_config)
    stats = manager.get_storage_stats()

    assert stats["loops_count"] == 0
    assert stats["overlays_count"] == 0
    assert stats["total_size_mb"] == 0.0
