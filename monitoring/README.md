# Monitoring & Health Checks Module

**Version:** 1.0.0  
**Shard:** SHARD-7  
**Status:** Complete ✅

## Overview

The monitoring module provides comprehensive health monitoring, Prometheus metrics export, FFmpeg process monitoring, and automatic recovery capabilities for the 24/7 radio stream system.

## Features

- 📊 **Prometheus Metrics Export** - Real-time metrics for monitoring stream health
- 🏥 **Health Check Endpoints** - Liveness, readiness, and detailed health checks
- 🔍 **FFmpeg Process Monitoring** - CPU, memory, and performance tracking
- 🔄 **Auto-Recovery System** - Automatic restart and failure recovery
- 📈 **Grafana Dashboard** - Pre-built visualization dashboard
- 🚨 **Alerting Rules** - Prometheus alert configurations

## Architecture

```
monitoring/
├── __init__.py              # Module exports
├── config.py                # Configuration management
├── metrics.py               # Prometheus metrics exporter
├── health_checks.py         # Health check logic
├── ffmpeg_monitor.py        # FFmpeg process monitoring
├── auto_recovery.py         # Auto-recovery system
├── requirements.txt         # Module dependencies
├── alerting_rules.yml       # Prometheus alert rules
└── tests/                   # Unit tests (97% coverage)
```

## Installation

```bash
# Install dependencies
pip install -r monitoring/requirements.txt

# Or install individually
pip install prometheus-client psutil aiohttp python-dotenv
```

## Quick Start

### 1. Basic Usage

```python
from monitoring import MetricsExporter, HealthChecker, FFmpegMonitor, AutoRecovery
from monitoring.config import get_config

# Initialize configuration
config = get_config()

# Create monitoring components
metrics = MetricsExporter()
health_checker = HealthChecker(config)
ffmpeg_monitor = FFmpegMonitor(config)
auto_recovery = AutoRecovery(config)

# Record metrics
metrics.record_track_played()
metrics.update_ffmpeg_status("running")
metrics.update_stream_uptime(300.0)

# Perform health check
result = await health_checker.check_liveness()
print(f"Health: {result.status}")

# Monitor FFmpeg process
health_report = await ffmpeg_monitor.check_process_health(
    pid=12345,
    uptime_seconds=300.0,
    process_state="running"
)

# Setup auto-recovery callbacks
async def restart_ffmpeg():
    # Your restart logic here
    pass

auto_recovery.set_restart_callback(restart_ffmpeg)
await auto_recovery.handle_ffmpeg_crash("Process crashed")
```

### 2. Prometheus Metrics Endpoint

```python
from fastapi import FastAPI
from monitoring import MetricsExporter

app = FastAPI()
metrics = MetricsExporter()

@app.get("/metrics")
def prometheus_metrics():
    return Response(
        content=metrics.get_metrics(),
        media_type="text/plain; version=0.0.4"
    )
```

### 3. Health Check Endpoints

```python
from fastapi import FastAPI
from monitoring import HealthChecker
from monitoring.config import get_config

app = FastAPI()
config = get_config()
health_checker = HealthChecker(config)

@app.get("/health/liveness")
async def liveness():
    result = await health_checker.check_liveness()
    return health_checker.get_health_dict(result)

@app.get("/health/readiness")
async def readiness():
    ffmpeg_running = True  # Check your FFmpeg status
    result = await health_checker.check_readiness(ffmpeg_running)
    return health_checker.get_health_dict(result)

@app.get("/health/detailed")
async def detailed():
    ffmpeg_status = {
        "state": "running",
        "pid": 12345,
        "uptime_seconds": 300
    }
    result = await health_checker.check_detailed(ffmpeg_status)
    return health_checker.get_health_dict(result)
```

## Configuration

All configuration is managed via environment variables:

```bash
# Metrics
METRICS_PORT=9090
METRICS_PATH=/metrics

# Health checks
HEALTH_CHECK_INTERVAL=5.0
FFMPEG_CHECK_INTERVAL=1.0
STREAM_FREEZE_TIMEOUT=30.0

# Auto-recovery
ENABLE_AUTO_RECOVERY=true
MAX_RESTART_ATTEMPTS=3
RESTART_COOLDOWN=60.0
AUDIO_STREAM_RETRY_INTERVAL=30.0
AUDIO_STREAM_MAX_RETRIES=20

# Thresholds
CPU_THRESHOLD_PERCENT=90.0
MEMORY_THRESHOLD_MB=2048.0
BITRATE_DROP_THRESHOLD_PERCENT=50.0

# External services
AZURACAST_URL=http://azuracast:8000
AZURACAST_API_KEY=your-api-key
RTMP_ENDPOINT=rtmp://nginx-rtmp:1935/live/stream
```

