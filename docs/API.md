# API Documentation

**24/7 FFmpeg YouTube Radio Stream - REST API Reference**

This document provides complete API documentation for the Metadata Watcher Service, including endpoint specifications, request/response formats, authentication, and examples.

## Table of Contents

1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication](#authentication)
4. [Endpoints](#endpoints)
5. [Request/Response Models](#requestresponse-models)
6. [Error Handling](#error-handling)
7. [Examples](#examples)
8. [Rate Limiting](#rate-limiting)

---

## Overview

The Metadata Watcher Service exposes a RESTful API built with FastAPI. It provides endpoints for:

- **Webhook Reception**: Receiving track change notifications from AzuraCast
- **Health Checks**: Monitoring service health and dependencies
- **Status Information**: Retrieving current stream and process information
- **Manual Control**: Manually triggering track switches for testing

### API Features

- **OpenAPI/Swagger**: Interactive documentation at `/docs`
- **ReDoc**: Alternative documentation at `/redoc`
- **JSON Responses**: All endpoints return JSON
- **Validation**: Request/response validation with Pydantic
- **Async**: Fully asynchronous for better performance

---

## Base URL

Default base URL:

```
http://localhost:9000
```

Production (with domain):

```
https://stream.yourdomain.com
```

### OpenAPI Documentation

Interactive API documentation is automatically available at:

- **Swagger UI**: `http://localhost:9000/docs`
- **ReDoc**: `http://localhost:9000/redoc`
- **OpenAPI JSON**: `http://localhost:9000/openapi.json`

---

## Authentication

The API uses two authentication mechanisms depending on the endpoint.

### 1. Webhook Secret Authentication

Used for: `/webhook/azuracast`

**Method**: Custom header `X-Webhook-Secret`

**Configuration**:
```bash
# In .env
WEBHOOK_SECRET=your-secret-here
```

**Request Header**:
```http
X-Webhook-Secret: your-secret-here
```

**Example**:
```bash
curl -X POST http://localhost:9000/webhook/azuracast \
  -H "X-Webhook-Secret: abc123..." \
  -H "Content-Type: application/json" \
  -d '{"song": {...}, "station": {...}}'
```

### 2. Bearer Token Authentication

Used for: `/manual/switch`

**Method**: HTTP Bearer token in Authorization header

**Configuration**:
```bash
# In .env
API_TOKEN=your-token-here
```

**Request Header**:
```http
Authorization: Bearer your-token-here
```

**Example**:
```bash
curl -X POST http://localhost:9000/manual/switch \
  -H "Authorization: Bearer xyz789..." \
  -H "Content-Type: application/json" \
  -d '{"artist": "Artist", "title": "Title"}'
```

### Authentication Errors

**401 Unauthorized**: Missing or invalid credentials

```json
{
  "detail": "Invalid webhook secret"
}
```

---

## Endpoints

### 1. Root Endpoint

Get service information and available endpoints.

#### `GET /`

**Authentication**: None

**Response**: `200 OK`

```json
{
  "service": "metadata-watcher",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "webhook": "/webhook/azuracast",
    "health": "/health",
    "status": "/status",
    "manual_switch": "/manual/switch"
  }
}
```

**Example**:
```bash
curl http://localhost:9000/
```

---

### 2. AzuraCast Webhook

Receive track change notifications from AzuraCast.

#### `POST /webhook/azuracast`

**Authentication**: Webhook secret (header: `X-Webhook-Secret`)

**Request Body**:

```json
{
  "song": {
    "id": "unique-song-id",
    "artist": "Artist Name",
    "title": "Song Title",
    "album": "Album Name",
    "duration": 180
  },
  "station": {
    "id": "station-id",
    "name": "Station Name"
  }
}
```

**Request Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `song.id` | string | Yes | Unique song identifier from AzuraCast |
| `song.artist` | string | Yes | Artist name |
| `song.title` | string | Yes | Song title |
| `song.album` | string | No | Album name |
| `song.duration` | integer | No | Song duration in seconds |
| `station.id` | string | Yes | Station identifier |
| `station.name` | string | Yes | Station name |

**Response**: `200 OK`

```json
{
  "status": "success",
  "message": "Track switched successfully",
  "track": {
    "artist": "Artist Name",
    "title": "Song Title",
    "loop": "/srv/loops/tracks/track_123.mp4"
  }
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or missing webhook secret
- `422 Unprocessable Entity`: Invalid request payload
- `500 Internal Server Error`: Failed to process track switch

**Example**:

```bash
curl -X POST http://localhost:9000/webhook/azuracast \
  -H "X-Webhook-Secret: your-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "song": {
      "id": "abc123",
      "artist": "Test Artist",
      "title": "Test Song",
      "album": "Test Album",
      "duration": 210
    },
    "station": {
      "id": "1",
      "name": "My Radio"
    }
  }'
```

**Response**:
```json
{
  "status": "success",
  "message": "Track switched successfully",
  "track": {
    "artist": "Test Artist",
    "title": "Test Song",
    "loop": "/srv/loops/tracks/test_artist_test_song.mp4"
  }
}
```

---

### 3. Health Check

Check service health and dependency status.

#### `GET /health`

**Authentication**: None

**Response**: `200 OK`

```json
{
  "status": "healthy",
  "service": "metadata-watcher",
  "timestamp": "2025-11-05T10:30:00.123456",
  "azuracast_reachable": true,
  "ffmpeg_status": "running"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall health: `healthy` or `degraded` |
| `service` | string | Service name |
| `timestamp` | string | Current timestamp (ISO 8601) |
| `azuracast_reachable` | boolean | Whether AzuraCast API is accessible |
| `ffmpeg_status` | string | FFmpeg process status: `running`, `stopped`, `crashed` |

**Health Status Logic**:

- `healthy`: All dependencies reachable and FFmpeg running
- `degraded`: One or more issues detected (AzuraCast unreachable, FFmpeg stopped)

**Example**:

```bash
curl http://localhost:9000/health
```

**Healthy Response**:
```json
{
  "status": "healthy",
  "service": "metadata-watcher",
  "timestamp": "2025-11-05T12:00:00.000000",
  "azuracast_reachable": true,
  "ffmpeg_status": "running"
}
```

**Degraded Response**:
```json
{
  "status": "degraded",
  "service": "metadata-watcher",
  "timestamp": "2025-11-05T12:00:00.000000",
  "azuracast_reachable": false,
  "ffmpeg_status": "stopped"
}
```

**Use Cases**:

- **Kubernetes/Docker Health Checks**: Liveness probe
- **Load Balancer**: Health check endpoint
- **Monitoring**: Automated health monitoring

---

### 4. Detailed Status

Get comprehensive service and stream status.

#### `GET /status`

**Authentication**: None

**Response**: `200 OK`

```json
{
  "service": "metadata-watcher",
  "status": "running",
  "timestamp": "2025-11-05T10:30:00.123456",
  "current_track": {
    "track_key": "artist - title",
    "uptime_seconds": 125.5,
    "started_at": "2025-11-05T10:28:00.000000"
  },
  "ffmpeg_process": {
    "pid": 12345,
    "status": "running",
    "track_key": "artist - title",
    "uptime_seconds": 125.5,
    "started_at": "2025-11-05T10:28:00.000000",
    "restart_count": 0
  }
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `service` | string | Service name |
| `status` | string | FFmpeg status: `running`, `stopped`, `crashed` |
| `timestamp` | string | Current timestamp (ISO 8601) |
| `current_track` | object\|null | Current playing track info (null if stopped) |
| `current_track.track_key` | string | Normalized track identifier |
| `current_track.uptime_seconds` | float | Seconds since track started |
| `current_track.started_at` | string | Track start timestamp |
| `ffmpeg_process` | object\|null | FFmpeg process details (null if not running) |
| `ffmpeg_process.pid` | integer | Process ID |
| `ffmpeg_process.status` | string | Process status |
| `ffmpeg_process.restart_count` | integer | Number of auto-restarts |

**Example**:

```bash
curl http://localhost:9000/status
```

**Response (Stream Active)**:
```json
{
  "service": "metadata-watcher",
  "status": "running",
  "timestamp": "2025-11-05T14:30:15.987654",
  "current_track": {
    "track_key": "daft punk - around the world",
    "uptime_seconds": 45.2,
    "started_at": "2025-11-05T14:29:30.000000"
  },
  "ffmpeg_process": {
    "pid": 8472,
    "status": "running",
    "track_key": "daft punk - around the world",
    "uptime_seconds": 45.2,
    "started_at": "2025-11-05T14:29:30.000000",
    "restart_count": 0
  }
}
```

**Response (No Stream)**:
```json
{
  "service": "metadata-watcher",
  "status": "stopped",
  "timestamp": "2025-11-05T14:30:15.987654",
  "current_track": null,
  "ffmpeg_process": null
}
```

**Use Cases**:

- **Dashboard**: Display current playing track
- **Monitoring**: Track uptime and restarts
- **Debugging**: Check process status

---

### 5. Manual Track Switch

Manually trigger a track switch (for testing).

#### `POST /manual/switch`

**Authentication**: Bearer token (header: `Authorization: Bearer <token>`)

**Request Body**:

```json
{
  "artist": "Artist Name",
  "title": "Song Title",
  "song_id": "optional-song-id"
}
```

**Request Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artist` | string | Yes | Artist name |
| `title` | string | Yes | Song title |
| `song_id` | string | No | Optional AzuraCast song ID |

**Response**: `200 OK`

```json
{
  "status": "success",
  "message": "Manual track switch successful",
  "track": {
    "artist": "Artist Name",
    "title": "Song Title",
    "loop": "/srv/loops/tracks/track_123.mp4"
  }
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or missing API token
- `422 Unprocessable Entity`: Invalid request payload
- `500 Internal Server Error`: Failed to switch track

**Example**:

```bash
curl -X POST http://localhost:9000/manual/switch \
  -H "Authorization: Bearer your-api-token" \
  -H "Content-Type: application/json" \
  -d '{
    "artist": "Daft Punk",
    "title": "Around the World"
  }'
```

**Response**:
```json
{
  "status": "success",
  "message": "Manual track switch successful",
  "track": {
    "artist": "Daft Punk",
    "title": "Around the World",
    "loop": "/srv/loops/tracks/daft_punk_around_the_world.mp4"
  }
}
```

**Use Cases**:

- **Testing**: Test track switching without waiting for AzuraCast
- **Manual Override**: Force specific track for special broadcasts
- **Debugging**: Trigger switches to test behavior

---

### 6. Prometheus Metrics

Expose Prometheus-compatible metrics.

#### `GET /metrics`

**Authentication**: None

**Response**: `200 OK` (Prometheus text format)

```
# HELP radio_tracks_played_total Total number of tracks played
# TYPE radio_tracks_played_total counter
radio_tracks_played_total 142

# HELP radio_ffmpeg_restarts_total Total number of FFmpeg process restarts
# TYPE radio_ffmpeg_restarts_total counter
radio_ffmpeg_restarts_total 2

# HELP radio_stream_uptime_seconds Current stream uptime in seconds
# TYPE radio_stream_uptime_seconds gauge
radio_stream_uptime_seconds 3600.5

# HELP radio_ffmpeg_status FFmpeg process status (1=running, 0=stopped)
# TYPE radio_ffmpeg_status gauge
radio_ffmpeg_status{status="running"} 1

# HELP radio_track_switch_duration_seconds Track switch duration histogram
# TYPE radio_track_switch_duration_seconds histogram
radio_track_switch_duration_seconds_bucket{le="0.5"} 45
radio_track_switch_duration_seconds_bucket{le="1.0"} 98
radio_track_switch_duration_seconds_bucket{le="2.0"} 142
radio_track_switch_duration_seconds_sum 175.3
radio_track_switch_duration_seconds_count 142
```

**Metrics Provided**:

- **Counters**:
  - `radio_tracks_played_total`: Total tracks played
  - `radio_ffmpeg_restarts_total`: Total FFmpeg restarts
  - `radio_errors_total{severity}`: Total errors by severity

- **Gauges**:
  - `radio_ffmpeg_status{status}`: FFmpeg status (1=running, 0=stopped)
  - `radio_stream_uptime_seconds`: Current stream uptime
  - `radio_ffmpeg_cpu_usage_percent`: FFmpeg CPU usage
  - `radio_ffmpeg_memory_mb`: FFmpeg memory usage

- **Histograms**:
  - `radio_track_switch_duration_seconds`: Track switch duration

**Example**:

```bash
curl http://localhost:9000/metrics
```

**Use Cases**:

- **Prometheus**: Scrape metrics for monitoring
- **Grafana**: Create dashboards from metrics
- **Alerting**: Trigger alerts based on metrics

---

## Request/Response Models

### Pydantic Models

All request/response models are validated using Pydantic.

#### SongInfo

```python
{
  "id": str,          # AzuraCast song ID
  "artist": str,      # Artist name
  "title": str,       # Song title
  "album": str,       # Optional: Album name
  "duration": int     # Optional: Duration in seconds
}
```

#### StationInfo

```python
{
  "id": str,    # Station ID
  "name": str   # Station name
}
```

#### WebhookPayload

```python
{
  "song": SongInfo,
  "station": StationInfo
}
```

#### HealthResponse

```python
{
  "status": str,               # "healthy" or "degraded"
  "service": str,              # Service name
  "timestamp": str,            # ISO 8601 timestamp
  "azuracast_reachable": bool, # AzuraCast connectivity
  "ffmpeg_status": str         # FFmpeg status
}
```

#### StatusResponse

```python
{
  "service": str,           # Service name
  "status": str,            # Status
  "timestamp": str,         # ISO 8601 timestamp
  "current_track": dict,    # Current track info (nullable)
  "ffmpeg_process": dict    # FFmpeg process info (nullable)
}
```

#### ManualSwitchRequest

```python
{
  "artist": str,   # Artist name
  "title": str,    # Song title
  "song_id": str   # Optional: Song ID
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 401 | Unauthorized | Missing or invalid authentication |
| 422 | Unprocessable Entity | Invalid request payload |
| 500 | Internal Server Error | Server error during processing |

### Error Response Format

All errors return JSON with detail message:

```json
{
  "detail": "Error description"
}
```

### Common Errors

#### 401 Unauthorized

```json
{
  "detail": "Invalid webhook secret"
}
```

**Cause**: Missing or incorrect `X-Webhook-Secret` header

**Solution**: Verify webhook secret matches `.env` configuration

---

#### 422 Unprocessable Entity

```json
{
  "detail": [
    {
      "loc": ["body", "song", "artist"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Cause**: Missing required field in request body

**Solution**: Include all required fields in request

---

#### 500 Internal Server Error

```json
{
  "detail": "Internal error: Failed to spawn FFmpeg process"
}
```

**Cause**: Server error during request processing

**Solution**: Check logs for detailed error information

---

## Examples

### Python Client

```python
import requests

# Configuration
BASE_URL = "http://localhost:9000"
WEBHOOK_SECRET = "your-webhook-secret"
API_TOKEN = "your-api-token"

# Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# Webhook (simulated from AzuraCast)
payload = {
    "song": {
        "id": "123",
        "artist": "Daft Punk",
        "title": "One More Time",
        "album": "Discovery",
        "duration": 320
    },
    "station": {
        "id": "1",
        "name": "My Radio"
    }
}
headers = {"X-Webhook-Secret": WEBHOOK_SECRET}
response = requests.post(
    f"{BASE_URL}/webhook/azuracast",
    json=payload,
    headers=headers
)
print(response.json())

# Manual track switch
payload = {
    "artist": "Justice",
    "title": "D.A.N.C.E."
}
headers = {"Authorization": f"Bearer {API_TOKEN}"}
response = requests.post(
    f"{BASE_URL}/manual/switch",
    json=payload,
    headers=headers
)
print(response.json())
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:9000';
const WEBHOOK_SECRET = 'your-webhook-secret';
const API_TOKEN = 'your-api-token';

// Health check
async function checkHealth() {
  const response = await axios.get(`${BASE_URL}/health`);
  console.log(response.data);
}

// Send webhook
async function sendWebhook() {
  const payload = {
    song: {
      id: '123',
      artist: 'Daft Punk',
      title: 'One More Time',
      album: 'Discovery',
      duration: 320
    },
    station: {
      id: '1',
      name: 'My Radio'
    }
  };
  
  const response = await axios.post(
    `${BASE_URL}/webhook/azuracast`,
    payload,
    {
      headers: {
        'X-Webhook-Secret': WEBHOOK_SECRET
      }
    }
  );
  console.log(response.data);
}

// Manual switch
async function manualSwitch() {
  const payload = {
    artist: 'Justice',
    title: 'D.A.N.C.E.'
  };
  
  const response = await axios.post(
    `${BASE_URL}/manual/switch`,
    payload,
    {
      headers: {
        'Authorization': `Bearer ${API_TOKEN}`
      }
    }
  );
  console.log(response.data);
}

checkHealth();
```

### cURL Examples

```bash
# Health check
curl http://localhost:9000/health | jq

# Status
curl http://localhost:9000/status | jq

# Webhook
curl -X POST http://localhost:9000/webhook/azuracast \
  -H "X-Webhook-Secret: your-secret" \
  -H "Content-Type: application/json" \
  -d @webhook_payload.json

# Manual switch
curl -X POST http://localhost:9000/manual/switch \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"artist":"Artist","title":"Title"}'

# Metrics
curl http://localhost:9000/metrics
```

---

## Rate Limiting

Rate limiting is configured via environment variables:

```bash
WEBHOOK_RATE_LIMIT=10        # Max 10 webhook requests per minute
API_RATE_LIMIT=60            # Max 60 API requests per minute
```

**Rate Limit Exceeded Response**: `429 Too Many Requests`

```json
{
  "detail": "Rate limit exceeded. Retry after 30 seconds.",
  "retry_after": 30
}
```

**Headers**:
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1699200000
Retry-After: 30
```

---

## Best Practices

### 1. Always Use HTTPS in Production

Never send authentication tokens over HTTP in production.

```bash
# Bad (development only)
curl http://example.com/manual/switch -H "Authorization: Bearer token"

# Good (production)
curl https://example.com/manual/switch -H "Authorization: Bearer token"
```

### 2. Handle Errors Gracefully

Always check status codes and handle errors:

```python
try:
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()
except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
except requests.exceptions.ConnectionError:
    print("Connection failed")
```

### 3. Implement Retry Logic

For webhooks, implement exponential backoff:

```python
import time

def send_with_retry(url, payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

### 4. Monitor API Performance

Track response times and error rates:

```python
import time

start = time.time()
response = requests.get(f"{BASE_URL}/health")
duration = time.time() - start

print(f"Response time: {duration:.2f}s")
```

---

## OpenAPI Specification

Full OpenAPI 3.0 specification is available at:

```
http://localhost:9000/openapi.json
```

Can be imported into:
- Postman
- Insomnia
- Swagger Editor
- API testing tools

---

**Document Version**: 1.0  
**Last Updated**: November 5, 2025  
**Maintained By**: SHARD-12 (Documentation)



