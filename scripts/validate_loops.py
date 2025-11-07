#!/usr/bin/env python3
"""Validate Loop Files - Verify all referenced MP4 files exist

Checks:
- File exists and is readable
- File is a valid MP4 (using ffprobe)
- File size is reasonable (>1KB)
- Resolution matches expected (optional)
- Duration is >5 seconds (for looping)

Usage:
    python scripts/validate_loops.py
    python scripts/validate_loops.py --check-format
    python scripts/validate_loops.py --fix-missing
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from track_mapper.config import TrackMapperConfig  # noqa: E402
from track_mapper.mapper import TrackMapper  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_file_exists(file_path: str) -> bool:
    """Check if file exists and is readable.

    Args:
        file_path: Path to file

    Returns:
        True if file exists and is readable
    """
    try:
        return os.path.isfile(file_path) and os.access(file_path, os.R_OK)
    except Exception:
        return False


def get_file_size(file_path: str) -> int:
    """Get file size in bytes.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes, or 0 if error
    """
    try:
        return os.path.getsize(file_path)
    except Exception:
        return 0


def probe_video_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Use ffprobe to get video file metadata.

    Args:
        file_path: Path to video file

    Returns:
        Dictionary with metadata, or None if error
    """
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", file_path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            logger.debug(f"ffprobe error: {result.stderr}")
            return None

        data = json.loads(result.stdout)

        # Extract relevant info
        format_info = data.get("format", {})
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"), None
        )

        if not video_stream:
            return None

        return {
            "duration": float(format_info.get("duration", 0)),
            "size": int(format_info.get("size", 0)),
            "format_name": format_info.get("format_name", ""),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "codec": video_stream.get("codec_name", ""),
            "fps": eval(video_stream.get("r_frame_rate", "0/1")),
        }

    except subprocess.TimeoutExpired:
        logger.error(f"ffprobe timeout for: {file_path}")
        return None
    except Exception as e:
        logger.debug(f"ffprobe error for {file_path}: {e}")
        return None


def validate_mapping(
    track_key: str,
    loop_path: str,
    check_format: bool = False,
    expected_resolution: Optional[tuple] = None,
) -> Dict[str, Any]:
    """Validate a single mapping.

    Args:
        track_key: Track key
        loop_path: Path to loop file
        check_format: Perform ffprobe format check
        expected_resolution: Expected (width, height), None to skip

    Returns:
        Dictionary with validation results
    """
    result = {"track_key": track_key, "loop_path": loop_path, "valid": True, "issues": []}

    # Check file exists
    if not check_file_exists(loop_path):
        result["valid"] = False
        result["issues"].append("File not found or not readable")
        return result

    # Check file size
    size = get_file_size(loop_path)
    if size < 1024:  # Less than 1KB
        result["valid"] = False
        result["issues"].append(f"File too small: {size} bytes")
        return result

    result["size_mb"] = round(size / (1024 * 1024), 2)

    # Check format with ffprobe (optional)
    if check_format:
        metadata = probe_video_file(loop_path)

        if not metadata:
            result["valid"] = False
            result["issues"].append("Invalid video format or ffprobe failed")
            return result

        result["metadata"] = metadata

        # Check duration
        if metadata["duration"] < 5.0:
            result["issues"].append(f"Duration too short for looping: {metadata['duration']:.1f}s")

        # Check codec
        if metadata["codec"] not in ["h264", "hevc", "vp9", "av1"]:
            result["issues"].append(f"Unusual codec (may work): {metadata['codec']}")

        # Check resolution
        if expected_resolution:
            exp_width, exp_height = expected_resolution
            if metadata["width"] != exp_width or metadata["height"] != exp_height:
                result["issues"].append(
                    f"Resolution mismatch: {metadata['width']}x{metadata['height']} "
                    f"(expected {exp_width}x{exp_height})"
                )

    return result


def validate_all_mappings(
    mapper: TrackMapper,
    check_format: bool = False,
    expected_resolution: Optional[tuple] = None,
    fix_missing: bool = False,
) -> Dict[str, Any]:
    """Validate all mappings in database.

    Args:
        mapper: TrackMapper instance
        check_format: Perform ffprobe format checks
        expected_resolution: Expected (width, height)
        fix_missing: Deactivate mappings with missing files

    Returns:
        Dictionary with validation statistics
    """
    logger.info("Fetching all mappings from database...")
    mappings = mapper.get_all_mappings(active_only=True)

    if not mappings:
        logger.warning("No active mappings found")
        return {"total": 0, "valid": 0, "invalid": 0, "fixed": 0}

    logger.info(f"Validating {len(mappings)} mappings...")

    stats = {"total": len(mappings), "valid": 0, "invalid": 0, "fixed": 0, "issues": []}

    for mapping in mappings:
        track_key = mapping["track_key"]
        loop_path = mapping["loop_file_path"]

        result = validate_mapping(
            track_key, loop_path, check_format=check_format, expected_resolution=expected_resolution
        )

        if result["valid"]:
            stats["valid"] += 1
            if check_format and result.get("issues"):
                logger.warning(f"✓ {track_key}: VALID with warnings")
                for issue in result["issues"]:
                    logger.warning(f"  - {issue}")
                stats["issues"].append(result)
            else:
                logger.debug(f"✓ {track_key}: VALID")
        else:
            stats["invalid"] += 1
            logger.error(f"✗ {track_key}: INVALID")
            for issue in result["issues"]:
                logger.error(f"  - {issue}")

            stats["issues"].append(result)

            # Fix by deactivating
            if fix_missing and "not found" in " ".join(result["issues"]).lower():
                try:
                    mapper.delete_mapping(track_key)
                    logger.info("  → Deactivated mapping")
                    stats["fixed"] += 1
                except Exception as e:
                    logger.error(f"  → Failed to deactivate: {e}")

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate all track-to-loop mappings")

    parser.add_argument(
        "--check-format", action="store_true", help="Use ffprobe to validate video format (slower)"
    )
    parser.add_argument(
        "--resolution", help="Expected resolution in format WIDTHxHEIGHT (e.g., 1280x720)"
    )
    parser.add_argument(
        "--fix-missing", action="store_true", help="Deactivate mappings with missing files"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse expected resolution
    expected_resolution = None
    if args.resolution:
        try:
            width, height = args.resolution.split("x")
            expected_resolution = (int(width), int(height))
            logger.info(f"Expected resolution: {expected_resolution[0]}x{expected_resolution[1]}")
        except ValueError:
            logger.error(f"Invalid resolution format: {args.resolution}")
            return 1

    try:
        # Initialize mapper
        config = TrackMapperConfig.from_env()
        logger.info(f"Connecting to database: {config.postgres_db}")

        with TrackMapper(config) as mapper:
            # Validate all mappings
            stats = validate_all_mappings(
                mapper,
                check_format=args.check_format,
                expected_resolution=expected_resolution,
                fix_missing=args.fix_missing,
            )

            # Print summary
            logger.info("")
            logger.info("=" * 60)
            logger.info("VALIDATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total mappings: {stats['total']}")
            logger.info(
                f"Valid: {stats['valid']} ({stats['valid']/stats['total']*100:.1f}%)"
                if stats["total"] > 0
                else "Valid: 0"
            )
            logger.info(f"Invalid: {stats['invalid']}")
            if args.fix_missing:
                logger.info(f"Fixed (deactivated): {stats['fixed']}")
            if stats["issues"]:
                logger.info(f"Warnings/Issues: {len(stats['issues'])}")
            logger.info("=" * 60)

            # Exit with error code if invalid mappings found
            return 0 if stats["invalid"] == 0 else 1

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
