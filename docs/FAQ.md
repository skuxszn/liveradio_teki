# Frequently Asked Questions (FAQ)

**24/7 FFmpeg YouTube Radio Stream - Common Questions**

This document answers the most frequently asked questions about the radio stream system.

## Table of Contents

1. [General Questions](#general-questions)
2. [Setup & Deployment](#setup--deployment)
3. [Configuration](#configuration)
4. [Video Loops](#video-loops)
5. [Streaming & Performance](#streaming--performance)
6. [Track Switching](#track-switching)
7. [Licensing & Legal](#licensing--legal)
8. [Costs & Resources](#costs--resources)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)

---

## General Questions

### What is this project?

This is a complete system for creating a 24/7 YouTube live stream that combines:
- Audio from an AzuraCast radio station
- Looping MP4 videos that change with each track
- Automatic video switching based on track metadata
- Monitoring, logging, and reliability features

Think of it as a "visual radio" where viewers see different video loops for each song.

---

### Do I need AzuraCast?

**Yes**, AzuraCast is required for two things:
1. **Audio source**: Provides the live audio stream
2. **Track metadata**: Sends webhooks when tracks change

**Alternatives**: You could modify the system to work with other radio automation software that provides webhooks, but significant code changes would be needed.

---

### Can this work with Icecast/Shoutcast instead of AzuraCast?

**Partially**. Icecast/Shoutcast can provide the audio stream, but they don't send webhooks for track changes. You would need to:
1. Poll the metadata endpoint
2. Detect track changes yourself
3. Trigger the video switch

This functionality is not currently built-in but could be added.

---

### Do I need to know programming to use this?

**No**, but basic command-line knowledge helps. You need to:
- Edit configuration files
- Run Docker commands
- Understand basic troubleshooting

If you can:
- Copy/paste commands into a terminal
- Edit text files
- Follow step-by-step instructions

...then you can deploy this system.

---

### Can I stream to platforms other than YouTube?

**Yes!** The system uses nginx-rtmp which can push to multiple platforms simultaneously:

Edit `nginx-rtmp/nginx.conf`:
```nginx
application live {
    live on;
    # YouTube
    push rtmp://a.rtmp.youtube.com/live2/${YOUTUBE_STREAM_KEY};
    # Twitch
    push rtmp://live.twitch.tv/app/${TWITCH_STREAM_KEY};
    # Facebook
    push rtmp://live-api-s.facebook.com:80/rtmp/${FACEBOOK_STREAM_KEY};
}
```

**Note**: Requires sufficient upload bandwidth (multiply bitrate by number of platforms).

---

## Setup & Deployment

### What are the minimum system requirements?

**For 720p @ 30fps**:
- CPU: 4 cores @ 2.0+ GHz
- RAM: 4 GB
- Disk: 50 GB
- Upload: 5 Mbps sustained
- OS: Linux (Ubuntu 20.04+, Debian 11+)

See [DEPLOYMENT.md](./DEPLOYMENT.md#system-requirements) for detailed requirements.

---

### Can this run on a Raspberry Pi?

**Maybe**, but not recommended:

- **Raspberry Pi 4 (8GB)**: Possible at 480p with optimized settings
- **Raspberry Pi 3**: Too weak, will struggle

**Better option**: Use a cheap VPS (Hetzner, DigitalOcean) for $10-20/month with better reliability.

---

### Can I run this on Windows?

**Yes**, with Docker Desktop:

1. Install Docker Desktop for Windows
2. Enable WSL2 backend
3. Follow the same setup instructions
4. Adjust paths for Windows (use forward slashes in Docker paths)

**However**: Linux is recommended for production. Windows Docker has higher overhead.

---

### How long does setup take?

**For experienced users**: 15-30 minutes  
**For beginners**: 1-2 hours (includes reading documentation)

Breakdown:
- Install Docker: 10 mins
- Clone and configure: 10 mins
- Create default video loop: 5 mins
- Start services: 5 mins
- Configure AzuraCast webhook: 5 mins
- Testing and verification: 15-30 mins

---

### Do I need a dedicated server?

**No**, but recommended for production:

**Shared Server**:
- ✅ Works for testing
- ❌ May have resource contention
- ❌ Higher chance of downtime

**Dedicated Server/VPS**:
- ✅ Consistent performance
- ✅ Better reliability
- ✅ Can allocate all resources

**Recommendation**: Start with a VPS (Virtual Private Server) for $10-20/month.

---

## Configuration

### What's the difference between the encoding presets?

| Preset | Quality | CPU Usage | Best For |
|--------|---------|-----------|----------|
| `ultrafast` | Lowest | 20% | Testing only |
| `veryfast` | Good | 30-40% | Production (default) |
| `fast` | Better | 40-50% | If CPU allows |
| `medium` | Best | 60-80% | Powerful CPUs only |

**For GPU (NVENC)**:
- `p1`: Fastest, lowest quality
- `p4`: Balanced (default)
- `p5`: Better quality
- `p7`: Best quality, slower

See [FFMPEG_TUNING.md](./FFMPEG_TUNING.md) for details.

---

### Should I use CPU or GPU encoding?

**Use CPU (libx264) if:**
- No NVIDIA GPU available
- Want best quality at given bitrate
- CPU has 6+ cores
- Streaming at 720p or lower

**Use GPU (h264_nvenc) if:**
- Have NVIDIA GTX 1050+ or RTX GPU
- Want lower CPU usage
- Streaming at 1080p or higher
- Need 60fps

**General rule**: GPU encoding is 3-5x faster but slightly lower quality at same bitrate.

---

### What bitrate should I use?

**Recommended bitrates**:

| Resolution | FPS | Bitrate Range | Recommended |
|-----------|-----|---------------|-------------|
| 720p | 30 | 2000-4000k | 2500-3000k |
| 720p | 60 | 3000-6000k | 4000-4500k |
| 1080p | 30 | 3500-7500k | 4500-5000k |
| 1080p | 60 | 5500-10000k | 6500-7500k |

**Choose based on**:
1. **Upload bandwidth**: Bitrate × 1.2 (for overhead)
2. **Video complexity**: Higher for fast motion, lower for static
3. **Quality goals**: Higher = better quality but more bandwidth

---

### How do I change the default loop?

**Option 1: Replace the file**
```bash
# Remove old default
rm /srv/loops/default.mp4

# Add your loop
cp your-loop.mp4 /srv/loops/default.mp4

# Validate
python scripts/validate_all_loops.py /srv/loops/default.mp4
```

**Option 2: Update database**
```bash
docker-compose exec postgres psql -U radio -d radio_db << EOF
UPDATE default_config SET value = '/srv/loops/your-loop.mp4' WHERE key = 'default_loop';
EOF
```

---

## Video Loops

### What format should video loops be?

**Required**:
- **Container**: MP4
- **Video Codec**: H.264 (x264)
- **Pixel Format**: yuv420p
- **Resolution**: Match your stream (e.g., 1280x720)
- **Frame Rate**: 30 fps (or match stream)
- **Duration**: Minimum 5 seconds

**Create from image**:
```bash
ffmpeg -loop 1 -i image.jpg -t 10 \
  -c:v libx264 -pix_fmt yuv420p -r 30 \
  output.mp4
```

See [ASSET_PREPARATION.md](./ASSET_PREPARATION.md) for detailed instructions.

---

### Can I use GIFs?

**No, not directly**. GIFs must be converted to MP4:

```bash
ffmpeg -i animation.gif \
  -vf "scale=1280:720,fps=30,format=yuv420p" \
  -c:v libx264 -preset medium \
  -pix_fmt yuv420p \
  output.mp4
```

**Why not use GIFs directly?** FFmpeg can read GIFs, but MP4 is far more efficient for streaming.

---

### How many video loops do I need?

**Minimum**: 1 (the default loop for all tracks)

**Recommended**:
- **Small library (<100 tracks)**: 1-10 unique loops
- **Medium library (100-1000 tracks)**: 10-50 unique loops
- **Large library (>1000 tracks)**: 50-500+ unique loops

**Strategy**:
1. Start with default loop
2. Add unique loops for popular/important tracks
3. Share loops between similar tracks (same artist, genre)

---

### Where can I find video loops?

**Free sources**:
- [Pexels Videos](https://www.pexels.com/videos/)
- [Pixabay Videos](https://pixabay.com/videos/)
- [Videvo](https://www.videvo.net/)

**Creative Commons images** (create loops from):
- [Unsplash](https://unsplash.com/)
- [Pexels Photos](https://www.pexels.com/)

**Create your own**:
- Use album art + motion effects (zoom, pan)
- Screen capture of visualizers (Milkdrop, ProjectM)
- Generate with AI (Stable Diffusion + video tools)

**IMPORTANT**: Always verify licensing and track sources (see [SECURITY.md](./SECURITY.md#license-compliance)).

---

### Can videos have audio?

**Yes, but it will be ignored**. FFmpeg only uses the video track and overlays the AzuraCast audio stream.

**Recommendation**: Remove audio from loops to save disk space:

```bash
ffmpeg -i loop-with-audio.mp4 -an -c:v copy loop-video-only.mp4
```

---

## Streaming & Performance

### How much bandwidth do I need?

**Formula**: `(Video Bitrate + Audio Bitrate) × 1.2`

**Examples**:
- 720p @ 2500k video + 192k audio = `2692k × 1.2 = 3.2 Mbps`
- 1080p @ 4500k video + 192k audio = `4692k × 1.2 = 5.6 Mbps`

**Important**: This is **upload** bandwidth, not download.

**Test your upload speed**: https://www.speedtest.net/

---

### Can I stream 1080p60?

**Yes**, with:
- **GPU encoding** (NVENC highly recommended)
- **8+ core CPU** (if using x264)
- **Upload bandwidth**: Minimum 10 Mbps
- **Bitrate**: 6500-7500k

Configuration:
```bash
VIDEO_RESOLUTION=1920:1080
VIDEO_BITRATE=7000k
VIDEO_ENCODER=h264_nvenc
```

---

### Why is my CPU usage so high?

**Common causes**:

**1. Preset too slow**:
```bash
# Change to faster preset
FFMPEG_PRESET=veryfast  # or ultrafast
```

**2. Resolution too high**:
```bash
# Reduce to 720p
VIDEO_RESOLUTION=1280:720
```

**3. Other processes running**:
```bash
# Check what's using CPU
htop
```

**4. No GPU acceleration**:
```bash
# Use NVENC if available
VIDEO_ENCODER=h264_nvenc
```

---

### Can I reduce latency to viewers?

**Current latency**: 5-15 seconds (typical for RTMP → YouTube)

**This is normal** and primarily determined by:
1. RTMP protocol overhead
2. YouTube transcoding
3. YouTube CDN buffering

**Cannot be significantly reduced** with this architecture. For ultra-low latency (<3s), you would need:
- YouTube Ultra-Low Latency mode (different protocol)
- WebRTC streaming (completely different technology)
- Significant architecture changes

**Bottom line**: This system is optimized for reliability, not minimal latency.

---

## Track Switching

### How fast are track switches?

**Typical switch time**: 2-3 seconds

**Breakdown**:
- Webhook received: ~0.1s
- Database query: ~0.05s
- FFmpeg spawn: ~0.5s
- Video fade-in: 1.0s
- Process overlap: 2.0s
- **Total**: ~2.6s

**Can it be faster?** Yes, with Option A (persistent FFmpeg with dual-input crossfade) for nearly instant switches. See [ADVANCED_TRANSITIONS.md](./ADVANCED_TRANSITIONS.md).

---

### Is there a gap in audio during switches?

**With default configuration (Option B)**: Small gap of 50-200ms possible

**Why?**
- Old FFmpeg process terminates
- New FFmpeg process starts
- Brief RTMP reconnection

**Solution for zero-gap**: Use Option A (advanced dual-input mode) for gapless transitions, but it's more complex.

**For most use cases**: 50-200ms gap is acceptable and viewers rarely notice.

---

### Can I disable track switching?

**Yes**, for continuous streaming of one video:

1. Don't configure AzuraCast webhook
2. Manually start a persistent stream:

```bash
ffmpeg -re -stream_loop -1 -i /srv/loops/permanent.mp4 \
  -i http://azuracast:8000/radio \
  -map 0:v -map 1:a \
  -c:v libx264 -preset veryfast -b:v 3000k \
  -c:a aac -b:a 192k \
  -f flv rtmp://a.rtmp.youtube.com/live2/YOUR_KEY
```

This bypasses the entire metadata-watcher system.

---

### How do I map tracks to loops?

**Method 1: Web UI** (Not currently implemented, planned for future)

**Method 2: Database**
```bash
docker-compose exec postgres psql -U radio -d radio_db

# In psql:
INSERT INTO track_mappings (track_key, loop_file_path)
VALUES ('artist - title', '/srv/loops/tracks/loop.mp4');
```

**Method 3: Bulk import from CSV**
```bash
# Create mappings.csv:
# artist,title,loop_path
# Artist 1,Song 1,/srv/loops/tracks/track001.mp4

python scripts/seed_mappings.py --csv mappings.csv
```

See [DEPLOYMENT.md](./DEPLOYMENT.md#step-7-add-track-mappings) for details.

---

## Licensing & Legal

### Do I need permission to stream music?

**Yes!** You need licenses for:
1. **Music**: From copyright holders or licensing agencies
2. **Videos**: For any visual content you use

**Options**:
- **Royalty-free music**: Use tracks with Creative Commons or similar licenses
- **Licensing agencies**: ASCAP, BMI, SESAC for commercial music
- **Direct from artists**: Get permission for specific tracks

**This system includes license tracking**: See [SECURITY.md](./SECURITY.md#license-compliance).

---

### Can I stream copyrighted music?

**Technically yes, legally depends**:

**YouTube's Content ID** may:
- Claim your stream (ads go to copyright holder)
- Mute audio
- Block stream in certain countries
- Issue copyright strikes

**Safe approaches**:
1. Use only royalty-free music
2. Get proper licenses
3. Use music you own rights to
4. Coordinate with copyright holders

**DO NOT**: Stream copyrighted music without permission and hope you won't get caught.

---

### What about the video loops?

Same rules apply! You need rights for:
- Stock videos
- Album art
- Generated visuals
- Any visual content

**Safe options**:
- Pexels, Pixabay (free, no attribution required)
- Unsplash (free images)
- Create your own
- Use Creative Commons with proper attribution

---

## Costs & Resources

### How much does this cost to run?

**One-time costs**:
- None (all open-source software)

**Monthly costs**:
- **VPS hosting**: $10-50/month
  - Hetzner: $10/month (4 vCPU, 8 GB RAM)
  - DigitalOcean: $24/month (4 vCPU, 8 GB RAM)
  - AWS EC2: $30-60/month (depends on configuration)

- **Bandwidth**: Usually included in VPS cost
  - Verify upload limits (some hosts cap at 1TB/month)

- **Storage**: Usually included
  - 100 GB recommended for large loop library

**Total**: $10-50/month for complete setup.

---

### Can I run this for free?

**Almost**:
- **Software**: All free and open-source
- **Hosting**: 
  - Oracle Cloud Free Tier (limited, but possible)
  - Home server (electricity + ISP)
  - Existing server (if you already have one)

**Challenges with free hosting**:
- Unreliable uptime
- Limited resources
- No support
- Bandwidth caps

**Recommendation**: Pay for reliable VPS hosting ($10-20/month) for peace of mind.

---

### How much disk space do I need for video loops?

**Estimates**:
- **10-second 720p loop**: ~3 MB
- **10-second 1080p loop**: ~8 MB

**Library sizes**:
- 100 tracks × 3 MB = 300 MB
- 1000 tracks × 3 MB = 3 GB
- 1000 tracks × 8 MB = 8 GB

**Add overhead**:
- Database: 100 MB - 1 GB
- Logs: 1-5 GB
- OS and software: 10-20 GB

**Recommendation**: 
- Minimum: 50 GB
- Comfortable: 100 GB
- Large library: 200+ GB

---

## Troubleshooting

### The stream works locally but not on YouTube. Why?

**Most common causes**:

1. **Wrong stream key**
   - Verify in YouTube Studio
   - Update in `.env`

2. **YouTube Live not enabled**
   - Enable in YouTube Studio
   - Wait 24 hours for first activation

3. **nginx-rtmp not pushing**
   - Check: `docker-compose logs nginx-rtmp | grep youtube`

4. **Firewall blocking outbound RTMP**
   - Test: `telnet a.rtmp.youtube.com 1935`

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md#issue-youtube-stream-not-appearing) for detailed diagnostics.

---

### Tracks are changing but video loops aren't switching. Why?

**Diagnosis**:
```bash
# Check webhook is being received
docker-compose logs -f metadata-watcher | grep webhook

# Check track mapping
docker-compose exec postgres psql -U radio -d radio_db
SELECT * FROM track_mappings WHERE track_key = 'artist - title';
```

**Common causes**:
1. **Track not mapped**: Returns default loop
2. **Wrong track key**: Normalization mismatch
3. **File doesn't exist**: Check `/srv/loops/`
4. **FFmpeg not restarting**: Check logs for errors

---

### How do I completely reset the system?

**Nuclear option** (deletes all data):

```bash
docker-compose down -v
sudo rm -rf /srv/loops/*
sudo rm -rf /var/log/radio/*
# Follow setup guide from scratch
```

**Safer option** (keep loops):

```bash
docker-compose down -v
docker-compose up -d
```

This recreates database but keeps video loops.

---

## Advanced Topics

### Can I customize the FFmpeg command?

**Yes**, edit `metadata_watcher/ffmpeg_manager.py`:

Find the `_build_command()` method and modify filters, codecs, or parameters.

**Example**: Add watermark:

```python
video_filters = [
    f"fade=t=in:st=0:d={fade_duration}",
    f"scale={resolution}",
    "format=yuv420p",
    "drawtext=text='My Radio':x=10:y=10:fontsize=24:fontcolor=white"
]
```

---

### Can I run multiple streams from one instance?

**Not easily**. Current architecture is one stream per deployment.

**For multiple streams**, deploy separate instances:
- Different directories
- Different ports
- Different YouTube streams

**Future enhancement**: Multi-tenant support could be added.

---

### How do I upgrade to newer versions?

```bash
# Backup data
./scripts/backup.sh

# Pull latest code
git pull origin main

# Rebuild containers
docker-compose build --no-cache

# Restart
docker-compose down
docker-compose up -d

# Verify
curl localhost:9000/health
```

---

### Can I contribute to this project?

**Yes!** Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Submit a Pull Request

See `CONTRIBUTING.md` (if exists) for guidelines.

---

## Still Have Questions?

**Check these resources**:
1. [Full Documentation](../README.md) - Start here
2. [Deployment Guide](./DEPLOYMENT.md) - Setup instructions
3. [Configuration Reference](./CONFIGURATION.md) - All settings
4. [Troubleshooting Guide](./TROUBLESHOOTING.md) - Common issues
5. [API Documentation](./API.md) - Endpoint reference

**Need help?**
- Open an issue on GitHub
- Join the Discord/Slack community
- Review existing issues for solutions

---

**Document Version**: 1.0  
**Last Updated**: November 5, 2025  
**Maintained By**: SHARD-12 (Documentation)

**Can't find your question?** Open an issue on GitHub to have it added to this FAQ!



