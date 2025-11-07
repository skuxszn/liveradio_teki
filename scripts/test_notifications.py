#!/usr/bin/env python3
"""
Manual test script for the notification system.

This script sends test notifications to Discord and/or Slack to verify
the notification system is working correctly.

Usage:
    python scripts/test_notifications.py
    python scripts/test_notifications.py --type track_change
    python scripts/test_notifications.py --all
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from notifier import Notifier, NotificationConfig, NotificationType

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_track_change(notifier: Notifier) -> None:
    """Test track change notification."""
    logger.info("Testing track change notification...")
    success = notifier.send_track_change(
        artist="The Beatles",
        title="Here Comes The Sun",
        album="Abbey Road",
        loop_file="beatles_abbey_road.mp4",
    )
    logger.info(f"Track change notification: {'✅ SUCCESS' if success else '❌ FAILED'}")


def test_error(notifier: Notifier) -> None:
    """Test error notification."""
    logger.info("Testing error notification...")
    success = notifier.send_error(
        "FFmpeg process crashed",
        context={"pid": "12345", "exit_code": "1", "retries": "3/3"},
    )
    logger.info(f"Error notification: {'✅ SUCCESS' if success else '❌ FAILED'}")


def test_warning(notifier: Notifier) -> None:
    """Test warning notification."""
    logger.info("Testing warning notification...")
    success = notifier.send_warning(
        "Audio stream temporarily unavailable, retrying...",
        context={"url": "http://azuracast:8000/radio", "retry": "2/10"},
    )
    logger.info(f"Warning notification: {'✅ SUCCESS' if success else '❌ FAILED'}")


def test_info(notifier: Notifier) -> None:
    """Test info notification."""
    logger.info("Testing info notification...")
    success = notifier.send_info(
        "Stream started successfully", context={"resolution": "1280x720", "bitrate": "3000k"}
    )
    logger.info(f"Info notification: {'✅ SUCCESS' if success else '❌ FAILED'}")


def test_daily_summary(notifier: Notifier) -> None:
    """Test daily summary notification."""
    logger.info("Testing daily summary notification...")
    success = notifier.send_daily_summary(tracks_played=142, uptime_percent=99.8, errors=2)
    logger.info(f"Daily summary notification: {'✅ SUCCESS' if success else '❌ FAILED'}")


def test_rate_limiting(notifier: Notifier) -> None:
    """Test rate limiting by sending multiple notifications rapidly."""
    logger.info("Testing rate limiting (sending 10 notifications rapidly)...")

    sent = 0
    blocked = 0

    for i in range(10):
        success = notifier.send_info(f"Test message #{i + 1}")
        if success:
            sent += 1
        else:
            blocked += 1

    logger.info(f"Rate limiting test: {sent} sent, {blocked} blocked by rate limiter")
    logger.info(
        "Rate limiter is working correctly!" if blocked > 0 else "⚠️ No rate limiting observed"
    )


def test_custom_notification(notifier: Notifier) -> None:
    """Test custom notification with all fields."""
    logger.info("Testing custom notification with all fields...")
    success = notifier.send(
        NotificationType.INFO,
        title="🎵 Custom Test Notification",
        description="This is a test notification with all available fields",
        fields={
            "Field 1": "Value 1",
            "Field 2": "Value 2",
            "Field 3": "Value 3",
        },
        thumbnail_url="https://via.placeholder.com/150",
    )
    logger.info(f"Custom notification: {'✅ SUCCESS' if success else '❌ FAILED'}")


def print_configuration(config: NotificationConfig) -> None:
    """Print current notification configuration."""
    logger.info("=== Notification Configuration ===")
    logger.info(
        f"Discord webhook configured: {'✅ Yes' if config.discord_webhook_url else '❌ No'}"
    )
    logger.info(f"Slack webhook configured: {'✅ Yes' if config.slack_webhook_url else '❌ No'}")
    logger.info(f"Notifications enabled: {config.enabled}")
    logger.info(f"Rate limiting enabled: {config.rate_limit_enabled}")
    logger.info(f"Quiet hours enabled: {config.quiet_hours_enabled}")
    if config.quiet_hours_enabled:
        logger.info(f"Quiet hours: {config.quiet_hours_start} - {config.quiet_hours_end}")
    logger.info(f"Async send: {config.async_send}")
    logger.info(f"Timeout: {config.timeout_seconds}s")
    logger.info("=" * 35)


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Test the notification system")
    parser.add_argument(
        "--type",
        choices=[
            "track_change",
            "error",
            "warning",
            "info",
            "daily_summary",
            "rate_limit",
            "custom",
        ],
        help="Test a specific notification type",
    )
    parser.add_argument("--all", action="store_true", help="Run all notification tests")
    parser.add_argument("--config", action="store_true", help="Print configuration and exit")
    parser.add_argument(
        "--force", action="store_true", help="Force send (bypass rate limits and quiet hours)"
    )

    args = parser.parse_args()

    # Initialize notifier
    config = NotificationConfig()
    notifier = Notifier(config)

    # Print configuration if requested
    if args.config:
        print_configuration(config)
        return

    # Check if webhooks are configured
    if not config.has_webhook_configured():
        logger.error("❌ No webhooks configured!")
        logger.error("Please set DISCORD_WEBHOOK_URL or SLACK_WEBHOOK_URL in your .env file")
        sys.exit(1)

    print_configuration(config)
    print()

    # Temporarily disable rate limiting if --force is used
    if args.force:
        logger.info("⚠️ Force mode enabled - bypassing rate limits and quiet hours")
        config.rate_limit_enabled = False
        config.quiet_hours_enabled = False

    # Run tests
    if args.all:
        logger.info("Running all notification tests...\n")
        test_track_change(notifier)
        test_error(notifier)
        test_warning(notifier)
        test_info(notifier)
        test_daily_summary(notifier)
        test_custom_notification(notifier)
        test_rate_limiting(notifier)
    elif args.type:
        if args.type == "track_change":
            test_track_change(notifier)
        elif args.type == "error":
            test_error(notifier)
        elif args.type == "warning":
            test_warning(notifier)
        elif args.type == "info":
            test_info(notifier)
        elif args.type == "daily_summary":
            test_daily_summary(notifier)
        elif args.type == "rate_limit":
            test_rate_limiting(notifier)
        elif args.type == "custom":
            test_custom_notification(notifier)
    else:
        # Default: run a simple test
        logger.info("Running default test (track change notification)...\n")
        test_track_change(notifier)

    # Print statistics
    print()
    logger.info("=== Notification Statistics ===")
    stats = notifier.get_stats()
    for key, value in stats.items():
        logger.info(f"{key}: {value}")
    logger.info("=" * 32)


if __name__ == "__main__":
    main()
