"""Tests for the notification configuration module."""

import os
from datetime import time
from unittest.mock import patch

import pytest

from notifier.config import (
    NotificationColor,
    NotificationConfig,
    NotificationType,
    RateLimitConfig,
)


class TestNotificationType:
    """Test NotificationType enum."""

    def test_notification_types_exist(self):
        """Test that all expected notification types exist."""
        assert NotificationType.TRACK_CHANGE
        assert NotificationType.ERROR
        assert NotificationType.WARNING
        assert NotificationType.INFO
        assert NotificationType.DAILY_SUMMARY

    def test_notification_type_values(self):
        """Test notification type values."""
        assert NotificationType.TRACK_CHANGE.value == "track_change"
        assert NotificationType.ERROR.value == "error"
        assert NotificationType.WARNING.value == "warning"
        assert NotificationType.INFO.value == "info"
        assert NotificationType.DAILY_SUMMARY.value == "daily_summary"


class TestNotificationColor:
    """Test NotificationColor enum."""

    def test_color_values_are_integers(self):
        """Test that color values are valid integers."""
        for color in NotificationColor:
            assert isinstance(color.value, int)
            assert 0 <= color.value <= 16777215  # Valid RGB range


class TestRateLimitConfig:
    """Test RateLimitConfig dataclass."""

    def test_default_values(self):
        """Test default rate limit configuration values."""
        config = RateLimitConfig()
        assert config.max_per_minute == 1
        assert config.max_per_hour == 60
        assert config.exponential_backoff is True
        assert config.backoff_multiplier == 2.0

    def test_custom_values(self):
        """Test custom rate limit configuration."""
        config = RateLimitConfig(
            max_per_minute=5, max_per_hour=100, exponential_backoff=False, backoff_multiplier=1.5
        )
        assert config.max_per_minute == 5
        assert config.max_per_hour == 100
        assert config.exponential_backoff is False
        assert config.backoff_multiplier == 1.5


