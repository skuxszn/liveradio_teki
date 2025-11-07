"""Tests for the main Notifier class."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notifier import Notifier
from notifier.config import NotificationConfig, NotificationType


class TestNotifier:
    """Test Notifier class."""

    @pytest.fixture
    def config(self):
        """Fixture to provide a test configuration."""
        config = MagicMock(spec=NotificationConfig)
        config.enabled = True
        config.async_send = False
        config.rate_limit_enabled = False
        config.discord_webhook_url = "https://discord.com/test"
        config.slack_webhook_url = None
        config.timeout_seconds = 5
        config.is_type_enabled.return_value = True
        config.has_webhook_configured.return_value = True
        config.is_quiet_hours.return_value = False
        config.get_color.return_value = 3066993
        config.get_rate_limit.return_value = MagicMock()
        return config

    @pytest.fixture
    def notifier(self, config):
        """Fixture to provide a notifier with test configuration."""
        return Notifier(config)

    def test_initialization(self, notifier, config):
        """Test notifier initialization."""
        assert notifier.config == config
        assert notifier.rate_limiter is not None
        assert notifier.discord_client is not None
        assert notifier.slack_client is not None
        assert notifier.stats["sent"] == 0
        assert notifier.stats["failed"] == 0

    def test_send_disabled(self, notifier, config):
        """Test that sending is blocked when notifications are disabled."""
        config.enabled = False

        result = notifier.send(NotificationType.INFO, "Test")

        assert result is False

    def test_send_type_disabled(self, notifier, config):
        """Test that sending is blocked for disabled notification types."""
        config.is_type_enabled.return_value = False

        result = notifier.send(NotificationType.INFO, "Test")

        assert result is False

    def test_send_no_webhooks(self, notifier, config):
        """Test that sending fails when no webhooks are configured."""
        config.has_webhook_configured.return_value = False

        result = notifier.send(NotificationType.INFO, "Test")

        assert result is False

    def test_send_quiet_hours(self, notifier, config):
        """Test that sending is blocked during quiet hours."""
        config.is_quiet_hours.return_value = True

        result = notifier.send(NotificationType.INFO, "Test")

        assert result is False
        assert notifier.stats["quiet_hours_blocked"] == 1

    def test_send_force_bypasses_checks(self, notifier, config):
        """Test that force=True bypasses all checks."""
        config.enabled = False
        config.is_quiet_hours.return_value = True

        with patch.object(notifier.discord_client, "send_sync", return_value=True):
            result = notifier.send(NotificationType.INFO, "Test", force=True)

            assert result is True

    def test_send_sync_success(self, notifier):
        """Test successful synchronous send."""
        with patch.object(notifier.discord_client, "send_sync", return_value=True):
            result = notifier.send(NotificationType.INFO, "Test")

            assert result is True
            assert notifier.stats["sent"] == 1

    def test_send_sync_failure(self, notifier):
        """Test failed synchronous send."""
        with patch.object(notifier.discord_client, "send_sync", return_value=False):
            result = notifier.send(NotificationType.INFO, "Test")

            assert result is False
            assert notifier.stats["failed"] == 1

    @pytest.mark.asyncio
    async def test_send_async_success(self, config):
        """Test successful asynchronous send."""
        notifier = Notifier(config)

        with patch.object(notifier.discord_client, "send_notification", new=AsyncMock(return_value=True)):
            result = await notifier.send_async(NotificationType.INFO, "Test")

            assert result is True
            assert notifier.stats["sent"] == 1

    def test_send_track_change(self, notifier):
        """Test convenience method for track change notifications."""
        with patch.object(notifier, "send", return_value=True) as mock_send:
            result = notifier.send_track_change(
                artist="Artist", title="Title", album="Album", loop_file="loop.mp4"
            )

            assert result is True
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert args[0][0] == NotificationType.TRACK_CHANGE
            assert "Artist - Title" in args[0][1]
            assert args[1]["fields"]["Album"] == "Album"
            assert args[1]["fields"]["Loop"] == "loop.mp4"

    def test_send_error(self, notifier):
        """Test convenience method for error notifications."""
        with patch.object(notifier, "send", return_value=True) as mock_send:
            result = notifier.send_error("Error message", context={"key": "value"})

            assert result is True
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert args[0][0] == NotificationType.ERROR
            assert "ERROR" in args[0][1]
            assert args[1]["force"] is True  # Errors bypass rate limiting

    def test_send_warning(self, notifier):
        """Test convenience method for warning notifications."""
        with patch.object(notifier, "send", return_value=True) as mock_send:
            result = notifier.send_warning("Warning message")

            assert result is True
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert args[0][0] == NotificationType.WARNING
            assert "WARNING" in args[0][1]

    def test_send_info(self, notifier):
        """Test convenience method for info notifications."""
        with patch.object(notifier, "send", return_value=True) as mock_send:
            result = notifier.send_info("Info message")

            assert result is True
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert args[0][0] == NotificationType.INFO

    def test_send_daily_summary(self, notifier):
        """Test convenience method for daily summary notifications."""
        with patch.object(notifier, "send", return_value=True) as mock_send:
            result = notifier.send_daily_summary(tracks_played=100, uptime_percent=99.5, errors=2)

            assert result is True
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert args[0][0] == NotificationType.DAILY_SUMMARY
            assert args[1]["fields"]["Tracks Played"] == "100"
            assert "99.5" in args[1]["fields"]["Uptime"]

    def test_get_stats(self, notifier):
        """Test getting notification statistics."""
        notifier.stats["sent"] = 10
        notifier.stats["failed"] = 2

        stats = notifier.get_stats()

        assert stats["sent"] == 10
        assert stats["failed"] == 2
        # Ensure it returns a copy
        stats["sent"] = 100
        assert notifier.stats["sent"] == 10

    def test_reset_stats(self, notifier):
        """Test resetting notification statistics."""
        notifier.stats["sent"] = 10
        notifier.stats["failed"] = 2

        notifier.reset_stats()

        assert notifier.stats["sent"] == 0
        assert notifier.stats["failed"] == 0

    def test_send_both_channels(self, config):
        """Test sending to both Discord and Slack."""
        config.discord_webhook_url = "https://discord.com/test"
        config.slack_webhook_url = "https://slack.com/test"
        notifier = Notifier(config)

        with patch.object(notifier.discord_client, "send_sync", return_value=True), patch.object(
            notifier.slack_client, "send_sync", return_value=True
        ):
            result = notifier.send(NotificationType.INFO, "Test")

            assert result is True

    def test_send_partial_success(self, config):
        """Test that partial success (one channel succeeds) is still success."""
        config.discord_webhook_url = "https://discord.com/test"
        config.slack_webhook_url = "https://slack.com/test"
        notifier = Notifier(config)

        with patch.object(notifier.discord_client, "send_sync", return_value=True), patch.object(
            notifier.slack_client, "send_sync", return_value=False
        ):
            result = notifier.send(NotificationType.INFO, "Test")

            assert result is True

    def test_send_with_fields(self, notifier):
        """Test sending with additional fields."""
        with patch.object(notifier.discord_client, "send_sync", return_value=True):
            result = notifier.send(
                NotificationType.INFO,
                "Test",
                description="Description",
                fields={"Field1": "Value1", "Field2": "Value2"},
            )

            assert result is True

    def test_send_with_thumbnail(self, notifier):
        """Test sending with thumbnail URL."""
        with patch.object(notifier.discord_client, "send_sync", return_value=True):
            result = notifier.send(
                NotificationType.INFO, "Test", thumbnail_url="https://example.com/thumb.png"
            )

            assert result is True

    def test_rate_limiting_integration(self, config):
        """Test rate limiting integration."""
        from notifier.config import RateLimitConfig
        
        config.rate_limit_enabled = True
        rate_config = RateLimitConfig(max_per_minute=2, max_per_hour=100)
        config.get_rate_limit.return_value = rate_config

        notifier = Notifier(config)

        with patch.object(notifier.discord_client, "send_sync", return_value=True):
            # First two should succeed
            assert notifier.send(NotificationType.INFO, "Test 1") is True
            assert notifier.send(NotificationType.INFO, "Test 2") is True

            # Third should be rate limited
            assert notifier.send(NotificationType.INFO, "Test 3") is False
            assert notifier.stats["rate_limited"] == 1

    def test_exception_handling(self, notifier):
        """Test that exceptions in clients don't crash the notifier."""
        with patch.object(notifier.discord_client, "send_sync", side_effect=Exception("Test error")):
            result = notifier.send(NotificationType.INFO, "Test")

            # Should return False but not raise exception
            assert result is False
            assert notifier.stats["failed"] == 1

    @pytest.mark.asyncio
    async def test_async_send_both_channels(self, config):
        """Test async sending to both channels."""
        config.discord_webhook_url = "https://discord.com/test"
        config.slack_webhook_url = "https://slack.com/test"
        notifier = Notifier(config)

        with patch.object(
            notifier.discord_client, "send_notification", new=AsyncMock(return_value=True)
        ), patch.object(notifier.slack_client, "send_notification", new=AsyncMock(return_value=True)):
            result = await notifier.send_async(NotificationType.INFO, "Test")

            assert result is True

    def test_default_config(self):
        """Test notifier with default configuration."""
        notifier = Notifier()

        assert notifier.config is not None
        assert isinstance(notifier.config, NotificationConfig)

