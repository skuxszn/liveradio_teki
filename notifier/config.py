"""
Configuration management for the notification system.

Handles environment variables, notification types, rate limits, and quiet hours.
"""

import os
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, Optional


class NotificationType(Enum):
    """Types of notifications that can be sent."""

    TRACK_CHANGE = "track_change"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DAILY_SUMMARY = "daily_summary"


class NotificationColor(Enum):
    """Color codes for Discord embeds."""

    TRACK_CHANGE = 3066993  # Green
    ERROR = 15158332  # Red
    WARNING = 16776960  # Yellow
    INFO = 3447003  # Blue
    DAILY_SUMMARY = 10181046  # Purple


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for a specific notification type."""

    max_per_minute: int = 1
    max_per_hour: int = 60
    exponential_backoff: bool = True
    backoff_multiplier: float = 2.0


class NotificationConfig:
    """Configuration for the notification system."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        # Webhook URLs
        self.discord_webhook_url: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")
        self.slack_webhook_url: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")

        # General settings
        self.enabled: bool = self._get_bool_env("NOTIFICATION_ENABLED", True)
        self.async_send: bool = self._get_bool_env("NOTIFICATION_ASYNC", True)
        self.timeout_seconds: int = int(os.getenv("NOTIFICATION_TIMEOUT", "5"))

        # Rate limiting
        self.rate_limit_enabled: bool = self._get_bool_env("RATE_LIMIT_ENABLED", True)
        self._rate_limits = self._load_rate_limits()

        # Quiet hours
        self.quiet_hours_enabled: bool = self._get_bool_env("QUIET_HOURS_ENABLED", False)
        self.quiet_hours_start: time = self._parse_time(os.getenv("QUIET_HOURS_START", "23:00"))
        self.quiet_hours_end: time = self._parse_time(os.getenv("QUIET_HOURS_END", "07:00"))

        # Notification type filtering
        self.disabled_types: List[NotificationType] = self._parse_disabled_types()

        # Discord-specific settings
        self.discord_username: str = os.getenv("DISCORD_USERNAME", "Radio Stream Bot")
        self.discord_avatar_url: Optional[str] = os.getenv("DISCORD_AVATAR_URL")

        # Slack-specific settings
        self.slack_username: str = os.getenv("SLACK_USERNAME", "Radio Stream Bot")
        self.slack_icon_emoji: str = os.getenv("SLACK_ICON_EMOJI", ":radio:")

    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """Parse boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format."""
        try:
            hours, minutes = map(int, time_str.split(":"))
            return time(hours, minutes)
        except (ValueError, AttributeError):
            return time(0, 0)

    def _parse_disabled_types(self) -> List[NotificationType]:
        """Parse disabled notification types from environment."""
        disabled = os.getenv("NOTIFICATION_DISABLED_TYPES", "")
        if not disabled:
            return []

        types = []
        for type_name in disabled.split(","):
            type_name = type_name.strip().upper()
            try:
                types.append(NotificationType[type_name])
            except KeyError:
                pass
        return types

    def _load_rate_limits(self) -> Dict[NotificationType, RateLimitConfig]:
        """Load rate limit configurations for each notification type."""
        # Default rate limits per notification type
        defaults = {
            NotificationType.TRACK_CHANGE: RateLimitConfig(max_per_minute=1, max_per_hour=60),
            NotificationType.ERROR: RateLimitConfig(max_per_minute=5, max_per_hour=100),
            NotificationType.WARNING: RateLimitConfig(max_per_minute=10, max_per_hour=200),
            NotificationType.INFO: RateLimitConfig(max_per_minute=5, max_per_hour=100),
            NotificationType.DAILY_SUMMARY: RateLimitConfig(max_per_minute=1, max_per_hour=2),
        }

        # Allow environment overrides
        for notification_type in NotificationType:
            type_name = notification_type.name
            max_per_min = int(
                os.getenv(
                    f"RATE_LIMIT_{type_name}_PER_MINUTE",
                    str(defaults[notification_type].max_per_minute),
                )
            )
            max_per_hour = int(
                os.getenv(
                    f"RATE_LIMIT_{type_name}_PER_HOUR",
                    str(defaults[notification_type].max_per_hour),
                )
            )
            defaults[notification_type].max_per_minute = max_per_min
            defaults[notification_type].max_per_hour = max_per_hour

        return defaults

    def get_rate_limit(self, notification_type: NotificationType) -> RateLimitConfig:
        """Get rate limit configuration for a notification type."""
        return self._rate_limits.get(
            notification_type, RateLimitConfig(max_per_minute=10, max_per_hour=100)
        )

    def is_type_enabled(self, notification_type: NotificationType) -> bool:
        """Check if a notification type is enabled."""
        return notification_type not in self.disabled_types

    def get_color(self, notification_type: NotificationType) -> int:
        """Get Discord embed color for notification type."""
        color_mapping = {
            NotificationType.TRACK_CHANGE: NotificationColor.TRACK_CHANGE.value,
            NotificationType.ERROR: NotificationColor.ERROR.value,
            NotificationType.WARNING: NotificationColor.WARNING.value,
            NotificationType.INFO: NotificationColor.INFO.value,
            NotificationType.DAILY_SUMMARY: NotificationColor.DAILY_SUMMARY.value,
        }
        return color_mapping.get(notification_type, NotificationColor.INFO.value)

    def is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        if not self.quiet_hours_enabled:
            return False

        now = datetime.now().time()

        # Handle overnight quiet hours (e.g., 23:00 to 07:00)
        if self.quiet_hours_start > self.quiet_hours_end:
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
        else:
            return self.quiet_hours_start <= now <= self.quiet_hours_end

    def has_webhook_configured(self) -> bool:
        """Check if at least one webhook is configured."""
        return bool(self.discord_webhook_url or self.slack_webhook_url)
