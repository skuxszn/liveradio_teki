# Configuration Reference

**24/7 FFmpeg YouTube Radio Stream - Complete Configuration Guide**

This document provides a comprehensive reference for all configuration options, environment variables, and settings for the radio stream system.

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [Configuration Files](#configuration-files)
3. [FFmpeg Encoding Presets](#ffmpeg-encoding-presets)
4. [Database Configuration](#database-configuration)
5. [Network Configuration](#network-configuration)
6. [Monitoring Configuration](#monitoring-configuration)
7. [Security Configuration](#security-configuration)
8. [Advanced Configuration](#advanced-configuration)

---

## Environment Variables

All environment variables are configured in the `.env` file. Copy from `env.example` to get started:

```bash
cp env.example .env
```

### Critical Settings

These **must** be configured for the system to work:

#### YouTube Streaming

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `YOUTUBE_STREAM_KEY` | **Yes** | _(none)_ | Your YouTube live stream key from YouTube Studio |

**How to Get**:
1. Go to [YouTube Studio](https://studio.youtube.com)
2. Click **Go Live** → **Stream**
3. Copy **Stream Key**

**Example**:
```bash
YOUTUBE_STREAM_KEY=xxxx-xxxx-xxxx-xxxx-xxxx
```

#### AzuraCast Integration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURACAST_URL` | **Yes** | _(none)_ | Base URL of your AzuraCast installation |
| `AZURACAST_API_KEY` | Yes | _(none)_ | API key for AzuraCast authentication |
| `AZURACAST_AUDIO_URL` | **Yes** | _(none)_ | Direct URL to audio stream |

**How to Get API Key**:
1. Log in to AzuraCast
2. Go to **Profile** → **API Keys**
3. Click **Add API Key**
4. Copy generated key

**Examples**:
```bash
AZURACAST_URL=http://radio.example.com
AZURACAST_API_KEY=1234567890abcdef1234567890abcdef
AZURACAST_AUDIO_URL=http://radio.example.com:8000/radio
```

#### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_USER` | Yes | `radio` | PostgreSQL username |
| `POSTGRES_PASSWORD` | **Yes** | _(none)_ | PostgreSQL password (CHANGE THIS!) |
| `POSTGRES_DB` | Yes | `radio_db` | PostgreSQL database name |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port |

**Security Warning**: Always use a strong, unique password in production.

**Generate Strong Password**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example**:
```bash
POSTGRES_USER=radio
POSTGRES_PASSWORD=XyZ123abc456def789SecurePassword
POSTGRES_DB=radio_db
POSTGRES_PORT=5432
```

#### Security Tokens

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WEBHOOK_SECRET` | **Yes** | _(none)_ | Secret for validating AzuraCast webhooks |
| `API_TOKEN` | **Yes** | _(none)_ | Bearer token for API authentication |

**Generate Tokens**:
```bash
# Use provided script
python scripts/generate_token.py --both

# Or manually
python3 -c "import secrets; print('WEBHOOK_SECRET=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('API_TOKEN=' + secrets.token_urlsafe(64))"
```

**Example**:
```bash
WEBHOOK_SECRET=abc123def456...64-characters-long
API_TOKEN=xyz789uvw012...64-characters-long
```

---

### Service Ports

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WATCHER_PORT` | No | `9000` | Metadata watcher HTTP port |
| `PROMETHEUS_PORT` | No | `9090` | Prometheus metrics port |
| `RTMP_PORT` | No | `1935` | RTMP server port |
| `NGINX_HTTP_PORT` | No | `8080` | nginx HTTP stats port |

**Example**:
```bash
WATCHER_PORT=9000
PROMETHEUS_PORT=9090
RTMP_PORT=1935
NGINX_HTTP_PORT=8080
```

**Note**: Only change if you have port conflicts.

---

### FFmpeg Encoding Settings

Configure video encoding parameters based on your hardware and quality requirements.

#### Basic Encoding

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VIDEO_RESOLUTION` | No | `1280:720` | Output resolution (width:height) |
| `VIDEO_BITRATE` | No | `3000k` | Video bitrate (higher = better quality) |
| `AUDIO_BITRATE` | No | `192k` | Audio bitrate |
| `VIDEO_ENCODER` | No | `libx264` | Encoder: `libx264` (CPU) or `h264_nvenc` (GPU) |
| `FFMPEG_PRESET` | No | `veryfast` | Encoding speed preset |
| `FADE_DURATION` | No | `1.0` | Fade in/out duration (seconds) |

**Recommended Configurations**:

**720p Standard** (4-core CPU):
```bash
VIDEO_RESOLUTION=1280:720
VIDEO_BITRATE=2500k
AUDIO_BITRATE=192k
VIDEO_ENCODER=libx264
FFMPEG_PRESET=veryfast
```

**1080p High Quality** (8-core CPU):
```bash
VIDEO_RESOLUTION=1920:1080
VIDEO_BITRATE=4500k
AUDIO_BITRATE=192k
VIDEO_ENCODER=libx264
FFMPEG_PRESET=fast
```

**1080p60 GPU** (NVIDIA GPU):
```bash
VIDEO_RESOLUTION=1920:1080
VIDEO_BITRATE=7000k
AUDIO_BITRATE=192k
VIDEO_ENCODER=h264_nvenc
FFMPEG_PRESET=p4
```

#### Advanced FFmpeg Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FFMPEG_LOG_LEVEL` | No | `info` | FFmpeg log verbosity: `quiet`, `panic`, `fatal`, `error`, `warning`, `info`, `verbose`, `debug` |
| `TRACK_OVERLAP_DURATION` | No | `2.0` | Overlap duration for track transitions (seconds) |
| `ENABLE_HLS` | No | `false` | Enable HLS output for local monitoring |

**Example**:
```bash
FFMPEG_LOG_LEVEL=info
TRACK_OVERLAP_DURATION=2.0
ENABLE_HLS=false
```

---

### Video Asset Paths

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOOPS_PATH` | No | `/srv/loops` | Root directory for video loop files |
| `DEFAULT_LOOP` | No | `/srv/loops/default.mp4` | Fallback loop for unmapped tracks |

**File Structure**:
```
/srv/loops/
├── default.mp4           # Fallback loop (required)
├── tracks/               # Track-specific loops
│   ├── track_001.mp4
│   ├── track_002.mp4
│   └── ...
├── overlays/             # Generated overlays (auto-managed)
└── templates/            # Overlay templates
```

**Example**:
```bash
LOOPS_PATH=/srv/loops
DEFAULT_LOOP=/srv/loops/default.mp4
```

---

### Notification Webhooks

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_WEBHOOK_URL` | No | _(empty)_ | Discord webhook URL for notifications |
| `SLACK_WEBHOOK_URL` | No | _(empty)_ | Slack webhook URL for notifications |

**How to Create Discord Webhook**:
1. Open Discord Server Settings
2. Go to **Integrations** → **Webhooks**
3. Click **New Webhook**
4. Copy **Webhook URL**

**Example**:
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456/abcdef...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00/B00/xxxx
```

**Note**: Leave empty to disable notifications.

---

### Logging Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Application log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_PATH` | No | `/var/log/radio` | Log file directory |

**Log Levels**:
- **DEBUG**: Verbose logging (development only)
- **INFO**: Normal operation logs (recommended)
- **WARNING**: Warning and errors only
- **ERROR**: Errors only
- **CRITICAL**: Critical failures only

**Example**:
```bash
LOG_LEVEL=INFO
LOG_PATH=/var/log/radio
```

---

### Monitoring & Health Checks

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENABLE_METRICS` | No | `true` | Enable Prometheus metrics export |
| `HEALTH_CHECK_INTERVAL` | No | `30` | Health check interval (seconds) |
| `MAX_RESTART_ATTEMPTS` | No | `3` | Max FFmpeg restart attempts before alerting |
| `RESTART_COOLDOWN_SECONDS` | No | `60` | Cooldown between restart attempts |

**Example**:
```bash
ENABLE_METRICS=true
HEALTH_CHECK_INTERVAL=30
MAX_RESTART_ATTEMPTS=3
RESTART_COOLDOWN_SECONDS=60
```

---

### Rate Limiting

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WEBHOOK_RATE_LIMIT` | No | `10` | Max webhook requests per minute |
| `NOTIFICATION_RATE_LIMIT` | No | `60` | Max notification messages per hour |

**Example**:
```bash
WEBHOOK_RATE_LIMIT=10
NOTIFICATION_RATE_LIMIT=60
```

**Note**: Adjust based on your track change frequency. Typical radio station: 3-5 track changes per minute.

---

### Database Connection Pool

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_POOL_SIZE` | No | `5` | Number of persistent database connections |
| `DB_MAX_OVERFLOW` | No | `10` | Max additional connections when pool is full |
| `DB_POOL_TIMEOUT` | No | `30` | Connection timeout (seconds) |

**Example**:
```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

**Tuning**: Increase for high-traffic scenarios.

---

### Advanced Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `production` | Environment: `development`, `testing`, `production` |
| `DEBUG` | No | `false` | Enable debug mode (verbose logging, no error suppression) |

**Example**:
```bash
ENVIRONMENT=production
DEBUG=false
```

**Warning**: Never use `DEBUG=true` in production.

---

## Configuration Files

### docker-compose.yml

Main orchestration file for all services.

**Location**: `./docker-compose.yml`

**Key Sections**:

#### Services

- **nginx-rtmp**: RTMP relay to YouTube
- **metadata-watcher**: Main application server
- **postgres**: Database
- **prometheus**: Metrics collection

#### Networks

- **radio_network**: Bridge network for inter-service communication
  - Subnet: `172.28.0.0/16`

#### Volumes

- **postgres_data**: Persistent database storage
- **prometheus_data**: Persistent metrics storage
- **nginx_logs**: nginx access and error logs

**Customization Example**:

```yaml
# docker-compose.override.yml (for local development)
version: '3.8'

services:
  metadata-watcher:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./metadata_watcher:/app/metadata_watcher  # Live code reload
```

---

### nginx-rtmp/nginx.conf

nginx RTMP module configuration.

**Location**: `./nginx-rtmp/nginx.conf`

**Key Settings**:

```nginx
rtmp {
    server {
        listen 1935;
        
        application live {
            live on;
            record off;
            
            # Push to YouTube
            push rtmp://a.rtmp.youtube.com/live2/${YOUTUBE_STREAM_KEY};
            
            # Optionally push to other platforms
            # push rtmp://live.twitch.tv/app/${TWITCH_STREAM_KEY};
        }
    }
}
```

**Multi-Platform Streaming**:

To stream to multiple platforms simultaneously, add additional `push` directives:

```nginx
push rtmp://a.rtmp.youtube.com/live2/${YOUTUBE_STREAM_KEY};
push rtmp://live.twitch.tv/app/${TWITCH_STREAM_KEY};
push rtmp://live-api-s.facebook.com:80/rtmp/${FACEBOOK_STREAM_KEY};
```

**Note**: Requires sufficient upload bandwidth (multiply bitrate by number of platforms).

---

### Prometheus Configuration

**Location**: `./monitoring/prometheus.yml`

**Default Scrape Targets**:

```yaml
scrape_configs:
  - job_name: 'metadata-watcher'
    scrape_interval: 10s
    static_configs:
      - targets: ['metadata-watcher:9000']
  
  - job_name: 'prometheus'
    scrape_interval: 10s
    static_configs:
      - targets: ['localhost:9090']
```

**Customization**: Add more targets or adjust scrape intervals.

---

### Alert Rules

**Location**: `./monitoring/alerting_rules.yml`

**Example Alert**:

```yaml
groups:
  - name: radio_alerts
    rules:
      - alert: StreamDown
        expr: radio_ffmpeg_status{status="running"} == 0
        for: 2m
        annotations:
          summary: "Radio stream is down"
          description: "FFmpeg has been stopped for more than 2 minutes"
```

**Customization**: Add custom alerts based on your requirements.

---

## FFmpeg Encoding Presets

The system includes predefined encoding presets for different quality levels.

**Location**: `metadata_watcher/config.py` (in code)

### Available Presets

| Preset | Resolution | FPS | Video Bitrate | Audio Bitrate | Encoder | Use Case |
|--------|-----------|-----|---------------|---------------|---------|----------|
| `480p_test` | 854x480 | 30 | 1000k | 128k | x264 | Testing only |
| `720p_fast` | 1280x720 | 30 | 2500k | 192k | x264 | Budget servers |
| `720p_quality` | 1280x720 | 30 | 3500k | 192k | x264 | Balanced |
| `1080p_fast` | 1920x1080 | 30 | 4500k | 192k | x264 | Mid-range servers |
| `1080p_quality` | 1920x1080 | 30 | 6000k | 192k | x264 | High-end servers |
| `720p_nvenc` | 1280x720 | 30 | 3000k | 192k | NVENC | GPU encoding |
| `1080p_nvenc` | 1920x1080 | 30 | 5000k | 192k | NVENC | GPU encoding |
| `1080p60_nvenc` | 1920x1080 | 60 | 7000k | 192k | NVENC | GPU high-quality |

### Selecting a Preset

Set via environment variables:

```bash
# For 720p fast preset
VIDEO_RESOLUTION=1280:720
VIDEO_BITRATE=2500k
VIDEO_ENCODER=libx264
FFMPEG_PRESET=veryfast

# For 1080p NVENC preset
VIDEO_RESOLUTION=1920:1080
VIDEO_BITRATE=5000k
VIDEO_ENCODER=h264_nvenc
FFMPEG_PRESET=p4
```

### Custom Preset

Create your own by adjusting parameters:

```bash
# Custom: 900p @ 40fps (unusual but valid)
VIDEO_RESOLUTION=1600:900
VIDEO_BITRATE=4000k
AUDIO_BITRATE=256k
VIDEO_ENCODER=libx264
FFMPEG_PRESET=medium
```

---

## Database Configuration

### Connection String

Auto-generated from environment variables:

```
postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
```

**Example**:
```
postgresql://radio:SecurePass123@postgres:5432/radio_db
```

### Schema Initialization

Schemas are automatically loaded from:
- `track_mapper/schema.sql` - Track mappings table
- `logging_module/schema.sql` - Play history and error logs

### Manual Database Access

```bash
# Via Docker
docker-compose exec postgres psql -U radio -d radio_db

# Via connection string
psql postgresql://radio:password@localhost:5432/radio_db
```

### Backup and Restore

**Backup**:
```bash
docker-compose exec postgres pg_dump -U radio radio_db > backup.sql
```

**Restore**:
```bash
cat backup.sql | docker-compose exec -T postgres psql -U radio radio_db
```

---

## Network Configuration

### Internal Network

All services communicate on a private bridge network:

- **Network Name**: `radio_network`
- **Subnet**: `172.28.0.0/16`
- **DNS**: Automatic (service names as hostnames)

**Example Connection**:
- From metadata-watcher to postgres: `postgresql://postgres:5432`
- From metadata-watcher to nginx-rtmp: `rtmp://nginx-rtmp:1935`

### Exposed Ports

| Service | Port | Purpose | Public? |
|---------|------|---------|---------|
| metadata-watcher | 9000 | HTTP API, webhook receiver | Yes |
| nginx-rtmp | 1935 | RTMP input (if used directly) | Optional |
| nginx-rtmp | 8080 | HTTP stats | Optional |
| postgres | 5432 | Database (for admin) | No |
| prometheus | 9090 | Metrics UI | Optional |

**Production Recommendation**: Only expose 9000 publicly, use reverse proxy for others.

---

## Monitoring Configuration

### Prometheus Metrics

**Endpoint**: `http://localhost:9000/metrics`

**Available Metrics**:

```
# Counters
radio_tracks_played_total
radio_ffmpeg_restarts_total
radio_errors_total{severity}

# Gauges
radio_ffmpeg_status{status}
radio_stream_uptime_seconds
radio_current_track_duration_seconds

# Histograms
radio_track_switch_duration_seconds
radio_ffmpeg_cpu_usage_percent
radio_ffmpeg_memory_mb
```

### Grafana Dashboard

**Location**: `./grafana/dashboards/radio_stream_dashboard.json`

**Import Steps**:
1. Access Grafana: `http://localhost:3000`
2. Login (default: admin/changeme)
3. Go to Dashboards → Import
4. Upload JSON file
5. Select Prometheus datasource

---

## Security Configuration

### Webhook Authentication

AzuraCast webhooks are validated using `X-Webhook-Secret` header.

**Configuration**:
1. Generate secret: `python scripts/generate_token.py --type webhook`
2. Set in `.env`: `WEBHOOK_SECRET=generated-value`
3. Set in AzuraCast webhook custom headers

### API Authentication

Manual control endpoints require Bearer token.

**Configuration**:
1. Generate token: `python scripts/generate_token.py --type api`
2. Set in `.env`: `API_TOKEN=generated-value`
3. Use in requests: `Authorization: Bearer <token>`

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
  http://localhost:9000/manual/switch \
  -d '{"track_id": "track_123"}'
```

---

## Advanced Configuration

### Custom FFmpeg Filters

Modify `metadata_watcher/ffmpeg_manager.py` to add custom video filters:

```python
# Example: Add watermark
filters = [
    f"fade=t=in:st=0:d={fade_duration}",
    f"scale={resolution}",
    "format=yuv420p",
    "drawtext=text='My Radio':x=10:y=10:fontsize=24:fontcolor=white"
]
```

### Multi-Instance Deployment

For load balancing or redundancy:

**docker-compose.scale.yml**:
```yaml
services:
  metadata-watcher:
    deploy:
      replicas: 3
    environment:
      - INSTANCE_ID=${HOSTNAME}
```

**Run**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale metadata-watcher=3
```

**Note**: Requires load balancer (nginx, HAProxy) for webhook distribution.

---

## Configuration Best Practices

### 1. Environment-Specific Configs

Use different `.env` files for each environment:

```bash
# Development
cp env.example .env.development

# Production
cp env.example .env.production
```

**Load**:
```bash
docker-compose --env-file .env.production up -d
```

### 2. Secrets Management

**Never commit `.env` to version control**:

```bash
# .gitignore
.env
.env.*
secrets/
```

**Use Docker secrets for production**:
```yaml
services:
  metadata-watcher:
    secrets:
      - postgres_password
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
```

### 3. Validate Configuration

Before deploying:

```bash
# Validate docker-compose.yml
docker-compose config

# Test with dry run
docker-compose up --no-start
```

### 4. Document Custom Changes

Keep a `CUSTOM_CONFIG.md` file for any deviations from defaults:

```markdown
# Custom Configuration Notes

## Changed Settings
- Increased `MAX_RESTART_ATTEMPTS` to 5 (from 3)
- Using custom FFmpeg filter for watermark
- Multi-platform streaming enabled (YouTube + Twitch)

## Reasons
...
```

---

## Troubleshooting Configuration

### Issue: Service Won't Start

**Check**:
```bash
# Validate environment variables
docker-compose config | grep environment

# Check for missing required variables
grep -E '^[A-Z_]+=\s*$' .env
```

### Issue: FFmpeg Encoding Errors

**Check**:
```bash
# Verify FFmpeg parameters
docker-compose exec metadata-watcher ffmpeg -h encoder=h264_nvenc

# Test encoding
docker-compose exec metadata-watcher ffmpeg \
  -i /srv/loops/default.mp4 \
  -c:v ${VIDEO_ENCODER} -b:v ${VIDEO_BITRATE} \
  -f null -
```

---

## Configuration Checklist

Before going live:

- [ ] `.env` file created from `env.example`
- [ ] All critical variables set (YouTube key, AzuraCast URL, passwords)
- [ ] Strong passwords and tokens generated
- [ ] FFmpeg encoding settings match hardware capabilities
- [ ] Upload bandwidth sufficient for selected bitrate
- [ ] Default video loop exists at `${DEFAULT_LOOP}`
- [ ] Webhook secret configured in both `.env` and AzuraCast
- [ ] Firewall rules configured
- [ ] Docker Compose validates without errors
- [ ] Health check endpoints respond correctly

---

## Reference Links

- **Environment Variables**: [.env.example](../env.example)
- **Docker Compose**: [docker-compose.yml](../docker-compose.yml)
- **FFmpeg Documentation**: https://ffmpeg.org/documentation.html
- **Prometheus Config**: https://prometheus.io/docs/prometheus/latest/configuration/

---

**Document Version**: 1.0  
**Last Updated**: November 5, 2025  
**Maintained By**: SHARD-12 (Documentation)



