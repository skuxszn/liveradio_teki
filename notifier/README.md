# Notification System

Discord and Slack webhook integration for real-time alerts and status updates in the 24/7 FFmpeg YouTube Radio Stream.

## Overview

The notification system provides a unified interface for sending formatted notifications to Discord and Slack channels. It includes:

- **Multi-platform support**: Discord and Slack webhooks
- **Rich formatting**: Embeds with fields, colors, and thumbnails
- **Rate limiting**: Prevent notification spam with configurable limits
- **Quiet hours**: Disable notifications during specified time ranges
- **Async/sync modes**: Fire-and-forget or blocking sends
- **Error handling**: Graceful failures that don't block the main application
- **Type safety**: Full Python 3.11+ type hints

## Features

### Notification Types

- **Track Change** (`TRACK_CHANGE`): When a new track starts playing
- **Error** (`ERROR`): Critical errors requiring attention
- **Warning** (`WARNING`): Non-critical warnings
- **Info** (`INFO`): General information messages
- **Daily Summary** (`DAILY_SUMMARY`): Daily statistics reports

### Rate Limiting

- Per-minute and per-hour limits for each notification type
- Exponential backoff for repeated identical notifications
- Configurable via environment variables
- Thread-safe implementation

### Quiet Hours

- Optionally disable notifications during specified hours (e.g., 11 PM - 7 AM)
- Handles overnight time ranges
- Per-notification-type filtering

## Installation

### Dependencies

```bash
pip install aiohttp python-dotenv
```

### Environment Variables

Add to your `.env` file:

```bash
# Discord webhook (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Slack webhook (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# General settings
NOTIFICATION_ENABLED=true
NOTIFICATION_ASYNC=true
NOTIFICATION_TIMEOUT=5

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_TRACK_CHANGE_PER_MINUTE=1
RATE_LIMIT_TRACK_CHANGE_PER_HOUR=60
RATE_LIMIT_ERROR_PER_MINUTE=5
RATE_LIMIT_ERROR_PER_HOUR=100

# Quiet hours (optional)
QUIET_HOURS_ENABLED=false
QUIET_HOURS_START=23:00
QUIET_HOURS_END=07:00

# Disabled notification types (optional, comma-separated)
NOTIFICATION_DISABLED_TYPES=

# Discord customization
DISCORD_USERNAME=Radio Stream Bot
DISCORD_AVATAR_URL=

# Slack customization
SLACK_USERNAME=Radio Stream Bot
SLACK_ICON_EMOJI=:radio:
```

## Usage

### Basic Usage

```python
from notifier import Notifier, NotificationType

# Initialize with default configuration
notifier = Notifier()

# Send a simple notification
notifier.send(
    NotificationType.INFO,
    "Stream started successfully"
)
```

### Track Change Notifications

```python
# Using the convenience method
notifier.send_track_change(
    artist="The Beatles",
    title="Here Comes The Sun",
    album="Abbey Road",
    loop_file="beatles_abbey_road.mp4"
)

# Equivalent to:
notifier.send(
    NotificationType.TRACK_CHANGE,
    "🎵 Now Playing: The Beatles - Here Comes The Sun",
    fields={
        "Album": "Abbey Road",
        "Loop": "beatles_abbey_road.mp4"
    }
)
```

### Error Notifications

```python
# Errors bypass rate limiting and quiet hours
notifier.send_error(
    "FFmpeg process crashed",
    context={
        "pid": "12345",
        "exit_code": "1",
        "retries": "3/3"
    }
)
```

### Warning Notifications

```python
notifier.send_warning(
    "Audio stream temporarily unavailable, retrying...",
    context={
        "url": "http://azuracast:8000/radio",
        "retry": "2/10"
    }
)
```

### Daily Summary

```python
notifier.send_daily_summary(
    tracks_played=142,
    uptime_percent=99.8,
    errors=2
)
```

### Advanced Usage

```python
# Send with all options
notifier.send(
    NotificationType.INFO,
    title="Custom Notification",
    description="This is a detailed description",
    fields={
        "Field 1": "Value 1",
        "Field 2": "Value 2"
    },
    thumbnail_url="https://example.com/thumbnail.png",
    force=True  # Bypass rate limiting and quiet hours
)
```

