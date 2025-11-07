# Video Loop Asset Preparation Guide

This guide explains how to prepare MP4 video loops for the 24/7 FFmpeg YouTube Radio Stream system.

## Overview

Video loops are the visual component displayed during audio playback. Each track can have its own dedicated loop, creating a unique visual experience for viewers.

## Requirements

### Video Specifications

| Property | Requirement | Notes |
|----------|-------------|-------|
| **Container** | MP4 | `.mp4` file extension |
| **Video Codec** | H.264 (x264) | High compatibility |
| **Resolution** | 1280x720 (720p) | Configurable, but consistent |
| **Frame Rate** | 30 fps | Or 25/60 fps, be consistent |
| **Duration** | ≥ 5 seconds | Minimum for smooth looping |
| **Pixel Format** | YUV420p | Required for YouTube streaming |
| **Audio** | None or AAC | Optional, will be replaced by stream audio |
| **Bitrate** | 2-5 Mbps | Balance quality and file size |

### File Organization

```
/srv/loops/
├── default.mp4              # Fallback loop (required)
├── tracks/
│   ├── track_001.mp4
│   ├── track_002.mp4
│   └── ...
├── overlays/                # Auto-generated overlays
│   └── [hash].png
└── templates/               # Overlay templates
    └── custom_template.png
```

## Preparation Methods

### Method 1: From Video File

If you have an existing video file (MP4, AVI, MOV, etc.):

```bash
ffmpeg -i input.mp4 \
  -vf "scale=1280:720,fps=30,format=yuv420p" \
  -c:v libx264 \
  -preset medium \
  -crf 20 \
  -b:v 3000k \
  -maxrate 4000k \
  -bufsize 8000k \
  -an \
  -movflags +faststart \
  output_loop.mp4
```

**Parameters explained:**
- `-vf scale=1280:720`: Resize to 720p
- `-vf fps=30`: Set frame rate to 30 fps
- `-vf format=yuv420p`: Set pixel format
- `-c:v libx264`: Use H.264 codec
- `-preset medium`: Encoding speed/quality balance
- `-crf 20`: Quality level (lower = higher quality)
- `-b:v 3000k`: Target bitrate
- `-an`: Remove audio
- `-movflags +faststart`: Optimize for streaming

### Method 2: From Static Image

Create a loop from a single image:

```bash
ffmpeg -loop 1 \
  -i image.jpg \
  -t 10 \
  -vf "scale=1280:720,format=yuv420p" \
  -c:v libx264 \
  -preset medium \
  -tune stillimage \
  -r 30 \
  -b:v 3000k \
  -pix_fmt yuv420p \
  -movflags +faststart \
  output_loop.mp4
```

**New parameters:**
- `-loop 1`: Loop the input
- `-t 10`: Duration (10 seconds)
- `-tune stillimage`: Optimize for static images

### Method 3: From Image Sequence

Animate a series of images:

```bash
ffmpeg -framerate 30 \
  -pattern_type glob \
  -i 'frames/*.png' \
  -vf "scale=1280:720,format=yuv420p" \
  -c:v libx264 \
  -preset medium \
  -r 30 \
  -b:v 3000k \
  -pix_fmt yuv420p \
  -movflags +faststart \
  output_loop.mp4
```

### Method 4: Using Project Script

Generate a default loop with test pattern:

```bash
python scripts/generate_default_loop.py \
  -o /srv/loops/default.mp4 \
  -d 10 \
  -r 1280:720 \
  -t "Default Loop"
```

Or from an image:

```bash
python scripts/generate_default_loop.py \
  -i /path/to/image.png \
  -o /srv/loops/track_123.mp4
```

## Advanced Techniques

### Adding Subtle Motion

Add a slow zoom effect to static images:

```bash
ffmpeg -loop 1 -i image.jpg -t 10 \
  -vf "scale=1400:788,zoompan=z='min(zoom+0.0005,1.1)':d=300:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720,format=yuv420p" \
  -c:v libx264 -preset medium -r 30 -b:v 3000k \
  -pix_fmt yuv420p -movflags +faststart \
  output_loop.mp4
```

### Ken Burns Effect (Pan & Zoom)

```bash
ffmpeg -loop 1 -i image.jpg -t 10 \
  -vf "scale=1600:900,zoompan=z='min(zoom+0.0015,1.5)':d=300:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720,format=yuv420p" \
  -c:v libx264 -preset medium -r 30 -b:v 3000k \
  -pix_fmt yuv420p -movflags +faststart \
  output_loop.mp4
```

### Crossfade Between Images

Create a smooth transition between two images:

