"""Unit tests for configuration management."""

import os
import pytest
from pathlib import Path
from metadata_watcher.config import Config


class TestConfig:
    """Test configuration loading and validation."""

    def test_from_env_missing_required(self, monkeypatch):
        """Test that missing required variables raise ValueError."""
        # Clear all env vars
        for key in [
            "AZURACAST_URL",
            "AZURACAST_API_KEY",
            "AZURACAST_AUDIO_URL",
            "POSTGRES_PASSWORD",
        ]:
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(ValueError, match="Missing required environment variables"):
            Config.from_env()

    def test_from_env_with_defaults(self, monkeypatch):
        """Test configuration loading with default values."""
        # Set required variables
        monkeypatch.setenv("AZURACAST_URL", "http://test.example.com")
        monkeypatch.setenv("AZURACAST_API_KEY", "test-key")
        monkeypatch.setenv("AZURACAST_AUDIO_URL", "http://test.example.com:8000/radio")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
        monkeypatch.setenv("ENVIRONMENT", "testing")

        config = Config.from_env()

        # Check required values
        assert config.azuracast_url == "http://test.example.com"
        assert config.azuracast_api_key == "test-key"
        assert config.postgres_password == "test-password"

        # Check defaults
        assert config.postgres_user == "radio"
        assert config.postgres_port == 5432
        assert config.video_resolution == "1280:720"
        assert config.watcher_port == 9000

    def test_from_env_custom_values(self, monkeypatch):
        """Test configuration with custom values."""
        monkeypatch.setenv("AZURACAST_URL", "http://custom.example.com")
        monkeypatch.setenv("AZURACAST_API_KEY", "custom-key")
        monkeypatch.setenv("AZURACAST_AUDIO_URL", "http://custom.example.com:8000/radio")
        monkeypatch.setenv("POSTGRES_PASSWORD", "custom-password")
        monkeypatch.setenv("VIDEO_RESOLUTION", "1920:1080")
        monkeypatch.setenv("VIDEO_BITRATE", "5000k")
        monkeypatch.setenv("WATCHER_PORT", "9001")
        monkeypatch.setenv("ENVIRONMENT", "testing")

        config = Config.from_env()

        assert config.video_resolution == "1920:1080"
        assert config.video_bitrate == "5000k"
        assert config.watcher_port == 9001

    def test_database_url_property(self, monkeypatch):
        """Test database URL construction."""
        monkeypatch.setenv("AZURACAST_URL", "http://test.example.com")
        monkeypatch.setenv("AZURACAST_API_KEY", "test-key")
        monkeypatch.setenv("AZURACAST_AUDIO_URL", "http://test.example.com:8000/radio")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
        monkeypatch.setenv("POSTGRES_USER", "testuser")
        monkeypatch.setenv("POSTGRES_HOST", "testhost")
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        monkeypatch.setenv("POSTGRES_DB", "testdb")
        monkeypatch.setenv("ENVIRONMENT", "testing")

        config = Config.from_env()

        expected_url = "postgresql://testuser:test-password@testhost:5433/testdb"
        assert config.database_url == expected_url

    def test_validate_valid_config(self, monkeypatch, tmp_path):
        """Test validation passes for valid configuration."""
        # Create a temporary default loop file
        default_loop = tmp_path / "default.mp4"
        default_loop.write_bytes(b"fake video data")

        monkeypatch.setenv("AZURACAST_URL", "http://test.example.com")
        monkeypatch.setenv("AZURACAST_API_KEY", "test-key")
        monkeypatch.setenv("AZURACAST_AUDIO_URL", "http://test.example.com:8000/radio")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
        monkeypatch.setenv("DEFAULT_LOOP", str(default_loop))
        monkeypatch.setenv("VIDEO_RESOLUTION", "1280:720")
        monkeypatch.setenv("VIDEO_ENCODER", "libx264")
        monkeypatch.setenv("FADE_DURATION", "1.5")
        monkeypatch.setenv("ENVIRONMENT", "testing")

        config = Config.from_env()
        config.validate()  # Should not raise

    def test_validate_invalid_resolution(self, monkeypatch):
        """Test validation fails for invalid resolution."""
        monkeypatch.setenv("AZURACAST_URL", "http://test.example.com")
        monkeypatch.setenv("AZURACAST_API_KEY", "test-key")
        monkeypatch.setenv("AZURACAST_AUDIO_URL", "http://test.example.com:8000/radio")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
        monkeypatch.setenv("VIDEO_RESOLUTION", "invalid")
        monkeypatch.setenv("ENVIRONMENT", "testing")

        config = Config.from_env()

        with pytest.raises(ValueError, match="Invalid video resolution format"):
            config.validate()

    def test_validate_invalid_encoder(self, monkeypatch, tmp_path):
        """Test validation fails for invalid encoder."""
        default_loop = tmp_path / "default.mp4"
        default_loop.write_bytes(b"fake video data")

        monkeypatch.setenv("AZURACAST_URL", "http://test.example.com")
        monkeypatch.setenv("AZURACAST_API_KEY", "test-key")
        monkeypatch.setenv("AZURACAST_AUDIO_URL", "http://test.example.com:8000/radio")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
        monkeypatch.setenv("DEFAULT_LOOP", str(default_loop))
        monkeypatch.setenv("VIDEO_ENCODER", "invalid_encoder")
        monkeypatch.setenv("ENVIRONMENT", "testing")

        config = Config.from_env()

        with pytest.raises(ValueError, match="Invalid encoder"):
            config.validate()

    def test_validate_invalid_fade_duration(self, monkeypatch, tmp_path):
        """Test validation fails for out-of-range fade duration."""
        default_loop = tmp_path / "default.mp4"
        default_loop.write_bytes(b"fake video data")

        monkeypatch.setenv("AZURACAST_URL", "http://test.example.com")
        monkeypatch.setenv("AZURACAST_API_KEY", "test-key")
        monkeypatch.setenv("AZURACAST_AUDIO_URL", "http://test.example.com:8000/radio")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
        monkeypatch.setenv("DEFAULT_LOOP", str(default_loop))
        monkeypatch.setenv("FADE_DURATION", "15.0")
        monkeypatch.setenv("ENVIRONMENT", "testing")

        config = Config.from_env()

        with pytest.raises(ValueError, match="Fade duration must be between 0 and 10"):
            config.validate()

    def test_rtmp_endpoint_construction(self, monkeypatch):
        """Test RTMP endpoint is constructed correctly."""
        monkeypatch.setenv("AZURACAST_URL", "http://test.example.com")
        monkeypatch.setenv("AZURACAST_API_KEY", "test-key")
        monkeypatch.setenv("AZURACAST_AUDIO_URL", "http://test.example.com:8000/radio")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
        monkeypatch.setenv("RTMP_HOST", "custom-rtmp")
        monkeypatch.setenv("RTMP_PORT", "1936")
        monkeypatch.setenv("ENVIRONMENT", "testing")

        config = Config.from_env()

        assert config.rtmp_endpoint == "rtmp://custom-rtmp:1936/live/stream"
