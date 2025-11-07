# Monitoring Setup Guide

Complete guide for setting up monitoring, metrics, and alerting for the 24/7 Radio Stream system.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Prometheus Setup](#prometheus-setup)
- [Grafana Setup](#grafana-setup)
- [Alert Manager Setup](#alert-manager-setup)
- [Integration with Services](#integration-with-services)
- [Health Checks](#health-checks)
- [Auto-Recovery](#auto-recovery)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Prerequisites

- Docker and Docker Compose installed
- Prometheus v2.40+
- Grafana v8.0+
- Python 3.11+ with virtual environment

## Prometheus Setup

### 1. Install Prometheus

Using Docker Compose (recommended):

```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: radio-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alerting_rules.yml:/etc/prometheus/alerting_rules.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    networks:
      - radio-network
    restart: unless-stopped

volumes:
  prometheus-data:

networks:
  radio-network:
    driver: bridge
```

### 2. Configure Prometheus

The configuration file `monitoring/prometheus.yml` includes:

- Scrape configs for all services
- Alert rules file
- External labels for environment identification

Key scrape targets:
- `metadata-watcher:9000/metrics` - Main application metrics
- `nginx-rtmp:8080/stat` - RTMP statistics
- `prometheus:9090` - Self-monitoring

### 3. Verify Prometheus

```bash
# Start Prometheus
docker-compose up -d prometheus

# Check Prometheus is running
curl http://localhost:9090/-/healthy

# Verify targets
curl http://localhost:9090/api/v1/targets

# Query metrics
curl 'http://localhost:9090/api/v1/query?query=radio_tracks_played_total'
```

## Grafana Setup

### 1. Install Grafana

```yaml
# docker-compose.yml
services:
  grafana:
    image: grafana/grafana:latest
    container_name: radio-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=changeme
      - GF_INSTALL_PLUGINS=
    networks:
      - radio-network
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  grafana-data:
```

### 2. Configure Prometheus Datasource

Create `grafana/datasources/prometheus.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### 3. Import Dashboard

**Option A: Automatic (via Docker volume)**

```yaml
# grafana/dashboards/dashboard.yml
apiVersion: 1

providers:
  - name: 'Radio Stream'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

Copy `grafana/dashboards/radio_stream_dashboard.json` to the dashboards folder.

**Option B: Manual Import**

1. Open Grafana: http://localhost:3000
2. Login (default: admin/changeme)
3. Go to Dashboards → Import
4. Upload `grafana/dashboards/radio_stream_dashboard.json`
5. Select "Prometheus" datasource
6. Click Import

### 4. Verify Grafana

```bash
# Check Grafana is running
curl http://localhost:3000/api/health

# List datasources
curl -u admin:changeme http://localhost:3000/api/datasources
```

## Alert Manager Setup

### 1. Install Alert Manager

```yaml
# docker-compose.yml
services:
  alertmanager:
    image: prom/alertmanager:latest
    container_name: radio-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager-data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    networks:
      - radio-network
    restart: unless-stopped

volumes:
  alertmanager-data:
```

### 2. Configure Alert Manager

Create `monitoring/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'discord-webhook'
  
  routes:
    - match:
        severity: critical
      receiver: 'discord-webhook'
      continue: true

receivers:
  - name: 'discord-webhook'
    webhook_configs:
      - url: 'http://metadata-watcher:9000/alerts/webhook'
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname']
```

### 3. Update Prometheus Config

Uncomment Alert Manager in `monitoring/prometheus.yml`:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### 4. Verify Alerts

```bash
# Check alert rules loaded
curl http://localhost:9090/api/v1/rules

# Check active alerts
curl http://localhost:9090/api/v1/alerts

# Test Alert Manager
curl http://localhost:9093/-/healthy
```

## Integration with Services

### Metadata Watcher Service

The metadata watcher service already exports metrics on port 9000.

**Verify metrics endpoint:**

```bash
curl http://localhost:9000/metrics
```

**Expected output:**

```
# HELP radio_tracks_played_total Total number of tracks played
# TYPE radio_tracks_played_total counter
radio_tracks_played_total 142

# HELP radio_ffmpeg_restarts_total Total number of FFmpeg process restarts
# TYPE radio_ffmpeg_restarts_total counter
radio_ffmpeg_restarts_total 2

# HELP radio_stream_uptime_seconds Current stream uptime in seconds
# TYPE radio_stream_uptime_seconds gauge
radio_stream_uptime_seconds 3600
...
```

### Adding Custom Metrics

In your application code:

```python
from monitoring import MetricsExporter

# Initialize metrics exporter
metrics = MetricsExporter()

# Record events
metrics.record_track_played()
metrics.record_ffmpeg_restart()
metrics.record_error(severity="warning")

# Update gauges
metrics.update_ffmpeg_status("running")
metrics.update_stream_uptime(3600.0)
metrics.update_ffmpeg_cpu(45.5)
metrics.update_ffmpeg_memory(512.0)

# Record histograms
metrics.record_track_switch_duration(1.5)
```

## Health Checks

### Kubernetes/Container Orchestration

If using Kubernetes or Docker health checks:

```yaml
# docker-compose.yml
services:
  metadata-watcher:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health/liveness"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Manual Health Checks

```bash
# Liveness probe
curl http://localhost:9000/health/liveness

# Readiness probe
curl http://localhost:9000/health/readiness

# Detailed health check
curl http://localhost:9000/health/detailed | jq
```

### Load Balancer Health Checks

Configure your load balancer to use `/health/readiness`:

- **Health check URL:** `/health/readiness`
- **Expected status:** 200 OK
- **Interval:** 30s
- **Timeout:** 5s
- **Healthy threshold:** 2
- **Unhealthy threshold:** 3

## Auto-Recovery

### Enable Auto-Recovery

Set environment variable:

```bash
ENABLE_AUTO_RECOVERY=true
```

### Configure Recovery Parameters

```bash
# Max FFmpeg restart attempts
MAX_RESTART_ATTEMPTS=3

# Cooldown between restarts (seconds)
RESTART_COOLDOWN=60.0

# Audio stream retry interval (seconds)
AUDIO_STREAM_RETRY_INTERVAL=30.0

# Max audio stream retries
AUDIO_STREAM_MAX_RETRIES=20
```

### Monitor Recovery Actions

Check recovery statistics:

```bash
curl http://localhost:9000/status | jq '.recovery_stats'
```

**Response:**

```json
{
  "restart_count": 2,
  "last_restart_time": "2025-11-05T10:30:00Z",
  "audio_retry_count": 5,
  "recent_attempts": 3,
  "auto_recovery_enabled": true
}
```

## Troubleshooting

### Prometheus Not Scraping Metrics

**Problem:** Targets showing as "DOWN" in Prometheus

**Solutions:**

1. Check service is running and port is accessible:
   ```bash
   docker-compose ps
   curl http://localhost:9000/metrics
   ```

2. Verify network connectivity:
   ```bash
   docker-compose exec prometheus ping metadata-watcher
   ```

3. Check Prometheus logs:
   ```bash
   docker-compose logs prometheus
   ```

4. Verify scrape config:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

### Grafana Dashboard Not Showing Data

**Problem:** Dashboard panels show "No Data"

**Solutions:**

1. Verify Prometheus datasource:
   ```bash
   # In Grafana UI: Configuration → Data Sources → Prometheus → Test
   ```

2. Check metric names match:
   ```bash
   # Query Prometheus directly
   curl 'http://localhost:9090/api/v1/query?query=radio_tracks_played_total'
   ```

3. Verify time range in dashboard

4. Check Prometheus is scraping:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

### Alerts Not Firing

**Problem:** Expected alerts not appearing

**Solutions:**

1. Check alert rules are loaded:
   ```bash
   curl http://localhost:9090/api/v1/rules | jq
   ```

2. Verify alert conditions are met:
   ```bash
   curl 'http://localhost:9090/api/v1/query?query=up{job="metadata-watcher"}'
   ```

3. Check Alert Manager is configured:
   ```bash
   curl http://localhost:9090/api/v1/alertmanagers
   ```

4. Review Alert Manager logs:
   ```bash
   docker-compose logs alertmanager
   ```

### High Memory Usage

**Problem:** Prometheus consuming too much memory

**Solutions:**

1. Reduce retention time:
   ```yaml
   command:
     - '--storage.tsdb.retention.time=15d'  # Reduced from 30d
   ```

2. Reduce scrape frequency:
   ```yaml
   scrape_configs:
     - job_name: 'metadata-watcher'
       scrape_interval: 30s  # Increased from 10s
   ```

3. Limit metric cardinality (avoid high-cardinality labels)

4. Monitor Prometheus metrics:
   ```bash
   curl 'http://localhost:9090/api/v1/query?query=prometheus_tsdb_storage_blocks_bytes'
   ```

## Best Practices

### 1. Metric Naming

- Use descriptive, hierarchical names: `radio_ffmpeg_cpu_usage_percent`
- Include units in name: `_seconds`, `_bytes`, `_percent`
- Use consistent prefixes: all metrics start with `radio_`

### 2. Label Usage

- Keep cardinality low (avoid user IDs, timestamps as labels)
- Use meaningful label names: `severity`, `status`, `service`
- Don't use labels for values that change frequently

### 3. Alert Design

- Set appropriate thresholds based on historical data
- Use `for` clause to avoid alert flapping
- Group related alerts
- Include actionable information in annotations

### 4. Dashboard Organization

- Group related panels together
- Use appropriate visualization types
- Set reasonable refresh intervals
- Add helpful descriptions to panels

### 5. Health Check Strategy

- Liveness: Check process is running
- Readiness: Check can serve traffic (dependencies ready)
- Detailed: Comprehensive status for debugging

### 6. Auto-Recovery

- Set reasonable cooldown periods to prevent restart loops
- Monitor recovery statistics
- Alert on repeated failures
- Log all recovery actions for debugging

### 7. Performance

- Keep scrape intervals reasonable (10-30s)
- Limit retention based on needs
- Monitor Prometheus resource usage
- Use recording rules for expensive queries

## Production Checklist

Before deploying to production:

- [ ] Prometheus is scraping all targets successfully
- [ ] Grafana dashboard displays correctly
- [ ] Alert rules are configured and tested
- [ ] Alert Manager is routing notifications
- [ ] Health checks are responding correctly
- [ ] Auto-recovery is tested and configured
- [ ] Metrics retention is appropriate
- [ ] Backups of Prometheus data are configured
- [ ] Access controls are in place (Grafana auth, Prometheus read-only)
- [ ] Documentation is updated
- [ ] Team is trained on monitoring tools
- [ ] Runbooks are created for common alerts

## Maintenance

### Regular Tasks

**Daily:**
- Check dashboard for anomalies
- Review active alerts

**Weekly:**
- Review auto-recovery statistics
- Check Prometheus disk usage
- Verify all targets are up

**Monthly:**
- Review alert thresholds
- Update dashboards based on feedback
- Check for Prometheus/Grafana updates

### Backup and Recovery

**Prometheus data:**
```bash
# Backup
docker-compose exec prometheus promtool tsdb snapshot /prometheus
docker cp radio-prometheus:/prometheus/snapshots/latest ./backups/

# Restore
docker cp ./backups/latest radio-prometheus:/prometheus/
docker-compose restart prometheus
```

**Grafana dashboards:**
```bash
# Export dashboard
curl -H "Authorization: Bearer <api-key>" \
  http://localhost:3000/api/dashboards/uid/<dashboard-uid> > dashboard-backup.json

# Import via UI or API
```

## Advanced Configuration

### Recording Rules

For expensive queries, create recording rules in `monitoring/recording_rules.yml`:

```yaml
groups:
  - name: radio_recording_rules
    interval: 30s
    rules:
      - record: radio:track_rate:5m
        expr: rate(radio_tracks_played_total[5m])
      
      - record: radio:error_rate:5m
        expr: rate(radio_errors_total[5m])
```

### Federation

For multi-datacenter setups:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'federate'
    scrape_interval: 15s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="metadata-watcher"}'
    static_configs:
      - targets:
          - 'prometheus-dc2:9090'
```

## Support

For issues or questions:
- Review this guide
- Check troubleshooting section
- Consult module README: `monitoring/README.md`
- Review test cases for usage examples

---

**Last Updated:** November 5, 2025  
**Version:** 1.0.0