```bash
ffmpeg \
  -loop 1 -t 5 -i image1.jpg \
  -loop 1 -t 5 -i image2.jpg \
  -filter_complex "
    [0:v]scale=1280:720,format=yuv420p,fade=t=out:st=4:d=1[v0];
    [1:v]scale=1280:720,format=yuv420p,fade=t=in:st=0:d=1[v1];
    [v0][v1]concat=n=2:v=1:a=0
  " \
  -c:v libx264 -preset medium -r 30 -b:v 3000k \
  -pix_fmt yuv420p -movflags +faststart \
  output_loop.mp4
```

### Adding Text Overlay

Add track information directly to the loop:

```bash
ffmpeg -i input.mp4 \
  -vf "drawtext=text='Artist - Title':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-100:box=1:boxcolor=black@0.5:boxborderw=10,scale=1280:720,format=yuv420p" \
  -c:v libx264 -preset medium -r 30 -b:v 3000k \
  -pix_fmt yuv420p -movflags +faststart \
  output_loop.mp4
```

**Note**: For dynamic text overlays, use the Asset Manager's overlay generation instead.

### Optimizing Loop Length

For seamless looping, ensure the loop duration matches or is a multiple of the average track length:

```bash
# Create a 3-minute loop (typical song length)
ffmpeg -loop 1 -i image.jpg -t 180 \
  -vf "scale=1280:720,format=yuv420p" \
  -c:v libx264 -preset medium -tune stillimage \
  -r 30 -b:v 3000k \
  -pix_fmt yuv420p -movflags +faststart \
  output_loop.mp4
```

## Quality vs. File Size

### High Quality (5-10 MB per 10s)

```bash
ffmpeg -i input.mp4 \
  -vf "scale=1280:720,format=yuv420p" \
  -c:v libx264 -preset slow -crf 18 \
  -b:v 5000k -maxrate 6000k -bufsize 12000k \
  -pix_fmt yuv420p -movflags +faststart \
  output_loop.mp4
```

### Balanced (2-4 MB per 10s) - **Recommended**

```bash
ffmpeg -i input.mp4 \
  -vf "scale=1280:720,format=yuv420p" \
  -c:v libx264 -preset medium -crf 20 \
  -b:v 3000k -maxrate 4000k -bufsize 8000k \
  -pix_fmt yuv420p -movflags +faststart \
  output_loop.mp4
```

### Low File Size (1-2 MB per 10s)

```bash
ffmpeg -i input.mp4 \
  -vf "scale=1280:720,format=yuv420p" \
  -c:v libx264 -preset fast -crf 23 \
  -b:v 2000k -maxrate 2500k -bufsize 5000k \
  -pix_fmt yuv420p -movflags +faststart \
  output_loop.mp4
```

## Validation

After creating loops, validate them:

```bash
# Validate a single file
python scripts/validate_all_loops.py /srv/loops/tracks/track_001.mp4

# Validate entire directory
python scripts/validate_all_loops.py /srv/loops/tracks

# Get detailed output
python scripts/validate_all_loops.py /srv/loops/tracks -v -o validation_report.json
```

### Manual Validation

Check video properties with ffprobe:

```bash
ffprobe -v error \
  -show_entries format=duration,size,bit_rate \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of json \
  output_loop.mp4
```

Expected output:
```json
{
  "streams": [
    {
      "codec_name": "h264",
      "width": 1280,
      "height": 720,
      "r_frame_rate": "30/1"
    }
  ],
  "format": {
    "duration": "10.000000",
    "size": "3840000",
    "bit_rate": "3072000"
  }
}
```

## Bulk Processing

### Batch Convert Images to Loops

```bash
#!/bin/bash
# Convert all JPG images in a directory to loops

INPUT_DIR="./images"
OUTPUT_DIR="/srv/loops/tracks"

for img in "$INPUT_DIR"/*.jpg; do
  basename=$(basename "$img" .jpg)
  ffmpeg -loop 1 -i "$img" -t 10 \
    -vf "scale=1280:720,format=yuv420p" \
    -c:v libx264 -preset medium -tune stillimage \
    -r 30 -b:v 3000k \
    -pix_fmt yuv420p -movflags +faststart \
    "$OUTPUT_DIR/${basename}_loop.mp4"
done
```

### Batch Validate and Report

```bash
#!/bin/bash
# Validate all loops and generate report

python scripts/validate_all_loops.py /srv/loops/tracks \
  -o validation_report.json

# Parse and display summary
cat validation_report.json | jq '{
  total: .total,
  valid: .valid,
  invalid: .invalid,
  success_rate: (.valid / .total * 100 | round)
}'
```

## Asset Sources

### Recommended Sources for Loop Content

