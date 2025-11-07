# Deployment Guide

**24/7 FFmpeg YouTube Radio Stream - Complete Deployment Instructions**

This guide walks you through deploying the radio stream system from scratch, including prerequisites, setup, configuration, and validation.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Requirements](#system-requirements)
3. [Quick Start (5 Minutes)](#quick-start)
4. [Detailed Setup](#detailed-setup)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Production Hardening](#production-hardening)
7. [Troubleshooting Deployment](#troubleshooting-deployment)

---

## Prerequisites

### Required Software

Before starting, ensure you have:

- **Docker**: Version 20.10+ ([Install Guide](https://docs.docker.com/get-docker/))
- **Docker Compose**: Version 2.0+ ([Install Guide](https://docs.docker.com/compose/install/))
- **Git**: For cloning the repository
- **Linux Server**: Ubuntu 20.04+ (recommended), Debian 11+, or similar

### Required Accounts/Services

- **YouTube Channel**: For live streaming ([Create here](https://www.youtube.com/create_channel))
- **YouTube Stream Key**: From YouTube Studio → Live → Stream Settings
- **AzuraCast Instance**: For radio automation ([Install Guide](https://www.azuracast.com/install/))

### Network Requirements

- **Public IP** or **domain name** (for webhook access)
- **Upload Bandwidth**: Minimum 5 Mbps (see [System Requirements](#system-requirements))
- **Open Ports**:
  - 9000: Metadata Watcher (webhook receiver)
  - 1935: RTMP (optional, if not using relay)
  - 9090: Prometheus (monitoring, can be internal only)

### Recommended Skills

- Basic Linux command line
- Docker fundamentals
- Understanding of environment variables

---

## System Requirements

Choose configuration based on your desired output quality:

### Minimum (720p @ 30fps, CPU Encoding)

```
CPU: 4 cores (2.0+ GHz)
RAM: 4 GB
Disk: 50 GB (20 GB for OS, 30 GB for loops and logs)
Upload: 5 Mbps sustained
```

**Suitable for**: Testing, small audience, budget hosting

### Recommended (1080p @ 30fps, CPU Encoding)

```
CPU: 8 cores (2.5+ GHz)
RAM: 8 GB
Disk: 100 GB SSD
Upload: 10 Mbps sustained
```

**Suitable for**: Production deployment, medium audience

### Optimal (1080p @ 60fps, GPU Encoding)

```
CPU: 4 cores (any modern CPU)
GPU: NVIDIA GTX 1650+ (with NVENC support)
RAM: 8 GB
Disk: 100 GB NVMe SSD
Upload: 15 Mbps sustained
```

**Suitable for**: High-quality production, large audience

### Disk Space Estimation

```
Base system: 5 GB
Docker images: 2 GB
Video loops: 3-10 GB (depends on library size)
  - ~3 MB per 10-second loop @ 720p
  - ~1000 tracks × 3 MB = 3 GB
Database & logs: 2-5 GB (grows over time)
Overhead: 5 GB

Total: 20-30 GB minimum, 50-100 GB recommended
```

---

## Quick Start (5 Minutes)

For experienced users who want to get running quickly:

```bash
# 1. Clone repository
git clone https://github.com/your-org/liveradio_teki.git
cd liveradio_teki

# 2. Copy and configure environment
cp env.example .env
nano .env  # Edit: YOUTUBE_STREAM_KEY, AZURACAST_URL, etc.

# 3. Create video loop directory
sudo mkdir -p /srv/loops
sudo chown $USER:$USER /srv/loops

# 4. Add default video loop
python scripts/generate_default_loop.py -o /srv/loops/default.mp4

# 5. Start services
docker-compose up -d

# 6. Check status
docker-compose ps
curl http://localhost:9000/health
```

**Next Steps**: Configure AzuraCast webhook, add track mappings, test stream.

---

## Detailed Setup

### Step 1: Server Preparation

#### 1.1 Update System

```bash
sudo apt update && sudo apt upgrade -y
```

#### 1.2 Install Docker

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
# Expected: Docker version 20.10.0 or higher
```

#### 1.3 Install Docker Compose

```bash
# Docker Compose is included with Docker Desktop
# For Linux servers, install separately:
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker-compose --version
# Expected: Docker Compose version v2.0.0 or higher
```

#### 1.4 Configure Firewall

```bash
# Install UFW if not present
sudo apt install ufw -y

# Allow SSH (IMPORTANT: before enabling firewall!)
sudo ufw allow 22/tcp

# Allow webhook endpoint
sudo ufw allow 9000/tcp

# Optional: Allow RTMP (if not using internal relay)
# sudo ufw allow 1935/tcp

# Optional: Allow monitoring (restrict to your IP)
# sudo ufw allow from YOUR_IP to any port 9090

# Enable firewall
sudo ufw enable
sudo ufw status
```

### Step 2: Clone and Configure

#### 2.1 Clone Repository

```bash
cd /home/$USER
git clone https://github.com/your-org/liveradio_teki.git
cd liveradio_teki
```

#### 2.2 Create Environment File

```bash
cp env.example .env
```

#### 2.3 Edit Configuration

Open `.env` in your favorite editor:

```bash
nano .env
```

**Critical Settings** (must configure):

```bash
# YouTube streaming
YOUTUBE_STREAM_KEY=your-youtube-stream-key-here

# AzuraCast
AZURACAST_URL=http://your-azuracast-server.com
AZURACAST_API_KEY=your-api-key-here
AZURACAST_AUDIO_URL=http://your-azuracast-server.com:8000/radio

# Database (change password!)
POSTGRES_PASSWORD=change-this-secure-password

# Security (generate tokens!)
WEBHOOK_SECRET=generate-a-random-secret-string
API_TOKEN=generate-another-random-token
```

**Generate Secure Tokens**:

```bash
# Generate webhook secret and API token
python scripts/generate_token.py --both

# Or manually with Python
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Optional Settings** (defaults are good for most):

```bash
# FFmpeg encoding (adjust based on system)
VIDEO_RESOLUTION=1280:720  # or 1920:1080
VIDEO_BITRATE=3000k        # or 4500k for 1080p
VIDEO_ENCODER=libx264      # or h264_nvenc for GPU

# Notifications (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Save and exit (Ctrl+X, Y, Enter in nano).

### Step 3: Prepare Video Loops

#### 3.1 Create Loops Directory

```bash
sudo mkdir -p /srv/loops/tracks
sudo chown -R $USER:$USER /srv/loops
```

#### 3.2 Generate Default Loop

```bash
# Option A: Generate from template
python scripts/generate_default_loop.py -o /srv/loops/default.mp4 -d 10

# Option B: Create from an image
python scripts/generate_default_loop.py \
  -i /path/to/your/image.jpg \
  -o /srv/loops/default.mp4
```

#### 3.3 Add Track-Specific Loops (Optional)

```bash
# Copy your prepared loops
cp /path/to/your/loops/*.mp4 /srv/loops/tracks/

# Validate loops
python scripts/validate_all_loops.py /srv/loops/tracks
```

See [ASSET_PREPARATION.md](./ASSET_PREPARATION.md) for creating high-quality loops.

### Step 4: Database Setup

The database will be automatically initialized when first starting Docker Compose, but you can verify the schema:

```bash
# Check schema files exist
ls track_mapper/schema.sql
ls logging_module/schema.sql
```

### Step 5: Start Services

#### 5.1 Build Images

```bash
docker-compose build
```

Expected output:
```
Building metadata-watcher
[+] Building 45.2s (12/12) FINISHED
...
Successfully tagged liveradio_teki_metadata-watcher:latest
```

#### 5.2 Start All Services

```bash
docker-compose up -d
```

Expected output:
```
Creating network "liveradio_teki_radio_network" ... done
Creating volume "liveradio_teki_postgres_data" ... done
Creating radio_postgres ... done
Creating radio_nginx_rtmp ... done
Creating radio_prometheus ... done
Creating radio_metadata_watcher ... done
```

#### 5.3 Verify Services

```bash
# Check all services are running
docker-compose ps

# Expected output:
#   NAME                     STATUS    PORTS
#   radio_metadata_watcher   Up        0.0.0.0:9000->9000/tcp
#   radio_nginx_rtmp         Up        0.0.0.0:1935->1935/tcp
#   radio_postgres           Up        0.0.0.0:5432->5432/tcp
#   radio_prometheus         Up        0.0.0.0:9090->9090/tcp
```

### Step 6: Configure AzuraCast Webhook

#### 6.1 Access AzuraCast Admin

1. Log in to your AzuraCast instance
2. Go to your station's settings
3. Navigate to: **Webhooks** section

#### 6.2 Create Webhook

1. Click **Add Webhook**
2. Configure:
   - **Name**: Radio Stream Video Switcher
   - **Webhook Type**: Generic Web Hook
   - **Webhook URL**: `http://your-server-ip:9000/webhook/azuracast`
   - **Triggers**: ✅ Song Change
   - **Custom Headers**: Add header
     - **Name**: `X-Webhook-Secret`
     - **Value**: `<your-WEBHOOK_SECRET-from-.env>`

3. Click **Save**

#### 6.3 Test Webhook

In AzuraCast, click **Test** on the webhook.

Check logs:
```bash
docker-compose logs -f metadata-watcher
```

Expected output:
```
INFO: Received track change webhook
INFO: Track: Artist - Title
INFO: Spawning FFmpeg process...
```

### Step 7: Add Track Mappings

#### 7.1 Manual Mapping (Single Track)

```bash
# Access Python environment
docker-compose exec metadata-watcher python

# In Python shell:
from track_mapper import TrackMapper
mapper = TrackMapper()
mapper.add_mapping("artist - title", "/srv/loops/tracks/track001.mp4")
exit()
```

#### 7.2 Bulk Import from CSV

Create `tracks.csv`:
```csv
artist,title,loop_path
Artist 1,Song 1,/srv/loops/tracks/track001.mp4
Artist 2,Song 2,/srv/loops/tracks/track002.mp4
```

Import:
```bash
python scripts/seed_mappings.py --csv tracks.csv
```

### Step 8: Verify Stream

#### 8.1 Check FFmpeg is Running

```bash
# View logs
docker-compose logs -f metadata-watcher

# You should see:
# INFO: FFmpeg started with PID 12345
# INFO: Stream active
```

#### 8.2 Test Local RTMP Stream

```bash
# If ffplay is installed
ffplay rtmp://localhost:1935/live/stream

# Or use VLC
vlc rtmp://localhost:1935/live/stream
```

#### 8.3 Check YouTube Studio

1. Go to [YouTube Studio](https://studio.youtube.com)
2. Click **Go Live**
3. You should see **Stream Status: Online**

---

## Post-Deployment Verification

### Health Checks

Run these commands to verify everything is working:

```bash
# 1. Metadata Watcher health
curl http://localhost:9000/health
# Expected: {"status":"healthy","ffmpeg":"running","uptime":123}

# 2. nginx-rtmp health
curl http://localhost:8080/health
# Expected: {"status":"ok"}

# 3. Prometheus health
curl http://localhost:9090/-/healthy
# Expected: Healthy

# 4. Database health
docker-compose exec postgres pg_isready -U radio
# Expected: /var/run/postgresql:5432 - accepting connections
```

### Metrics Verification

```bash
# Check Prometheus metrics
curl http://localhost:9000/metrics | grep radio_

# Expected output includes:
# radio_tracks_played_total 5
# radio_ffmpeg_status{status="running"} 1
# radio_stream_uptime_seconds 300
```

### Log Verification

```bash
# Check metadata-watcher logs
docker-compose logs --tail=50 metadata-watcher

# Check nginx-rtmp logs
docker-compose logs --tail=50 nginx-rtmp

# Check for errors
docker-compose logs | grep -i error
```

### Database Verification

```bash
# Connect to database
docker-compose exec postgres psql -U radio -d radio_db

# In psql:
\dt  # List tables
SELECT COUNT(*) FROM track_mappings;  # Check mappings
SELECT COUNT(*) FROM play_history;     # Check logged plays
\q   # Exit
```

---

## Production Hardening

### 1. Enable HTTPS

Use a reverse proxy (nginx or Caddy) with Let's Encrypt:

```nginx
# /etc/nginx/sites-available/radio-stream
server {
    listen 443 ssl http2;
    server_name stream.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/stream.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stream.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 2. Restrict Access

```bash
# Firewall: Allow only AzuraCast IP to webhook
sudo ufw delete allow 9000/tcp
sudo ufw allow from AZURACAST_IP to any port 9000

# Or use nginx rate limiting
```

### 3. Backup Configuration

```bash
# Create backup script
cat > /home/$USER/backup_radio.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/backup/radio/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U radio radio_db | gzip > $BACKUP_DIR/database.sql.gz

# Backup .env
cp .env $BACKUP_DIR/.env.backup

# Backup track mappings
docker-compose exec -T postgres psql -U radio -d radio_db -c "\COPY track_mappings TO STDOUT CSV HEADER" > $BACKUP_DIR/mappings.csv

# Rotate old backups (keep 30 days)
find /backup/radio -type d -mtime +30 -exec rm -rf {} +
EOF

chmod +x /home/$USER/backup_radio.sh

# Schedule daily backups
(crontab -l 2>/dev/null; echo "0 2 * * * /home/$USER/backup_radio.sh") | crontab -
```

### 4. Enable Monitoring Alerts

Configure Prometheus alerts (see [MONITORING.md](./MONITORING.md)).

### 5. Log Rotation

Docker handles log rotation by default, but you can customize:

```bash
# Edit daemon.json
sudo nano /etc/docker/daemon.json

# Add:
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

# Restart Docker
sudo systemctl restart docker
docker-compose restart
```

### 6. Resource Limits

Already configured in docker-compose.yml, but verify:

```bash
# Check resource usage
docker stats

# Adjust if needed in docker-compose.yml
```

---

## Troubleshooting Deployment

### Issue: Docker Compose Fails to Start

**Symptoms**: `docker-compose up` returns errors

**Solutions**:

1. Check Docker is running:
   ```bash
   sudo systemctl status docker
   ```

2. Validate docker-compose.yml:
   ```bash
   docker-compose config
   ```

3. Check port conflicts:
   ```bash
   sudo netstat -tlnp | grep -E '(9000|1935|5432|9090)'
   ```

4. View detailed errors:
   ```bash
   docker-compose up --no-start
   docker-compose logs
   ```

### Issue: Services Won't Start

**Symptoms**: Container exits immediately

**Solutions**:

1. Check logs:
   ```bash
   docker-compose logs metadata-watcher
   ```

2. Check environment variables:
   ```bash
   docker-compose config | grep -A 20 environment
   ```

3. Test service manually:
   ```bash
   docker-compose run --rm metadata-watcher python -c "import app; print('OK')"
   ```

### Issue: Webhook Not Receiving Requests

**Symptoms**: No logs when AzuraCast changes tracks

**Solutions**:

1. Check firewall:
   ```bash
   sudo ufw status
   curl http://YOUR_SERVER_IP:9000/health
   ```

2. Verify webhook URL in AzuraCast

3. Check webhook secret matches

4. Test webhook manually:
   ```bash
   curl -X POST http://localhost:9000/webhook/azuracast \
     -H "X-Webhook-Secret: YOUR_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"song":{"artist":"Test","title":"Test"}}'
   ```

### Issue: FFmpeg Not Starting

**Symptoms**: Logs show FFmpeg errors

**Solutions**:

1. Verify default loop exists:
   ```bash
   ls -lh /srv/loops/default.mp4
   ```

2. Check FFmpeg is installed:
   ```bash
   docker-compose exec metadata-watcher ffmpeg -version
   ```

3. Test FFmpeg command manually:
   ```bash
   docker-compose exec metadata-watcher ffmpeg -i /srv/loops/default.mp4 -f null -
   ```

4. Check RTMP endpoint is accessible:
   ```bash
   docker-compose exec metadata-watcher nc -zv nginx-rtmp 1935
   ```

### Issue: YouTube Stream Not Appearing

**Symptoms**: Local RTMP works but YouTube shows offline

**Solutions**:

1. Verify YouTube stream key:
   ```bash
   docker-compose exec nginx-rtmp grep YOUTUBE_STREAM_KEY /usr/local/nginx/conf/nginx.conf
   ```

2. Check nginx-rtmp logs:
   ```bash
   docker-compose logs nginx-rtmp | grep youtube
   ```

3. Test RTMP push manually:
   ```bash
   ffmpeg -re -i /srv/loops/default.mp4 \
     -c:v libx264 -preset veryfast -b:v 3000k \
     -c:a aac -b:a 192k \
     -f flv rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
   ```

4. Verify YouTube Live is enabled in your channel settings

### Issue: Database Connection Errors

**Symptoms**: "Could not connect to database"

**Solutions**:

1. Check postgres is running:
   ```bash
   docker-compose ps postgres
   ```

2. Verify database credentials:
   ```bash
   docker-compose exec postgres psql -U radio -d radio_db -c "SELECT 1;"
   ```

3. Check network connectivity:
   ```bash
   docker-compose exec metadata-watcher nc -zv postgres 5432
   ```

4. Recreate database:
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

---

## Next Steps

After successful deployment:

1. **Configure Monitoring**: Set up Grafana dashboards ([MONITORING.md](./MONITORING.md))
2. **Add More Tracks**: Populate track-to-video mappings
3. **Test Failover**: Verify auto-recovery works
4. **Set Up Backups**: Automate database and config backups
5. **Enable Notifications**: Configure Discord/Slack alerts
6. **Tune Performance**: Adjust FFmpeg settings for your hardware

---

## Support Resources

- **Configuration Reference**: [CONFIGURATION.md](./CONFIGURATION.md)
- **API Documentation**: [API.md](./API.md)
- **Troubleshooting Guide**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Security Best Practices**: [SECURITY.md](./SECURITY.md)
- **FFmpeg Optimization**: [FFMPEG_TUNING.md](./FFMPEG_TUNING.md)

---

**Document Version**: 1.0  
**Last Updated**: November 5, 2025  
**Maintained By**: SHARD-12 (Documentation)



