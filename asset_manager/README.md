# Asset Manager

Video asset management module for the 24/7 FFmpeg YouTube Radio Stream project.

## Overview

The Asset Manager module provides comprehensive video loop management, including:
- Video file validation using ffprobe
- Metadata extraction from MP4 files
- Dynamic overlay generation with track information
- Asset cleanup and storage management

## Installation

The module is part of the main project. Ensure dependencies are installed:

```bash
pip install -r requirements-dev.txt
```

Required external tools:
- **FFmpeg/ffprobe**: For video validation and metadata extraction
- **Pillow**: For overlay generation

## Quick Start

```python
from asset_manager import AssetManager

# Initialize the manager
manager = AssetManager()

# Validate a video loop
result = manager.validate_loop("/srv/loops/track_123.mp4")
if result.valid:
    print("✓ Video is valid")
else:
    print(f"✗ Validation errors: {result.errors}")

# Get video metadata
metadata = manager.get_loop_metadata("/srv/loops/track_123.mp4")
print(f"Duration: {metadata['duration']}s")
print(f"Resolution: {metadata['width']}x{metadata['height']}")

# Generate "Now Playing" overlay
overlay_path = manager.generate_overlay(
    artist="Artist Name",
    title="Song Title",
    album="Album Name"
)
print(f"Overlay generated: {overlay_path}")
```

## API Reference

### AssetManager

Main interface for asset management operations.

#### Methods

##### `validate_loop(file_path: str) -> ValidationResult`

Validate a video loop file.

**Parameters:**
- `file_path`: Path to the MP4 file

**Returns:**
- `ValidationResult` object with `valid` (bool), `errors` (list), and `metadata` (dict)

**Validation checks:**
- File exists and is readable
- Format is MP4 container
- Video codec is H.264
- Resolution matches target (default: 1280x720)
- Duration ≥ minimum (default: 5 seconds)
- Audio codec is allowed (AAC or none)

**Example:**
```python
result = manager.validate_loop("/srv/loops/track.mp4")
if not result.valid:
    for error in result.errors:
        print(f"Error: {error}")
```

##### `get_loop_metadata(file_path: str) -> dict`

Extract metadata from a video file.

**Parameters:**
- `file_path`: Path to the MP4 file

**Returns:**
- Dictionary with video metadata:
  - `duration`: Video duration in seconds
  - `width`: Video width in pixels
  - `height`: Video height in pixels
  - `video_codec`: Video codec name (e.g., "h264")
  - `audio_codec`: Audio codec name or None
  - `bitrate`: Bitrate in bits/second
  - `fps`: Frames per second
  - `format_name`: Container format
  - `file_size`: File size in bytes

**Example:**
```python
metadata = manager.get_loop_metadata("/srv/loops/track.mp4")
print(f"Video: {metadata['width']}x{metadata['height']} @ {metadata['fps']}fps")
print(f"Duration: {metadata['duration']:.2f}s")
```

##### `generate_overlay(artist: str, title: str, template: str = None, album: str = None) -> str`

Generate a PNG overlay with track information.

**Parameters:**
- `artist`: Artist name
- `title`: Song title
- `template`: Optional template filename (from templates directory)
- `album`: Optional album name

**Returns:**
- Absolute path to generated PNG file

**Notes:**
- Overlays are cached based on content hash
- Cached overlays are reused if fresh (within TTL)
- Default: lower-third overlay with semi-transparent background

**Example:**
```python
# Basic overlay
overlay = manager.generate_overlay("Artist", "Title")

# With album
overlay = manager.generate_overlay("Artist", "Title", album="Album")

# Using template
overlay = manager.generate_overlay("Artist", "Title", template="custom.png")
```

##### `cleanup_old_overlays(older_than_hours: int = None) -> int`

Remove overlay files older than specified hours.

**Parameters:**
- `older_than_hours`: Age threshold in hours (default: from config, usually 1 hour)

**Returns:**
- Number of files deleted

**Example:**
```python
deleted = manager.cleanup_old_overlays(older_than_hours=24)
print(f"Cleaned up {deleted} old overlays")
```

##### `ensure_default_loop_exists() -> bool`

Verify that the default loop file exists and is valid.

**Returns:**
- `True` if default loop is valid, `False` otherwise

