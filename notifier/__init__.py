"""
Notification System for 24/7 FFmpeg YouTube Radio Stream.

This module provides Discord and Slack webhook integration for real-time alerts
and status updates with rate limiting and rich embed formatting.

Main components:
- Notifier: Unified notification interface
- DiscordClient: Discord webhook client with embed support
- SlackClient: Slack webhook client
- RateLimiter: Rate limiting with exponential backoff
- NotificationConfig: Configuration management

Example:
    from notifier import Notifier, NotificationType

    notifier = Notifier()
    notifier.send(
        NotificationType.TRACK_CHANGE,
        "🎵 Now Playing: Artist - Title",
        {"album": "Album Name", "loop": "track123.mp4"}
    )
"""

from .config import NotificationConfig, NotificationType
from .notifier import Notifier

__version__ = "1.0.0"
__all__ = ["Notifier", "NotificationConfig", "NotificationType"]
