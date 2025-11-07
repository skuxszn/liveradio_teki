"""Tests for the rate limiter module."""

import time
from datetime import datetime, timedelta

import pytest

from notifier.config import NotificationType, RateLimitConfig
from notifier.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.fixture
    def limiter(self):
        """Fixture to provide a fresh rate limiter."""
        return RateLimiter()

    @pytest.fixture
    def config(self):
        """Fixture to provide a rate limit configuration."""
        return RateLimitConfig(max_per_minute=5, max_per_hour=100)

    def test_can_send_initially(self, limiter, config):
        """Test that first notification can be sent."""
        can_send, reason = limiter.can_send(NotificationType.INFO, config)
        assert can_send is True
        assert reason is None

    def test_record_sent(self, limiter, config):
        """Test recording sent notifications."""
        limiter.record_sent(NotificationType.INFO, config)
        stats = limiter.get_stats(NotificationType.INFO)
        assert stats["minute_count"] == 1
        assert stats["hour_count"] == 1

    def test_per_minute_limit(self, limiter, config):
        """Test per-minute rate limiting."""
        notification_type = NotificationType.INFO

        # Send up to the limit
        for i in range(config.max_per_minute):
            can_send, _ = limiter.can_send(notification_type, config)
            assert can_send is True
            limiter.record_sent(notification_type, config)

        # Next one should be blocked
        can_send, reason = limiter.can_send(notification_type, config)
        assert can_send is False
        assert "per minute" in reason

    def test_per_hour_limit(self, limiter):
        """Test per-hour rate limiting."""
        notification_type = NotificationType.INFO
        config = RateLimitConfig(max_per_minute=100, max_per_hour=5)

        # Send up to the hour limit
        for i in range(config.max_per_hour):
            can_send, _ = limiter.can_send(notification_type, config)
            assert can_send is True
            limiter.record_sent(notification_type, config)

        # Next one should be blocked by hour limit
        can_send, reason = limiter.can_send(notification_type, config)
        assert can_send is False
        assert "per hour" in reason

    def test_exponential_backoff(self, limiter):
        """Test exponential backoff for duplicate content."""
        notification_type = NotificationType.ERROR
        config = RateLimitConfig(max_per_minute=100, max_per_hour=1000, exponential_backoff=True)
        content = "Test error message"

        # First send should work
        can_send, _ = limiter.can_send(notification_type, config, content)
        assert can_send is True
        limiter.record_sent(notification_type, config, content)

        # Immediate resend should be blocked by backoff
        can_send, reason = limiter.can_send(notification_type, config, content)
        assert can_send is False
        assert "Backoff" in reason

    def test_exponential_backoff_increases(self, limiter):
        """Test that backoff delay increases exponentially."""
        notification_type = NotificationType.ERROR
        config = RateLimitConfig(
            max_per_minute=100,
            max_per_hour=1000,
            exponential_backoff=True,
            backoff_multiplier=2.0,
        )
        content = "Test error message"

        # First send
        limiter.record_sent(notification_type, config, content)
        assert limiter._backoff_delays[hash(content)] == 1.0

        # Wait for backoff to expire
        time.sleep(1.1)

        # Second send - backoff should double
        limiter.record_sent(notification_type, config, content)
        assert limiter._backoff_delays[hash(content)] == 2.0

        # Wait for backoff to expire
        time.sleep(2.1)

        # Third send - backoff should double again
        limiter.record_sent(notification_type, config, content)
        assert limiter._backoff_delays[hash(content)] == 4.0

    def test_different_types_independent(self, limiter, config):
        """Test that different notification types have independent limits."""
        # Fill up INFO notifications
        for i in range(config.max_per_minute):
            limiter.record_sent(NotificationType.INFO, config)

        # INFO should be blocked
        can_send, _ = limiter.can_send(NotificationType.INFO, config)
        assert can_send is False

        # But ERROR should still work
        can_send, _ = limiter.can_send(NotificationType.ERROR, config)
        assert can_send is True

    def test_old_records_cleaned(self, limiter, config):
        """Test that old records are cleaned up."""
        notification_type = NotificationType.INFO

        # Send a notification
        limiter.record_sent(notification_type, config)
        stats = limiter.get_stats(notification_type)
        assert stats["minute_count"] == 1

        # Manually age the record
        old_time = datetime.now() - timedelta(minutes=2)
        limiter._minute_records[notification_type][0] = old_time

        # Getting stats should clean it
        stats = limiter.get_stats(notification_type)
        assert stats["minute_count"] == 0

    def test_reset_specific_type(self, limiter, config):
        """Test resetting a specific notification type."""
        limiter.record_sent(NotificationType.INFO, config)
        limiter.record_sent(NotificationType.ERROR, config)

        # Reset INFO only
        limiter.reset(NotificationType.INFO)

        stats_info = limiter.get_stats(NotificationType.INFO)
        stats_error = limiter.get_stats(NotificationType.ERROR)

        assert stats_info["minute_count"] == 0
        assert stats_error["minute_count"] == 1

    def test_reset_all(self, limiter, config):
        """Test resetting all notification types."""
        limiter.record_sent(NotificationType.INFO, config)
        limiter.record_sent(NotificationType.ERROR, config)

        # Reset all
        limiter.reset()

        stats_info = limiter.get_stats(NotificationType.INFO)
        stats_error = limiter.get_stats(NotificationType.ERROR)

        assert stats_info["minute_count"] == 0
        assert stats_error["minute_count"] == 0

    def test_get_stats_empty(self, limiter):
        """Test getting stats for notification type with no records."""
        stats = limiter.get_stats(NotificationType.INFO)
        assert stats["minute_count"] == 0
        assert stats["hour_count"] == 0

    def test_thread_safety(self, limiter, config):
        """Test that rate limiter is thread-safe."""
        import threading

        notification_type = NotificationType.INFO
        results = []

        def send_notification():
            can_send, _ = limiter.can_send(notification_type, config)
            if can_send:
                limiter.record_sent(notification_type, config)
            results.append(can_send)

        # Create multiple threads
        threads = [threading.Thread(target=send_notification) for _ in range(20)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # Should respect the limit despite concurrent access
        stats = limiter.get_stats(notification_type)
        assert stats["minute_count"] <= config.max_per_minute

    def test_backoff_cleanup(self, limiter):
        """Test that old backoff records are cleaned up."""
        notification_type = NotificationType.ERROR
        config = RateLimitConfig(exponential_backoff=True)
        content = "Test message"

        # Record a notification
        limiter.record_sent(notification_type, config, content)

        content_hash = hash(content)
        assert content_hash in limiter._last_notification
        assert content_hash in limiter._backoff_delays

        # Manually age the record
        old_time = datetime.now() - timedelta(hours=2)
        limiter._last_notification[content_hash] = old_time

        # Clean records should remove it
        limiter._clean_old_records(notification_type, datetime.now())

        assert content_hash not in limiter._last_notification
        assert content_hash not in limiter._backoff_delays

    def test_no_backoff_when_disabled(self, limiter):
        """Test that backoff doesn't apply when disabled."""
        notification_type = NotificationType.ERROR
        config = RateLimitConfig(
            max_per_minute=100, max_per_hour=1000, exponential_backoff=False
        )
        content = "Test error message"

        # Send same content twice immediately
        can_send, _ = limiter.can_send(notification_type, config, content)
        assert can_send is True
        limiter.record_sent(notification_type, config, content)

        can_send, _ = limiter.can_send(notification_type, config, content)
        assert can_send is True  # Should not be blocked by backoff

    def test_backoff_max_delay(self, limiter):
        """Test that backoff delay is capped at maximum."""
        notification_type = NotificationType.ERROR
        config = RateLimitConfig(
            max_per_minute=1000,
            max_per_hour=10000,
            exponential_backoff=True,
            backoff_multiplier=2.0,
        )
        content = "Test message"

        # Simulate many repeated sends to reach max delay
        for _ in range(20):
            limiter.record_sent(notification_type, config, content)

        # Backoff should be capped at 1 hour (3600 seconds)
        content_hash = hash(content)
        assert limiter._backoff_delays[content_hash] <= 3600.0



