# Failover and Auto-Recovery Tests

This directory contains tests that verify the system's ability to automatically recover from various failure scenarios.

## Overview

According to SHARD-11 specifications, the system must:
- Auto-recover from FFmpeg crashes within 5 seconds
- Handle all failure scenarios gracefully
- Maintain <0.1% downtime over 24 hours
- Never crash due to external service failures

## Test Categories

### 1. FFmpeg Recovery Tests (`test_ffmpeg_recovery.py`)

Tests FFmpeg process-level failures:
- FFmpeg crash triggers automatic restart
- Restart limit (max 3 retries per track)
- Frozen stream detection (no frames for 30s)
- Zombie process cleanup
- Graceful overlap timing

### 2. Service Recovery Tests (`test_service_recovery.py`)

Tests Docker service and network failures:
- PostgreSQL container restart recovery
- nginx-rtmp container restart recovery
- Prometheus unavailability handling
- Network isolation scenarios
- Cascading failures
- Disaster recovery

## Running Failover Tests

### Prerequisites

1. Docker and Docker Compose running
2. Test environment set up:
```bash
docker-compose -f docker-compose.test.yml up -d
```

### Run All Failover Tests

```bash
pytest tests/failover/ -v
```

### Run Specific Test Categories

```bash
# FFmpeg recovery tests only
pytest tests/failover/test_ffmpeg_recovery.py -v

# Service recovery tests only
pytest tests/failover/test_service_recovery.py -v
```

### Run with Markers

```bash
# Integration tests only (require Docker)
pytest tests/failover/ -v -m integration

# Slow tests only (long-running)
pytest tests/failover/ -v -m slow

# Skip slow tests
pytest tests/failover/ -v -m "not slow"
```

## Test Scenarios

### FFmpeg Failures

| Scenario | Expected Recovery | Test |
|----------|------------------|------|
| FFmpeg crashes | Auto-restart within 5s | ✓ |
| Repeated crashes | Stop after 3 retries | ✓ |
| Stream frozen | Detect within 30s | ✓ |
| Process zombies | Clean up properly | ✓ |

### Service Failures

| Scenario | Expected Recovery | Test |
|----------|------------------|------|
| PostgreSQL restart | Reconnect automatically | ✓ |
| nginx-rtmp restart | Reconnect RTMP stream | ✓ |
| AzuraCast down | Use last known track | ✓ |
| YouTube unreachable | Buffer locally | ✓ |

### Network Failures

| Scenario | Expected Recovery | Test |
|----------|------------------|------|
| Audio stream down | Retry every 30s | ✓ |
| RTMP connection lost | Immediate alert | ✓ |
| Discord webhook timeout | Don't block app | ✓ |

### Error Scenarios

| Scenario | Expected Recovery | Test |
|----------|------------------|------|
| Missing loop file | Use default loop | ✓ |
| Corrupt video file | Use default loop | ✓ |
| Invalid webhook | Return 422, continue | ✓ |
| Encoder failure | Fallback to x264 | ✓ |

## Manual Failover Testing

For manual testing of real Docker services:

### 1. Test Database Restart

```bash
# Restart postgres container
docker-compose restart postgres

# Watch logs
docker-compose logs -f metadata-watcher

# Verify recovery
curl http://localhost:9000/health
```

### 2. Test nginx-rtmp Restart

```bash
# Restart nginx-rtmp
docker-compose restart nginx-rtmp

# Watch FFmpeg reconnect
docker-compose logs -f metadata-watcher
```

### 3. Test FFmpeg Crash

```bash
# Kill FFmpeg process
docker-compose exec metadata-watcher pkill -9 ffmpeg

# Watch auto-restart
docker-compose logs -f metadata-watcher
```

### 4. Test Network Partition

```bash
# Disconnect container from network
docker network disconnect liveradio_default metadata-watcher

# Wait 30 seconds

# Reconnect
docker network connect liveradio_default metadata-watcher
```

## Success Criteria

All failover tests must pass with the following criteria:

- **Recovery Time**: <5 seconds for FFmpeg crashes
- **Retry Logic**: Proper exponential backoff
- **Resource Cleanup**: No process/memory leaks
- **Graceful Degradation**: Core functionality works with degraded features
- **Alerting**: Critical failures trigger alerts
- **Logging**: All failures logged with context

## Monitoring During Tests

Watch these metrics during failover tests:

```bash
# System resources
docker stats

# Application logs
docker-compose logs -f metadata-watcher

# Prometheus metrics
curl http://localhost:9090/metrics | grep radio_

# Health status
watch -n 1 'curl -s http://localhost:9000/health | jq'
```

## Troubleshooting

### Tests Fail Due to Timing

Some tests depend on timing. If tests fail due to timing issues:
1. Increase timeouts in test fixtures
2. Check system load (high load can slow recovery)
3. Verify Docker resources are sufficient

### Docker Services Not Available

If Docker-dependent tests are skipped:
```bash
# Verify Docker is running
docker ps

# Start test environment
docker-compose -f docker-compose.test.yml up -d
```

### Tests Hang

If tests hang:
1. Check for deadlocks in process cleanup
2. Verify timeouts are set on all external calls
3. Use pytest-timeout to enforce test timeouts:
```bash
pytest tests/failover/ -v --timeout=300
```

## Adding New Failover Tests

When adding new failover tests:

1. Identify the failure scenario
2. Define expected recovery behavior
3. Write test that simulates failure
4. Verify recovery within expected time
5. Check for resource leaks
6. Document in this README

Example template:

```python
@pytest.mark.integration
def test_new_failure_scenario(self):
    """Test recovery from new failure scenario."""
    # 1. Setup initial state
    
    # 2. Simulate failure
    
    # 3. Verify recovery happens
    
    # 4. Check recovery time
    
    # 5. Verify no resource leaks
    
    # 6. Assert success
    assert recovered, "Failed to recover from scenario"
```



