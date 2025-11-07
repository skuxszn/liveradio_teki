# Logging & Analytics Module (SHARD-5)

Comprehensive logging system and track play history for analytics and debugging in the 24/7 FFmpeg YouTube Radio Stream project.

## Overview

This module provides:
- **Track Play History**: Log every track play session with metadata
- **Error Tracking**: System-wide error logging with severity levels
- **System Metrics**: Performance and resource usage tracking
- **Analytics Queries**: Pre-built queries for common analytics tasks
- **Export Tools**: CSV export and HTML/text report generation
- **Structured Logging**: JSON-formatted logs with rotation

## Components

### 1. RadioLogger (`logger.py`)

Main logging class for tracking plays, errors, and metrics.

#### Features
- Database-backed logging with connection pooling
- Structured JSON logging to rotating files
- Track play lifecycle management
- Error logging with context and stack traces
- System metrics collection
- <10ms performance overhead

#### Usage

```python
from logging_module import RadioLogger, LoggingConfig

# Initialize
config = LoggingConfig.from_env()
logger = RadioLogger(config)

# Log track started
play_id = logger.log_track_started(
    track_info={
        "artist": "The Beatles",
        "title": "Hey Jude",
        "album": "1968-1970",
        "azuracast_song_id": "123",
        "duration": 431
    },
    loop_path="/srv/loops/the_beatles_hey_jude.mp4",
    ffmpeg_pid=12345
)

# Log errors
logger.log_error(
    service="ffmpeg",
    severity="error",
    message="Connection refused to RTMP server",
    context={"host": "nginx-rtmp", "port": 1935},
    play_history_id=play_id
)

# Log metrics
logger.log_metric(
    metric_name="cpu_usage",
    metric_value=45.2,
    unit="percent",
    service="ffmpeg"
)

# End track
logger.log_track_ended(
    play_id=play_id,
    had_errors=False
)

# Query recent plays
recent = logger.get_recent_plays(limit=10)
for play in recent:
    print(f"{play['artist']} - {play['title']}")

# Get current playing
current = logger.get_current_playing()
if current:
    print(f"Now playing: {current['artist']} - {current['title']}")

# Cleanup old data
deleted = logger.cleanup_old_data()
print(f"Deleted {deleted['play_history']} old records")

# Close
logger.close()
```

#### Context Manager

```python
with RadioLogger(config) as logger:
    logger.log_track_started(...)
    # Automatically closes on exit
```

### 2. Analytics (`analytics.py`)

Analytics query engine for reporting and insights.

#### Features
- Pre-built analytics queries
- Flexible date range filtering
- Top tracks, error summaries, uptime statistics
- Daily and weekly report generation

#### Usage

```python
from logging_module import Analytics, LoggingConfig
from datetime import datetime, timedelta

# Initialize
config = LoggingConfig.from_env()
analytics = Analytics(config)

# Get play statistics
stats = analytics.get_play_stats(days=7)
print(f"Total plays: {stats['total_plays']}")
print(f"Uptime: {stats['uptime_percent']:.2f}%")
print(f"Error rate: {stats['error_rate']:.2f}%")

# Get most played tracks
most_played = analytics.get_most_played_tracks(days=30, limit=10)
for i, track in enumerate(most_played, 1):
    print(f"{i}. {track['artist']} - {track['title']}: {track['play_count']} plays")

# Get error summary
errors = analytics.get_error_summary(days=7)
for error in errors:
    print(f"{error['service']}/{error['severity']}: {error['error_count']} errors")

# Get hourly distribution
distribution = analytics.get_hourly_play_distribution(days=7)
for hour in distribution:
    print(f"Hour {hour['hour_of_day']}: {hour['play_count']} plays")

# Get daily summary
daily = analytics.get_daily_summary()
print(f"Yesterday: {daily['total_plays']} plays, {daily['uptime_percent']:.2f}% uptime")

# Get weekly summary
weekly = analytics.get_weekly_summary()
print(f"This week: {weekly['total_plays']} plays, {weekly['unique_tracks']} unique tracks")

# Get track history
history = analytics.get_track_history("The Beatles", "Hey Jude", limit=20)
print(f"Played {len(history)} times")

# Get uptime by day
uptime = analytics.get_uptime_by_day(days=30)
for day in uptime:
    print(f"{day['date']}: {day['uptime_percent']:.2f}%")

# Get error timeline
timeline = analytics.get_error_timeline(days=7, severity="error")
for error in timeline:
    print(f"{error['timestamp']}: {error['service']} - {error['message']}")

# Close
analytics.close()
```

### 3. Configuration (`config.py`)

Configuration management from environment variables.

#### Environment Variables

