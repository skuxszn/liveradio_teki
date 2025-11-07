# Load Testing

This directory contains load tests for the 24/7 FFmpeg YouTube Radio Stream using Locust.

## Prerequisites

Install Locust:
```bash
pip install locust
```

Or use the project's requirements-dev.txt:
```bash
pip install -r requirements-dev.txt
```

## Running Load Tests

### Interactive Mode (Web UI)

Start the metadata watcher service, then run:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:9000
```

Then open http://localhost:8089 in your browser to configure and start the test.

### Headless Mode

Run a predefined test:

```bash
# 10 concurrent users, spawning 2 per second, running for 5 minutes
locust -f tests/load/locustfile.py \
    --host=http://localhost:9000 \
    --users 10 \
    --spawn-rate 2 \
    --run-time 5m \
    --headless
```

### Stress Test

Test rapid track changes:

```bash
# 50 concurrent users with rapid track changes
locust -f tests/load/locustfile.py \
    --host=http://localhost:9000 \
    --users 50 \
    --spawn-rate 5 \
    --run-time 10m \
    --headless
```

## Test Scenarios

### Normal Load Test

Uses `AzuraCastWebhookUser` which simulates:
- Track change webhooks (most common)
- Health checks
- Status checks
- Invalid webhook handling

### Stress Test

Uses `RapidTrackChangeUser` which simulates:
- Very rapid track changes (0.5-1s intervals)
- High load on FFmpeg process management

## Success Criteria

According to SHARD-11 specifications:

- **1000 track switches**: System should handle without crashes
- **24-hour stream**: Maintain <0.1% downtime
- **Response times**: Webhook endpoint <500ms p95
- **Error rate**: <1% of requests
- **FFmpeg stability**: No process leaks or memory issues

## Metrics to Monitor

While running load tests, monitor:

1. **Application Metrics**:
   - Response times (p50, p95, p99)
   - Request throughput (RPS)
   - Error rate
   - Failure rate

2. **System Metrics**:
   - CPU usage
   - Memory usage
   - FFmpeg process count
   - File descriptor count

3. **FFmpeg Metrics**:
   - Process restart count
   - Video frame rate
   - Audio sync issues
   - RTMP connection stability

## Example Output

```
Name                          # reqs  # fails  Avg  Min  Max  Median  req/s failures/s
Track Change Webhook          1000    0        245  120  890  230     10.2  0.00
Health Check                  200     0        45   25   120  40      2.0   0.00
Status Check                  100     0        89   55   250  85      1.0   0.00
Invalid Webhook               50      0        78   45   180  75      0.5   0.00
Aggregated                    1350    0        189  25   890  150     13.7  0.00
```

## Troubleshooting

### High Failure Rate

- Check if metadata_watcher service is running
- Verify webhook secret configuration
- Check database connection
- Review application logs

### High Response Times

- Check FFmpeg process count
- Monitor system resources (CPU/memory)
- Review database query performance
- Check RTMP relay status

### Memory Leaks

- Run extended test (24 hours)
- Monitor memory growth over time
- Check for orphaned FFmpeg processes
- Review process cleanup logic



