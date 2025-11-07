"""
Configuration management for the asset manager module.
"""

import os
from dataclasses import dataclass


@dataclass
class AssetConfig:
    """Configuration for asset management."""

    # Storage paths
    loops_base_path: str = os.getenv("LOOPS_BASE_PATH", "/srv/loops")
    default_loop_path: str = os.getenv("DEFAULT_LOOP_PATH", "/srv/loops/default.mp4")
    overlays_path: str = os.getenv("OVERLAYS_PATH", "/srv/loops/overlays")
    templates_path: str = os.getenv("TEMPLATES_PATH", "/srv/loops/templates")

    # Video validation settings
    target_resolution: str = os.getenv("TARGET_RESOLUTION", "1280:720")
    min_duration_seconds: int = int(os.getenv("MIN_DURATION_SECONDS", "5"))
    required_video_codec: str = os.getenv("REQUIRED_VIDEO_CODEC", "h264")
    allowed_audio_codecs: str = os.getenv("ALLOWED_AUDIO_CODECS", "aac,none")

    # Overlay settings
    overlay_ttl_hours: int = int(os.getenv("OVERLAY_TTL_HOURS", "1"))
    overlay_font_size: int = int(os.getenv("OVERLAY_FONT_SIZE", "48"))
    overlay_font_color: str = os.getenv("OVERLAY_FONT_COLOR", "#FFFFFF")
    overlay_background_color: str = os.getenv("OVERLAY_BACKGROUND_COLOR", "#000000")
    overlay_opacity: int = int(os.getenv("OVERLAY_OPACITY", "180"))

    # Performance settings
    validation_timeout_seconds: int = int(os.getenv("VALIDATION_TIMEOUT_SECONDS", "10"))
    ffprobe_path: str = os.getenv("FFPROBE_PATH", "ffprobe")
    ffmpeg_path: str = os.getenv("FFMPEG_PATH", "ffmpeg")

    def get_target_width(self) -> int:
        """Extract target width from resolution string."""
        return int(self.target_resolution.split(":")[0])

    def get_target_height(self) -> int:
        """Extract target height from resolution string."""
        return int(self.target_resolution.split(":")[1])

    def get_allowed_audio_codecs_list(self) -> list[str]:
        """Get list of allowed audio codecs."""
        return [codec.strip() for codec in self.allowed_audio_codecs.split(",")]


def get_config() -> AssetConfig:
    """Get asset configuration instance."""
    return AssetConfig()
