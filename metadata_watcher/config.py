"""Configuration management for metadata watcher service.

Loads configuration from environment variables with validation and defaults.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Configuration for the metadata watcher service."""

    # AzuraCast settings
    azuracast_url: str
    azuracast_api_key: str
    azuracast_audio_url: str

    # RTMP endpoint
    rtmp_endpoint: str

    # Database settings
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int

    # FFmpeg settings
    video_resolution: str
    video_bitrate: str
    audio_bitrate: str
    video_encoder: str
    ffmpeg_preset: str
    fade_duration: float

    # Video assets
    loops_path: Path
    default_loop: Path

    # Service settings
    watcher_port: int
    log_level: str
    log_path: Path
    environment: str
    debug: bool
    ffmpeg_log_level: str

    # Process management
    track_overlap_duration: float
    max_restart_attempts: int
    restart_cooldown_seconds: int

    # Text overlay (with default)
    enable_text_overlay: bool = False

    # Logo watermark (with defaults)
    enable_logo_watermark: bool = False
    logo_path: str = "/app/logos/logo.png"
    logo_position: str = "top-right"
    logo_opacity: float = 0.8

    # Security (with defaults)
    webhook_secret: Optional[str] = None
    api_token: Optional[str] = None

    # Notifications (optional, with defaults)
    discord_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config: Configuration instance with values from environment.

        Raises:
            ValueError: If required environment variables are missing.
        """
        # Required variables
        required = {
            "AZURACAST_URL": os.getenv("AZURACAST_URL"),
            "AZURACAST_API_KEY": os.getenv("AZURACAST_API_KEY"),
            "AZURACAST_AUDIO_URL": os.getenv("AZURACAST_AUDIO_URL"),
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        }

        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Build RTMP endpoint
        rtmp_host = os.getenv("RTMP_HOST", "nginx-rtmp")
        rtmp_port = os.getenv("RTMP_PORT", "1935")
        rtmp_endpoint = f"rtmp://{rtmp_host}:{rtmp_port}/live/stream"

        # Build database host (internal Docker network name)
        postgres_host = os.getenv("POSTGRES_HOST", "postgres")

        return cls(
            # AzuraCast
            azuracast_url=required["AZURACAST_URL"],
            azuracast_api_key=required["AZURACAST_API_KEY"],
            azuracast_audio_url=required["AZURACAST_AUDIO_URL"],
            # RTMP
            rtmp_endpoint=rtmp_endpoint,
            # Database
            postgres_user=os.getenv("POSTGRES_USER", "radio"),
            postgres_password=required["POSTGRES_PASSWORD"],
            postgres_db=os.getenv("POSTGRES_DB", "radio_db"),
            postgres_host=postgres_host,
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            # FFmpeg
            video_resolution=os.getenv("VIDEO_RESOLUTION", "1280:720"),
            video_bitrate=os.getenv("VIDEO_BITRATE", "3000k"),
            audio_bitrate=os.getenv("AUDIO_BITRATE", "192k"),
            video_encoder=os.getenv("VIDEO_ENCODER", "libx264"),
            ffmpeg_preset=os.getenv("FFMPEG_PRESET", "veryfast"),
            fade_duration=float(os.getenv("FADE_DURATION", "1.0")),
            # Assets
            loops_path=Path(os.getenv("LOOPS_PATH", "/app/loops")),
            default_loop=Path(os.getenv("DEFAULT_LOOP", "/app/loops/default.mp4")),
            # Service
            watcher_port=int(os.getenv("WATCHER_PORT", "9000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_path=Path(os.getenv("LOG_PATH", "/var/log/radio")),
            environment=os.getenv("ENVIRONMENT", "production"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            ffmpeg_log_level=os.getenv("FFMPEG_LOG_LEVEL", "info"),
            # Process management
            track_overlap_duration=float(os.getenv("TRACK_OVERLAP_DURATION", "2.0")),
            max_restart_attempts=int(os.getenv("MAX_RESTART_ATTEMPTS", "3")),
            restart_cooldown_seconds=int(os.getenv("RESTART_COOLDOWN_SECONDS", "60")),
            # Security (optional)
            webhook_secret=os.getenv("WEBHOOK_SECRET"),
            api_token=os.getenv("API_TOKEN"),
            # Notifications (optional)
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
        )

    @property
    def database_url(self) -> str:
        """Get the PostgreSQL database URL.

        Returns:
            str: Database connection URL.
        """
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration values are invalid.
        """
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
                f"Invalid encoder '{self.video_encoder}'. "
                f"Must be one of: {', '.join(valid_encoders)}"
            )

        # Validate fade duration
        if self.fade_duration < 0 or self.fade_duration > 10:
            raise ValueError("Fade duration must be between 0 and 10 seconds")

        # Check default loop exists (if not in test mode)
        if self.environment != "testing" and not self.default_loop.exists():
            raise ValueError(f"Default loop file not found: {self.default_loop}")
