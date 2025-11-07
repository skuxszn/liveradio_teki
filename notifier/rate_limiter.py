"""
Rate limiting logic for notifications with exponential backoff.

Prevents notification spam by enforcing per-minute and per-hour limits
with configurable exponential backoff for repeated notifications.
"""

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Deque, Dict, Optional

from notifier.config import NotificationType, RateLimitConfig


@dataclass
class NotificationRecord:
    """Record of a sent notification."""

    timestamp: datetime
    notification_type: NotificationType
    content_hash: Optional[int] = None


class RateLimiter:
    """Rate limiter with per-type limits and exponential backoff."""

    def __init__(self) -> None:
        """Initialize the rate limiter."""
        self._lock = Lock()
        self._minute_records: Dict[NotificationType, Deque[datetime]] = {}
        self._hour_records: Dict[NotificationType, Deque[datetime]] = {}
        self._last_notification: Dict[int, datetime] = {}  # content_hash -> timestamp
        self._backoff_delays: Dict[int, float] = {}  # content_hash -> delay in seconds

    def can_send(
        self,
        notification_type: NotificationType,
        config: RateLimitConfig,
        content: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a notification can be sent based on rate limits.

        Args:
            notification_type: Type of notification
            config: Rate limit configuration
            content: Optional content for deduplication

        Returns:
            Tuple of (can_send: bool, reason: Optional[str])
            If can_send is False, reason explains why.
        """
        with self._lock:
            now = datetime.now()

            # Initialize records for this type if needed
            if notification_type not in self._minute_records:
                self._minute_records[notification_type] = deque()
                self._hour_records[notification_type] = deque()

            # Clean old records
            self._clean_old_records(notification_type, now)

            # Check per-minute limit
            minute_count = len(self._minute_records[notification_type])
            if minute_count >= config.max_per_minute:
                return False, f"Rate limit: {minute_count}/{config.max_per_minute} per minute"

            # Check per-hour limit
            hour_count = len(self._hour_records[notification_type])
            if hour_count >= config.max_per_hour:
                return False, f"Rate limit: {hour_count}/{config.max_per_hour} per hour"

            # Check exponential backoff for duplicate content
            if content and config.exponential_backoff:
                content_hash = hash(content)
                if content_hash in self._last_notification:
                    last_time = self._last_notification[content_hash]
                    required_delay = self._backoff_delays.get(content_hash, 1.0)
                    time_since_last = (now - last_time).total_seconds()

                    if time_since_last < required_delay:
                        return (
                            False,
                            f"Backoff: {required_delay - time_since_last:.1f}s remaining",
                        )

            return True, None

    def record_sent(
        self,
        notification_type: NotificationType,
        config: RateLimitConfig,
        content: Optional[str] = None,
    ) -> None:
        """
        Record that a notification was sent.

        Args:
            notification_type: Type of notification
            config: Rate limit configuration
            content: Optional content for backoff tracking
        """
        with self._lock:
            now = datetime.now()

            # Initialize records for this type if needed
            if notification_type not in self._minute_records:
                self._minute_records[notification_type] = deque()
                self._hour_records[notification_type] = deque()

            # Record the notification
            self._minute_records[notification_type].append(now)
            self._hour_records[notification_type].append(now)

            # Update exponential backoff tracking
            if content and config.exponential_backoff:
                content_hash = hash(content)

                if content_hash in self._last_notification:
                    # Increase backoff delay
                    current_delay = self._backoff_delays.get(content_hash, 1.0)
                    self._backoff_delays[content_hash] = min(
                        current_delay * config.backoff_multiplier, 3600.0  # Max 1 hour
                    )
                else:
                    # First occurrence, start with base delay
                    self._backoff_delays[content_hash] = 1.0

                self._last_notification[content_hash] = now

    def _clean_old_records(self, notification_type: NotificationType, now: datetime) -> None:
        """Remove expired records."""
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)

        # Clean minute records
        minute_queue = self._minute_records[notification_type]
        while minute_queue and minute_queue[0] < one_minute_ago:
            minute_queue.popleft()

        # Clean hour records
        hour_queue = self._hour_records[notification_type]
        while hour_queue and hour_queue[0] < one_hour_ago:
            hour_queue.popleft()

        # Clean backoff tracking (remove entries older than 1 hour)
        expired_hashes = [
            h for h, t in self._last_notification.items() if (now - t).total_seconds() > 3600
        ]
        for h in expired_hashes:
            del self._last_notification[h]
            if h in self._backoff_delays:
                del self._backoff_delays[h]

    def get_stats(self, notification_type: NotificationType) -> Dict[str, int]:
        """
        Get current rate limit statistics.

        Args:
            notification_type: Type of notification

        Returns:
            Dictionary with 'minute_count' and 'hour_count'
        """
        with self._lock:
            now = datetime.now()
            if notification_type in self._minute_records:
                self._clean_old_records(notification_type, now)
                return {
                    "minute_count": len(self._minute_records[notification_type]),
                    "hour_count": len(self._hour_records[notification_type]),
                }
            return {"minute_count": 0, "hour_count": 0}

    def reset(self, notification_type: Optional[NotificationType] = None) -> None:
        """
        Reset rate limit records.

        Args:
            notification_type: If provided, reset only this type. Otherwise reset all.
        """
        with self._lock:
            if notification_type:
                if notification_type in self._minute_records:
                    self._minute_records[notification_type].clear()
                if notification_type in self._hour_records:
                    self._hour_records[notification_type].clear()
            else:
                self._minute_records.clear()
                self._hour_records.clear()
                self._last_notification.clear()
                self._backoff_delays.clear()
