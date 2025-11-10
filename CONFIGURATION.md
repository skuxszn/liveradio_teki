# System Configuration Guide

## Overview

The 24/7 FFmpeg YouTube Radio Stream uses **dynamic configuration** stored in the dashboard database. This means all runtime settings are managed through the dashboard UI and automatically propagate to all services without requiring container restarts.

## Configuration Sources

### Primary: Dashboard Database

All runtime configuration is stored in the **dashboard database** (`dashboard_settings` table).

**Benefits:**
- ✅ Single source of truth
- ✅ Real-time updates without restarts
- ✅ User-friendly web interface
- ✅ Audit trail of all changes
- ✅ Consistent across all services

### Fallback: Environment Variables

Services fall back to `.env` environment variables if:
- Dashboard API is unavailable
- Initial startup before dashboard connection
- Development/testing environments

## Accessing Configuration

### 1. Via Dashboard UI (Recommended)

**URL:** http://localhost:3001/settings

The dashboard provides a user-friendly interface to view and modify all settings organized by category.

**Steps:**
1. Navigate to http://localhost:3001
2. Login with your credentials
3. Go to Settings page
4. Select a category (stream, encoding, paths, etc.)
5. Modify values as needed
6. Click Save
7. All services automatically pick up changes within 60 seconds

### 2. Via API

**Endpoint:** `GET /api/v1/config/`

```bash
# Fetch all configuration
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:9001/api/v1/config/

# Get specific category
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:9001/api/v1/config/stream

# Update a setting
curl -X PUT -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "new-value"}' \
  http://localhost:9001/api/v1/config/stream/YOUTUBE_STREAM_KEY
```

### 3. Direct Database Access

**For advanced users only:**

```bash
# Connect to PostgreSQL
docker exec -it radio_postgres psql -U radio -d radio_db

# View all settings
SELECT category, key, value, description FROM dashboard_settings ORDER BY category, key;

# Update a setting
UPDATE dashboard_settings 
SET value = 'new-value' 
WHERE category = 'stream' AND key = 'YOUTUBE_STREAM_KEY';
```

## Configuration Categories

### Stream Settings (`stream`)

Controls streaming sources and destinations.

| Setting | Description | Example |
|---------|-------------|---------|
| `YOUTUBE_STREAM_KEY` | YouTube live stream key | `xxxx-xxxx-xxxx-xxxx` |
| `AZURACAST_URL` | AzuraCast server URL | `http://azuracast:8080` |
| `AZURACAST_API_KEY` | AzuraCast API authentication key | `your-api-key` |
| `AZURACAST_AUDIO_URL` | Direct audio stream URL | `http://azuracast:8000/radio.mp3` |
| `RTMP_ENDPOINT` | Internal RTMP relay endpoint | `rtmp://nginx-rtmp:1935/live/stream` |
| `WEBHOOK_SECRET` | Secret for AzuraCast webhooks | `your-webhook-secret` |

### Encoding Settings (`encoding`)

FFmpeg video and audio encoding parameters.

| Setting | Description | Example |
|---------|-------------|---------|
| `VIDEO_RESOLUTION` | Video resolution (width:height) | `1280:720` |
| `VIDEO_BITRATE` | Video bitrate | `3000k` |
| `AUDIO_BITRATE` | Audio bitrate | `192k` |
| `VIDEO_ENCODER` | FFmpeg video encoder | `libx264` |
| `FFMPEG_PRESET` | Encoding speed/quality preset | `veryfast` |
| `FADE_DURATION` | Audio/video fade duration (seconds) | `1.0` |
| `TRACK_OVERLAP_DURATION` | Track transition overlap (seconds) | `2.0` |
| `FFMPEG_LOG_LEVEL` | FFmpeg log verbosity | `info` |
| `MAX_RESTART_ATTEMPTS` | Max FFmpeg restart attempts | `3` |
| `RESTART_COOLDOWN_SECONDS` | Cooldown between restarts | `60` |

### Path Settings (`paths`)

File system paths for videos, logs, etc.

| Setting | Description | Example |
|---------|-------------|---------|
| `LOOPS_PATH` | Video loops directory | `/srv/loops` |
| `DEFAULT_LOOP` | Default loop video file | `/srv/loops/default.mp4` |
| `LOG_PATH` | Log files directory | `/var/log/radio` |

### Security Settings (`security`)

Secrets, tokens, and authentication.

| Setting | Description | Example |
|---------|-------------|---------|
| `JWT_SECRET` | JWT signing secret | `your-jwt-secret` |
| `API_TOKEN` | Internal API token for services | `your-api-token` |