## Prometheus Metrics

### Counters

- `radio_tracks_played_total` - Total number of tracks played
- `radio_ffmpeg_restarts_total` - Total FFmpeg process restarts
- `radio_errors_total{severity}` - Total errors by severity level

### Gauges

- `radio_ffmpeg_status{status}` - FFmpeg process status (running/stopped/crashed)
- `radio_stream_uptime_seconds` - Current stream uptime
- `radio_current_track_duration_seconds` - Current track playback duration
- `radio_ffmpeg_cpu_usage_percent` - FFmpeg CPU usage
- `radio_ffmpeg_memory_mb` - FFmpeg memory usage
- `radio_audio_stream_available` - Audio stream availability (1/0)
- `radio_rtmp_connection_status` - RTMP connection status (1/0)

### Histograms

- `radio_track_switch_duration_seconds` - Track switch duration distribution

## Health Check Endpoints

### `/health/liveness`

Checks if the service is alive and responding.

**Response:**
```json
{
  "status": "healthy",
  "message": "Service is alive",
  "timestamp": "2025-11-05T10:00:00Z",
  "details": {"check": "liveness"}
}
```

### `/health/readiness`

Checks if the service is ready to serve traffic (FFmpeg running).

**Response:**
```json
{
  "status": "healthy",
  "message": "Service is ready",
  "timestamp": "2025-11-05T10:00:00Z",
  "details": {"ffmpeg_running": true}
}
```

### `/health/detailed`

Provides detailed status of all components.

**Response:**
```json
{
  "status": "healthy",
  "message": "All components healthy",
  "timestamp": "2025-11-05T10:00:00Z",
  "details": {
    "components": {
      "ffmpeg": {
        "status": "healthy",
        "state": "running",
        "pid": 12345,
        "uptime_seconds": 300
      },
      "azuracast": {
        "status": "healthy",
        "message": "AzuraCast is reachable"
      }
    }
  }
}
```

## Auto-Recovery

The auto-recovery system automatically handles common failure scenarios:

### FFmpeg Crash Recovery

```python
# Triggered automatically when FFmpeg crashes
action = await auto_recovery.handle_ffmpeg_crash("Error message")

# Actions:
# - RESTART_FFMPEG: Attempts to restart the process
# - ESCALATE_ALERT: Max retries reached, sends critical alert
# - NONE: Recovery disabled or in cooldown
```

### Audio Stream Retry

```python
# Triggered when audio stream becomes unavailable
action = await auto_recovery.handle_audio_stream_unavailable()

# Retries connection every 30s up to 20 times (10 minutes)
```

### RTMP Reconnection

```python
# Triggered when RTMP connection is lost
action = await auto_recovery.handle_rtmp_connection_lost()

# Restarts FFmpeg to re-establish connection
```

### Recovery Statistics

```python
# Get recovery statistics
stats = auto_recovery.get_recovery_stats()

# Returns:
{
  "restart_count": 2,
  "last_restart_time": "2025-11-05T10:00:00Z",
  "audio_retry_count": 5,
  "recent_attempts": 3,
  "auto_recovery_enabled": true
}

# Get recovery history
history = auto_recovery.get_recovery_history(limit=10)
```

## FFmpeg Monitoring

### Process Health Checks

```python
# Check FFmpeg process health
report = await ffmpeg_monitor.check_process_health(
    pid=12345,
    uptime_seconds=300.0,
    process_state="running"
)

# Report includes:
# - status: HEALTHY / WARNING / CRITICAL
# - cpu_percent: CPU usage
# - memory_mb: Memory usage in MB
# - warnings: List of issues detected
```

### Stream Freeze Detection

```python
# Detect frozen streams (no new frames)
is_frozen = await ffmpeg_monitor.check_stream_freeze(
    current_frame_count=9000
)

# Returns True if no new frames for > 30s
```

