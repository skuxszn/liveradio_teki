#!/usr/bin/env python3
"""
Generate a default video loop from a static image.

This script creates a simple MP4 video loop from a static image
that can be used as the fallback loop when no track-specific loop is available.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_default_loop(
    output_path: str,
    input_image: str | None = None,
    duration: int = 10,
    resolution: str = "1280:720",
    fps: int = 30,
    bitrate: str = "3000k",
) -> bool:
    """
    Create a default video loop from an image or color.

    Args:
        output_path: Path where to save the MP4 file
        input_image: Optional input image. If None, creates colored background.
        duration: Duration of the loop in seconds
        resolution: Video resolution (width:height)
        fps: Frames per second
        bitrate: Video bitrate

    Returns:
        True if successful, False otherwise
    """
    try:
        if input_image and Path(input_image).exists():
            # Create loop from image
            logger.info(f"Creating loop from image: {input_image}")
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-loop",
                "1",
                "-i",
                input_image,
                "-t",
                str(duration),
                "-vf",
                f"scale={resolution},format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-tune",
                "stillimage",
                "-r",
                str(fps),
                "-b:v",
                bitrate,
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                output_path,
            ]
        else:
            # Create loop from color test pattern
            logger.info("Creating loop from test pattern")
            width, height = resolution.split(":")
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x1a1a2e:s={width}x{height}:d={duration}:r={fps}",
                "-f",
                "lavfi",
                "-i",
                f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
                "-filter_complex",
                "[0:v][1:v]blend=all_mode=screen:all_opacity=0.3[v]",
                "-map",
                "[v]",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-b:v",
                bitrate,
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                output_path,
            ]

        logger.info(f"Running FFmpeg command...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        logger.info(f"✓ Default loop created: {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Failed to create default loop: {e}")
        return False


def add_text_overlay(
    video_path: str,
    output_path: str,
    text: str = "Default Loop",
) -> bool:
    """
    Add a text overlay to a video.

    Args:
        video_path: Input video path
        output_path: Output video path
        text: Text to overlay

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Adding text overlay...")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            f"drawtext=text='{text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5:boxborderw=10",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            output_path,
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"✓ Text overlay added: {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Failed to add text overlay: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate a default video loop from an image or pattern"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="/srv/loops/default.mp4",
        help="Output MP4 file path (default: /srv/loops/default.mp4)",
    )
    parser.add_argument(
        "-i",
        "--input",
        help="Input image file (PNG/JPG). If not provided, creates a test pattern.",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        default=10,
        help="Duration in seconds (default: 10)",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        default="1280:720",
        help="Resolution in width:height format (default: 1280:720)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Frames per second (default: 30)",
    )
    parser.add_argument(
        "-b",
        "--bitrate",
        default="3000k",
        help="Video bitrate (default: 3000k)",
    )
    parser.add_argument(
        "-t",
        "--text",
        help="Add text overlay",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create the loop
    if args.text:
        # Create temporary file, add text, then move
        temp_path = str(output_path.with_suffix(".tmp.mp4"))
        success = create_default_loop(
            temp_path,
            args.input,
            args.duration,
            args.resolution,
            args.fps,
            args.bitrate,
        )
        if success:
            success = add_text_overlay(temp_path, str(output_path), args.text)
            # Clean up temp file
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
    else:
        success = create_default_loop(
            str(output_path),
            args.input,
            args.duration,
            args.resolution,
            args.fps,
            args.bitrate,
        )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