### Advanced Settings (`advanced`)

System-level configuration.

| Setting | Description | Example |
|---------|-------------|---------|
| `LOG_LEVEL` | Application log level | `INFO` |
| `DEBUG` | Enable debug mode | `false` |
| `ENVIRONMENT` | Environment name | `production` |
| `ENABLE_METRICS` | Enable Prometheus metrics | `true` |
| `CONFIG_REFRESH_INTERVAL` | Config refresh interval (seconds) | `60` |

### Database Settings (`database`)

PostgreSQL connection parameters.

| Setting | Description | Example |
|---------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL hostname | `postgres` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER` | PostgreSQL username | `radio` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `your-password` |
| `POSTGRES_DB` | PostgreSQL database name | `radio_db` |

### Notification Settings (`notifications`)

Webhooks for alerts and notifications.

| Setting | Description | Example |
|---------|-------------|---------|
| `DISCORD_WEBHOOK_URL` | Discord webhook URL | `https://discord.com/api/webhooks/...` |
| `SLACK_WEBHOOK_URL` | Slack webhook URL | `https://hooks.slack.com/services/...` |

## How Dynamic Configuration Works

### Architecture

```
┌─────────────────┐
│  Dashboard DB   │ ◄── Single source of truth
│  (PostgreSQL)   │
└────────┬────────┘
         │
┌────────▼────────┐
│  Dashboard API  │
│ /config/export  │ ◄── Internal API endpoint
└────────┬────────┘
         │
         │ (Fetches every 60s)
         │
    ┌────┴────┬────────────┬─────────────┐
    ▼         ▼            ▼             ▼
┌─────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐
│nginx-rtmp│ │metadata- │ │dashboard│ │other   │
│         │ │watcher   │ │-api     │ │services│
└─────────┘ └──────────┘ └─────────┘ └────────┘
```

### Service Integration

Each service integrates dynamic configuration using one of these methods:

#### 1. Python Services (metadata-watcher, dashboard-api)

Uses the shared `DashboardConfigClient`:

```python
from shared.config_client import DashboardConfigClient

config_client = DashboardConfigClient(
    dashboard_url=os.getenv("DASHBOARD_API_URL"),
    api_token=os.getenv("API_TOKEN"),
    service_name="my-service"
)

# Fetch configuration
config = await config_client.fetch_config()

# Get specific setting
youtube_key = config_client.get_setting("stream", "YOUTUBE_STREAM_KEY")

# Auto-refresh
asyncio.create_task(config_client.start_auto_refresh())
```

#### 2. nginx-rtmp Service

Uses Python `push_manager.py` to:
1. Fetch stream key from dashboard
2. Update nginx.conf template
3. Reload nginx gracefully
4. Repeat every 60 seconds

### Configuration Refresh Cycle

1. **Service starts** → Fetches initial config from dashboard
2. **Every 60 seconds** → Checks for configuration changes
3. **Config changed?** → Applies new configuration automatically
4. **Dashboard unavailable?** → Falls back to environment variables

## Configuration Migration

### Adding Missing Settings

If you need to add settings that exist in `.env` but not in the database:

```bash
# Run the migration script
docker exec radio_dashboard_api python3 /app/migrations/add_missing_settings.py
```

This will:
- Scan all required settings
- Add missing settings to database
- Populate values from environment variables
- Update descriptions and defaults

### Manual Setting Creation

To add a custom setting:

```bash
docker exec radio_postgres psql -U radio -d radio_db -c "
INSERT INTO dashboard_settings (category, key, value, default_value, description, is_secret)
VALUES ('custom', 'MY_SETTING', 'my-value', '', 'My custom setting', false);
"
```

## Troubleshooting

### Services Not Picking Up Config Changes

**Check auto-refresh is working:**

```bash
docker logs radio_metadata_watcher | grep "config"
docker logs radio_nginx_rtmp | grep "Config updated"
```

**Expected output:**
```
[metadata-watcher] Successfully fetched configuration
[nginx-rtmp] Config updated with stream key: xxxx-xxxx-x...
```

**If not seeing updates:**

1. Check API token is set:
   ```bash
   docker exec radio_metadata_watcher env | grep API_TOKEN
   ```

2. Check dashboard API is accessible:
   ```bash
   docker exec radio_metadata_watcher curl -I http://dashboard-api:9001/health
   ```

3. Check refresh interval:
   ```bash
   docker exec radio_metadata_watcher env | grep CONFIG_REFRESH_INTERVAL
   ```

### Dashboard API Not Responding

```bash
# Check service is running
docker ps | grep dashboard-api

# Check logs
docker logs radio_dashboard_api

# Restart if needed
docker-compose restart dashboard-api
```