### Bitrate Drop Detection

```python
# Detect significant bitrate drops
has_dropped = await ffmpeg_monitor.check_bitrate_drop(
    current_bitrate_kbps=2500.0
)

# Returns True if bitrate drops > 50%
```

## Grafana Dashboard

A pre-built Grafana dashboard is available at `grafana/dashboards/radio_stream_dashboard.json`.

**Panels:**
- Stream Status (gauge)
- Stream Uptime (time series)
- Total Tracks Played (stat)
- FFmpeg CPU Usage (time series)
- FFmpeg Memory Usage (time series)
- Track Switch Duration (histogram)
- Error Rate (time series)
- FFmpeg Restarts (stat)
- Audio Stream Status (gauge)
- RTMP Connection Status (gauge)

**Import:**
1. Open Grafana
2. Go to Dashboards → Import
3. Upload `grafana/dashboards/radio_stream_dashboard.json`
4. Select Prometheus datasource
5. Import

## Prometheus Alerting

Alert rules are defined in `monitoring/alerting_rules.yml`.

**Configured Alerts:**
- `StreamDown` - Service unreachable for > 2 minutes
- `RTMPRelayDown` - RTMP relay down for > 1 minute
- `HighErrorRate` - Error rate > 10/sec for 5 minutes
- `FrequentFFmpegRestarts` - > 3 restarts in 10 minutes
- `DatabaseDown` - Database unreachable for > 2 minutes
- `NoTracksPlayed` - No tracks played in 30 minutes
- `LongRunningTrack` - Track playing > 15 minutes

## Testing

```bash
# Run all tests
pytest monitoring/tests/ -v

# Run with coverage
pytest monitoring/tests/ -v --cov=monitoring --cov-report=term-missing

# Current coverage: 97%
# All 64 tests passing ✅
```

## Integration with Other Modules

### SHARD-2 (Metadata Watcher)

```python
# In metadata_watcher/app.py
from monitoring import MetricsExporter, HealthChecker

metrics = MetricsExporter()
health_checker = HealthChecker(config)

@app.post("/webhook/azuracast")
async def webhook(payload):
    metrics.record_track_played()
    # ... handle webhook
```

### SHARD-4 (FFmpeg Manager)

```python
# In ffmpeg_manager/process_manager.py
from monitoring import FFmpegMonitor, AutoRecovery

monitor = FFmpegMonitor(config)
recovery = AutoRecovery(config)

# Monitor process health
report = await monitor.check_process_health(...)
metrics.update_from_ffmpeg_status(status)
```

## Troubleshooting

### Metrics not appearing in Prometheus

1. Check metrics endpoint is accessible: `curl http://localhost:9090/metrics`
2. Verify Prometheus scrape config in `monitoring/prometheus.yml`
3. Check Prometheus targets: http://localhost:9090/targets

### Health checks failing

1. Verify environment variables are set correctly
2. Check AzuraCast connectivity: `curl http://azuracast:8000/api/status`
3. Review logs for error messages

### Auto-recovery not working

1. Verify `ENABLE_AUTO_RECOVERY=true`
2. Check restart callback is configured
3. Review cooldown settings (may be blocking retries)
4. Check logs for recovery attempts

## Performance Considerations

- Metrics collection is lightweight (<1ms overhead)
- Health checks run asynchronously
- FFmpeg monitoring uses non-blocking I/O
- Auto-recovery has configurable cooldowns to prevent restart loops

## Security

- No sensitive data is exposed in metrics
- Health check endpoints can be restricted with authentication
- Configuration via environment variables (no hardcoded secrets)

## Future Enhancements

- Custom metric exporters for other systems
- Machine learning-based anomaly detection
- Predictive failure analysis
- Advanced recovery strategies

## API Reference

See inline docstrings for detailed API documentation:

```python
from monitoring import MetricsExporter
help(MetricsExporter)
```

## Contributing

1. Write tests for new features
2. Maintain >80% code coverage
3. Follow PEP 8 style guidelines
4. Update documentation

## License

Part of the 24/7 FFmpeg YouTube Radio Stream project.

## Support

For issues or questions:
- Check the troubleshooting section
- Review test cases for usage examples
- Consult `docs/MONITORING.md` for setup guide

---

**Last Updated:** November 5, 2025  
**Maintainer:** SHARD-7 Development Team



