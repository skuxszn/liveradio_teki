# Metadata Watcher Service (SHARD-2)

**Status**: ✅ COMPLETE  
**Version**: 1.0.0  
**Dependencies**: SHARD-1 (Core Infrastructure)

## Overview

The Metadata Watcher Service is a FastAPI-based webhook receiver that orchestrates FFmpeg process lifecycle for the 24/7 YouTube Radio Stream. It listens for track changes from AzuraCast and performs seamless video loop switching with graceful handovers.

## Features

- ✅ **AzuraCast Webhook Integration**: Receives real-time track change notifications
- ✅ **FFmpeg Process Management**: Spawns, monitors, and gracefully terminates FFmpeg processes
- ✅ **Track-to-Loop Mapping**: Resolves tracks to video loop files with fallback support
- ✅ **Graceful Overlap**: 2-second overlap between tracks for seamless transitions
- ✅ **Auto-Recovery**: Automatic process restart with cooldown and attempt limits
- ✅ **Health Monitoring**: Comprehensive health and status endpoints
- ✅ **Security**: Webhook secret and API token authentication
- ✅ **Fade Transitions**: Video and audio fade effects for smooth track changes

## Architecture

```
AzuraCast Webhook → Metadata Watcher → Track Resolver → FFmpeg Manager
                                                              ↓
                                                     FFmpeg Process → nginx-rtmp → YouTube
```

## Installation

### Prerequisites

- Python 3.11+
- FFmpeg 6.0+
- SHARD-1 infrastructure (Docker Compose services)

### Install Dependencies

```bash
cd metadata_watcher
pip install -r requirements.txt
```

### Configuration

Copy and configure environment variables:

```bash
cp .env.example .env
# Edit .env with your settings
```

