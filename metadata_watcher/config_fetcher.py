"""Dynamic configuration fetcher from dashboard API.

Fetches configuration from the dashboard database via API instead of static .env files.
"""

import asyncio
import logging
from typing import Optional
from pathlib import Path

import httpx

from .config import Config

logger = logging.getLogger(__name__)


class ConfigFetcher:
    """Fetches and manages dynamic configuration from dashboard API."""

    def __init__(self, dashboard_url: str, api_token: str, refresh_interval: int = 60):
        """Initialize config fetcher.

        Args:
            dashboard_url: URL of dashboard API.
            api_token: API token for authentication.
            refresh_interval: How often to refresh config (seconds).
        """
        self.dashboard_url = dashboard_url.rstrip("/")
        self.api_token = api_token
        self.refresh_interval = refresh_interval
        self.current_config: Optional[Config] = None
        self._fetch_lock = asyncio.Lock()

    async def fetch_config(self) -> Optional[Config]:
        """Fetch configuration from dashboard API.

        Returns:
            Config: Configuration object or None if fetch failed.
        """
        async with self._fetch_lock:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Use internal service endpoint with API token auth
                    response = await client.get(
                        f"{self.dashboard_url}/api/v1/config/internal/export",
                        headers={"Authorization": f"Bearer {self.api_token}"},
                    )

                    if response.status_code != 200:
                        logger.error(f"Failed to fetch config: HTTP {response.status_code}")
                        return None

                    data = response.json()
                    settings = data.get("settings", {})

                    # Build Config from dashboard settings
                    config = self._build_config_from_settings(settings)

                    logger.info("Successfully fetched configuration from dashboard")
                    self.current_config = config
                    return config

            except httpx.RequestError as e:
                logger.error(f"Error fetching config from dashboard: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error fetching config: {e}", exc_info=True)
                return None

    def _build_config_from_settings(self, settings: dict) -> Config:
        """Build Config object from dashboard settings.

        Args:
            settings: Settings dictionary from dashboard.

        Returns:
            Config: Configuration object.
        """
        # Dashboard uses these category names
        stream = settings.get("stream", {})
        encoding = settings.get("encoding", {})  # NOT "ffmpeg"!
        paths = settings.get("paths", {})
        advanced = settings.get("advanced", {})
        security = settings.get("security", {})
        notifications = settings.get("notifications", {})

        # Required database settings (still from env for now)
        import os

        postgres_password = os.getenv("POSTGRES_PASSWORD", "")

        return Config(
            # AzuraCast (from dashboard)
            azuracast_url=stream.get("AZURACAST_URL", "http://localhost"),
            azuracast_api_key=stream.get("AZURACAST_API_KEY", ""),
            azuracast_audio_url=stream.get("AZURACAST_AUDIO_URL", ""),
            # RTMP (from dashboard)
            rtmp_endpoint=stream.get("RTMP_ENDPOINT", "rtmp://nginx-rtmp:1935/live/stream"),
            # Database (still from env)
            postgres_user=os.getenv("POSTGRES_USER", "radio"),
            postgres_password=postgres_password,
            postgres_db=os.getenv("POSTGRES_DB", "radio_db"),
            postgres_host=os.getenv("POSTGRES_HOST", "postgres"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            # FFmpeg (from dashboard "encoding" category)
            video_resolution=encoding.get("VIDEO_RESOLUTION", "1280:720"),
            video_bitrate=encoding.get("VIDEO_BITRATE", "3000k"),
            audio_bitrate=encoding.get("AUDIO_BITRATE", "128k"),
            video_encoder=encoding.get("VIDEO_ENCODER", "libx264"),
            ffmpeg_preset=encoding.get("FFMPEG_PRESET", "ultrafast"),
            fade_duration=float(encoding.get("FADE_DURATION", "0")),
            enable_text_overlay=encoding.get("ENABLE_TEXT_OVERLAY", "false").lower() == "true",
            enable_logo_watermark=encoding.get("ENABLE_LOGO_WATERMARK", "false").lower() == "true",
            logo_position=encoding.get("LOGO_POSITION", "top-right"),
            logo_opacity=float(encoding.get("LOGO_OPACITY", "0.8")),
            # Assets (from dashboard "paths" category)
            loops_path=Path(paths.get("LOOPS_PATH", "/app/loops")),
            default_loop=Path(paths.get("DEFAULT_LOOP", "/app/loops/default.mp4")),
            logo_path=paths.get("LOGO_PATH", "/app/logos/logo.png"),
            # Service (from dashboard "advanced" category)
            watcher_port=int(os.getenv("WATCHER_PORT", "9000")),  # Keep from env
            log_level=advanced.get("LOG_LEVEL", "INFO"),
            log_path=Path(paths.get("LOG_PATH", "/var/log/radio")),
            environment=advanced.get("ENVIRONMENT", "production"),
            debug=advanced.get("DEBUG", "false").lower() == "true",
            ffmpeg_log_level=encoding.get("FFMPEG_LOG_LEVEL", "info"),
            # Process management (from dashboard "encoding" category)
            track_overlap_duration=float(encoding.get("TRACK_OVERLAP_DURATION", "2.0")),
            max_restart_attempts=int(encoding.get("MAX_RESTART_ATTEMPTS", "3")),
            restart_cooldown_seconds=int(encoding.get("RESTART_COOLDOWN_SECONDS", "10")),
            # Security (from dashboard "security" category)
            webhook_secret=security.get("WEBHOOK_SECRET") or stream.get("WEBHOOK_SECRET"),
            api_token=os.getenv("API_TOKEN"),  # Keep from env
            # Notifications (from dashboard "notifications" category)
            discord_webhook_url=notifications.get("DISCORD_WEBHOOK_URL"),
            slack_webhook_url=notifications.get("SLACK_WEBHOOK_URL"),
        )

    async def start_auto_refresh(self, callback=None):
        """Start automatic configuration refresh loop.

        Args:
            callback: Optional callback function to call when config changes.
        """
        logger.info(f"Starting config auto-refresh (interval: {self.refresh_interval}s)")

        while True:
            try:
                old_config_dict = self.current_config.__dict__.copy() if self.current_config else {}
                new_config = await self.fetch_config()

                if new_config:
                    # Check if critical config changed
                    if self.current_config:
                        changed_keys = []
                        for key, value in new_config.__dict__.items():
                            if old_config_dict.get(key) != value:
                                changed_keys.append(key)

                        if changed_keys:
                            logger.info(f"Configuration changed: {', '.join(changed_keys)}")
                            if callback:
                                await callback(new_config, changed_keys)

                    self.current_config = new_config

                await asyncio.sleep(self.refresh_interval)

            except asyncio.CancelledError:
                logger.info("Config auto-refresh cancelled")
                break
            except Exception as e:
                logger.error(f"Error in config auto-refresh: {e}", exc_info=True)
                await asyncio.sleep(self.refresh_interval)

    def get_config(self) -> Optional[Config]:
        """Get current configuration.

        Returns:
            Config: Current configuration or None if not fetched yet.
        """
        return self.current_config
