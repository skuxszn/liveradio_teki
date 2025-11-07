"""
Slack webhook client for sending notifications.

Sends formatted notifications to Slack channels via webhooks with support for
attachments, fields, and custom formatting.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from notifier.config import NotificationConfig, NotificationType

logger = logging.getLogger(__name__)


class SlackAttachment:
    """Builder for Slack attachment objects."""

    def __init__(
        self,
        title: str,
        text: Optional[str] = None,
        color: str = "good",
        fallback: Optional[str] = None,
    ):
        """
        Initialize a Slack attachment.

        Args:
            title: Attachment title
            text: Attachment text
            color: Color (good, warning, danger, or hex code)
            fallback: Fallback text for notifications
        """
        self.data: Dict[str, Any] = {
            "title": title,
            "color": color,
            "fallback": fallback or title,
        }

        if text:
            self.data["text"] = text

    def add_field(self, title: str, value: str, short: bool = True) -> "SlackAttachment":
        """
        Add a field to the attachment.

        Args:
            title: Field title
            value: Field value
            short: Whether to display as short field

        Returns:
            Self for method chaining
        """
        if "fields" not in self.data:
            self.data["fields"] = []

        self.data["fields"].append({"title": title, "value": value, "short": short})
        return self

    def set_footer(self, text: str, icon: Optional[str] = None) -> "SlackAttachment":
        """
        Set attachment footer.

        Args:
            text: Footer text
            icon: Optional footer icon URL

        Returns:
            Self for method chaining
        """
        self.data["footer"] = text
        if icon:
            self.data["footer_icon"] = icon
        return self

    def set_timestamp(self, timestamp: int) -> "SlackAttachment":
        """
        Set attachment timestamp.

        Args:
            timestamp: Unix timestamp

        Returns:
            Self for method chaining
        """
        self.data["ts"] = timestamp
        return self

    def set_thumbnail(self, url: str) -> "SlackAttachment":
        """
        Set attachment thumbnail.

        Args:
            url: Image URL

        Returns:
            Self for method chaining
        """
        self.data["thumb_url"] = url
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert attachment to dictionary for JSON serialization."""
        return self.data


class SlackClient:
    """Slack webhook client."""

    # Color mappings for notification types
    COLOR_MAP = {
        NotificationType.TRACK_CHANGE: "good",  # Green
        NotificationType.ERROR: "danger",  # Red
        NotificationType.WARNING: "warning",  # Yellow
        NotificationType.INFO: "#36a64f",  # Blue
        NotificationType.DAILY_SUMMARY: "#9c27b0",  # Purple
    }

    def __init__(self, config: NotificationConfig):
        """
        Initialize Slack client.

        Args:
            config: Notification configuration
        """
        self.config = config
        self.webhook_url = config.slack_webhook_url

    async def send_message(
        self,
        text: Optional[str] = None,
        attachments: Optional[List[SlackAttachment]] = None,
        username: Optional[str] = None,
        icon_emoji: Optional[str] = None,
    ) -> bool:
        """
        Send a message to Slack.

        Args:
            text: Message text
            attachments: List of Slack attachments
            username: Override bot username
            icon_emoji: Override bot icon emoji

        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        payload: Dict[str, Any] = {}

        if text:
            payload["text"] = text

        if attachments:
            payload["attachments"] = [att.to_dict() for att in attachments]

        if username or self.config.slack_username:
            payload["username"] = username or self.config.slack_username

        if icon_emoji or self.config.slack_icon_emoji:
            payload["icon_emoji"] = icon_emoji or self.config.slack_icon_emoji

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                ) as response:
                    response_text = await response.text()

                    if response.status == 200 and response_text == "ok":
                        logger.debug("Slack notification sent successfully")
                        return True
                    else:
                        logger.error(
                            f"Slack notification failed: {response.status} - {response_text}"
                        )
                        return False

        except asyncio.TimeoutError:
            logger.error("Slack notification timed out")
            return False
        except aiohttp.ClientError as e:
            logger.error(f"Slack notification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack notification: {e}")
            return False

    async def send_notification(
        self,
        notification_type: NotificationType,
        title: str,
        text: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        thumbnail_url: Optional[str] = None,
    ) -> bool:
        """
        Send a formatted notification.

        Args:
            notification_type: Type of notification
            title: Notification title
            text: Optional text content
            fields: Optional dictionary of field title->value
            thumbnail_url: Optional thumbnail image URL

        Returns:
            True if successful, False otherwise
        """
        color = self.COLOR_MAP.get(notification_type, "good")
        attachment = SlackAttachment(
            title=title, text=text, color=color, fallback=f"{title}: {text or ''}"
        )

        if fields:
            for field_title, field_value in fields.items():
                attachment.add_field(field_title, str(field_value), short=True)

        if thumbnail_url:
            attachment.set_thumbnail(thumbnail_url)

        # Add footer with notification type
        attachment.set_footer(f"Type: {notification_type.value}")

        # Add timestamp
        from time import time

        attachment.set_timestamp(int(time()))

        return await self.send_message(attachments=[attachment])

    def send_sync(
        self,
        notification_type: NotificationType,
        title: str,
        text: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        thumbnail_url: Optional[str] = None,
    ) -> bool:
        """
        Synchronous wrapper for send_notification.

        Args:
            notification_type: Type of notification
            title: Notification title
            text: Optional text content
            fields: Optional dictionary of field title->value
            thumbnail_url: Optional thumbnail image URL

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is running, schedule the coroutine
                future = asyncio.ensure_future(
                    self.send_notification(notification_type, title, text, fields, thumbnail_url)
                )
                # Don't wait for it, fire and forget
                return True
            else:
                # If no event loop is running, run it synchronously
                return loop.run_until_complete(
                    self.send_notification(notification_type, title, text, fields, thumbnail_url)
                )
        except Exception as e:
            logger.error(f"Error in sync Slack send: {e}")
            return False