class TestNotificationConfig:
    """Test NotificationConfig class."""

    @pytest.fixture
    def clean_env(self):
        """Fixture to provide clean environment."""
        # Store original env vars
        original_env = os.environ.copy()

        # Clear notification-related vars
        keys_to_clear = [k for k in os.environ.keys() if k.startswith(("DISCORD_", "SLACK_", "NOTIFICATION_", "QUIET_", "RATE_LIMIT_"))]
        for key in keys_to_clear:
            os.environ.pop(key, None)

        yield

        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

    def test_default_configuration(self, clean_env):
        """Test default configuration values."""
        config = NotificationConfig()

        assert config.discord_webhook_url is None
        assert config.slack_webhook_url is None
        assert config.enabled is True
        assert config.async_send is True
        assert config.timeout_seconds == 5
        assert config.rate_limit_enabled is True

    def test_webhook_urls_from_env(self, clean_env):
        """Test webhook URLs are loaded from environment."""
        os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.com/webhook/test"
        os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/test"

        config = NotificationConfig()

        assert config.discord_webhook_url == "https://discord.com/webhook/test"
        assert config.slack_webhook_url == "https://hooks.slack.com/test"

    def test_boolean_env_parsing(self, clean_env):
        """Test boolean environment variable parsing."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ]

        for value, expected in test_cases:
            os.environ["NOTIFICATION_ENABLED"] = value
            config = NotificationConfig()
            assert config.enabled == expected, f"Failed for value: {value}"

    def test_quiet_hours_parsing(self, clean_env):
        """Test quiet hours time parsing."""
        os.environ["QUIET_HOURS_ENABLED"] = "true"
        os.environ["QUIET_HOURS_START"] = "23:30"
        os.environ["QUIET_HOURS_END"] = "07:15"

        config = NotificationConfig()

        assert config.quiet_hours_enabled is True
        assert config.quiet_hours_start == time(23, 30)
        assert config.quiet_hours_end == time(7, 15)

    def test_disabled_types_parsing(self, clean_env):
        """Test parsing of disabled notification types."""
        os.environ["NOTIFICATION_DISABLED_TYPES"] = "TRACK_CHANGE,INFO"

        config = NotificationConfig()

        assert NotificationType.TRACK_CHANGE in config.disabled_types
        assert NotificationType.INFO in config.disabled_types
        assert NotificationType.ERROR not in config.disabled_types

    def test_is_type_enabled(self, clean_env):
        """Test is_type_enabled method."""
        os.environ["NOTIFICATION_DISABLED_TYPES"] = "ERROR"

        config = NotificationConfig()

        assert config.is_type_enabled(NotificationType.TRACK_CHANGE) is True
        assert config.is_type_enabled(NotificationType.ERROR) is False

    def test_get_color(self, clean_env):
        """Test get_color method."""
        config = NotificationConfig()

        assert config.get_color(NotificationType.TRACK_CHANGE) == NotificationColor.TRACK_CHANGE.value
        assert config.get_color(NotificationType.ERROR) == NotificationColor.ERROR.value
        assert config.get_color(NotificationType.WARNING) == NotificationColor.WARNING.value

    def test_has_webhook_configured(self, clean_env):
        """Test has_webhook_configured method."""
        config = NotificationConfig()
        assert config.has_webhook_configured() is False

        os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.com/test"
        config = NotificationConfig()
        assert config.has_webhook_configured() is True

        os.environ.pop("DISCORD_WEBHOOK_URL")
        os.environ["SLACK_WEBHOOK_URL"] = "https://slack.com/test"
        config = NotificationConfig()
        assert config.has_webhook_configured() is True

    def test_is_quiet_hours_daytime(self, clean_env):
        """Test quiet hours check during daytime hours."""
        os.environ["QUIET_HOURS_ENABLED"] = "true"
        os.environ["QUIET_HOURS_START"] = "23:00"
        os.environ["QUIET_HOURS_END"] = "07:00"

        config = NotificationConfig()

        # Mock current time to 10:00 (not quiet hours)
        with patch("notifier.config.datetime") as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(10, 0)
            assert config.is_quiet_hours() is False

    def test_is_quiet_hours_nighttime(self, clean_env):
        """Test quiet hours check during nighttime hours."""
        os.environ["QUIET_HOURS_ENABLED"] = "true"
        os.environ["QUIET_HOURS_START"] = "23:00"
        os.environ["QUIET_HOURS_END"] = "07:00"

        config = NotificationConfig()

        # Mock current time to 01:00 (quiet hours)
        with patch("notifier.config.datetime") as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(1, 0)
            assert config.is_quiet_hours() is True

    def test_is_quiet_hours_disabled(self, clean_env):
        """Test quiet hours when disabled."""
        os.environ["QUIET_HOURS_ENABLED"] = "false"

        config = NotificationConfig()

        # Should always return False when disabled
        with patch("notifier.config.datetime") as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(1, 0)
            assert config.is_quiet_hours() is False

    def test_get_rate_limit(self, clean_env):
        """Test get_rate_limit method."""
        config = NotificationConfig()

        rate_limit = config.get_rate_limit(NotificationType.TRACK_CHANGE)
        assert isinstance(rate_limit, RateLimitConfig)
        assert rate_limit.max_per_minute == 1
        assert rate_limit.max_per_hour == 60

    def test_rate_limit_env_override(self, clean_env):
        """Test rate limit configuration from environment."""
        os.environ["RATE_LIMIT_ERROR_PER_MINUTE"] = "10"
        os.environ["RATE_LIMIT_ERROR_PER_HOUR"] = "200"

        config = NotificationConfig()
        rate_limit = config.get_rate_limit(NotificationType.ERROR)

        assert rate_limit.max_per_minute == 10
        assert rate_limit.max_per_hour == 200



