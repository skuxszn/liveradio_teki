"""
Unified notification interface for the radio stream system.

This is the main entry point for sending notifications. It handles:
- Rate limiting
- Quiet hours
- Multi-channel delivery (Discord + Slack)
- Asynchronous and synchronous sending
- Error handling without blocking the main application
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from notifier.config import NotificationConfig, NotificationType
from notifier.discord import DiscordClient
from notifier.rate_limiter import RateLimiter
from notifier.slack import SlackClient

logger = logging.getLogger(__name__)


class Notifier:
    """Unified notification interface."""

    def __init__(self, config: Optional[NotificationConfig] = None):
        """
        Initialize the notifier.

        Args:
            config: Optional configuration. If not provided, uses default config.
        """
        self.config = config or NotificationConfig()
        self.rate_limiter = RateLimiter()
        self.discord_client = DiscordClient(self.config)
        self.slack_client = SlackClient(self.config)

        # Statistics
        self.stats = {
            "sent": 0,
            "failed": 0,
            "rate_limited": 0,
            "quiet_hours_blocked": 0,
        }

    def send(
        self,
        notification_type: NotificationType,
        title: str,
        description: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        thumbnail_url: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """
        Send a notification (synchronous).

        Args:
            notification_type: Type of notification
            title: Notification title
            description: Optional description text
            fields: Optional dictionary of field name->value pairs
            thumbnail_url: Optional thumbnail image URL
            force: If True, bypass rate limiting and quiet hours

        Returns:
            True if at least one notification was sent successfully
        """
        # Check if notifications are enabled
        if not self.config.enabled and not force:
            logger.debug("Notifications are disabled")
            return False

        # Check if this notification type is enabled
        if not self.config.is_type_enabled(notification_type) and not force:
            logger.debug(f"Notification type {notification_type.value} is disabled")
            return False

        # Check if we have any webhooks configured
        if not self.config.has_webhook_configured():
            logger.warning("No webhooks configured, cannot send notification")
            return False

        # Check quiet hours
        if self.config.is_quiet_hours() and not force:
            logger.debug(f"Quiet hours active, skipping notification: {notification_type.value}")
            self.stats["quiet_hours_blocked"] += 1
            return False

        # Check rate limiting
        if self.config.rate_limit_enabled and not force:
            rate_config = self.config.get_rate_limit(notification_type)
            can_send, reason = self.rate_limiter.can_send(
                notification_type, rate_config, content=title
            )

            if not can_send:
                logger.debug(f"Rate limit blocked notification: {reason}")
                self.stats["rate_limited"] += 1
                return False

        # Send to configured channels
        success = False

        if self.config.async_send:
            # Fire and forget - don't block
            asyncio.create_task(
                self._send_async(notification_type, title, description, fields, thumbnail_url)
            )
            success = True  # Assume success for async
        else:
            # Synchronous sending
            success = self._send_sync(notification_type, title, description, fields, thumbnail_url)

        # Record the send
        if success and self.config.rate_limit_enabled and not force:
            rate_config = self.config.get_rate_limit(notification_type)
            self.rate_limiter.record_sent(notification_type, rate_config, content=title)

        return success

    async def send_async(
        self,
        notification_type: NotificationType,
        title: str,
        description: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        thumbnail_url: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """
        Send a notification (asynchronous).

        Args:
            notification_type: Type of notification
            title: Notification title
            description: Optional description text
            fields: Optional dictionary of field name->value pairs
            thumbnail_url: Optional thumbnail image URL
            force: If True, bypass rate limiting and quiet hours

        Returns:
            True if at least one notification was sent successfully
        """
        # Check if notifications are enabled
        if not self.config.enabled and not force:
            logger.debug("Notifications are disabled")
            return False

        # Check if this notification type is enabled
        if not self.config.is_type_enabled(notification_type) and not force:
            logger.debug(f"Notification type {notification_type.value} is disabled")
            return False

        # Check if we have any webhooks configured
        if not self.config.has_webhook_configured():
            logger.warning("No webhooks configured, cannot send notification")
            return False

        # Check quiet hours
        if self.config.is_quiet_hours() and not force:
            logger.debug(f"Quiet hours active, skipping notification: {notification_type.value}")
            self.stats["quiet_hours_blocked"] += 1
            return False

        # Check rate limiting
        if self.config.rate_limit_enabled and not force:
            rate_config = self.config.get_rate_limit(notification_type)
            can_send, reason = self.rate_limiter.can_send(
                notification_type, rate_config, content=title
            )

            if not can_send:
                logger.debug(f"Rate limit blocked notification: {reason}")
                self.stats["rate_limited"] += 1
                return False

        # Send to configured channels
        success = await self._send_async(
            notification_type, title, description, fields, thumbnail_url
        )

        # Record the send
        if success and self.config.rate_limit_enabled and not force:
            rate_config = self.config.get_rate_limit(notification_type)
            self.rate_limiter.record_sent(notification_type, rate_config, content=title)

        return success

    async def _send_async(
        self,
        notification_type: NotificationType,
        title: str,
        description: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        thumbnail_url: Optional[str] = None,
    ) -> bool:
        """Internal async send implementation."""
        results = []

        # Send to Discord
        if self.config.discord_webhook_url:
            try:
                result = await self.discord_client.send_notification(
                    notification_type, title, description, fields, thumbnail_url
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error sending Discord notification: {e}")
                results.append(False)

        # Send to Slack
        if self.config.slack_webhook_url:
            try:
                result = await self.slack_client.send_notification(
                    notification_type, title, description, fields, thumbnail_url
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error sending Slack notification: {e}")
                results.append(False)

        # Update statistics
        if any(results):
            self.stats["sent"] += 1
            return True
        else:
            self.stats["failed"] += 1
            return False

    def _send_sync(
        self,
        notification_type: NotificationType,
        title: str,
        description: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        thumbnail_url: Optional[str] = None,
    ) -> bool:
        """Internal sync send implementation."""
        results = []

        # Send to Discord
        if self.config.discord_webhook_url:
            try:
                result = self.discord_client.send_sync(
                    notification_type, title, description, fields, thumbnail_url
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error sending Discord notification: {e}")
                results.append(False)

        # Send to Slack
        if self.config.slack_webhook_url:
            try:
                result = self.slack_client.send_sync(
                    notification_type, title, description, fields, thumbnail_url
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error sending Slack notification: {e}")
                results.append(False)

        # Update statistics
        if any(results):
            self.stats["sent"] += 1
            return True
        else:
            self.stats["failed"] += 1
            return False

    def send_track_change(
        self, artist: str, title: str, album: Optional[str] = None, loop_file: Optional[str] = None
    ) -> bool:
        """
        Convenience method for track change notifications.

        Args:
            artist: Track artist
            title: Track title
            album: Optional album name
            loop_file: Optional loop file name

        Returns:
            True if sent successfully
        """
        fields = {}
        if album:
            fields["Album"] = album
        if loop_file:
            fields["Loop"] = loop_file

        return self.send(
            NotificationType.TRACK_CHANGE,
            f"🎵 Now Playing: {artist} - {title}",
            fields=fields if fields else None,
        )

    def send_error(self, message: str, context: Optional[Dict[str, str]] = None) -> bool:
        """
        Convenience method for error notifications.

        Args:
            message: Error message
            context: Optional context information

        Returns:
            True if sent successfully
        """
        return self.send(NotificationType.ERROR, f"🚨 ERROR: {message}", fields=context, force=True)

    def send_warning(self, message: str, context: Optional[Dict[str, str]] = None) -> bool:
        """
        Convenience method for warning notifications.

        Args:
            message: Warning message
            context: Optional context information

        Returns:
            True if sent successfully
        """
        return self.send(NotificationType.WARNING, f"⚠️ WARNING: {message}", fields=context)

    def send_info(self, message: str, context: Optional[Dict[str, str]] = None) -> bool:
        """
        Convenience method for info notifications.

        Args:
            message: Info message
            context: Optional context information

        Returns:
            True if sent successfully
        """
        return self.send(NotificationType.INFO, f"✅ {message}", fields=context)

    def send_daily_summary(
        self, tracks_played: int, uptime_percent: float, errors: int = 0
    ) -> bool:
        """
        Convenience method for daily summary notifications.

        Args:
            tracks_played: Number of tracks played
            uptime_percent: Uptime percentage
            errors: Number of errors

        Returns:
            True if sent successfully
        """
        fields = {
            "Tracks Played": str(tracks_played),
            "Uptime": f"{uptime_percent:.1f}%",
            "Errors": str(errors),
        }

        return self.send(NotificationType.DAILY_SUMMARY, "📊 Daily Report", fields=fields)

    def get_stats(self) -> Dict[str, int]:
        """
        Get notification statistics.

        Returns:
            Dictionary with statistics
        """
        return self.stats.copy()

    def reset_stats(self) -> None:
        """Reset notification statistics."""
        self.stats = {
            "sent": 0,
            "failed": 0,
            "rate_limited": 0,
            "quiet_hours_blocked": 0,
        }
