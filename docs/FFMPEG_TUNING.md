# FFmpeg Encoding Optimization Guide

**SHARD-4: FFmpeg Process Manager**  
**Last Updated**: November 5, 2025

## Overview

This guide covers FFmpeg encoding optimization for 24/7 YouTube live streaming, including preset selection, performance tuning, quality optimization, and troubleshooting.

## Table of Contents

- [Encoding Basics](#encoding-basics)
- [Preset Selection](#preset-selection)
- [CPU vs GPU Encoding](#cpu-vs-gpu-encoding)
- [Quality Optimization](#quality-optimization)
- [Performance Tuning](#performance-tuning)
- [Network Considerations](#network-considerations)
- [Troubleshooting](#troubleshooting)
- [Advanced Configurations](#advanced-configurations)

---

## Encoding Basics

### Video Encoding Pipeline

```
Video Loop (MP4) → Decode → Scale → Encode → Mux with Audio → RTMP Output
Live Audio (HTTP) → Decode → Resample → Encode ↗
```

### Key Parameters

| Parameter | Description | Impact |
|-----------|-------------|--------|
| **Resolution** | Video dimensions (e.g., 1920x1080) | Quality, bandwidth, CPU |
| **Bitrate** | Data rate in kbps (e.g., 3000k) | Quality, bandwidth |
| **Framerate** | Frames per second (30 or 60) | Smoothness, CPU, bandwidth |
| **Preset** | Encoding speed/quality tradeoff | CPU usage, quality |
| **GOP Size** | Keyframe interval | Seeking, quality |
| **Pixel Format** | Color space (yuv420p) | Compatibility |

---

## Preset Selection

### Decision Tree

```
Do you have NVIDIA GPU?
├─ Yes → 1080p_nvenc (recommended)
│        └─ High FPS needed? → 1080p60_nvenc
└─ No → CPU encoding
    └─ CPU cores?
        ├─ 2-4 cores → 720p_fast
        ├─ 4-8 cores → 720p_quality or 1080p_fast
        └─ 8+ cores → 1080p_quality
```

### Preset Comparison

#### CPU Encoding (x264)

| Preset | Resolution | Bitrate | CPU Usage | Quality | Use Case |
|--------|-----------|---------|-----------|---------|----------|
| **480p_test** | 854x480 | 1000k | ~15% | Low | Testing/debugging |
| **720p_fast** | 1280x720 | 2500k | 30-40% | Good | Budget servers |
| **720p_quality** | 1280x720 | 3500k | 40-50% | Better | Balanced |
| **1080p_fast** | 1920x1080 | 4500k | 50-60% | Good | Mid-range servers |
| **1080p_quality** | 1920x1080 | 6000k | 60-80% | Best | High-end servers |

#### GPU Encoding (NVENC)

| Preset | Resolution | FPS | Bitrate | CPU Usage | GPU Usage | Quality |
|--------|-----------|-----|---------|-----------|-----------|---------|
| **720p_nvenc** | 1280x720 | 30 | 3000k | 10-15% | 30-40% | Good |
| **1080p_nvenc** | 1920x1080 | 30 | 5000k | 15-20% | 40-50% | Better |
| **1080p60_nvenc** | 1920x1080 | 60 | 7000k | 20-25% | 50-60% | Best |

---

## CPU vs GPU Encoding

### x264 (CPU Encoding)

**Pros**:
- ✅ Better quality at same bitrate
- ✅ Works on any hardware
- ✅ More encoding options/control
- ✅ Better for static content

**Cons**:
- ❌ High CPU usage
- ❌ Slower encoding
- ❌ May throttle on weak CPUs

**When to Use**:
- No GPU available
- Quality is priority over CPU usage
- Server has many CPU cores

### NVENC (GPU Encoding)

**Pros**:
- ✅ Very low CPU usage (~10-20%)
- ✅ Fast encoding
- ✅ Dedicated hardware encoder
- ✅ Consistent performance

**Cons**:
- ❌ Requires NVIDIA GPU (GTX 1050+)
- ❌ Slightly lower quality at same bitrate
- ❌ Fewer encoding options

**When to Use**:
- NVIDIA GPU available (consumer or datacenter)
- CPU needs to be free for other tasks
- 1080p60 streaming desired

### NVENC Requirements

**Minimum**: NVIDIA GTX 1050 / MX150 or newer  
**Recommended**: GTX 1650+ or RTX series  
**Best**: RTX 3060+ or datacenter GPUs (T4, A10)

Check NVENC support:
```bash
ffmpeg -hide_banner -encoders | grep nvenc
```

---

## Quality Optimization

### Bitrate Guidelines

#### 720p (1280x720)

| FPS | Minimum | Recommended | High Quality |
|-----|---------|-------------|--------------|
| 30 | 2000k | 2500-3000k | 3500-4000k |
| 60 | 3000k | 4000-4500k | 5000-6000k |

#### 1080p (1920x1080)

| FPS | Minimum | Recommended | High Quality |
|-----|---------|-------------|--------------|
| 30 | 3500k | 4500-5000k | 6000-7500k |
| 60 | 5500k | 6500-7500k | 8500-10000k |

### Visual Quality vs File Size

**Formula**: `Quality ∝ (Bitrate / (Width × Height × FPS))`

**Example**:
- 720p @ 30fps with 2500k: 0.00048 bits per pixel
- 1080p @ 30fps with 4500k: 0.00043 bits per pixel

→ 720p will have slightly better quality despite lower bitrate

### x264 Preset Impact

| Preset | Encoding Speed | Quality | CPU Usage |
|--------|---------------|---------|-----------|
| ultrafast | 10x | Lowest | 20% |
| veryfast | 5x | Low | 30% |
| fast | 3x | Good | 40% |
| medium | 1x | Better | 60% |
| slow | 0.5x | Best | 80% |

**For 24/7 streaming**: Use `veryfast` or `fast` to avoid CPU overload.

---

## Performance Tuning

### CPU Optimization

#### Thread Count

FFmpeg auto-detects CPU cores, but can be overridden:
```bash
-threads 4  # Use 4 threads (usually auto is best)
```

#### Thread Queue Size

Increase if seeing "Thread message queue blocking" warnings:
```python
FFmpegConfig(thread_queue_size=1024)  # Default: 512
```

#### CPU Affinity (Linux)

Pin FFmpeg to specific cores:
```bash
taskset -c 0-3 ffmpeg ...  # Use cores 0-3
```

### GPU Optimization

#### NVENC Preset

| Preset | Quality | Speed | Use Case |
|--------|---------|-------|----------|
| p1 (fastest) | Lowest | Fastest | Testing |
| p4 (default) | Good | Fast | 24/7 streaming |
| p5 | Better | Medium | High quality |
| p7 (slowest) | Best | Slowest | Archive quality |

Configuration:
```python
# Default in config.py uses p4 for balanced performance
# p5 used for 1080p60 for better quality
```

#### GPU Memory

Monitor with:
```bash
nvidia-smi dmon -s u  # Monitor GPU utilization
```

Typical usage: 200-500 MB VRAM

### Memory Optimization

#### Buffer Sizes

```python
FFmpegConfig(
    # Input buffer
    thread_queue_size=512,
    
    # Output buffer (set in command builder)
    # bufsize = bitrate * 2
)
```

#### Reduce Memory Footprint

- Use lower thread queue size (256 instead of 512)
- Reduce GOP size (30 instead of 50)
- Use `veryfast` preset

---

## Network Considerations

### Upload Bandwidth

**Formula**: `Required = (Video Bitrate + Audio Bitrate) × 1.2`

| Preset | Video | Audio | Total | Recommended Upload |
|--------|-------|-------|-------|-------------------|
| 720p_fast | 2500k | 192k | 2692k | 4 Mbps |
| 720p_quality | 3500k | 192k | 3692k | 5 Mbps |
| 1080p_fast | 4500k | 192k | 4692k | 6 Mbps |
| 1080p_quality | 6000k | 192k | 6192k | 8 Mbps |
| 1080p_nvenc | 5000k | 192k | 5192k | 7 Mbps |
| 1080p60_nvenc | 7000k | 192k | 7192k | 9 Mbps |

Add 20% overhead for network variance.

### Adaptive Bitrate

Not currently implemented, but could be added:
```python
# Monitor network and adjust bitrate
if network_congestion_detected():
    switch_to_lower_preset()
```

### Latency

**Typical latency to YouTube**:
- RTMP push: 100-300ms
- YouTube processing: 3-10 seconds
- Total viewer latency: 5-15 seconds

**Reduce latency**:
- Use `-tune zerolatency` (already enabled for x264)
- Smaller GOP size (25-30 instead of 50)
- Lower `-maxrate` and `-bufsize`

---

## Troubleshooting

### Common Issues

#### 1. High CPU Usage (>80%)

**Symptoms**: CPU constantly maxed out, system slow  
**Solutions**:
- Switch to faster preset (`fast` → `veryfast`)
- Reduce resolution (1080p → 720p)
- Use NVENC if GPU available
- Reduce framerate (60fps → 30fps)

#### 2. Dropped Frames

**Symptoms**: `drop=X` in FFmpeg output increasing  
**Solutions**:
- Increase thread queue size
- Reduce encoding preset complexity
- Check disk I/O (if reading from HDD)
- Monitor CPU throttling (thermal issues)

#### 3. Low Quality Output

**Symptoms**: Visible compression artifacts, blocky video  
**Solutions**:
- Increase bitrate
- Use slower preset (`veryfast` → `fast`)
- Check source video loop quality
- Verify correct resolution scaling

#### 4. Audio/Video Desync

**Symptoms**: Audio drift from video over time  
**Solutions**:
- Ensure audio sample rate is consistent (44100 Hz)
- Check for dropped frames
- Verify audio stream is continuous
- Use `-async 1` flag (can be added to command builder)

#### 5. Stream Buffering

**Symptoms**: Viewers seeing frequent buffering  
**Solutions**:
- Reduce bitrate
- Check upload bandwidth stability
- Verify RTMP server is not overloaded
- Monitor network packet loss

### Performance Monitoring

#### Check Encoding Speed

```bash
# From FFmpeg output
speed=1.00x  # Real-time (good)
speed=0.80x  # Too slow (CPU can't keep up)
speed=1.20x  # Too fast (might indicate issues)
```

**Target**: 0.95x - 1.05x for stable streaming

#### Monitor Resource Usage

```bash
# CPU
top -p <ffmpeg_pid>

# GPU (NVIDIA)
nvidia-smi dmon -s u

# Memory
ps aux | grep ffmpeg

# Network
iftop  # Install: apt install iftop
```

### Debug Commands

#### Test Encoding Speed

```bash
# Benchmark encoding (no streaming)
ffmpeg -re -stream_loop -1 -i loop.mp4 \
  -c:v libx264 -preset veryfast -b:v 3000k \
  -f null -

# Check speed= in output
```

#### Validate Output

```bash
# Test RTMP push locally
ffplay rtmp://localhost:1935/live/stream

# Check stream info
ffprobe rtmp://localhost:1935/live/stream
```

---

## Advanced Configurations

### Custom Encoding Settings

Create custom encoding config:

```python
from dataclasses import dataclass
from ffmpeg_manager.config import EncodingConfig, ENCODING_PRESETS, EncodingPreset

# Define custom preset
ENCODING_PRESETS[EncodingPreset.PRESET_720P_FAST] = EncodingConfig(
    name="Custom 720p",
    resolution="1280:720",
    video_codec="libx264",
    video_bitrate="3200k",  # Custom bitrate
    video_preset="faster",   # Custom preset
    audio_codec="aac",
    audio_bitrate="256k",    # Higher audio quality
    audio_sample_rate="48000",  # Higher sample rate
    framerate=30,
    keyframe_interval=30,    # Smaller GOP for faster seeking
    pixel_format="yuv420p",
    use_nvenc=False,
)
```

### Two-Pass Encoding (Not Recommended for Live)

For pre-encoding video loops:

```bash
# Pass 1
ffmpeg -i source.mp4 -c:v libx264 -b:v 3000k -pass 1 -f null -

# Pass 2
ffmpeg -i source.mp4 -c:v libx264 -b:v 3000k -pass 2 output.mp4
```

### Hardware-Accelerated Decoding

Decode input with GPU (NVDEC):

```python
# Add to command builder
cmd = [
    "ffmpeg",
    "-hwaccel", "cuda",  # Use CUDA hardware acceleration
    "-hwaccel_output_format", "cuda",  # Keep frames on GPU
    "-i", input_file,
    # ... rest of encoding
]
```

**Note**: May reduce CPU usage by 10-20% if decoding is bottleneck.

### Audio Processing

#### Normalize Audio Levels

```python
# Add audio filter
filters.append("loudnorm=I=-16:LRA=11:TP=-1.5")  # EBU R128 loudness
```

#### Stereo Enhancement

```python
filters.append("extrastereo=m=1.5")  # Enhance stereo separation
```

### Multiple Output Formats

Stream to multiple destinations:

```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -b:v 3000k -f flv rtmp://youtube.com/live/KEY1 \
  -c:v libx264 -b:v 2000k -f flv rtmp://twitch.tv/live/KEY2
```

---

## Best Practices

### For 24/7 Reliability

1. **Use `veryfast` or `fast` preset** - Prevents CPU overload
2. **Set appropriate bitrate** - Match your upload bandwidth
3. **Enable auto-recovery** - Process manager handles crashes
4. **Monitor dropped frames** - Alert if >100 in an hour
5. **Test before going live** - Run for 1 hour locally first

### For Quality

1. **Higher bitrate** - If bandwidth allows
2. **Slower preset** - If CPU allows (fast/medium)
3. **Good source loops** - Garbage in, garbage out
4. **Consistent resolution** - Don't upscale, maintain native res
5. **GOP size = framerate** - Better quality for live streams

### For Performance

1. **NVENC if available** - Frees up CPU
2. **SSD for video loops** - Faster disk I/O
3. **Wired network** - Avoid WiFi for reliability
4. **Dedicated server** - Don't run other heavy processes
5. **Monitor temperature** - Prevent thermal throttling

---

## YouTube-Specific Recommendations

### Recommended Settings for YouTube Live

| Quality | Resolution | FPS | Bitrate | Preset |
|---------|-----------|-----|---------|--------|
| Standard | 1280x720 | 30 | 2500k | 720p_fast |
| High | 1920x1080 | 30 | 4500k | 1080p_fast or 1080p_nvenc |
| Maximum | 1920x1080 | 60 | 7000k | 1080p60_nvenc |

### YouTube Ingestion Limits

- **Maximum bitrate**: 51 Mbps (way more than needed)
- **Maximum resolution**: 3840x2160 (4K)
- **Maximum framerate**: 60 fps
- **Required keyframe interval**: 2 seconds (60 frames @ 30fps)

Our defaults (keyframe_interval=50 @ 30fps ≈ 1.67s) are within limits.

---

## Appendix

### FFmpeg Command Breakdown

```bash
ffmpeg                                    # FFmpeg binary
  -re                                     # Read input at native framerate
  -stream_loop -1                         # Loop video indefinitely
  -thread_queue_size 512                  # Input buffer size
  -i /srv/loops/video.mp4                # Video input
  -thread_queue_size 512                  # Input buffer size
  -i http://audio:8000/stream            # Audio input
  -map 0:v                               # Map video from input 0
  -map 1:a                               # Map audio from input 1
  -vf "fade=t=in:st=0:d=1,scale=1280:720,format=yuv420p,fps=30"  # Video filters
  -c:v libx264                           # Video codec
  -preset veryfast                        # x264 encoding speed
  -b:v 2500k                             # Video bitrate
  -maxrate 2500k                         # Max bitrate (CBR)
  -bufsize 5000k                         # Rate control buffer
  -g 50                                  # GOP size (keyframe interval)
  -keyint_min 50                         # Minimum keyframe interval
  -sc_threshold 0                        # Disable scene change detection
  -pix_fmt yuv420p                       # Pixel format
  -af "afade=t=in:ss=0:d=1"             # Audio fade-in
  -c:a aac                               # Audio codec
  -b:a 192k                              # Audio bitrate
  -ar 44100                              # Audio sample rate
  -ac 2                                  # Audio channels (stereo)
  -f flv                                 # Output format
  rtmp://nginx-rtmp:1935/live/stream    # Output destination
```

### Resource Links

- **FFmpeg Documentation**: https://ffmpeg.org/documentation.html
- **x264 Encoding Guide**: https://trac.ffmpeg.org/wiki/Encode/H.264
- **NVENC Guide**: https://docs.nvidia.com/video-technologies/video-codec-sdk/
- **YouTube Live Specs**: https://support.google.com/youtube/answer/2853702

---

**Last Updated**: November 5, 2025  
**Part of**: SHARD-4 (FFmpeg Process Manager)  
**Project**: 24/7 FFmpeg YouTube Radio Stream