```bash
# Database
POSTGRES_HOST=localhost         # PostgreSQL host
POSTGRES_PORT=5432             # PostgreSQL port
POSTGRES_USER=radio            # PostgreSQL username
POSTGRES_PASSWORD=secret       # PostgreSQL password
POSTGRES_DB=radio_db           # PostgreSQL database

# Logging
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_PATH=/var/log/radio        # Log file directory
LOG_FILE_MAX_BYTES=104857600   # Max log file size (100MB)
LOG_FILE_BACKUP_COUNT=10       # Number of backup files

# Database Pool
DB_POOL_SIZE=5                 # Connection pool size
DB_MAX_OVERFLOW=10             # Max overflow connections
DB_POOL_TIMEOUT=30             # Connection timeout (seconds)
DB_POOL_RECYCLE=3600           # Connection recycle time (seconds)

# Data Retention
PLAY_HISTORY_RETENTION_DAYS=90 # Days to keep play history
ERROR_LOG_RETENTION_DAYS=30    # Days to keep resolved errors
METRICS_RETENTION_DAYS=30      # Days to keep metrics

# Debug
DEBUG=false                    # Enable debug mode
```

#### Usage

```python
from logging_module import LoggingConfig

# Load from environment
config = LoggingConfig.from_env()

# Or create manually
config = LoggingConfig(
    postgres_host="localhost",
    postgres_port=5432,
    log_level="DEBUG",
    debug=True
)

# Validate
config.validate()

# Get database URL
print(config.database_url)
```

## Database Schema

### Tables

#### `play_history`
Records every track play session.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| track_key | VARCHAR(512) | Normalized "artist - title" |
| artist | VARCHAR(256) | Artist name |
| title | VARCHAR(256) | Song title |
| album | VARCHAR(256) | Album name |
| azuracast_song_id | VARCHAR(128) | AzuraCast song ID |
| loop_file_path | VARCHAR(1024) | Path to MP4 loop |
| started_at | TIMESTAMP | When track started |
| ended_at | TIMESTAMP | When track ended |
| duration_seconds | INTEGER | Actual play duration |
| expected_duration_seconds | INTEGER | Expected duration |
| ffmpeg_pid | INTEGER | FFmpeg process ID |
| had_errors | BOOLEAN | Whether errors occurred |
| error_message | TEXT | Error details |
| error_count | INTEGER | Number of errors |
| metadata | JSONB | Additional metadata |

#### `error_log`
System-wide error tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| timestamp | TIMESTAMP | When error occurred |
| service | VARCHAR(64) | Service name |
| severity | VARCHAR(16) | info/warning/error/critical |
| message | TEXT | Error message |
| context | JSONB | Error context |
| stack_trace | TEXT | Stack trace |
| resolved | BOOLEAN | Whether resolved |
| resolved_at | TIMESTAMP | When resolved |
| play_history_id | INTEGER | Associated play session |

#### `system_metrics`
Performance and resource metrics.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| timestamp | TIMESTAMP | When metric was recorded |
| metric_name | VARCHAR(128) | Metric name |
| metric_value | NUMERIC | Metric value |
| unit | VARCHAR(32) | Unit of measurement |
| service | VARCHAR(64) | Service name |
| metadata | JSONB | Additional metadata |

### Stored Functions

- `get_play_stats(start_date, end_date)` - Aggregate play statistics
- `get_most_played_tracks(start_date, end_date, limit)` - Top N tracks
- `get_error_summary(start_date, end_date)` - Error counts by service/severity
- `get_hourly_play_distribution(start_date, end_date)` - Plays by hour of day
- `archive_old_play_history(days_to_keep)` - Clean old play records
- `clean_resolved_errors(days_to_keep)` - Clean resolved errors

### Views

- `recent_plays` - Last 100 plays
- `current_playing` - Currently playing track

## Scripts

### Export Analytics (`scripts/export_analytics.py`)

Export data to CSV files.

```bash
# Export last 7 days
python scripts/export_analytics.py --days 7

# Export with errors and metrics
python scripts/export_analytics.py --days 30 --include-errors --include-metrics

# Custom output directory
python scripts/export_analytics.py --output-dir /tmp/reports

# Full options
python scripts/export_analytics.py \
    --days 30 \
    --output-dir ./analytics_export \
    --include-errors \
    --include-metrics
```

**Outputs:**
- `play_history_YYYYMMDD_HHMMSS.csv` - Full play history
- `analytics_summary_YYYYMMDD_HHMMSS.csv` - Summary statistics
- `error_log_YYYYMMDD_HHMMSS.csv` - Error log (if --include-errors)
- `system_metrics_YYYYMMDD_HHMMSS.csv` - Metrics (if --include-metrics)

### Generate Report (`scripts/generate_report.py`)

Generate analytics reports in text and HTML formats.

