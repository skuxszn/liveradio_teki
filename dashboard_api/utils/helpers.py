"""Helper utility functions."""

import subprocess
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_video_metadata(video_path: Path) -> Optional[dict]:
    """Extract video metadata using ffprobe.

    Args:
        video_path: Path to video file.

    Returns:
        Optional[dict]: Video metadata or None if extraction fails.
    """
    if not video_path.exists():
        return None

    try:
        # Use ffprobe to get video information
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return None

        import json

        data = json.loads(result.stdout)

        # Extract video stream info
        video_stream = next(
            (s for s in data.get("streams", []) if s["codec_type"] == "video"), None
        )

        # Extract audio stream info
        audio_stream = next(
            (s for s in data.get("streams", []) if s["codec_type"] == "audio"), None
        )

        if not video_stream:
            return None

        format_info = data.get("format", {})

        metadata = {
            "duration": float(format_info.get("duration", 0)),
            "file_size": int(format_info.get("size", 0)),
            "bitrate": int(format_info.get("bit_rate", 0)) // 1000,  # Convert to kbps
            "resolution": f"{video_stream.get('width')}x{video_stream.get('height')}",
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "frame_rate": eval(video_stream.get("r_frame_rate", "0/1")),
            "video_codec": video_stream.get("codec_name", "unknown"),
            "pixel_format": video_stream.get("pix_fmt", "unknown"),
            "audio_codec": audio_stream.get("codec_name", "unknown") if audio_stream else "none",
        }

        return metadata

    except Exception as e:
        logger.error(f"Failed to extract video metadata: {e}")
        return None


def validate_video_file(
    video_path: Path, required_resolution: Optional[str] = None
) -> tuple[bool, list[str]]:
    """Validate video file meets requirements.

    Args:
        video_path: Path to video file.
        required_resolution: Optional required resolution (e.g., "1280x720").

    Returns:
        tuple[bool, list[str]]: (is_valid, list of error messages).
    """
    errors = []

    metadata = get_video_metadata(video_path)
    if not metadata:
        errors.append("Could not extract video metadata")
        return False, errors

    # Check codec
    if metadata["video_codec"] not in ["h264", "hevc"]:
        errors.append(f"Unsupported video codec: {metadata['video_codec']} (must be H.264 or HEVC)")

    # Check pixel format
    if metadata["pixel_format"] != "yuv420p":
        errors.append(f"Unsupported pixel format: {metadata['pixel_format']} (must be yuv420p)")

    # Check duration
    if metadata["duration"] < 5:
        errors.append(f"Video too short: {metadata['duration']}s (minimum 5 seconds)")

    # Check resolution if specified
    if required_resolution:
        if metadata["resolution"] != required_resolution:
            errors.append(
                f"Resolution mismatch: {metadata['resolution']} (expected {required_resolution})"
            )

    return len(errors) == 0, errors


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes.

    Returns:
        str: Formatted size (e.g., "1.5 MB").
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format.

    Args:
        seconds: Duration in seconds.

    Returns:
        str: Formatted duration (e.g., "1h 23m 45s").
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)

