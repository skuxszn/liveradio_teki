"""Tests for advanced configuration."""

import os
import pytest

from advanced.config import AdvancedConfig


class TestAdvancedConfig:
    """Test suite for AdvancedConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AdvancedConfig()
        
        assert config.audio_url == "http://localhost:8000/radio"
        assert config.rtmp_endpoint == "rtmp://nginx-rtmp:1935/live/stream"
        assert config.crossfade_duration == 2.0
        assert config.crossfade_transition == "fade"
        assert config.resolution == "1280:720"
        assert config.framerate == 30
        assert config.video_bitrate == "3000k"
        assert config.audio_bitrate == "192k"
    
    def test_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("AUDIO_URL", "http://test:9000/audio")
        monkeypatch.setenv("RTMP_ENDPOINT", "rtmp://test:1935/stream")
        monkeypatch.setenv("CROSSFADE_DURATION", "3.5")
        monkeypatch.setenv("CROSSFADE_TRANSITION", "wipeleft")
        monkeypatch.setenv("VIDEO_RESOLUTION", "1920:1080")
        monkeypatch.setenv("VIDEO_BITRATE", "5000k")
        monkeypatch.setenv("AUDIO_BITRATE", "256k")
        monkeypatch.setenv("DEBUG", "true")
        
        config = AdvancedConfig.from_env()
        
        assert config.audio_url == "http://test:9000/audio"
        assert config.rtmp_endpoint == "rtmp://test:1935/stream"
        assert config.crossfade_duration == 3.5
        assert config.crossfade_transition == "wipeleft"
        assert config.resolution == "1920:1080"
        assert config.video_bitrate == "5000k"
        assert config.audio_bitrate == "256k"
        assert config.debug is True
    
    def test_validate_success(self):
        """Test successful validation."""
        config = AdvancedConfig()
        config.validate()  # Should not raise
    
    def test_validate_negative_crossfade(self):
        """Test validation fails for negative crossfade duration."""
        config = AdvancedConfig(crossfade_duration=-1.0)
        
        with pytest.raises(ValueError, match="crossfade_duration must be non-negative"):
            config.validate()
    
    def test_validate_excessive_crossfade(self):
        """Test validation fails for excessive crossfade duration."""
        config = AdvancedConfig(crossfade_duration=15.0)
        
        with pytest.raises(ValueError, match="should not exceed 10 seconds"):
            config.validate()
    
    def test_validate_hls_segment_duration(self):
        """Test validation fails for invalid HLS segment duration."""
        config = AdvancedConfig(hls_segment_duration=0)
        
        with pytest.raises(ValueError, match="hls_segment_duration must be at least 1"):
            config.validate()
    
    def test_validate_hls_playlist_size(self):
        """Test validation fails for invalid HLS playlist size."""
        config = AdvancedConfig(hls_playlist_size=1)
        
        with pytest.raises(ValueError, match="hls_playlist_size must be at least 2"):
            config.validate()
    
    def test_validate_framerate(self):
        """Test validation fails for invalid framerate."""
        config = AdvancedConfig(framerate=0)
        
        with pytest.raises(ValueError, match="framerate must be between 1 and 60"):
            config.validate()
        
        config = AdvancedConfig(framerate=61)
        
        with pytest.raises(ValueError, match="framerate must be between 1 and 60"):
            config.validate()
    
    def test_validate_process_timeout(self):
        """Test validation fails for invalid process timeout."""
        config = AdvancedConfig(process_timeout=0)
        
        with pytest.raises(ValueError, match="process_timeout must be at least 1"):
            config.validate()
    
    def test_validate_max_restart_attempts(self):
        """Test validation fails for negative max restart attempts."""
        config = AdvancedConfig(max_restart_attempts=-1)
        
        with pytest.raises(ValueError, match="max_restart_attempts must be non-negative"):
            config.validate()
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = AdvancedConfig(
            audio_url="http://test/audio",
            crossfade_duration=3.0,
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["audio_url"] == "http://test/audio"
        assert config_dict["crossfade_duration"] == 3.0
        assert "rtmp_endpoint" in config_dict
        assert "video_bitrate" in config_dict



