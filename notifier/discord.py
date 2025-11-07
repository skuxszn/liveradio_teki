"""
Discord webhook client with rich embed support.

Sends formatted notifications to Discord channels via webhooks with support for
embeds, fields, thumbnails, and custom formatting.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from notifier.config import NotificationConfig, NotificationType

logger = logging.getLogger(__name__)


class DiscordEmbed:
    """Builder for Discord embed objects."""

    def __init__(
        self,
        title: str,
        description: Optional[str] = None,
        color: int = 3066993,
        timestamp: Optional[datetime] = None,
    ):
        """
        Initialize a Discord embed.

        Args:
            title: Embed title
            description: Embed description
            color: Embed color (decimal)
            timestamp: Timestamp for the embed
        """
        self.data: Dict[str, Any] = {
            "title": title,
            "color": color,
        }

        if description:
            self.data["description"] = description

        if timestamp:
            self.data["timestamp"] = timestamp.isoformat()
        else:
            self.data["timestamp"] = datetime.utcnow().isoformat()

    def add_field(self, name: str, value: str, inline: bool = False) -> "DiscordEmbed":
        """
        Add a field to the embed.

        Args:
            name: Field name
            value: Field value
            inline: Whether to display inline

        Returns:
            Self for method chaining
        """
        if "fields" not in self.data:
            self.data["fields"] = []

        self.data["fields"].append({"name": name, "value": value, "inline": inline})
        return self

    def set_thumbnail(self, url: str) -> "DiscordEmbed":
        """
        Set embed thumbnail.

        Args:
            url: Image URL

        Returns:
            Self for method chaining
        """
        self.data["thumbnail"] = {"url": url}
        return self

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> "DiscordEmbed":
        """
        Set embed footer.

        Args:
            text: Footer text
            icon_url: Optional footer icon URL

        Returns:
            Self for method chaining
        """
        self.data["footer"] = {"text": text}
        if icon_url:
            self.data["footer"]["icon_url"] = icon_url
        return self

    def set_author(
        self, name: str, url: Optional[str] = None, icon_url: Optional[str] = None
    ) -> "DiscordEmbed":
        """
        Set embed author.

        Args:
            name: Author name
            url: Optional author URL
            icon_url: Optional author icon URL

        Returns:
            Self for method chaining
        """
        self.data["author"] = {"name": name}
        if url:
            self.data["author"]["url"] = url
        if icon_url:
            self.data["author"]["icon_url"] = icon_url
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert embed to dictionary for JSON serialization."""
        return self.data


class DiscordClient:
    """Discord webhook client."""

    def __init__(self, config: NotificationConfig):
        """
        Initialize Discord client.

        Args:
            config: Notification configuration
        """
        self.config = config
        self.webhook_url = config.discord_webhook_url

    async def send_message(
        self,
        content: Optional[str] = None,
        embeds: Optional[List[DiscordEmbed]] = None,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> bool:
        """
        Send a message to Discord.

        Args:
            content: Message content (text)
            embeds: List of Discord embeds
            username: Override bot username
            avatar_url: Override bot avatar

        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
            return False

        payload: Dict[str, Any] = {}

        if content:
            payload["content"] = content

        if embeds:
            payload["embeds"] = [embed.to_dict() for embed in embeds]

        if username or self.config.discord_username:
            payload["username"] = username or self.config.discord_username

        if avatar_url or self.config.discord_avatar_url:
            payload["avatar_url"] = avatar_url or self.config.discord_avatar_url

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                ) as response:
                    if response.status == 204:
                        logger.debug("Discord notification sent successfully")
                        return True
                    elif response.status == 429:
                        # Rate limited by Discord
                        retry_after = (await response.json()).get("retry_after", 1)
                        logger.warning(f"Discord rate limit hit, retry after {retry_after}s")
                        return False
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Discord notification failed: {response.status} - {error_text}"
                        )
                        return False

        except asyncio.TimeoutError:
            logger.error("Discord notification timed out")
            return False
        except aiohttp.ClientError as e:
            logger.error(f"Discord notification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord notification: {e}")
            return False

    async def send_notification(
        self,
        notification_type: NotificationType,
        title: str,
        description: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        thumbnail_url: Optional[str] = None,
    ) -> bool:
        """
        Send a formatted notification.

        Args:
            notification_type: Type of notification
            title: Notification title
            description: Optional description
            fields: Optional dictionary of field name->value
            thumbnail_url: Optional thumbnail image URL

        Returns:
            True if successful, False otherwise
        """
        color = self.config.get_color(notification_type)
        embed = DiscordEmbed(title=title, description=description, color=color)

        if fields:
            for name, value in fields.items():
                embed.add_field(name, str(value), inline=True)

        if thumbnail_url:
            embed.set_thumbnail(thumbnail_url)

        # Add footer with notification type
        embed.set_footer(f"Type: {notification_type.value}")

        return await self.send_message(embeds=[embed])

    def send_sync(
        self,
        notification_type: NotificationType,
        title: str,
        description: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        thumbnail_url: Optional[str] = None,
    ) -> bool:
        """
        Synchronous wrapper for send_notification.

        Args:
            notification_type: Type of notification
            title: Notification title
            description: Optional description
            fields: Optional dictionary of field name->value
            thumbnail_url: Optional thumbnail image URL

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is running, schedule the coroutine
                future = asyncio.ensure_future(
                    self.send_notification(
                        notification_type, title, description, fields, thumbnail_url
                    )
                )
                # Don't wait for it, fire and forget
                return True
            else:
                # If no event loop is running, run it synchronously
                return loop.run_until_complete(
                    self.send_notification(
                        notification_type, title, description, fields, thumbnail_url
                    )
                )
        except Exception as e:
            logger.error(f"Error in sync Discord send: {e}")
            return False