### Settings Missing from Database

```bash
# Run migration
docker exec radio_dashboard_api python3 /app/migrations/add_missing_settings.py

# Verify settings exist
docker exec radio_postgres psql -U radio -d radio_db -c \
  "SELECT category, key FROM dashboard_settings ORDER BY category, key;"
```

### Configuration Not Persisting

If changes are lost after restart, ensure:

1. PostgreSQL volume is properly mounted:
   ```bash
   docker volume ls | grep postgres_data
   ```

2. Database is healthy:
   ```bash
   docker exec radio_postgres pg_isready -U radio
   ```

3. Changes are being saved to database, not just memory

## Best Practices

### ✅ DO:

- **Use dashboard UI** for all configuration changes
- **Test changes** in development before production
- **Document** why settings were changed
- **Use secrets** for sensitive values (mark `is_secret=true`)
- **Set reasonable defaults** so services work out-of-box
- **Monitor logs** after configuration changes

### ❌ DON'T:

- **Don't edit `.env` directly** - changes won't persist
- **Don't restart containers** to apply config - it's automatic
- **Don't hardcode values** in service code
- **Don't store secrets** in plain text (use dashboard secrets)
- **Don't bypass the API** - always use proper endpoints

## Development vs Production

### Development

```bash
# Use .env as primary source
# Dashboard is optional
# Faster iteration with direct .env edits
```

### Production

```bash
# Use dashboard database as primary source
# .env only for initial bootstrap and fallback
# All changes via dashboard UI
# Automatic propagation to all services
```

## Service-Specific Notes

### nginx-rtmp

- Automatically reloads nginx on stream key changes
- Template-based configuration (`nginx.conf.template`)
- Graceful reload preserves active streams
- Falls back to `YOUTUBE_STREAM_KEY` env var if dashboard unavailable

### metadata-watcher

- Already fully integrated with dynamic config
- Fetches all encoding and stream settings from dashboard
- Updates FFmpeg parameters without restart
- Falls back to environment variables if needed

### dashboard-api

- Reads its own database for configuration
- Provides `/config/internal/export` endpoint for other services
- Requires `API_TOKEN` for internal service authentication

## Security Considerations

### Secrets Management

- Mark sensitive settings with `is_secret=true`
- Dashboard UI shows `***` for secret values
- API responses can mask secret values
- Never log secret values in plaintext

### API Authentication

All services use `API_TOKEN` for internal communication:

```bash
# Set in .env
API_TOKEN=your-secure-random-token

# Services automatically use this to authenticate
```

### Access Control

- Dashboard UI requires authentication
- API endpoints require valid JWT or API token
- Database connection uses strong passwords
- Internal network only (not exposed to internet)

## Monitoring Configuration

### Metrics

Prometheus metrics track configuration:

- `config_fetch_total` - Number of config fetches
- `config_fetch_errors_total` - Number of fetch failures
- `config_last_fetch_timestamp` - Last successful fetch time
- `config_refresh_duration_seconds` - Time to fetch config

### Alerts

Set up alerts for:

- Configuration fetch failures
- Services using fallback configuration
- Unusual configuration change frequency
- Missing required settings

## Migration Checklist

When migrating a new service to dynamic configuration:

- [ ] Add `DASHBOARD_API_URL` to service environment
- [ ] Add `API_TOKEN` to service environment
- [ ] Add `CONFIG_REFRESH_INTERVAL` (default: 60)
- [ ] Integrate `DashboardConfigClient` or equivalent
- [ ] Add settings to database migration
- [ ] Test configuration fetch
- [ ] Test auto-refresh
- [ ] Test fallback to environment variables
- [ ] Update service documentation
- [ ] Add monitoring/logging

## Summary

**Key Points:**

1. 🎯 **Dashboard database** is the single source of truth
2. 🔄 **Auto-refresh** every 60 seconds - no restarts needed
3. 🛡️ **Graceful fallback** to environment variables
4. 🖥️ **User-friendly UI** for non-technical users
5. 📝 **Audit trail** of all configuration changes
6. 🚀 **Real-time propagation** to all services

**Quick Start:**

1. Configure settings via dashboard UI at http://localhost:3001/settings
2. Changes automatically propagate within 60 seconds
3. Monitor logs to confirm services pick up changes
4. No container restarts needed!

---

**For more information, see:**
- `MIGRATE_TO_DYNAMIC_CONFIG.md` - Migration guide
- `README.md` - General system documentation
- `DASHBOARD_QUICKSTART.md` - Dashboard setup guide