Required environment variables:
- `AZURACAST_URL`: Your AzuraCast installation URL
- `AZURACAST_API_KEY`: API key for AzuraCast
- `AZURACAST_AUDIO_URL`: Audio stream URL (e.g., http://azuracast:8000/radio)
- `POSTGRES_PASSWORD`: Database password

See `env.example` for all available configuration options.

## API Endpoints

### 1. Root Endpoint

**GET /**

Returns service information and available endpoints.

**Response:**
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

### 2. AzuraCast Webhook

**POST /webhook/azuracast**

Receives track change notifications from AzuraCast.

**Headers:**
- `X-Webhook-Secret`: Webhook secret for authentication (if configured)

**Request Body:**
```json
{
  "song": {
    "id": "123",
    "artist": "Artist Name",
    "title": "Song Title",
    "album": "Album Name",
    "duration": 180
  },
  "station": {
    "id": "1",
    "name": "Station Name"
  }
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Track switched successfully",
  "track": {
    "artist": "Artist Name",
    "title": "Song Title",
    "loop": "/srv/loops/tracks/artist_name_-_song_title.mp4"
  }
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid webhook secret
- `422 Unprocessable Entity`: Invalid payload structure
- `500 Internal Server Error`: Track switch failed

### 3. Health Check

**GET /health**

Checks service health and AzuraCast connectivity.

**Response:**
```json
{
  "status": "healthy",
  "service": "metadata-watcher",
  "timestamp": "2025-11-03T12:34:56.789Z",
  "azuracast_reachable": true,
  "ffmpeg_status": "running"
}
```

**Status Values:**
- `healthy`: All systems operational
- `degraded`: Service running but AzuraCast unreachable

### 4. Status Endpoint

**GET /status**

Returns detailed service status including current track and FFmpeg process information.

**Response:**
```json
{
  "service": "metadata-watcher",
  "status": "running",
  "timestamp": "2025-11-03T12:34:56.789Z",
  "current_track": {
    "track_key": "artist - title",
    "uptime_seconds": 125.5,
    "started_at": "2025-11-03T12:32:51.289Z"
  },
  "ffmpeg_process": {
    "pid": 12345,
    "track_key": "artist - title",
    "loop_path": "/srv/loops/tracks/track.mp4",
    "uptime_seconds": 125.5,
    "started_at": "2025-11-03T12:32:51.289Z"
  }
}
```

### 5. Manual Track Switch

**POST /manual/switch**

Manually trigger a track switch (for testing).

**Headers:**
- `Authorization`: Bearer token (if configured)

**Request Body:**
```json
{
  "artist": "Test Artist",
  "title": "Test Song",
  "song_id": "123"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Manual track switch successful",
  "track": {
    "artist": "Test Artist",
    "title": "Test Song",
    "loop": "/srv/loops/tracks/test_artist_-_test_song.mp4"
  }
}
```

## Usage

### Running the Service

**Development:**
```bash
python -m metadata_watcher.app
```

**Production (with Uvicorn):**
```bash
uvicorn metadata_watcher.app:app --host 0.0.0.0 --port 9000
```

**Docker:**
```bash
docker build -t metadata-watcher -f metadata_watcher/Dockerfile .
docker run -p 9000:9000 --env-file .env metadata-watcher
```

### Configuring AzuraCast Webhook

1. Go to your AzuraCast station settings
2. Navigate to: **Automation** → **Web Hooks**
3. Add a new webhook:
   - **Name**: Metadata Watcher
   - **Webhook URL**: `http://your-server:9000/webhook/azuracast`
   - **Triggers**: Check "Song changes (metadata update)"
   - **Secret**: (optional, set `WEBHOOK_SECRET` in .env)

### Testing

**Run all tests:**
```bash
pytest tests/unit/metadata_watcher/ tests/integration/metadata_watcher/ -v
```

**With coverage:**
```bash
pytest tests/unit/metadata_watcher/ --cov=metadata_watcher --cov-report=html
```

**Manual webhook test:**
```bash
curl -X POST http://localhost:9000/webhook/azuracast \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your-secret" \
  -d '{
    "song": {
      "id": "123",
      "artist": "Test Artist",
      "title": "Test Song"
    },
    "station": {
      "id": "1",
      "name": "Test Station"
    }
  }'
```

## Module Documentation

### Config (`config.py`)

Configuration management with environment variable loading and validation.

**Key Methods:**
- `Config.from_env()`: Load configuration from environment
- `config.validate()`: Validate configuration values
- `config.database_url`: Get PostgreSQL connection URL

### Track Resolver (`track_resolver.py`)

Maps track metadata to video loop files.

**Resolution Priority:**
1. Track-specific loop: `/srv/loops/tracks/{artist}_{title}.mp4`
2. Song ID loop: `/srv/loops/tracks/track_{song_id}_loop.mp4`
3. Default loop: `/srv/loops/default.mp4`

**Key Methods:**
- `resolve_loop(artist, title, song_id)`: Resolve track to loop file path
- `get_default_loop()`: Get default loop path

### FFmpeg Manager (`ffmpeg_manager.py`)

Manages FFmpeg process lifecycle with graceful handovers.

**Key Features:**
- Async process spawning
- Graceful overlap (2-second default)
- Auto-restart with cooldown
- Process monitoring and cleanup

**Key Methods:**
- `switch_track(track_key, artist, title, loop_path)`: Switch to new track
- `get_status()`: Get current process status
- `cleanup()`: Terminate processes and cleanup

### FastAPI App (`app.py`)

Main application with webhook and API endpoints.

**Lifespan Management:**
- Startup: Initializes config, track resolver, and FFmpeg manager
- Shutdown: Cleanup FFmpeg processes

## FFmpeg Command Structure

The service builds optimized FFmpeg commands with:

**Video Processing:**
- Infinite loop of video file (`-stream_loop -1`)
- Fade-in transition (`fade=t=in:st=0:d=1`)
- Resolution scaling and format conversion
- H.264/NVENC encoding with preset and bitrate control

**Audio Processing:**
- Live audio from AzuraCast stream
- AAC encoding at 192k
- Audio fade-in (`afade=t=in:ss=0:d=1`)

**Example Command:**
```bash
ffmpeg -re \
  -stream_loop -1 -i /srv/loops/track.mp4 \
  -i http://azuracast:8000/radio \
  -map 0:v -map 1:a \
  -vf "fade=t=in:st=0:d=1,scale=1280:720,format=yuv420p" \
  -c:v libx264 -preset veryfast -g 50 -b:v 3000k \
  -c:a aac -b:a 192k -ar 44100 \
  -af "afade=t=in:ss=0:d=1" \
  -f flv rtmp://nginx-rtmp:1935/live/stream
```

## Error Handling

### Process Failures

- **Immediate exit**: Logged with stderr output, no spawn
- **Crash during overlap**: Old process continues, retry spawn
- **Max attempts exceeded**: Alert and use last working configuration

### Recovery Mechanisms

- **Restart cooldown**: 60 seconds between restart attempts (configurable)
- **Max attempts**: 3 attempts per track before giving up
- **Cooldown reset**: After successful cooldown period, attempts counter resets

## Performance

### Resource Usage

**Baseline** (service only, no FFmpeg):
- CPU: <5%
- Memory: ~50 MB

**With FFmpeg** (720p x264):
- CPU: 30-50% per process
- Memory: ~100 MB per process
- During overlap: Up to 2 processes briefly

### Timing

- Webhook response: <50ms
- Process spawn: ~500ms
- Track overlap: 2 seconds (configurable)
- Graceful termination: <5 seconds

## Integration Points

### Consumes (from SHARD-1)

- **RTMP Endpoint**: `rtmp://nginx-rtmp:1935/live/stream`
- **PostgreSQL**: Database connection (for future SHARD-3 integration)
- **Environment Variables**: Configuration from Docker Compose

### Produces (for other shards)

- **FFmpeg Stream**: RTMP push to nginx-rtmp
- **Status Information**: Available via `/status` endpoint
- **Events**: Track changes, errors (for SHARD-5 logging)

### Future Integration

- **SHARD-3**: Database-backed track mappings
- **SHARD-5**: Structured logging to database
- **SHARD-6**: Notifications for track changes and errors
- **SHARD-7**: Prometheus metrics export

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
# Docker
docker-compose logs -f metadata-watcher

# Direct run
python -m metadata_watcher.app
```

**Common issues:**
- Missing environment variables: Check `.env` file
- Port already in use: Change `WATCHER_PORT`
- FFmpeg not found: Install FFmpeg or check PATH

### Webhook Not Received

**Verify:**
1. Service is running: `curl http://localhost:9000/health`
2. AzuraCast can reach service: Check network connectivity
3. Webhook secret matches: Compare AzuraCast and `.env` settings
4. Webhook is enabled: Check AzuraCast webhook configuration

### FFmpeg Won't Spawn

**Check:**
1. Loop file exists: Verify path in logs
2. Audio stream reachable: Test `AZURACAST_AUDIO_URL`
3. RTMP endpoint available: Check nginx-rtmp status
4. FFmpeg installed: Run `ffmpeg -version`

**Debug spawn issues:**
```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG
python -m metadata_watcher.app
```

### Track Not Found

**Resolution:**
1. Check loop file naming: Must match normalized track key
2. Verify loops directory: `ls -la /srv/loops/tracks/`
3. Check default loop exists: `/srv/loops/default.mp4`
4. Review normalization: Special characters removed, lowercase

## Security Considerations

### Authentication

- **Webhook Secret**: Validates requests from AzuraCast
- **API Token**: Protects manual control endpoints
- **Generate secure tokens**: Use `openssl rand -hex 32`

### Network Security

- **Internal Docker network**: Services communicate privately
- **Firewall rules**: Only expose necessary ports
- **HTTPS**: Use reverse proxy (nginx) with SSL for production

### Process Isolation

- **Non-root user**: Dockerfile runs as `radiouser`
- **Read-only filesystem**: Where possible
- **Resource limits**: Configure cgroups in production

## Testing

### Unit Tests

**Coverage**: 91% (401 statements, 36 missed)

**Key test modules:**
- `test_config.py`: Configuration loading and validation
- `test_track_resolver.py`: Track resolution logic
- `test_ffmpeg_manager.py`: Process lifecycle management
- `test_app.py`: API endpoints and webhooks

### Integration Tests

**Coverage**: 10 end-to-end scenarios

**Test scenarios:**
- Complete track change workflow
- Multiple consecutive track changes
- Process lifecycle and cleanup
- Error handling and recovery
- Restart cooldown enforcement

### Running Tests

```bash
# All tests
pytest tests/unit/metadata_watcher/ tests/integration/metadata_watcher/ -v

# Specific module
pytest tests/unit/metadata_watcher/test_config.py -v

# With coverage report
pytest tests/unit/metadata_watcher/ --cov=metadata_watcher --cov-report=html
open htmlcov/index.html
```

## Known Limitations

1. **Single Station**: Designed for one AzuraCast station
2. **Sequential Processing**: Webhooks processed one at a time
3. **No Persistent State**: Process state lost on restart
4. **Manual Mapping**: Track-to-loop mapping requires file system organization

## Future Enhancements

- [ ] Database-backed track mappings (SHARD-3 integration)
- [ ] Prometheus metrics export (SHARD-7 integration)
- [ ] Discord/Slack notifications (SHARD-6 integration)
- [ ] Dynamic overlay generation (SHARD-8 integration)
- [ ] Multi-station support
- [ ] Persistent process state
- [ ] Admin web UI for track mappings

## Contributing

When contributing to this module:

1. Follow Python 3.11+ type hints
2. Add docstrings (Google style)
3. Write tests for new features (maintain ≥80% coverage)
4. Run linters: `black`, `flake8`, `mypy`
5. Update this README for API changes

## Support

**Documentation:**
- [Project README](../README.md)
- [Development Shards](../DEVELOPMENT_SHARDS.md)
- [AI Agent Quickstart](../AI_AGENT_QUICKSTART.md)

**Logs:**
- Service logs: Docker Compose logs or stdout
- FFmpeg logs: Check FFmpeg stderr in process output

## Version History

### 1.0.0 (November 3, 2025)
- ✅ Initial implementation
- ✅ FastAPI webhook receiver
- ✅ FFmpeg process management
- ✅ Track-to-loop resolution
- ✅ Graceful overlap transitions
- ✅ Comprehensive tests (91% coverage)
- ✅ Full API documentation

---

**SHARD-2 Complete**: Ready for integration with SHARD-3 (Track Mapping) and SHARD-4 (FFmpeg Process Manager enhancements).
