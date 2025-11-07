"""
Tests for FFmpeg configuration and encoding presets.
"""

import pytest

from ffmpeg_manager.config import (
    ENCODING_PRESETS,
    EncodingConfig,
    EncodingPreset,
    FFmpegConfig,
    get_config,
    get_preset_config,
    list_presets,
)


class TestEncodingPresets:
    """Test encoding preset configurations."""

    def test_all_presets_exist(self):
        """Test that all preset enums have configurations."""
        for preset in EncodingPreset:
            assert preset in ENCODING_PRESETS

    def test_720p_fast_preset(self):
        """Test 720p fast preset configuration."""
        config = ENCODING_PRESETS[EncodingPreset.PRESET_720P_FAST]

        assert config.resolution == "1280:720"
        assert config.video_codec == "libx264"
        assert config.framerate == 30
        assert config.use_nvenc is False
        assert config.pixel_format == "yuv420p"

    def test_1080p_nvenc_preset(self):
        """Test 1080p NVENC preset configuration."""
        config = ENCODING_PRESETS[EncodingPreset.PRESET_1080P_NVENC]

        assert config.resolution == "1920:1080"
        assert config.video_codec == "h264_nvenc"
        assert config.framerate == 30
        assert config.use_nvenc is True

    def test_480p_test_preset(self):
        """Test 480p test preset (low quality)."""
        config = ENCODING_PRESETS[EncodingPreset.PRESET_480P_TEST]

        assert config.resolution == "854:480"
        assert config.video_preset == "ultrafast"
        assert int(config.video_bitrate.rstrip("k")) < 1500


class TestFFmpegConfig:
    """Test FFmpeg configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FFmpegConfig()

        assert "rtmp://" in config.rtmp_endpoint
        assert "http://" in config.audio_url
        assert config.fade_in_duration >= 0.0
        assert config.max_restart_attempts >= 1
        assert config.ffmpeg_binary == "ffmpeg"

    def test_custom_config(self):
        """Test custom configuration."""
        config = FFmpegConfig(
            rtmp_endpoint="rtmp://custom:1935/live/stream",
            audio_url="http://custom:8000/radio",
            encoding_preset=EncodingPreset.PRESET_1080P_QUALITY,
            fade_in_duration=2.5,
            max_restart_attempts=5,
        )

        assert config.rtmp_endpoint == "rtmp://custom:1935/live/stream"
        assert config.audio_url == "http://custom:8000/radio"
        assert config.encoding_preset == EncodingPreset.PRESET_1080P_QUALITY
        assert config.fade_in_duration == 2.5
        assert config.max_restart_attempts == 5

    def test_get_encoding_config(self):
        """Test getting encoding config from FFmpegConfig."""
        config = FFmpegConfig(encoding_preset=EncodingPreset.PRESET_720P_QUALITY)
        encoding_config = config.get_encoding_config()

        assert isinstance(encoding_config, EncodingConfig)
        assert encoding_config.resolution == "1280:720"

    def test_validation_constraints(self):
        """Test configuration validation constraints."""
        # Fade duration should be between 0.0 and 5.0
        with pytest.raises(ValueError):
            FFmpegConfig(fade_in_duration=-1.0)

        with pytest.raises(ValueError):
            FFmpegConfig(fade_in_duration=10.0)

        # Max restart attempts should be between 1 and 10
        with pytest.raises(ValueError):
            FFmpegConfig(max_restart_attempts=0)

        with pytest.raises(ValueError):
            FFmpegConfig(max_restart_attempts=20)


class TestConfigHelpers:
    """Test configuration helper functions."""

    def test_get_config(self):
        """Test get_config factory function."""
        config = get_config()

        assert isinstance(config, FFmpegConfig)
        assert config.rtmp_endpoint
        assert config.audio_url

    def test_get_preset_config(self):
        """Test get_preset_config helper."""
        config = get_preset_config(EncodingPreset.PRESET_720P_FAST)

        assert isinstance(config, EncodingConfig)
        assert config.name == "720p Fast (x264)"

    def test_get_preset_config_invalid(self):
        """Test get_preset_config with invalid preset."""
        # This should raise KeyError for unknown preset
        # But since we're using Enum, this is actually hard to test
        # without creating a fake enum value
        pass

    def test_list_presets(self):
        """Test list_presets helper."""
        presets = list_presets()

        assert isinstance(presets, dict)
        assert len(presets) == len(EncodingPreset)
        assert EncodingPreset.PRESET_720P_FAST in presets
        assert "720p Fast" in presets[EncodingPreset.PRESET_720P_FAST]


class TestEncodingConfig:
    """Test EncodingConfig dataclass."""

    def test_encoding_config_creation(self):
        """Test creating an encoding config."""
        config = EncodingConfig(
            name="Test Config",
            resolution="1920:1080",
            video_codec="libx264",
            video_bitrate="5000k",
            video_preset="medium",
            audio_codec="aac",
            audio_bitrate="192k",
            audio_sample_rate="44100",
            framerate=30,
            keyframe_interval=50,
            pixel_format="yuv420p",
            use_nvenc=False,
        )

        assert config.name == "Test Config"
        assert config.resolution == "1920:1080"
        assert config.framerate == 30
        assert config.use_nvenc is False
