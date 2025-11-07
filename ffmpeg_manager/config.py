"""
FFmpeg configuration and encoding presets.

Provides different encoding configurations for various quality levels and
hardware acceleration options (CPU x264 vs NVENC GPU encoding).
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class EncodingPreset(str, Enum):
    """Available encoding presets."""

    # CPU encoding (x264)
    PRESET_720P_FAST = "720p_fast"
    PRESET_720P_QUALITY = "720p_quality"
    PRESET_1080P_FAST = "1080p_fast"
    PRESET_1080P_QUALITY = "1080p_quality"

    # GPU encoding (NVENC)
    PRESET_720P_NVENC = "720p_nvenc"
    PRESET_1080P_NVENC = "1080p_nvenc"
    PRESET_1080P60_NVENC = "1080p60_nvenc"

    # Low quality for testing
    PRESET_480P_TEST = "480p_test"


@dataclass
class EncodingConfig:
    """Configuration for a specific encoding preset."""

    name: str
    resolution: str  # e.g., "1280:720"
    video_codec: str  # "libx264" or "h264_nvenc"
    video_bitrate: str  # e.g., "3000k"
    video_preset: str  # "veryfast", "fast", "medium" for x264; "p4", "p5" for nvenc
    audio_codec: str  # "aac"
    audio_bitrate: str  # e.g., "192k"
    audio_sample_rate: str  # e.g., "44100"
    framerate: int  # e.g., 30 or 60
    keyframe_interval: int  # GOP size, e.g., 50
    pixel_format: str  # "yuv420p"
    use_nvenc: bool  # True if GPU encoding


# Encoding preset configurations
ENCODING_PRESETS: Dict[EncodingPreset, EncodingConfig] = {
    EncodingPreset.PRESET_720P_FAST: EncodingConfig(
        name="720p Fast (x264)",
        resolution="1280:720",
        video_codec="libx264",
        video_bitrate="2500k",
        video_preset="veryfast",
        audio_codec="aac",
        audio_bitrate="128k",
        audio_sample_rate="44100",
        framerate=30,
        keyframe_interval=50,
        pixel_format="yuv420p",
        use_nvenc=False,
    ),
    EncodingPreset.PRESET_720P_QUALITY: EncodingConfig(
        name="720p Quality (x264)",
        resolution="1280:720",
        video_codec="libx264",
        video_bitrate="3500k",
        video_preset="fast",
        audio_codec="aac",
        audio_bitrate="192k",
        audio_sample_rate="44100",
        framerate=30,
        keyframe_interval=50,
        pixel_format="yuv420p",
        use_nvenc=False,
    ),
    EncodingPreset.PRESET_1080P_FAST: EncodingConfig(
        name="1080p Fast (x264)",
        resolution="1920:1080",
        video_codec="libx264",
        video_bitrate="4500k",
        video_preset="veryfast",
        audio_codec="aac",
        audio_bitrate="192k",
        audio_sample_rate="44100",
        framerate=30,
        keyframe_interval=50,
        pixel_format="yuv420p",
        use_nvenc=False,
    ),
    EncodingPreset.PRESET_1080P_QUALITY: EncodingConfig(
        name="1080p Quality (x264)",
        resolution="1920:1080",
        video_codec="libx264",
        video_bitrate="6000k",
        video_preset="medium",
        audio_codec="aac",
        audio_bitrate="192k",
        audio_sample_rate="44100",
        framerate=30,
        keyframe_interval=50,
        pixel_format="yuv420p",
        use_nvenc=False,
    ),
    EncodingPreset.PRESET_720P_NVENC: EncodingConfig(
        name="720p NVENC",
        resolution="1280:720",
        video_codec="h264_nvenc",
        video_bitrate="3000k",
        video_preset="p4",  # NVENC preset (p1-p7, p4 is balanced)
        audio_codec="aac",
        audio_bitrate="192k",
        audio_sample_rate="44100",
        framerate=30,
        keyframe_interval=50,
        pixel_format="yuv420p",
        use_nvenc=True,
    ),
    EncodingPreset.PRESET_1080P_NVENC: EncodingConfig(
        name="1080p NVENC",
        resolution="1920:1080",
        video_codec="h264_nvenc",
        video_bitrate="5000k",
        video_preset="p4",
        audio_codec="aac",
        audio_bitrate="192k",
        audio_sample_rate="44100",
        framerate=30,
        keyframe_interval=50,
        pixel_format="yuv420p",
        use_nvenc=True,
    ),
    EncodingPreset.PRESET_1080P60_NVENC: EncodingConfig(
        name="1080p60 NVENC",
        resolution="1920:1080",
        video_codec="h264_nvenc",
        video_bitrate="7000k",
        video_preset="p5",  # Higher quality for 60fps
        audio_codec="aac",
        audio_bitrate="192k",
        audio_sample_rate="44100",
        framerate=60,
        keyframe_interval=100,
        pixel_format="yuv420p",
        use_nvenc=True,
    ),
    EncodingPreset.PRESET_480P_TEST: EncodingConfig(
        name="480p Test",
        resolution="854:480",
        video_codec="libx264",
        video_bitrate="1000k",
        video_preset="ultrafast",
        audio_codec="aac",
        audio_bitrate="96k",
        audio_sample_rate="44100",
        framerate=30,
        keyframe_interval=50,
        pixel_format="yuv420p",
        use_nvenc=False,
    ),
}


class FFmpegConfig(BaseSettings):
    """FFmpeg manager configuration from environment variables."""

    # RTMP output
    rtmp_endpoint: str = Field(
        default="rtmp://nginx-rtmp:1935/live/stream",
        description="RTMP endpoint for output stream",
    )

    # Audio input
    audio_url: str = Field(
        default="http://azuracast:8000/radio",
        description="HTTP URL of live audio stream from AzuraCast",
    )

    # Encoding preset
    encoding_preset: EncodingPreset = Field(
        default=EncodingPreset.PRESET_720P_FAST,
        description="Encoding quality preset",
    )

    # Fade transitions
    fade_in_duration: float = Field(
        default=1.0,
        description="Fade-in duration in seconds for video and audio",
        ge=0.0,
        le=5.0,
    )

    # Process management
    overlap_duration: float = Field(
        default=2.0,
        description="Overlap duration when switching tracks (seconds)",
        ge=0.0,
        le=10.0,
    )

    max_restart_attempts: int = Field(
        default=3,
        description="Maximum FFmpeg restart attempts per track",
        ge=1,
        le=10,
    )

    process_timeout: int = Field(
        default=30,
        description="Timeout for FFmpeg process operations (seconds)",
        ge=5,
        le=300,
    )

    # FFmpeg binary
    ffmpeg_binary: str = Field(
        default="ffmpeg",
        description="Path to FFmpeg binary",
    )

    # Logging
    log_level: str = Field(
        default="info",
        description="FFmpeg log level (quiet, panic, fatal, error, warning, info, verbose, debug)",
    )

    # Performance
    thread_queue_size: int = Field(
        default=512,
        description="Thread queue size for input streams",
        ge=64,
        le=4096,
    )

    model_config = ConfigDict(
        env_prefix="FFMPEG_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from environment
    )

    def get_encoding_config(self) -> EncodingConfig:
        """Get the encoding configuration for the selected preset."""
        return ENCODING_PRESETS[self.encoding_preset]


def get_config() -> FFmpegConfig:
    """
    Get FFmpeg configuration from environment variables.

    Returns:
        FFmpegConfig: Configuration instance
    """
    return FFmpegConfig()


def get_preset_config(preset: EncodingPreset) -> EncodingConfig:
    """
    Get encoding configuration for a specific preset.

    Args:
        preset: Encoding preset

    Returns:
        EncodingConfig: Preset configuration

    Raises:
        KeyError: If preset is not found
    """
    if preset not in ENCODING_PRESETS:
        raise KeyError(f"Unknown encoding preset: {preset}")
    return ENCODING_PRESETS[preset]


def list_presets() -> Dict[EncodingPreset, str]:
    """
    List all available encoding presets.

    Returns:
        Dict mapping preset enum to human-readable name
    """
    return {preset: config.name for preset, config in ENCODING_PRESETS.items()}
