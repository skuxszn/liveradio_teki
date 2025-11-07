"""
Tests for the validator module.
"""

import os
from pathlib import Path

import pytest

from asset_manager.config import AssetConfig
from asset_manager.validator import ValidationResult, VideoMetadata, VideoValidator


def test_validation_result_add_error():
    """Test adding errors to ValidationResult."""
    result = ValidationResult(valid=True, file_path="/test/file.mp4", errors=[])

    assert result.valid is True
    assert len(result.errors) == 0

    result.add_error("Test error")

    assert result.valid is False
    assert len(result.errors) == 1
    assert result.errors[0] == "Test error"


def test_video_metadata_to_dict():
    """Test VideoMetadata to_dict conversion."""
    metadata = VideoMetadata(
        duration=10.5,
        width=1280,
        height=720,
        video_codec="h264",
        audio_codec="aac",
        bitrate=3000000,
        fps=30.0,
        format_name="mov,mp4,m4a,3gp,3g2,mj2",
        file_size=1024000,
    )

    data = metadata.to_dict()

    assert data["duration"] == 10.5
    assert data["width"] == 1280
    assert data["height"] == 720
    assert data["video_codec"] == "h264"
    assert data["audio_codec"] == "aac"


def test_validator_initialization(test_config: AssetConfig):
    """Test VideoValidator initialization."""
    validator = VideoValidator(test_config)
    assert validator.config == test_config


def test_validate_loop_nonexistent_file(test_config: AssetConfig):
    """Test validating a non-existent file."""
    validator = VideoValidator(test_config)
    result = validator.validate_loop("/nonexistent/file.mp4")

    assert result.valid is False
    assert len(result.errors) > 0
    assert "does not exist" in result.errors[0]


def test_validate_loop_directory(test_config: AssetConfig, temp_dir: str):
    """Test validating a directory instead of file."""
    validator = VideoValidator(test_config)
    result = validator.validate_loop(temp_dir)

    assert result.valid is False
    assert any("not a file" in err for err in result.errors)


def test_validate_loop_unreadable_file(test_config: AssetConfig, temp_dir: str):
    """Test validating an unreadable file."""
    # Create a file
    test_file = os.path.join(temp_dir, "unreadable.mp4")
    Path(test_file).touch()

    # Make it unreadable (this might fail on some systems, so we catch it)
    try:
        os.chmod(test_file, 0o000)

        validator = VideoValidator(test_config)
        result = validator.validate_loop(test_file)

        # Restore permissions for cleanup
        os.chmod(test_file, 0o644)

        assert result.valid is False
        assert any("not readable" in err or "accessing file" in err for err in result.errors)
    except (OSError, PermissionError):
        # Skip if we can't make file unreadable (e.g., running as root)
        pytest.skip("Cannot make file unreadable on this system")


def test_validate_loop_valid_video(test_config: AssetConfig, test_video_path: str):
    """Test validating a valid video file."""
    validator = VideoValidator(test_config)
    result = validator.validate_loop(test_video_path)

    assert result.valid is True
    assert len(result.errors) == 0
    assert result.metadata is not None


def test_validate_loop_wrong_resolution(test_config: AssetConfig, test_video_wrong_resolution: str):
    """Test validating a video with wrong resolution."""
    validator = VideoValidator(test_config)
    result = validator.validate_loop(test_video_wrong_resolution)

    assert result.valid is False
    assert any("resolution" in err.lower() for err in result.errors)


def test_validate_loop_short_duration(test_config: AssetConfig, test_video_short_duration: str):
    """Test validating a video with short duration."""
    validator = VideoValidator(test_config)
    result = validator.validate_loop(test_video_short_duration)

    assert result.valid is False
    assert any("duration" in err.lower() for err in result.errors)


def test_get_loop_metadata(test_config: AssetConfig, test_video_path: str):
    """Test extracting metadata from a video."""
    validator = VideoValidator(test_config)
    metadata = validator.get_loop_metadata(test_video_path)

    assert isinstance(metadata, VideoMetadata)
    assert metadata.width == 1280
    assert metadata.height == 720
    assert metadata.duration >= 5.0
    assert metadata.video_codec == "h264"


def test_get_loop_metadata_nonexistent_file(test_config: AssetConfig):
    """Test extracting metadata from non-existent file."""
    validator = VideoValidator(test_config)

    with pytest.raises(RuntimeError):
        validator.get_loop_metadata("/nonexistent/file.mp4")


def test_extract_fps(test_config: AssetConfig):
    """Test FPS extraction from stream data."""
    validator = VideoValidator(test_config)

    # Test normal case
    stream_data = {"r_frame_rate": "30/1"}
    fps = validator._extract_fps(stream_data)
    assert fps == 30.0

    # Test fractional FPS
    stream_data = {"r_frame_rate": "30000/1001"}
    fps = validator._extract_fps(stream_data)
    assert 29.97 <= fps <= 29.98

    # Test missing FPS
    stream_data = {}
    fps = validator._extract_fps(stream_data)
    assert fps == 0.0

    # Test invalid format
    stream_data = {"r_frame_rate": "invalid"}
    fps = validator._extract_fps(stream_data)
    assert fps == 0.0
