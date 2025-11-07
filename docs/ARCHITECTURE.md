# System Architecture

**24/7 FFmpeg YouTube Radio Stream - Architecture Documentation**

This document describes the overall system architecture, component interactions, data flows, and design decisions for the radio stream system.

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Network Architecture](#network-architecture)
5. [Database Schema](#database-schema)
6. [Process Lifecycle](#process-lifecycle)
7. [Monitoring & Observability](#monitoring--observability)
8. [Security Architecture](#security-architecture)
9. [Scalability & Performance](#scalability--performance)
10. [Design Decisions](#design-decisions)

---

## High-Level Overview

### System Purpose

The system creates a 24/7 YouTube live stream by:
1. Playing audio from AzuraCast radio automation
2. Overlaying different looping MP4 videos for each track
3. Automatically switching videos when tracks change
4. Streaming via RTMP to YouTube

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        24/7 Radio Stream System                      │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐          ┌──────────────────────────────────────────┐
│  AzuraCast   │  Webhook │        Metadata Watcher Service          │
│   (External) │─────────▶│  - FastAPI Web Server                    │
│              │          │  - Track Resolver                         │
│   Audio ─────┼─────────▶│  - FFmpeg Manager                        │
│   Stream     │   HTTP   │  - Metrics Exporter                      │
└──────────────┘          └──────┬───────────────────────────────────┘
                                 │
                                 │ spawns/manages
                                 ▼
                          ┌──────────────┐
                          │    FFmpeg    │
                          │   Process    │
                          │              │
                          │ Video Loop ◀─┼──── /srv/loops/
                          │   +          │
                          │ Audio Stream │
                          └──────┬───────┘
                                 │ RTMP
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      nginx-rtmp Relay                                │
│  - Receives RTMP stream from FFmpeg                                  │
│  - Buffers for stability                                             │
│  - Pushes to YouTube (and optionally other platforms)                │
└───────────┬─────────────────────────────────────────────────────────┘
            │ RTMP
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         YouTube Live                                  │
│  - Receives RTMP stream                                               │
│  - Transcodes to multiple qualities                                  │
│  - Distributes to viewers worldwide                                  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────┐          ┌──────────────┐        ┌──────────────────┐
│  PostgreSQL  │◀─────────│   Logging    │        │   Prometheus     │
│              │          │    Module    │        │   (Metrics)      │
│ - Mappings   │          │              │◀───────│                  │
│ - History    │          │ - Play logs  │ scrape │ - Uptime         │
│ - Errors     │          │ - Analytics  │        │ - Track counts   │
└──────────────┘          └──────────────┘        │ - Error rates    │
                                                   └──────────────────┘
```

### Key Components

1. **AzuraCast**: Radio automation, audio source, webhook sender
2. **Metadata Watcher**: Orchestration service, webhook receiver
3. **FFmpeg**: Video encoding and streaming
4. **nginx-rtmp**: RTMP relay/buffer to YouTube
5. **PostgreSQL**: Track mappings and analytics
6. **Prometheus**: Metrics collection and monitoring

---

## Component Architecture

### 1. Metadata Watcher Service

**Purpose**: Central orchestration service that receives track changes and manages FFmpeg processes.

**Components**:

```
metadata_watcher/
├── app.py                 # FastAPI application, HTTP endpoints
├── config.py              # Configuration management
├── ffmpeg_manager.py      # FFmpeg process lifecycle
├── track_resolver.py      # Track-to-video mapping resolution
└── requirements.txt       # Python dependencies
```

**Responsibilities**:
- Receive webhooks from AzuraCast
- Resolve track → video loop mapping
- Spawn/manage FFmpeg processes
- Monitor process health
- Export Prometheus metrics
- Provide health check endpoints

**Technology Stack**:
- **Language**: Python 3.11+
- **Framework**: FastAPI (async)
- **Process Management**: asyncio + subprocess
- **HTTP Client**: aiohttp
- **Validation**: Pydantic

**Key Interfaces**:
- **Input**: HTTP webhooks from AzuraCast
- **Output**: FFmpeg process commands
- **Storage**: PostgreSQL (track mappings)
- **Monitoring**: Prometheus metrics

---

### 2. FFmpeg Process

**Purpose**: Encode video loop + audio stream and output to RTMP.

**Process Flow**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FFmpeg Process                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Input 0: Video Loop (MP4)                                           │
│  ┌───────────────┐                                                   │
│  │ /srv/loops/   │                                                   │
│  │ track_123.mp4 │──┐                                                │
│  └───────────────┘  │                                                │
│                     │                                                │
│  Input 1: Live Audio Stream                ┌────────────────────┐   │
│  ┌───────────────────┐                     │  Video Filters     │   │
│  │ http://azuracast  │──┐                  │  - Fade in         │   │
│  │ :8000/radio       │  │                  │  - Scale           │   │
│  └───────────────────┘  │                  │  - Format (yuv420p)│   │
│                         │                  │  - FPS (30)        │   │
│                         ▼                  └──────────┬─────────┘   │
│                    ┌────────────┐                     │             │
│                    │   Decode   │                     │             │
│                    └─────┬──────┘                     │             │
│                          │                            │             │
│                          ▼                            ▼             │
│                    ┌──────────────────────────────────────┐         │
│                    │         Encode (libx264/NVENC)       │         │
│                    │  - Resolution: 1280x720 or 1920x1080 │         │
│                    │  - Bitrate: 3000k or 4500k           │         │
│                    │  - Preset: veryfast                  │         │
│                    └──────────────┬───────────────────────┘         │
│                                   │                                 │
│                                   ▼                                 │
│                    ┌──────────────────────────────┐                 │
│                    │    Mux (Video + Audio)       │                 │
│                    │    - FLV container           │                 │
│                    └──────────────┬───────────────┘                 │
│                                   │                                 │
│                                   ▼                                 │
│                    ┌──────────────────────────────┐                 │
│                    │    RTMP Output               │                 │
│                    │    rtmp://nginx-rtmp:1935    │                 │
│                    └──────────────────────────────┘                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Command Structure**:

```bash
ffmpeg -re \
  -stream_loop -1 -thread_queue_size 512 -i /srv/loops/track.mp4 \
  -thread_queue_size 512 -i http://azuracast:8000/radio \
  -map 0:v -map 1:a \
  -vf "fade=t=in:st=0:d=1,scale=1280:720,format=yuv420p,fps=30" \
  -c:v libx264 -preset veryfast -b:v 3000k -maxrate 3000k -bufsize 6000k \
  -g 50 -keyint_min 50 -sc_threshold 0 -pix_fmt yuv420p \
  -af "afade=t=in:ss=0:d=1" \
  -c:a aac -b:a 192k -ar 44100 -ac 2 \
  -f flv rtmp://nginx-rtmp:1935/live/stream
```

**Key Parameters**:
- `-re`: Read input at native framerate
- `-stream_loop -1`: Loop video indefinitely
- `-map 0:v -map 1:a`: Map video from input 0, audio from input 1
- `-vf`: Video filters (fade, scale, format)
- `-c:v libx264`: Video codec (or h264_nvenc for GPU)
- `-preset veryfast`: Encoding speed
- `-b:v 3000k`: Video bitrate
- `-f flv`: Output format (Flash Video for RTMP)

---

### 3. nginx-rtmp Relay

**Purpose**: Provide stable RTMP relay between FFmpeg and YouTube.

**Why It's Needed**:

1. **Buffering**: Smooths out temporary encoding hiccups
2. **Reconnection**: Handles YouTube connection issues gracefully
3. **Multi-Platform**: Easy to push to multiple streaming platforms
4. **Separation of Concerns**: FFmpeg doesn't need to handle YouTube protocol

**Configuration** (`nginx-rtmp/nginx.conf`):

```nginx
worker_processes auto;
rtmp_auto_push on;

events {
    worker_connections 1024;
}

rtmp {
    server {
        listen 1935;
        chunk_size 4096;

        application live {
            live on;
            record off;
            
            # Buffer settings
            interleave on;
            wait_key on;
            wait_video on;
            
            # Push to YouTube
            push rtmp://a.rtmp.youtube.com/live2/${YOUTUBE_STREAM_KEY};
        }
    }
}

http {
    server {
        listen 8080;
        
        location /health {
            return 200 "OK";
        }
        
        location /stat {
            rtmp_stat all;
        }
    }
}
```

**Features**:
- **Buffering**: 4KB chunk size for smooth streaming
- **Key Frame Wait**: Ensures stream starts on keyframe
- **Health Check**: HTTP endpoint at port 8080
- **Stats**: RTMP statistics at `/stat`

---

### 4. Track Mapper (Database)

**Purpose**: Map tracks to their corresponding video loops.

**Schema**:

```sql
CREATE TABLE track_mappings (
    id SERIAL PRIMARY KEY,
    track_key VARCHAR(512) UNIQUE NOT NULL,    -- "artist - title" (normalized)
    azuracast_song_id VARCHAR(128),
    loop_file_path VARCHAR(1024) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    play_count INTEGER DEFAULT 0
);

CREATE INDEX idx_track_key ON track_mappings(track_key);
CREATE INDEX idx_song_id ON track_mappings(azuracast_song_id);
```

**Resolution Logic**:

```
Input: artist="Daft Punk", title="One More Time", song_id="abc123"

1. Normalize: track_key = "daft punk - one more time"
2. Query: SELECT loop_file_path FROM track_mappings WHERE track_key = ?
3. If found: Return loop_file_path
4. Else: Try song_id lookup
5. Else: Return default loop (/srv/loops/default.mp4)
```

**Normalization Rules**:
- Convert to lowercase
- Replace multiple spaces with single space
- Remove special characters (keep alphanumeric, spaces, hyphens)
- Trim whitespace

---

### 5. Logging Module

**Purpose**: Track play history and errors for analytics.

**Schema**:

```sql
CREATE TABLE play_history (
    id SERIAL PRIMARY KEY,
    track_key VARCHAR(512) NOT NULL,
    artist VARCHAR(256),
    title VARCHAR(256),
    album VARCHAR(256),
    azuracast_song_id VARCHAR(128),
    loop_file_path VARCHAR(1024),
    started_at TIMESTAMP NOT NULL,
    duration_seconds INTEGER,
    ffmpeg_pid INTEGER,
    had_errors BOOLEAN DEFAULT FALSE,
    error_message TEXT
);

CREATE TABLE error_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    service VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    message TEXT NOT NULL,
    context JSONB
);

CREATE INDEX idx_play_history_started ON play_history(started_at DESC);
CREATE INDEX idx_error_log_timestamp ON error_log(timestamp DESC);
```

**Analytics Queries**:

```sql
-- Tracks per hour
SELECT date_trunc('hour', started_at) as hour, COUNT(*) 
FROM play_history 
GROUP BY hour 
ORDER BY hour DESC;

-- Most played tracks
SELECT track_key, COUNT(*) as plays 
FROM play_history 
GROUP BY track_key 
ORDER BY plays DESC 
LIMIT 10;

-- Error rate over time
SELECT date_trunc('hour', timestamp) as hour, 
       severity, 
       COUNT(*) 
FROM error_log 
GROUP BY hour, severity 
ORDER BY hour DESC;
```

---

### 6. Monitoring (Prometheus)

**Purpose**: Collect metrics for monitoring and alerting.

**Metrics Exposed**:

```python
# Counters
radio_tracks_played_total: Total tracks played
radio_ffmpeg_restarts_total: Total FFmpeg restarts
radio_errors_total{severity}: Total errors by severity

# Gauges
radio_ffmpeg_status{status}: FFmpeg status (1=running, 0=stopped)
radio_stream_uptime_seconds: Current stream uptime
radio_ffmpeg_cpu_usage_percent: FFmpeg CPU usage
radio_ffmpeg_memory_mb: FFmpeg memory usage

# Histograms
radio_track_switch_duration_seconds: Track switch duration
```

**Configuration** (`monitoring/prometheus.yml`):

```yaml
global:
  scrape_interval: 10s
  evaluation_interval: 10s

scrape_configs:
  - job_name: 'metadata-watcher'
    static_configs:
      - targets: ['metadata-watcher:9000']
  
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

rule_files:
  - 'alerting_rules.yml'
```

---

## Data Flow

### 1. Track Change Flow

```
┌──────────────┐
│  AzuraCast   │
│              │
│ Track Change │
│   Detected   │
└──────┬───────┘
       │
       │ HTTP POST /webhook/azuracast
       │ Headers: X-Webhook-Secret
       │ Body: {song: {...}, station: {...}}
       ▼
┌──────────────────────────────────┐
│  Metadata Watcher                │
│                                  │
│  1. Validate webhook secret      │
│  2. Parse payload                │
└──────┬───────────────────────────┘
       │
       │ Query track mapping
       ▼
┌──────────────────────────────────┐
│  Track Resolver                  │
│                                  │
│  1. Normalize track key          │
│  2. Query database               │
│  3. Return loop path             │
└──────┬───────────────────────────┘
       │
       │ loop_path
       ▼
┌──────────────────────────────────┐
│  FFmpeg Manager                  │
│                                  │
│  1. Build FFmpeg command         │
│  2. Spawn new process            │
│  3. Wait 2s (overlap)            │
│  4. Terminate old process        │
└──────┬───────────────────────────┘
       │
       │ FFmpeg command
       ▼
┌──────────────────────────────────┐
│  FFmpeg Process                  │
│                                  │
│  - Read video loop               │
│  - Fetch audio stream            │
│  - Encode to RTMP                │
└──────┬───────────────────────────┘
       │
       │ RTMP stream
       ▼
┌──────────────────────────────────┐
│  nginx-rtmp                      │
│                                  │
│  - Buffer stream                 │
│  - Push to YouTube               │
└──────────────────────────────────┘
```

**Timing**:
- Webhook → Response: <100ms
- FFmpeg spawn: ~500ms
- Track overlap: 2 seconds (configurable)
- Total switch duration: ~2.5 seconds

---

### 2. Audio Stream Flow

```
AzuraCast Radio Engine
       │
       │ Plays next song
       │
       ▼
Liquidsoap/Icecast Streaming
       │
       │ HTTP audio stream
       │ Format: MP3 or AAC
       │
       ▼
FFmpeg (Input 1)
       │
       │ Decodes audio
       │ Re-encodes to AAC 192k
       │
       ▼
RTMP Mux (with video)
       │
       ▼
YouTube Ingest
```

**Audio Characteristics**:
- **Input**: MP3 or AAC from AzuraCast
- **Decode**: FFmpeg converts to PCM
- **Encode**: AAC 192k, 44.1kHz, Stereo
- **Sync**: `-async 1` ensures A/V sync

---

### 3. Video Loop Flow

```
Video Loop Files (/srv/loops/)
       │
       │ track_123.mp4 (looping MP4)
       │
       ▼
FFmpeg (Input 0)
       │
       │ -stream_loop -1 (infinite loop)
       │ Decode H.264
       │
       ▼
Video Filters
       │
       │ - Fade in (1s)
       │ - Scale to target resolution
       │ - Format conversion (yuv420p)
       │ - Frame rate adjustment (30fps)
       │
       ▼
Encode (libx264 or NVENC)
       │
       │ - Bitrate: 3000k or 4500k
       │ - Keyframe every 50 frames
       │
       ▼
RTMP Mux (with audio)
```

---

## Network Architecture

### Docker Network Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Bridge Network                         │
│                    Subnet: 172.28.0.0/16                         │
│                                                                   │
│  ┌──────────────────┐     ┌──────────────────┐                  │
│  │ metadata-watcher │     │   nginx-rtmp     │                  │
│  │  172.28.0.2      │────▶│   172.28.0.3     │                  │
│  │  Port: 9000      │RTMP │   Port: 1935     │                  │
│  └────────┬─────────┘     └─────────┬────────┘                  │
│           │                          │                           │
│           │                          │                           │
│           ▼                          │                           │
│  ┌──────────────────┐               │                           │
│  │   PostgreSQL     │               │                           │
│  │   172.28.0.4     │               │                           │
│  │   Port: 5432     │               │                           │
│  └──────────────────┘               │                           │
│                                      │                           │
│  ┌──────────────────┐               │                           │
│  │   Prometheus     │               │                           │
│  │   172.28.0.5     │               │                           │
│  │   Port: 9090     │               │                           │
│  └──────────────────┘               │                           │
│                                      │                           │
└──────────────────────────────────────┼───────────────────────────┘
                                       │
                                       │ RTMP to internet
                                       ▼
                           ┌────────────────────────┐
                           │   YouTube RTMP Ingest  │
                           │ a.rtmp.youtube.com     │
                           └────────────────────────┘
```

### Exposed Ports

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| metadata-watcher | 9000 | 9000 | HTTP API, webhooks |
| nginx-rtmp | 1935 | 1935 | RTMP input (optional) |
| nginx-rtmp | 8080 | 8080 | HTTP stats |
| postgres | 5432 | 5432 | Database (admin access) |
| prometheus | 9090 | 9090 | Metrics UI |

**Production Security**:
- Only expose port 9000 publicly
- Restrict 5432, 9090 to internal network or VPN
- Use reverse proxy with SSL/TLS for 9000

---

## Database Schema

### Entity Relationship Diagram

```
┌──────────────────────────┐
│    track_mappings        │
├──────────────────────────┤
│ PK  id                   │
│ UNQ track_key            │
│     azuracast_song_id    │
│     loop_file_path       │
│     created_at           │
│     updated_at           │
│     play_count           │
└────────┬─────────────────┘
         │
         │ Referenced by
         │
         ▼
┌──────────────────────────┐
│     play_history         │
├──────────────────────────┤
│ PK  id                   │
│     track_key            │
│     artist               │
│     title                │
│     album                │
│     azuracast_song_id    │
│     loop_file_path       │
│     started_at           │
│     duration_seconds     │
│     ffmpeg_pid           │
│     had_errors           │
│     error_message        │
└──────────────────────────┘

┌──────────────────────────┐
│      error_log           │
├──────────────────────────┤
│ PK  id                   │
│     timestamp            │
│     service              │
│     severity             │
│     message              │
│     context (JSONB)      │
└──────────────────────────┘

┌──────────────────────────┐
│    default_config        │
├──────────────────────────┤
│ PK  key                  │
│     value                │
└──────────────────────────┘
```

---

## Process Lifecycle

### FFmpeg Process State Machine

```
┌─────────────┐
│   STOPPED   │ Initial state
└──────┬──────┘
       │
       │ Track change event
       ▼
┌─────────────┐
│  SPAWNING   │ Building command, starting process
└──────┬──────┘
       │
       │ Process started successfully
       ▼
┌─────────────┐
│   RUNNING   │◀───────┐ Auto-restart on crash
└──────┬──────┘        │ (up to MAX_RESTART_ATTEMPTS)
       │               │
       │ Process crash │
       ▼               │
┌─────────────┐        │
│  CRASHED    │────────┘
└──────┬──────┘
       │
       │ Max restarts exceeded
       ▼
┌─────────────┐
│   FAILED    │ Manual intervention required
└─────────────┘
```

### Track Switch Sequence

```
Time    Event
─────────────────────────────────────────────────────────────
T+0.0s  AzuraCast detects track change
T+0.1s  Webhook sent to metadata-watcher
T+0.2s  Webhook received, validated
T+0.3s  Track resolver queries database
T+0.4s  Video loop path resolved
T+0.5s  FFmpeg command built
T+0.6s  New FFmpeg process spawned
T+1.0s  New process starts streaming (with fade-in)
T+1.5s  Video transition visible on stream
T+2.5s  Old FFmpeg process terminated
T+3.0s  Cleanup complete, new track active
```

---

## Monitoring & Observability

### Logging Architecture

```
Application Logs
       │
       ├─ Console (stdout) ──▶ Docker logs
       │
       └─ File ──▶ /var/log/radio/app.log
              │
              └─ Rotation (100MB, 10 files)
```

**Log Levels**:
- **DEBUG**: Development debugging
- **INFO**: Normal operations (track changes, process spawns)
- **WARNING**: Recoverable issues (temp failures, retries)
- **ERROR**: Errors requiring attention
- **CRITICAL**: System failures

**Structured Logging** (JSON):

```json
{
  "timestamp": "2025-11-05T10:30:00.123456",
  "level": "INFO",
  "service": "metadata-watcher",
  "message": "Track switched",
  "context": {
    "artist": "Daft Punk",
    "title": "One More Time",
    "loop_path": "/srv/loops/tracks/track_123.mp4",
    "ffmpeg_pid": 12345
  }
}
```

---

## Security Architecture

### Defense in Depth

```
Layer 1: Network Security
├─ Firewall (UFW/iptables)
├─ Rate limiting (nginx/application)
└─ DDoS protection (Cloudflare/AWS Shield)

Layer 2: Application Security
├─ Webhook secret validation
├─ API token authentication
├─ Input validation (Pydantic)
└─ SQL injection prevention (ORM)

Layer 3: Container Security
├─ Non-root user (radiouser)
├─ Read-only filesystem
├─ Resource limits (CPU/memory)
└─ Security scanning (Trivy)

Layer 4: Data Security
├─ Secrets management (.env, Docker secrets)
├─ Database encryption at rest
├─ TLS in transit (HTTPS)
└─ License compliance tracking
```

---

## Scalability & Performance

### Performance Characteristics

**Throughput**:
- Webhook handling: 100+ requests/second
- Track switches: 3-5 per minute (typical)
- Stream encoding: 24/7 continuous

**Resource Usage** (720p):
- CPU: 30-40% (1 core)
- Memory: 200-300 MB (metadata-watcher)
- Memory: 150-250 MB (FFmpeg)
- Network: 3 Mbps upload (sustained)
- Disk I/O: Minimal (loop files cached)

**Bottlenecks**:
1. **CPU**: FFmpeg encoding (use NVENC for GPU)
2. **Upload Bandwidth**: Bitrate × 1.2 minimum
3. **Disk I/O**: If loops on HDD (use SSD)

### Horizontal Scaling

For multiple concurrent streams:

```
┌──────────────────┐
│  Load Balancer   │
│    (nginx)       │
└────────┬─────────┘
         │
         ├─────────────┬─────────────┐
         ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Watcher #1  │ │ Watcher #2  │ │ Watcher #3  │
│ Stream A    │ │ Stream B    │ │ Stream C    │
└─────────────┘ └─────────────┘ └─────────────┘
         │             │             │
         └─────────────┴─────────────┘
                       │
                       ▼
               ┌─────────────┐
               │ PostgreSQL  │
               │  (shared)   │
               └─────────────┘
```

---

## Design Decisions

### 1. Why spawn-per-track instead of persistent FFmpeg?

**Decision**: Spawn new FFmpeg process per track (Option B)

**Rationale**:
- Simpler implementation
- Easier to debug (clean slate per track)
- Better resource cleanup
- Lower risk of memory leaks
- Trade-off: 50-200ms gap vs. complexity

**Alternative**: Persistent FFmpeg with dual-input (Option A)
- Available for zero-gap transitions
- More complex, documented in ADVANCED_TRANSITIONS.md

---

### 2. Why nginx-rtmp relay instead of direct YouTube push?

**Decision**: Use nginx-rtmp as intermediate relay

**Rationale**:
- **Buffering**: Smooths encoding hiccups
- **Reconnection**: Handles YouTube issues gracefully
- **Multi-platform**: Easy to add Twitch, Facebook
- **Separation**: FFmpeg doesn't manage YouTube protocol

---

### 3. Why PostgreSQL instead of file-based mappings?

**Decision**: Use PostgreSQL database

**Rationale**:
- **Dynamic updates**: Change mappings without restart
- **Analytics**: Query play history easily
- **Scalability**: Handles thousands of tracks
- **Reliability**: ACID guarantees
- **Future-proof**: Can add complex queries

---

### 4. Why Python/FastAPI instead of Go/Rust?

**Decision**: Python 3.11+ with FastAPI

**Rationale**:
- **Rapid development**: Faster iteration
- **Rich ecosystem**: aiohttp, Pydantic, SQLAlchemy
- **Readable**: Easier maintenance
- **Async**: FastAPI provides async without complexity
- **Trade-off**: Slightly higher memory usage vs. speed of development

---

### 5. Why Docker Compose instead of Kubernetes?

**Decision**: Docker Compose for deployment

**Rationale**:
- **Simplicity**: Single-server deployment is common
- **Low overhead**: No k8s cluster needed
- **Easy to understand**: Lower learning curve
- **Cost**: Can run on $20/month VPS
- **Future**: Can migrate to Kubernetes if scaling needed

---

## Conclusion

The architecture is designed for:
- **Reliability**: 24/7 operation with auto-recovery
- **Simplicity**: Easy to deploy and maintain
- **Observability**: Comprehensive monitoring and logging
- **Flexibility**: Easy to extend and customize

For specific implementation details, see:
- [DEPLOYMENT.md](./DEPLOYMENT.md) - How to deploy
- [CONFIGURATION.md](./CONFIGURATION.md) - Configuration options
- [API.md](./API.md) - API endpoints
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues

---

**Document Version**: 1.0  
**Last Updated**: November 5, 2025  
**Maintained By**: SHARD-12 (Documentation)



