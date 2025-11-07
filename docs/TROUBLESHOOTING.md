# Troubleshooting Guide

**24/7 FFmpeg YouTube Radio Stream - Common Issues and Solutions**

This guide helps you diagnose and resolve common problems with the radio stream system.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Service Issues](#service-issues)
3. [FFmpeg Issues](#ffmpeg-issues)
4. [Stream Quality Issues](#stream-quality-issues)
5. [Database Issues](#database-issues)
6. [Network Issues](#network-issues)
7. [Performance Issues](#performance-issues)
8. [Debugging Tools](#debugging-tools)
9. [Getting Help](#getting-help)

---

## Quick Diagnostics

Run these commands first to identify the problem area:

```bash
# Check all services are running
docker-compose ps

# Check service logs for errors
docker-compose logs --tail=50 | grep -i error

# Test health endpoints
curl http://localhost:9000/health
curl http://localhost:8080/health

# Check stream status
curl http://localhost:9000/status | jq

# Check resource usage
docker stats

# Check disk space
df -h
```

---

## Service Issues

### Issue: Services Won't Start

**Symptoms**: `docker-compose up` fails or containers exit immediately

**Diagnosis**:
```bash
# Check Docker daemon
sudo systemctl status docker

# View container logs
docker-compose logs <service-name>

# Check for port conflicts
sudo netstat -tlnp | grep -E '(9000|1935|5432|9090)'
```

**Solutions**:

**1. Docker not running**:
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

**2. Port conflicts**:
```bash
# Find process using the port
sudo lsof -i :9000

# Either stop the conflicting process or change port in .env
```

**3. Missing environment variables**:
```bash
# Verify .env exists
ls -la .env

# Check for missing required variables
grep -E '^[A-Z_]+=\s*$' .env
```

**4. Permission issues**:
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
# Log out and back in

# Fix volume permissions
sudo chown -R $USER:$USER /srv/loops
```

---

### Issue: Metadata Watcher Crashes on Startup

**Symptoms**: Container exits with Python errors

**Diagnosis**:
```bash
docker-compose logs metadata-watcher
```

**Common Causes**:

**1. Missing dependencies**:
```bash
# Rebuild with no cache
docker-compose build --no-cache metadata-watcher
docker-compose up -d metadata-watcher
```

**2. Invalid configuration**:
```bash
# Validate .env
docker-compose config | grep -A 20 metadata-watcher

# Test configuration loading
docker-compose run --rm metadata-watcher python -c "from metadata_watcher.config import Config; c = Config.from_env(); c.validate(); print('OK')"
```

**3. Database connection failure**:
```bash
# Check postgres is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U radio -d radio_db -c "SELECT 1;"

# If fails, check DATABASE_URL in .env
```

---

### Issue: nginx-rtmp Won't Start

**Symptoms**: nginx-rtmp container exits with config errors

**Diagnosis**:
```bash
docker-compose logs nginx-rtmp
```

**Solutions**:

**1. Invalid nginx.conf**:
```bash
# Validate nginx config
docker-compose exec nginx-rtmp nginx -t

# If validation fails, check nginx-rtmp/nginx.conf syntax
```

**2. Missing stream key**:
```bash
# Verify YOUTUBE_STREAM_KEY is set
docker-compose exec nginx-rtmp env | grep YOUTUBE_STREAM_KEY
```

**3. Port 1935 in use**:
```bash
# Find conflicting process
sudo lsof -i :1935

# Change RTMP_PORT in .env if needed
```

---

## FFmpeg Issues

### Issue: FFmpeg Process Won't Start

**Symptoms**: Logs show "Failed to spawn FFmpeg" or immediate crash

**Diagnosis**:
```bash
# Check FFmpeg is available
docker-compose exec metadata-watcher ffmpeg -version

# Check video loop exists
docker-compose exec metadata-watcher ls -lh /srv/loops/default.mp4

# Test FFmpeg command manually
docker-compose exec metadata-watcher ffmpeg -i /srv/loops/default.mp4 -f null -
```

**Solutions**:

**1. Missing default loop**:
```bash
# Generate default loop
python scripts/generate_default_loop.py -o /srv/loops/default.mp4
```

**2. Invalid video file**:
```bash
# Validate video file
ffprobe /srv/loops/default.mp4

# Expected: H.264 video, MP4 container
# If invalid, regenerate or replace
```

**3. Audio stream unreachable**:
```bash
# Test audio URL
curl -I http://azuracast-url:8000/radio

# If fails, verify AZURACAST_AUDIO_URL in .env
```

**4. RTMP endpoint unreachable**:
```bash
# Test RTMP connectivity
docker-compose exec metadata-watcher nc -zv nginx-rtmp 1935

# If fails, check nginx-rtmp is running
docker-compose ps nginx-rtmp
```

---

### Issue: FFmpeg Crashes Repeatedly

**Symptoms**: Process restarts continuously, never stabilizes

**Diagnosis**:
```bash
# View FFmpeg logs
docker-compose logs -f metadata-watcher | grep ffmpeg

# Check restart count
curl http://localhost:9000/status | jq '.ffmpeg_process.restart_count'
```

**Common Errors**:

**1. "Connection refused" (RTMP)**:
```bash
# Verify nginx-rtmp is running
docker-compose ps nginx-rtmp

# Check nginx-rtmp logs
docker-compose logs nginx-rtmp

# Restart nginx-rtmp
docker-compose restart nginx-rtmp
```

**2. "Invalid codec parameters"**:
```bash
# Check video loop format
ffprobe -show_streams /srv/loops/default.mp4

# Required: H.264 video, yuv420p pixel format
# Fix: Re-encode video loop
ffmpeg -i input.mp4 \
  -c:v libx264 -pix_fmt yuv420p \
  -c:a aac \
  /srv/loops/default.mp4
```

**3. "No such file or directory"**:
```bash
# Check file permissions
docker-compose exec metadata-watcher ls -l /srv/loops/

# Fix permissions
sudo chown -R $USER:$USER /srv/loops
```

**4. "Out of memory"**:
```bash
# Check available memory
free -h

# Reduce encoding quality in .env:
VIDEO_BITRATE=2000k
VIDEO_RESOLUTION=854:480

# Or increase Docker memory limit
```

---

### Issue: FFmpeg Audio/Video Desync

**Symptoms**: Audio and video drift apart over time

**Diagnosis**:
```bash
# Monitor FFmpeg output
docker-compose logs -f metadata-watcher | grep "speed="
```

**Solutions**:

**1. Encoding too slow**:
```bash
# Check encoding speed (should be ~1.0x)
# If <0.95x, CPU can't keep up

# Solution: Use faster preset
VIDEO_ENCODER=libx264
FFMPEG_PRESET=ultrafast

# Or use GPU encoding
VIDEO_ENCODER=h264_nvenc
```

**2. Variable audio stream**:
```bash
# Check audio stream consistency
ffprobe http://azuracast-url:8000/radio

# If sample rate varies, add audio resampling:
# (modify ffmpeg_manager.py to add: -ar 44100 -async 1)
```

**3. Network buffering**:
```bash
# Increase thread queue size in config
THREAD_QUEUE_SIZE=1024  # Default: 512
```

---

## Stream Quality Issues

### Issue: Low Video Quality / Pixelation

**Symptoms**: Visible compression artifacts, blocky video

**Solutions**:

**1. Increase bitrate**:
```bash
# In .env
VIDEO_BITRATE=4500k  # For 1080p
VIDEO_BITRATE=3000k  # For 720p
```

**2. Use slower preset**:
```bash
FFMPEG_PRESET=fast  # Instead of veryfast
```

**3. Check source quality**:
```bash
# Validate video loop quality
ffprobe -show_streams /srv/loops/track.mp4

# Should have bitrate > VIDEO_BITRATE
# If source is low quality, encoding won't improve it
```

**4. Use GPU encoding**:
```bash
# NVENC provides better quality at same bitrate
VIDEO_ENCODER=h264_nvenc
FFMPEG_PRESET=p5  # Higher quality preset
```

---

### Issue: Audio Quality Issues

**Symptoms**: Distorted, crackling, or muffled audio

**Solutions**:

**1. Increase audio bitrate**:
```bash
AUDIO_BITRATE=256k  # Up from 192k
```

**2. Check source audio**:
```bash
# Test AzuraCast audio stream
ffplay http://azuracast-url:8000/radio

# If source is bad, encoding won't fix it
```

**3. Disable audio filters**:
```bash
# Remove fade filters if causing issues
# Edit metadata_watcher/ffmpeg_manager.py
# Comment out: -af "afade=t=in:ss=0:d=1"
```

---

### Issue: Stream Buffering for Viewers

**Symptoms**: Viewers report frequent buffering

**Diagnosis**:
```bash
# Check upload bandwidth usage
iftop  # Install: sudo apt install iftop

# Check if bitrate is too high for connection
```

**Solutions**:

**1. Reduce bitrate**:
```bash
VIDEO_BITRATE=2500k  # Reduce from 3000k or higher
AUDIO_BITRATE=128k   # Reduce from 192k
```

**2. Check network stability**:
```bash
# Ping YouTube RTMP server
ping a.rtmp.youtube.com

# Check for packet loss
mtr a.rtmp.youtube.com
```

**3. Use CBR (Constant Bitrate)**:
```bash
# Edit ffmpeg_manager.py to ensure:
# -b:v 3000k -maxrate 3000k -bufsize 6000k
# (already default)
```

---

## Database Issues

### Issue: Database Connection Errors

**Symptoms**: "Could not connect to database" errors

**Diagnosis**:
```bash
# Check postgres is running
docker-compose ps postgres

# Check postgres logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U radio -d radio_db -c "SELECT 1;"
```

**Solutions**:

**1. Postgres not started**:
```bash
docker-compose up -d postgres
docker-compose logs postgres
```

**2. Wrong credentials**:
```bash
# Verify .env settings
grep POSTGRES .env

# Test with correct credentials
docker-compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB
```

**3. Database doesn't exist**:
```bash
# Create database
docker-compose exec postgres psql -U radio -c "CREATE DATABASE radio_db;"

# Reinitialize
docker-compose down -v
docker-compose up -d
```

**4. Connection pool exhausted**:
```bash
# Increase pool size in .env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Restart metadata-watcher
docker-compose restart metadata-watcher
```

---

### Issue: Slow Database Queries

**Symptoms**: Slow track switches, high latency

**Diagnosis**:
```bash
# Check query performance
docker-compose exec postgres psql -U radio -d radio_db

# In psql:
EXPLAIN ANALYZE SELECT * FROM track_mappings WHERE track_key = 'test';
```

**Solutions**:

**1. Missing indexes**:
```bash
# Recreate indexes
docker-compose exec postgres psql -U radio -d radio_db << EOF
CREATE INDEX IF NOT EXISTS idx_track_key ON track_mappings(track_key);
CREATE INDEX IF NOT EXISTS idx_song_id ON track_mappings(azuracast_song_id);
EOF
```

**2. Vacuum database**:
```bash
docker-compose exec postgres psql -U radio -d radio_db -c "VACUUM ANALYZE;"
```

**3. Too much history**:
```bash
# Archive old play history
docker-compose exec postgres psql -U radio -d radio_db << EOF
DELETE FROM play_history WHERE started_at < NOW() - INTERVAL '30 days';
VACUUM ANALYZE play_history;
EOF
```

---

## Network Issues

### Issue: Webhook Not Receiving Requests

**Symptoms**: No logs when tracks change in AzuraCast

**Diagnosis**:
```bash
# Check firewall
sudo ufw status

# Test from external machine
curl http://YOUR_PUBLIC_IP:9000/health
```

**Solutions**:

**1. Firewall blocking**:
```bash
sudo ufw allow 9000/tcp
sudo ufw reload
```

**2. Wrong webhook URL**:
```bash
# In AzuraCast, webhook should be:
http://YOUR_SERVER_IP:9000/webhook/azuracast

# NOT localhost or 127.0.0.1 (unless AzuraCast is on same server)
```

**3. Webhook secret mismatch**:
```bash
# Verify secrets match
# In .env:
echo $WEBHOOK_SECRET

# Must match X-Webhook-Secret header in AzuraCast
```

**4. Test webhook manually**:
```bash
curl -X POST http://localhost:9000/webhook/azuracast \
  -H "X-Webhook-Secret: your-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "song": {
      "id": "test",
      "artist": "Test Artist",
      "title": "Test Song"
    },
    "station": {
      "id": "1",
      "name": "Test Station"
    }
  }'
```

---

### Issue: YouTube Stream Not Appearing

**Symptoms**: Local RTMP works, but YouTube shows "Offline"

**Diagnosis**:
```bash
# Check nginx-rtmp is pushing
docker-compose logs nginx-rtmp | grep youtube

# Verify stream key
docker-compose exec nginx-rtmp env | grep YOUTUBE_STREAM_KEY
```

**Solutions**:

**1. Invalid stream key**:
```bash
# Get correct key from YouTube Studio
# Update .env
YOUTUBE_STREAM_KEY=your-correct-stream-key

# Restart nginx-rtmp
docker-compose restart nginx-rtmp
```

**2. YouTube Live not enabled**:
- Go to YouTube Studio
- Enable Live Streaming
- Wait 24 hours for activation (first-time enablement)

**3. Stream settings mismatch**:
```bash
# YouTube requires:
# - Resolution: 240p to 4K
# - Framerate: Up to 60fps
# - Bitrate: Up to 51 Mbps (way more than we use)
# - Keyframe interval: 2 seconds

# Our defaults comply, but if changed, verify
```

**4. Test direct push**:
```bash
# Bypass nginx-rtmp, push directly
ffmpeg -re -i /srv/loops/default.mp4 \
  -c:v libx264 -preset veryfast -b:v 3000k \
  -c:a aac -b:a 192k \
  -f flv rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
  
# If this works, issue is with nginx-rtmp
# If this fails, issue is with YouTube or stream key
```

---

## Performance Issues

### Issue: High CPU Usage

**Symptoms**: CPU constantly at 80-100%, system slow

**Diagnosis**:
```bash
# Check CPU usage by container
docker stats

# Check FFmpeg CPU usage
top -p $(pgrep -f ffmpeg)
```

**Solutions**:

**1. Use faster encoding preset**:
```bash
FFMPEG_PRESET=ultrafast  # Fastest
FFMPEG_PRESET=superfast  # Very fast
FFMPEG_PRESET=veryfast   # Fast (default)
```

**2. Reduce resolution**:
```bash
VIDEO_RESOLUTION=1280:720  # Down from 1920:1080
```

**3. Reduce bitrate**:
```bash
VIDEO_BITRATE=2500k  # Down from 3000k or higher
```

**4. Use GPU encoding**:
```bash
# If you have NVIDIA GPU
VIDEO_ENCODER=h264_nvenc
```

**5. Limit other processes**:
```bash
# Check what else is running
htop

# Stop unnecessary services
sudo systemctl stop <service>
```

---

### Issue: High Memory Usage

**Symptoms**: Memory usage climbing over time, eventual OOM

**Diagnosis**:
```bash
# Check memory usage
free -h

# Check for memory leaks
docker stats --no-stream
```

**Solutions**:

**1. Restart FFmpeg periodically**:
```bash
# Add cron job to restart daily
0 4 * * * docker-compose restart metadata-watcher
```

**2. Reduce buffer sizes**:
```bash
# Edit metadata_watcher/ffmpeg_manager.py
# Reduce -bufsize from 6000k to 4000k
```

**3. Clear old logs**:
```bash
# Set up log rotation
docker-compose down
# Edit /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
sudo systemctl restart docker
docker-compose up -d
```

---

### Issue: Disk Space Full

**Symptoms**: "No space left on device" errors

**Diagnosis**:
```bash
# Check disk usage
df -h

# Find large directories
du -sh /* | sort -rh | head -10
```

**Solutions**:

**1. Clear Docker logs**:
```bash
docker system prune -a --volumes
```

**2. Clear old database entries**:
```bash
# Remove old play history
docker-compose exec postgres psql -U radio -d radio_db << EOF
DELETE FROM play_history WHERE started_at < NOW() - INTERVAL '90 days';
VACUUM FULL;
EOF
```

**3. Remove unused video loops**:
```bash
# Find unused loops
cd /srv/loops/tracks
ls -lh | sort -k5 -hr  # Sort by size

# Remove large unused files
```

---

## Debugging Tools

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs metadata-watcher

# Follow logs (live)
docker-compose logs -f

# Last N lines
docker-compose logs --tail=50

# Since timestamp
docker-compose logs --since 2025-11-05T10:00:00
```

### Execute Commands in Containers

```bash
# Interactive shell
docker-compose exec metadata-watcher bash

# Run command
docker-compose exec metadata-watcher ls -la /srv/loops

# Run as different user
docker-compose exec -u root metadata-watcher apt-get update
```

### Test Endpoints

```bash
# Health check
curl -s http://localhost:9000/health | jq

# Detailed status
curl -s http://localhost:9000/status | jq

# Prometheus metrics
curl http://localhost:9000/metrics | grep radio_
```

### Monitor Resources

```bash
# Real-time container stats
docker stats

# System resources
htop

# Network
iftop

# Disk I/O
iotop
```

### Test FFmpeg Manually

```bash
# Enter container
docker-compose exec metadata-watcher bash

# Test encoding
ffmpeg -i /srv/loops/default.mp4 \
  -c:v libx264 -preset veryfast -b:v 3000k \
  -f null -

# Check encoding speed (should be ~1.0x)
```

### Database Queries

```bash
# Connect to database
docker-compose exec postgres psql -U radio -d radio_db

# Useful queries:
SELECT COUNT(*) FROM track_mappings;
SELECT COUNT(*) FROM play_history;
SELECT * FROM play_history ORDER BY started_at DESC LIMIT 10;
SELECT track_key, COUNT(*) FROM play_history GROUP BY track_key ORDER BY count DESC LIMIT 10;
```

---

## Getting Help

### Before Asking for Help

1. **Check logs**: `docker-compose logs`
2. **Test health**: `curl localhost:9000/health`
3. **Review this guide**: Search for your specific error
4. **Check documentation**: [DEPLOYMENT.md](./DEPLOYMENT.md), [CONFIGURATION.md](./CONFIGURATION.md)

### Information to Provide

When reporting issues, include:

```bash
# System info
uname -a
docker --version
docker-compose --version

# Service status
docker-compose ps

# Recent logs
docker-compose logs --tail=100 > logs.txt

# Configuration (redact secrets!)
docker-compose config > config.txt

# Resource usage
docker stats --no-stream > stats.txt

# Error messages
# Copy exact error messages
```

### Where to Get Help

1. **Documentation**: Check all docs in `docs/` directory
2. **GitHub Issues**: Search existing issues, create new if needed
3. **Community**: Discord/Slack channels
4. **Professional Support**: For production deployments

---

## Emergency Procedures

### Complete System Reset

**WARNING**: This deletes all data. Use only as last resort.

```bash
# Stop everything
docker-compose down -v

# Remove all data
sudo rm -rf /srv/loops/*
sudo rm -rf /var/log/radio/*

# Recreate from scratch
cp env.example .env
nano .env  # Configure

# Generate default loop
python scripts/generate_default_loop.py -o /srv/loops/default.mp4

# Start fresh
docker-compose up -d

# Verify
docker-compose ps
curl localhost:9000/health
```

### Restore from Backup

```bash
# Stop services
docker-compose down

# Restore database
cat backup.sql | docker-compose run --rm postgres psql -U radio -d radio_db

# Restore .env
cp .env.backup .env

# Restore loops
rsync -av /backup/loops/ /srv/loops/

# Start services
docker-compose up -d
```

---

**Document Version**: 1.0  
**Last Updated**: November 5, 2025  
**Maintained By**: SHARD-12 (Documentation)

**Pro Tip**: Keep this guide bookmarked. Most issues can be resolved in <5 minutes with the right diagnostic command.



