"""Configuration for advanced FFmpeg module.

Manages settings for persistent FFmpeg process with dual-input crossfading.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AdvancedConfig:
    """Configuration for advanced FFmpeg features.
    
    Attributes:
        audio_url: URL of the live audio stream
        rtmp_endpoint: RTMP endpoint for output
        ffmpeg_binary: Path to FFmpeg binary
        
        # Crossfade settings
        crossfade_duration: Duration of crossfade in seconds
        crossfade_transition: Type of transition (fade, wipeleft, wiperight, etc.)
        
        # HLS settings
        hls_segment_duration: HLS segment duration in seconds
        hls_playlist_size: Number of segments in playlist
        hls_temp_dir: Temporary directory for HLS files
        
        # Video settings
        resolution: Output resolution (e.g., "1280:720")
        framerate: Output framerate (e.g., 30)
        video_bitrate: Video bitrate (e.g., "3000k")
        video_codec: Video codec (e.g., "libx264")
        video_preset: Encoding preset (e.g., "veryfast")
        pixel_format: Pixel format (e.g., "yuv420p")
        
        # Audio settings
        audio_bitrate: Audio bitrate (e.g., "192k")
        audio_codec: Audio codec (e.g., "aac")
        audio_sample_rate: Audio sample rate (e.g., "44100")
        
        # Process settings
        process_timeout: Timeout for process operations in seconds
        restart_on_error: Whether to restart on errors
        max_restart_attempts: Maximum number of restart attempts
        
        # Logging
        log_level: FFmpeg log level
        debug: Enable debug mode
    """
    
    # Connection settings
    audio_url: str = "http://localhost:8000/radio"
    rtmp_endpoint: str = "rtmp://nginx-rtmp:1935/live/stream"
    ffmpeg_binary: str = "ffmpeg"
    
    # Crossfade settings
    crossfade_duration: float = 2.0
    crossfade_transition: str = "fade"
    
    # HLS settings
    hls_segment_duration: int = 2
    hls_playlist_size: int = 5
    hls_temp_dir: str = "/tmp/radio_hls"
    
    # Video settings
    resolution: str = "1280:720"
    framerate: int = 30
    video_bitrate: str = "3000k"
    video_codec: str = "libx264"
    video_preset: str = "veryfast"
    pixel_format: str = "yuv420p"
    keyframe_interval: int = 60
    
    # Audio settings
    audio_bitrate: str = "192k"
    audio_codec: str = "aac"
    audio_sample_rate: str = "44100"
    
    # Process settings
    process_timeout: int = 10
    restart_on_error: bool = True
    max_restart_attempts: int = 3
    
    # Logging
    log_level: str = "info"
    debug: bool = False
    
    @classmethod
    def from_env(cls) -> "AdvancedConfig":
        """Create configuration from environment variables.
        
        Environment variables:
            AUDIO_URL: Audio stream URL
            RTMP_ENDPOINT: RTMP output endpoint
            FFMPEG_BINARY: Path to FFmpeg binary
            CROSSFADE_DURATION: Crossfade duration in seconds
            CROSSFADE_TRANSITION: Type of crossfade transition
            VIDEO_RESOLUTION: Output resolution
            VIDEO_BITRATE: Video bitrate
            AUDIO_BITRATE: Audio bitrate
            DEBUG: Enable debug mode (true/false)
        
        Returns:
            AdvancedConfig instance with values from environment
        """
        return cls(
            audio_url=os.getenv("AUDIO_URL", cls.audio_url),
            rtmp_endpoint=os.getenv("RTMP_ENDPOINT", cls.rtmp_endpoint),
            ffmpeg_binary=os.getenv("FFMPEG_BINARY", cls.ffmpeg_binary),
            
            crossfade_duration=float(os.getenv("CROSSFADE_DURATION", cls.crossfade_duration)),
            crossfade_transition=os.getenv("CROSSFADE_TRANSITION", cls.crossfade_transition),
            
            hls_segment_duration=int(os.getenv("HLS_SEGMENT_DURATION", cls.hls_segment_duration)),
            hls_playlist_size=int(os.getenv("HLS_PLAYLIST_SIZE", cls.hls_playlist_size)),
            hls_temp_dir=os.getenv("HLS_TEMP_DIR", cls.hls_temp_dir),
            
            resolution=os.getenv("VIDEO_RESOLUTION", cls.resolution),
            framerate=int(os.getenv("VIDEO_FRAMERATE", cls.framerate)),
            video_bitrate=os.getenv("VIDEO_BITRATE", cls.video_bitrate),
            video_codec=os.getenv("VIDEO_CODEC", cls.video_codec),
            video_preset=os.getenv("VIDEO_PRESET", cls.video_preset),
            pixel_format=os.getenv("PIXEL_FORMAT", cls.pixel_format),
            keyframe_interval=int(os.getenv("KEYFRAME_INTERVAL", cls.keyframe_interval)),
            
            audio_bitrate=os.getenv("AUDIO_BITRATE", cls.audio_bitrate),
            audio_codec=os.getenv("AUDIO_CODEC", cls.audio_codec),
            audio_sample_rate=os.getenv("AUDIO_SAMPLE_RATE", cls.audio_sample_rate),
            
            process_timeout=int(os.getenv("PROCESS_TIMEOUT", cls.process_timeout)),
            restart_on_error=os.getenv("RESTART_ON_ERROR", "true").lower() == "true",
            max_restart_attempts=int(os.getenv("MAX_RESTART_ATTEMPTS", cls.max_restart_attempts)),
            
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )
    
    def validate(self) -> None:
        """Validate configuration values.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if self.crossfade_duration < 0:
            raise ValueError("crossfade_duration must be non-negative")
        
        if self.crossfade_duration > 10:
            raise ValueError("crossfade_duration should not exceed 10 seconds")
        
        if self.hls_segment_duration < 1:
            raise ValueError("hls_segment_duration must be at least 1 second")
        
        if self.hls_playlist_size < 2:
            raise ValueError("hls_playlist_size must be at least 2")
        
        if self.framerate < 1 or self.framerate > 60:
            raise ValueError("framerate must be between 1 and 60")
        
        if self.process_timeout < 1:
            raise ValueError("process_timeout must be at least 1 second")
        
        if self.max_restart_attempts < 0:
            raise ValueError("max_restart_attempts must be non-negative")
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "audio_url": self.audio_url,
            "rtmp_endpoint": self.rtmp_endpoint,
            "ffmpeg_binary": self.ffmpeg_binary,
            "crossfade_duration": self.crossfade_duration,
            "crossfade_transition": self.crossfade_transition,
            "hls_segment_duration": self.hls_segment_duration,
            "hls_playlist_size": self.hls_playlist_size,
            "hls_temp_dir": self.hls_temp_dir,
            "resolution": self.resolution,
            "framerate": self.framerate,
            "video_bitrate": self.video_bitrate,
            "video_codec": self.video_codec,
            "video_preset": self.video_preset,
            "pixel_format": self.pixel_format,
            "keyframe_interval": self.keyframe_interval,
            "audio_bitrate": self.audio_bitrate,
            "audio_codec": self.audio_codec,
            "audio_sample_rate": self.audio_sample_rate,
            "process_timeout": self.process_timeout,
            "restart_on_error": self.restart_on_error,
            "max_restart_attempts": self.max_restart_attempts,
            "log_level": self.log_level,
            "debug": self.debug,
        }