### Async Usage

```python
import asyncio

async def send_async():
    notifier = Notifier()
    
    await notifier.send_async(
        NotificationType.INFO,
        "Async notification"
    )

asyncio.run(send_async())
```

### Custom Configuration

```python
from notifier import Notifier, NotificationConfig

# Create custom configuration
config = NotificationConfig()
config.enabled = True
config.async_send = False  # Use synchronous sends
config.rate_limit_enabled = False  # Disable rate limiting

notifier = Notifier(config)
```

## API Reference

### Notifier

Main notification interface.

#### Methods

##### `send(notification_type, title, description=None, fields=None, thumbnail_url=None, force=False)`

Send a notification synchronously.

**Parameters:**
- `notification_type` (NotificationType): Type of notification
- `title` (str): Notification title
- `description` (str, optional): Notification description
- `fields` (dict, optional): Additional fields as key-value pairs
- `thumbnail_url` (str, optional): URL of thumbnail image
- `force` (bool, optional): Bypass rate limiting and quiet hours

**Returns:** `bool` - True if at least one notification sent successfully

##### `send_async(notification_type, title, ...)`

Send a notification asynchronously.

Same parameters as `send()`.

**Returns:** `bool` - True if at least one notification sent successfully

##### `send_track_change(artist, title, album=None, loop_file=None)`

Convenience method for track change notifications.

##### `send_error(message, context=None)`

Convenience method for error notifications. Bypasses rate limiting.

##### `send_warning(message, context=None)`

Convenience method for warning notifications.

##### `send_info(message, context=None)`

Convenience method for info notifications.

##### `send_daily_summary(tracks_played, uptime_percent, errors=0)`

Convenience method for daily summary notifications.

##### `get_stats()`

Get notification statistics.

**Returns:** `dict` with keys: `sent`, `failed`, `rate_limited`, `quiet_hours_blocked`

##### `reset_stats()`

Reset notification statistics.

### NotificationConfig

Configuration management for the notification system.

#### Methods

##### `is_type_enabled(notification_type)`

Check if a notification type is enabled.

##### `is_quiet_hours()`

Check if current time is within quiet hours.

##### `get_color(notification_type)`

Get Discord embed color for notification type.

##### `has_webhook_configured()`

Check if at least one webhook is configured.

## Discord Formatting

Discord notifications support rich embeds:

```python
from notifier.discord import DiscordClient, DiscordEmbed

# Create a custom embed
embed = DiscordEmbed(
    title="Custom Notification",
    description="Detailed description",
    color=3066993  # Green
)

embed.add_field("Field 1", "Value 1", inline=True)
embed.add_field("Field 2", "Value 2", inline=True)
embed.set_thumbnail("https://example.com/image.png")
embed.set_footer("Footer text")
```

### Discord Color Reference

- Track Change: 3066993 (Green)
- Error: 15158332 (Red)
- Warning: 16776960 (Yellow)
- Info: 3447003 (Blue)
- Daily Summary: 10181046 (Purple)

## Slack Formatting

Slack notifications use attachments with colored sidebars:

```python
from notifier.slack import SlackClient, SlackAttachment

# Create a custom attachment
attachment = SlackAttachment(
    title="Custom Notification",
    text="Detailed text",
    color="good"  # Green, warning, danger, or hex code
)

attachment.add_field("Field 1", "Value 1", short=True)
attachment.set_thumbnail("https://example.com/image.png")
```

## Rate Limiting

Default rate limits per notification type:

| Type | Per Minute | Per Hour |
|------|------------|----------|
| Track Change | 1 | 60 |
| Error | 5 | 100 |
| Warning | 10 | 200 |
| Info | 5 | 100 |
| Daily Summary | 1 | 2 |

Override via environment variables:

```bash
RATE_LIMIT_ERROR_PER_MINUTE=10
RATE_LIMIT_ERROR_PER_HOUR=200
```

### Exponential Backoff

