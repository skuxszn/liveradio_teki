"""
Tests for the config module.
"""

import os

from asset_manager.config import AssetConfig, get_config


def test_asset_config_defaults():
    """Test AssetConfig with default values."""
    config = AssetConfig()

    assert config.loops_base_path == os.getenv("LOOPS_BASE_PATH", "/srv/loops")
    assert config.target_resolution == os.getenv("TARGET_RESOLUTION", "1280:720")
    assert config.min_duration_seconds == int(os.getenv("MIN_DURATION_SECONDS", "5"))


def test_asset_config_custom_values():
    """Test AssetConfig with custom values."""
    config = AssetConfig(
        loops_base_path="/custom/loops",
        target_resolution="1920:1080",
        min_duration_seconds=10,
    )

    assert config.loops_base_path == "/custom/loops"
    assert config.target_resolution == "1920:1080"
    assert config.min_duration_seconds == 10


def test_get_target_width():
    """Test extracting target width from resolution."""
    config = AssetConfig(target_resolution="1920:1080")
    assert config.get_target_width() == 1920


def test_get_target_height():
    """Test extracting target height from resolution."""
    config = AssetConfig(target_resolution="1920:1080")
    assert config.get_target_height() == 1080


def test_get_allowed_audio_codecs_list():
    """Test parsing allowed audio codecs."""
    config = AssetConfig(allowed_audio_codecs="aac,mp3,none")
    codecs = config.get_allowed_audio_codecs_list()

    assert len(codecs) == 3
    assert "aac" in codecs
    assert "mp3" in codecs
    assert "none" in codecs


def test_get_config():
    """Test get_config function."""
    config = get_config()
    assert isinstance(config, AssetConfig)