```bash
# Generate weekly report
python scripts/generate_report.py

# Generate 30-day report
python scripts/generate_report.py --days 30

# Generate HTML only
python scripts/generate_report.py --format html

# Generate and send Discord notification
python scripts/generate_report.py --send-notification

# Custom webhook
python scripts/generate_report.py --webhook-url https://discord.com/api/webhooks/...

# Full options
python scripts/generate_report.py \
    --days 7 \
    --format both \
    --output-dir ./reports \
    --send-notification
```

**Outputs:**
- `weekly_report_YYYYMMDD_HHMMSS.txt` - Text format report
- `weekly_report_YYYYMMDD_HHMMSS.html` - HTML format report
- Discord/Slack notification (if --send-notification)

## Installation

### 1. Database Setup

```bash
# Connect to PostgreSQL
psql -U radio -d radio_db

# Run schema
\i logging_module/schema.sql
```

### 2. Python Dependencies

Already included in `requirements-dev.txt`:
- sqlalchemy
- pytest (for tests)
- pytest-cov (for coverage)

### 3. Environment Configuration

```bash
# Copy example
cp env.example .env

# Edit configuration
vim .env
```

## Testing

```bash
# Run all tests
pytest logging_module/tests/ -v

# Run with coverage
pytest logging_module/tests/ -v --cov=logging_module --cov-report=html

# Run specific test file
pytest logging_module/tests/test_logger.py -v

# Run specific test
pytest logging_module/tests/test_logger.py::TestRadioLogger::test_log_track_started -v
```

## Performance

- **Logging overhead**: <10ms per track change
- **Database pool**: Configurable connection pooling
- **Log rotation**: Automatic file rotation at 100MB (configurable)
- **Cleanup**: Automatic data retention policies

## Integration

### With Metadata Watcher (SHARD-2)

```python
from logging_module import RadioLogger, LoggingConfig

# In metadata watcher
logger = RadioLogger(LoggingConfig.from_env())

# On track change
play_id = logger.log_track_started(
    track_info=azuracast_webhook_data["song"],
    loop_path=loop_file_path,
    ffmpeg_pid=ffmpeg_process.pid
)

# On error
logger.log_error("ffmpeg", "error", "Stream disconnected")

# On track end
logger.log_track_ended(play_id, had_errors=False)
```

### With FFmpeg Manager (SHARD-4)

```python
# Log FFmpeg errors
logger.log_error(
    "ffmpeg",
    "critical",
    "FFmpeg crashed",
    context={"exit_code": proc.returncode},
    stack_trace=traceback.format_exc()
)

# Log metrics
logger.log_metric("cpu_usage", psutil.cpu_percent(), "percent", "ffmpeg")
logger.log_metric("memory_mb", psutil.Process().memory_info().rss / 1024 / 1024, "MB", "ffmpeg")
```

### With Monitoring (SHARD-7)

```python
from logging_module import Analytics

# Get metrics for Prometheus
analytics = Analytics(config)
stats = analytics.get_play_stats(days=1)

# Export to Prometheus metrics
prometheus_metrics.uptime_gauge.set(stats['uptime_percent'])
prometheus_metrics.error_rate_gauge.set(stats['error_rate'])
prometheus_metrics.total_plays_counter.inc(stats['total_plays'])
```

## Troubleshooting

### Issue: Database connection fails

**Solution**: Check PostgreSQL credentials and connectivity
```bash
psql -U $POSTGRES_USER -h $POSTGRES_HOST -d $POSTGRES_DB
```

### Issue: Log files not created

**Solution**: Check permissions on log directory
```bash
mkdir -p /var/log/radio
chmod 755 /var/log/radio
```

### Issue: Slow analytics queries

**Solution**: Ensure database indexes are created
```sql
-- Check indexes
\di play_history*

-- Recreate if missing
CREATE INDEX IF NOT EXISTS idx_play_history_started ON play_history(started_at DESC);
```

### Issue: Out of database connections

**Solution**: Adjust pool size
```bash
# In .env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

## Known Limitations

- PostgreSQL 15+ required for JSONB features
- Log file rotation requires write permissions
- Cleanup functions should be run periodically (cron job recommended)
- Very large datasets (>1M records) may require query optimization

## Future Enhancements

- Real-time analytics dashboard
- Machine learning for track recommendations
- Anomaly detection for error patterns
- Automatic performance optimization suggestions
- Integration with external analytics platforms

## Contributing

When modifying this module:
1. Maintain backward compatibility
2. Add tests for new features
3. Update this README
4. Run linters (black, flake8, mypy)
5. Ensure ≥80% test coverage

## License

Part of the 24/7 FFmpeg YouTube Radio Stream project.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review test cases for usage examples
3. Check PostgreSQL logs for database errors
4. Enable DEBUG mode for verbose logging

---

**Version**: 1.0.0  
**Last Updated**: November 5, 2025  
**Status**: ✅ Production Ready
