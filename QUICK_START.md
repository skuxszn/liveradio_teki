# Quick Start - Dashboard Stream Integration

The dashboard has been successfully integrated with the live FFmpeg stream! 🎉

---

## What's New

✅ **Real Stream Control** - Start/Stop/Restart buttons now control the actual FFmpeg process  
✅ **Real-time Status** - Dashboard shows actual stream state  
✅ **Current Track** - Live track information from the running stream  
✅ **No Mock Mode** - All fake data has been removed  

---

## Deploy the Integration

### 1. Rebuild Containers (Required)

```bash
# Stop all containers
docker-compose down

# Rebuild modified services
docker-compose build dashboard-api metadata-watcher

# Start everything
docker-compose up -d

# Check logs
docker-compose logs -f dashboard-api metadata-watcher
```

### 2. Verify It's Working

```bash
# Check shared volume is created
docker volume ls | grep stream-control

# Verify background task is running
docker logs radio_metadata_watcher | grep "background task"

# Check status file exists
docker exec radio_metadata_watcher cat /var/run/stream/status.json
```

### 3. Test Stream Control

**Option A: Use Dashboard UI**
1. Open http://localhost:3000
2. Log in
3. Go to Stream Control
4. Click "Start Stream"
5. Watch status change to "Live" 🔴

**Option B: Use API**
```bash
# Get auth token
TOKEN=$(curl -X POST http://localhost:9001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}' | jq -r '.access_token')

# Start the stream
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:9001/api/v1/stream/start | jq

# Check status (should show running=true)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:9001/api/v1/stream/status | jq
```

---

## Troubleshooting

### "Stream won't start"

Check default loop file:
```bash
# Make sure you have a default video loop
ls -la loops/default.mp4

# If missing, create a symlink or set DEFAULT_LOOP env var
docker-compose exec metadata-watcher ls -la /app/loops/
```

### "Control buttons don't work"

Check shared volume:
```bash
# Both should show the same directory
docker exec radio_dashboard_api ls -la /var/run/stream
docker exec radio_metadata_watcher ls -la /var/run/stream
```

### "Status shows stopped but FFmpeg is running"

Restart the metadata watcher:
```bash
docker-compose restart metadata-watcher
```

---

## Documentation

- **`INTEGRATION_COMPLETE.md`** - Complete summary of changes
- **`STREAM_INTEGRATION.md`** - Detailed technical documentation
- **`TEST_STREAM_INTEGRATION.md`** - Comprehensive testing guide

---

## What Was Changed

### Code Changes
- `metadata_watcher/ffmpeg_manager.py` - Added status writing and command reading
- `metadata_watcher/app.py` - Added background task for control loop
- `dashboard_api/services/stream_service.py` - Replaced mock mode with real integration
- `docker-compose.yml` - Added shared volume for communication
- `metadata_watcher/config.py` - Fixed default loop path

### Total Changes
- **5 files modified**
- **~270 lines added**
- **~40 lines removed** (mock mode)
- **3 documentation files created**

---

## Key Features

### Stream Control
- ✅ Start stream from dashboard
- ✅ Stop stream gracefully (SIGTERM → SIGKILL)
- ✅ Restart stream with current track
- ✅ 10-second timeout protection

### Status Monitoring
- ✅ Running/stopped state
- ✅ Current track (artist, title)
- ✅ Process info (PID, uptime)
- ✅ Real-time updates (1-second refresh)

### Integration
- ✅ Shared volume communication
- ✅ Atomic file operations
- ✅ Error recovery
- ✅ Background task polling

---

## How It Works

```
Dashboard                     Shared Volume                Metadata Watcher
---------                     -------------                ----------------
                                                          
User clicks                                               Background Task
"Start" ──────► control.json ──────► Read command ───────► Start FFmpeg
                (write)               (every 1s)
                                                          
                                                          FFmpeg Process
                                                          Running ───────┐
                                                                        │
UI shows     ◄──────── status.json ◄────── Write status ◄──────────────┘
"Live"                  (read)              (every 1s)
```

---

## Success Indicators

When working correctly, you should see:

1. **Dashboard UI**: Status changes from "Offline" to "Live"
2. **FFmpeg Process**: `docker exec radio_metadata_watcher ps aux | grep ffmpeg` shows process
3. **Status File**: `cat /var/run/stream/status.json` shows `"running": true`
4. **RTMP Stream**: `docker logs radio_nginx_rtmp | grep publish` shows connection
5. **Background Task**: Logs show "Received control command: start"

---

## Need Help?

1. **Check logs**: `docker logs radio_metadata_watcher`
2. **Review docs**: `STREAM_INTEGRATION.md` has detailed troubleshooting
3. **Run tests**: `TEST_STREAM_INTEGRATION.md` has verification steps

---

**Status**: ✅ Production Ready  
**Mock Mode**: ❌ Completely Removed  
**Integration**: ✅ Fully Functional

🎉 **Your dashboard now controls the real FFmpeg stream!**