Repeated identical notifications trigger exponential backoff:
- First duplicate: 1 second delay
- Second duplicate: 2 seconds delay
- Third duplicate: 4 seconds delay
- Maximum: 3600 seconds (1 hour)

## Testing

### Run Unit Tests

```bash
pytest notifier/tests/ -v --cov=notifier
```

### Manual Testing

```bash
# Test all notification types
python scripts/test_notifications.py --all

# Test specific type
python scripts/test_notifications.py --type track_change

# Test with force (bypass limits)
python scripts/test_notifications.py --force

# View configuration
python scripts/test_notifications.py --config
```

## Integration with Other Modules

### From Metadata Watcher (SHARD-2)

```python
from notifier import Notifier, NotificationType

notifier = Notifier()

# On track change
notifier.send_track_change(
    artist=track_info["artist"],
    title=track_info["title"],
    album=track_info.get("album"),
    loop_file=loop_path
)
```

### From FFmpeg Manager (SHARD-4)

```python
# On FFmpeg crash
notifier.send_error(
    f"FFmpeg crashed after {retries} retries",
    context={
        "pid": str(process.pid),
        "exit_code": str(process.returncode),
        "track": current_track
    }
)

# On successful restart
notifier.send_info(
    "FFmpeg restarted successfully",
    context={"pid": str(new_process.pid)}
)
```

### From Monitoring (SHARD-7)

```python
# Daily summary
notifier.send_daily_summary(
    tracks_played=stats["tracks"],
    uptime_percent=stats["uptime"],
    errors=stats["errors"]
)
```

## Error Handling

The notification system is designed to fail gracefully:

- **Network errors**: Logged but don't crash the application
- **Rate limiting**: Notifications are dropped silently (with logging)
- **Invalid webhooks**: Warnings logged, application continues
- **Timeout**: 5-second default timeout prevents blocking

All errors are logged using Python's standard logging module.

## Performance

- **Async mode**: Fire-and-forget, ~1ms overhead
- **Sync mode**: Blocks until sent, ~50-200ms per notification
- **Rate limiter**: O(1) lookups, minimal overhead
- **Memory**: ~1KB per 1000 notifications (with cleanup)

## Security

- **Webhook URLs**: Stored in environment variables, never in code
- **HTTPS only**: All webhook URLs must use HTTPS
- **No sensitive data**: Don't include passwords or tokens in notifications
- **Input validation**: All inputs are validated and sanitized

## Troubleshooting

### Notifications not sending

1. Check webhook URLs are configured:
   ```python
   from notifier import NotificationConfig
   config = NotificationConfig()
   print(config.has_webhook_configured())
   ```

2. Check notifications are enabled:
   ```bash
   NOTIFICATION_ENABLED=true
   ```

3. Check quiet hours:
   ```bash
   QUIET_HOURS_ENABLED=false
   ```

### Rate limiting too aggressive

Adjust limits in `.env`:

```bash
RATE_LIMIT_TRACK_CHANGE_PER_MINUTE=5
RATE_LIMIT_TRACK_CHANGE_PER_HOUR=300
```

Or disable rate limiting:

```bash
RATE_LIMIT_ENABLED=false
```

### Discord webhook returns 404

Verify the webhook URL is correct and the webhook hasn't been deleted in Discord.

### Slack webhook returns "no_service"

Verify the Slack app is still installed and the webhook URL is correct.

## Development

### Running Tests

```bash
# All tests
pytest notifier/tests/ -v

# With coverage
pytest notifier/tests/ --cov=notifier --cov-report=html

# Specific test file
pytest notifier/tests/test_discord.py -v

# With debugging
pytest notifier/tests/ -v -s --pdb
```

### Code Style

```bash
# Format code
black notifier/ --line-length 100

# Check types
mypy notifier/ --strict

# Lint
flake8 notifier/
```

## License

Part of the 24/7 FFmpeg YouTube Radio Stream project.

## Support

For issues or questions, check the main project documentation or create an issue in the project repository.

---

**Version**: 1.0.0  
**Last Updated**: November 5, 2025  
**Module**: SHARD-6 - Notification System



