"""Configuration management for metadata watcher service using Pydantic settings."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration for the metadata watcher service."""

    # AzuraCast settings
    azuracast_url: str
    azuracast_api_key: str
    azuracast_audio_url: str

    # RTMP endpoint
    rtmp_endpoint: str = "rtmp://nginx-rtmp:1935/live/stream"

    # Database settings
    postgres_user: str = "radio"
    postgres_password: str
    postgres_db: str = "radio_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # FFmpeg settings
    video_resolution: str = "1280:720"
    video_bitrate: str = "3000k"
    audio_bitrate: str = "192k"
    video_encoder: str = "libx264"
    ffmpeg_preset: str = "veryfast"
    fade_duration: float = 1.0

    # Video assets
    loops_path: Path = Path("/app/loops")
    default_loop: Path = Path("/app/loops/default.mp4")

    # Service settings
    watcher_port: int = 9000
    log_level: str = "INFO"
    log_path: Path = Path("/var/log/radio")
    environment: str = "production"
    debug: bool = False
    ffmpeg_log_level: str = "info"

    # Process management
    track_overlap_duration: float = 2.0
    max_restart_attempts: int = 3
    restart_cooldown_seconds: int = 60

    # Text overlay (with default)
    enable_text_overlay: bool = False

    # Logo watermark (with defaults)
    enable_logo_watermark: bool = False
    logo_path: str = "/app/logos/logo.png"
    logo_position: str = "top-right"
    logo_opacity: float = 0.8

    # Security
    webhook_secret: Optional[str] = None
    api_token: str

    # Notifications (optional)
    discord_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        """Get the PostgreSQL database URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def validate(self) -> None:
        """Additional validation for non-trivial fields."""
        # Check video resolution format
        try:
            width, height = self.video_resolution.split(":")
            if int(width) <= 0 or int(height) <= 0:
                raise ValueError("Resolution dimensions must be positive")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid video resolution format: {self.video_resolution}") from e

        # Validate encoder
        valid_encoders = ["libx264", "h264_nvenc", "libx265", "hevc_nvenc"]
        if self.video_encoder not in valid_encoders:
            raise ValueError(
                f"Invalid encoder '{self.video_encoder}'. Must be one of: {', '.join(valid_encoders)}"
            )

        # Validate fade duration
        if self.fade_duration < 0 or self.fade_duration > 10:
            raise ValueError("Fade duration must be between 0 and 10 seconds")

        # Check default loop exists (if not in test mode)
        if self.environment != "testing" and not self.default_loop.exists():
            raise ValueError(f"Default loop file not found: {self.default_loop}")

    @classmethod
    def from_env(cls) -> "Config":
        """Backwards-compatible constructor for legacy callers."""
        # Allow overriding RTMP host/port
        rtmp_host = os.getenv("RTMP_HOST", "nginx-rtmp")
        rtmp_port = os.getenv("RTMP_PORT", "1935")
        rtmp_endpoint = f"rtmp://{rtmp_host}:{rtmp_port}/live/stream"

        # Instantiate settings (will validate required fields)
        settings = cls(rtmp_endpoint=rtmp_endpoint)
        return settings