**Example:**
```python
if not manager.ensure_default_loop_exists():
    print("Warning: Default loop is missing or invalid")
```

##### `get_loop_or_default(file_path: str) -> str`

Get a validated loop path or fall back to default.

**Parameters:**
- `file_path`: Requested loop file path

**Returns:**
- Validated loop path or default loop path if validation fails

**Example:**
```python
safe_loop = manager.get_loop_or_default("/srv/loops/track_123.mp4")
# Use safe_loop in FFmpeg command
```

##### `validate_all_loops_in_directory(directory: str = None) -> dict`

Validate all MP4 files in a directory.

**Parameters:**
- `directory`: Directory to scan (default: `/srv/loops/tracks`)

**Returns:**
- Dictionary with statistics:
  ```python
  {
      "total": 10,
      "valid": 8,
      "invalid": 2,
      "errors": [
          {
              "file": "/path/to/invalid.mp4",
              "errors": ["Resolution mismatch", ...]
          }
      ]
  }
  ```

**Example:**
```python
results = manager.validate_all_loops_in_directory("/srv/loops/tracks")
print(f"{results['valid']}/{results['total']} loops are valid")
```

##### `get_storage_stats() -> dict`

Get storage statistics for loop assets.

**Returns:**
- Dictionary with storage info:
  ```python
  {
      "loops_count": 50,
      "overlays_count": 120,
      "total_size_mb": 1234.56,
      "loops_size_mb": 1200.00,
      "overlays_size_mb": 34.56
  }
  ```

**Example:**
```python
stats = manager.get_storage_stats()
print(f"Total storage: {stats['total_size_mb']:.2f} MB")
print(f"Loops: {stats['loops_count']} files")
```

### VideoValidator

Low-level validator for video files (usually accessed via AssetManager).

### OverlayGenerator

Low-level overlay generator (usually accessed via AssetManager).

## Configuration

Configuration is managed via environment variables or `AssetConfig`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOPS_BASE_PATH` | `/srv/loops` | Base directory for video loops |
| `DEFAULT_LOOP_PATH` | `/srv/loops/default.mp4` | Default fallback loop |
| `OVERLAYS_PATH` | `/srv/loops/overlays` | Directory for generated overlays |
| `TEMPLATES_PATH` | `/srv/loops/templates` | Directory for overlay templates |
| `TARGET_RESOLUTION` | `1280:720` | Expected video resolution |
| `MIN_DURATION_SECONDS` | `5` | Minimum video duration |
| `REQUIRED_VIDEO_CODEC` | `h264` | Required video codec |
| `ALLOWED_AUDIO_CODECS` | `aac,none` | Allowed audio codecs |
| `OVERLAY_TTL_HOURS` | `1` | Overlay cache TTL |
| `OVERLAY_FONT_SIZE` | `48` | Font size for overlays |
| `OVERLAY_FONT_COLOR` | `#FFFFFF` | Font color (hex) |
| `OVERLAY_BACKGROUND_COLOR` | `#000000` | Background color (hex) |
| `OVERLAY_OPACITY` | `180` | Background opacity (0-255) |
| `VALIDATION_TIMEOUT_SECONDS` | `10` | FFprobe timeout |
| `FFPROBE_PATH` | `ffprobe` | Path to ffprobe binary |
| `FFMPEG_PATH` | `ffmpeg` | Path to ffmpeg binary |

### Custom Configuration

```python
from asset_manager import AssetManager
from asset_manager.config import AssetConfig

config = AssetConfig(
    loops_base_path="/custom/loops",
    target_resolution="1920:1080",
    min_duration_seconds=10
)

manager = AssetManager(config)
```

## Command-Line Scripts

### Validate All Loops

```bash
# Validate all loops in default directory
python scripts/validate_all_loops.py

# Validate specific directory
python scripts/validate_all_loops.py /path/to/loops

# Export results to JSON
python scripts/validate_all_loops.py -o results.json

# Validate only default loop
python scripts/validate_all_loops.py --default-loop

# Verbose output
python scripts/validate_all_loops.py -v
```

### Generate Default Loop