1. **Creative Commons Images**
   - Unsplash (https://unsplash.com)
   - Pexels (https://pexels.com)
   - Pixabay (https://pixabay.com)

2. **Creative Commons Videos**
   - Pixabay Videos
   - Pexels Videos
   - Videvo (https://videvo.net)

3. **Generative Art**
   - Processing
   - p5.js
   - Shadertoy exports

4. **Album Art**
   - Use with proper licensing
   - Add motion effects for visual interest

### License Tracking

Document licenses for all assets:

```json
{
  "tracks": [
    {
      "id": "track_123",
      "artist": "Artist Name",
      "title": "Song Title",
      "loop_file": "track_123.mp4",
      "loop_source": "https://unsplash.com/photos/xxx",
      "loop_license": "Unsplash License",
      "loop_author": "Photographer Name",
      "created_date": "2025-11-03"
    }
  ]
}
```

## Troubleshooting

### Loop is Choppy When Streaming

**Problem**: Video appears to stutter during playback

**Solutions**:
1. Ensure keyframe interval matches: `-g 50 -keyint_min 50`
2. Use constant frame rate: `-r 30`
3. Check bitrate isn't too low: minimum 2000k for 720p

### Loop Doesn't Seamlessly Repeat

**Problem**: Visible "jump" when loop restarts

**Solutions**:
1. Use longer loops (10+ seconds)
2. Create content with smooth transitions
3. Add fade in/out at start/end:
   ```bash
   -vf "fade=t=in:st=0:d=1,fade=t=out:st=9:d=1"
   ```

### File Size Too Large

**Problem**: Loops taking too much disk space

**Solutions**:
1. Reduce bitrate: `-b:v 2000k`
2. Increase compression: `-crf 23`
3. Use faster preset: `-preset fast`
4. Reduce duration for static content

### Validation Fails: Wrong Pixel Format

**Problem**: `Validation error: Invalid pixel format`

**Solution**: Ensure `yuv420p` in conversion:
```bash
-vf "format=yuv420p" -pix_fmt yuv420p
```

### Validation Fails: Duration Too Short

**Problem**: `Duration too short: 2.0s (minimum 5s)`

**Solution**: Increase `-t` parameter:
```bash
ffmpeg -loop 1 -i image.jpg -t 10 ...
```

## Best Practices

1. **Consistency**: Use the same resolution and frame rate for all loops
2. **Performance**: Keep loops under 1 minute to reduce memory usage
3. **Seamless**: Design content that looks good when looped
4. **Naming**: Use descriptive filenames: `artist_title_loop.mp4`
5. **Backup**: Keep source files (images, high-res videos) separately
6. **Documentation**: Track licenses and sources for all visual assets
7. **Testing**: Always validate before deploying to production
8. **Optimization**: Use `-movflags +faststart` for faster streaming startup
9. **Default**: Always have a valid `default.mp4` as fallback
10. **Storage**: Monitor disk usage and cleanup old/unused loops

## Integration with Track Mapper

After creating loops, add them to the track mapping database:

```python
from track_mapper import TrackMapper

mapper = TrackMapper()

# Add mapping
mapper.add_mapping(
    track_key="artist - title",
    loop_path="/srv/loops/tracks/track_123.mp4"
)
```

Or use bulk import:

```bash
# Create CSV with mappings
# artist,title,loop_path
# Artist 1,Song 1,/srv/loops/tracks/track_001.mp4

python scripts/seed_mappings.py --csv tracks.csv
```

## Performance Considerations

### Disk I/O

- **SSD recommended**: Faster loop loading and seeking
- **RAID**: Consider RAID 0/10 for large loop libraries
- **NFS**: Network storage adds latency, test thoroughly

### Storage Planning

Estimate storage needs:

```
Average loop size: 3 MB (10 seconds, 3000k bitrate)
Number of tracks: 1000
Total storage: 1000 × 3 MB = 3 GB

Add 20% for overlays and temp files: ~4 GB total
```

## Useful Tools

- **FFmpeg**: Essential for video processing
- **HandBrake**: GUI alternative for batch conversion  
- **Adobe After Effects**: Professional motion graphics
- **Blender**: 3D animations and effects
- **GIMP**: Image editing and preparation
- **Shotcut**: Free video editor

## Additional Resources

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [H.264 Encoding Guide](https://trac.ffmpeg.org/wiki/Encode/H.264)
- [YouTube Streaming Requirements](https://support.google.com/youtube/answer/2853702)
- [Asset Manager README](../asset_manager/README.md)

## Conclusion

Properly prepared video loops enhance the viewer experience. Follow this guide to ensure your loops are optimized, valid, and ready for 24/7 streaming.

For questions or issues, refer to the main project documentation or troubleshooting guides.