```bash
# Generate from test pattern
python scripts/generate_default_loop.py

# Generate from image
python scripts/generate_default_loop.py -i /path/to/image.png

# Specify output path
python scripts/generate_default_loop.py -o /srv/loops/default.mp4

# Custom duration and resolution
python scripts/generate_default_loop.py -d 20 -r 1920:1080

# Add text overlay
python scripts/generate_default_loop.py -t "Default Loop"
```

## Integration Examples

### With FFmpeg Manager (SHARD-4)

```python
from asset_manager import AssetManager
from ffmpeg_manager import FFmpegManager

asset_mgr = AssetManager()
ffmpeg_mgr = FFmpegManager()

# Get validated loop path
loop_path = asset_mgr.get_loop_or_default("/srv/loops/track_123.mp4")

# Generate overlay
overlay_path = asset_mgr.generate_overlay("Artist", "Title")

# Build FFmpeg command with overlay
cmd = ffmpeg_mgr.build_command(
    loop_path=loop_path,
    overlay_path=overlay_path,  # Optional
    audio_url="http://azuracast:8000/radio",
    rtmp_endpoint="rtmp://nginx-rtmp:1935/live/stream"
)
```

### With Track Mapper (SHARD-3)

```python
from asset_manager import AssetManager
from track_mapper import TrackMapper

asset_mgr = AssetManager()
track_mapper = TrackMapper()

# Get loop path from track mapper
loop_path = track_mapper.get_loop("Artist", "Title")

# Validate before use
result = asset_mgr.validate_loop(loop_path)
if not result.valid:
    loop_path = asset_mgr.config.default_loop_path
```

### With Logging Module (SHARD-5)

```python
from asset_manager import AssetManager
from logging_module import Logger

asset_mgr = AssetManager()
logger = Logger()

# Validate and log errors
result = asset_mgr.validate_loop(loop_path)
if not result.valid:
    logger.log_error(
        service="asset_manager",
        severity="error",
        message=f"Loop validation failed: {loop_path}",
        context={"errors": result.errors}
    )
```

## Performance

Typical performance on modern hardware:

- **Video Validation**: < 100ms per file (ffprobe execution)
- **Overlay Generation**: < 500ms (with font rendering)
- **Cached Overlay**: < 1ms (file existence check)
- **Batch Validation**: ~100 files/minute

### Optimization Tips

1. **Use caching**: Overlays are automatically cached
2. **Cleanup regularly**: Run `cleanup_old_overlays()` periodically
3. **Validate once**: Cache validation results for frequently used loops
4. **Use default loop**: For unknown tracks, avoid repeated validation failures

## Testing

Run tests with coverage:

```bash
pytest asset_manager/tests/ -v --cov=asset_manager
```

Current coverage: **95%** (46 tests passing)

## Known Limitations

1. **Font availability**: Overlay generation requires system fonts; falls back to default if unavailable
2. **Template system**: Current template support is basic; future enhancement planned
3. **Video formats**: Only MP4 container with H.264 video is validated
4. **Synchronous operations**: All operations are synchronous (no async support yet)

## Troubleshooting

### FFprobe Not Found

```
RuntimeError: ffprobe not found at: ffprobe
```

**Solution**: Install FFmpeg or set `FFPROBE_PATH` environment variable

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# Or specify path
export FFPROBE_PATH=/usr/local/bin/ffprobe
```

### Font Warnings

```
WARNING: System fonts not found, using default
```

**Solution**: Install DejaVu fonts (optional, overlay still works)

```bash
sudo apt-get install fonts-dejavu
```

### Validation Timeouts

```
RuntimeError: ffprobe timeout after 10s
```

**Solution**: Increase timeout or check file integrity

```python
config = AssetConfig(validation_timeout_seconds=30)
```

## Future Enhancements

- [ ] Async/await support for better performance
- [ ] Advanced template system with JSON metadata
- [ ] Video thumbnail generation
- [ ] Support for additional video formats (WebM, AVI)
- [ ] Automatic video conversion to target format
- [ ] Integration with CDN for remote loops
- [ ] Overlay animation support

## License

Part of the 24/7 FFmpeg YouTube Radio Stream project.

## Support

For issues or questions, check:
- [Main Project README](../README.md)
- [Asset Preparation Guide](../docs/ASSET_PREPARATION.md)
- [Integration Documentation](../docs/ARCHITECTURE.md)



