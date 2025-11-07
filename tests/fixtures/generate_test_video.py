#!/usr/bin/env python3
"""
Generate test video loops for testing purposes
"""
import subprocess
import sys
from pathlib import Path


def generate_test_loop(
    output_path: str,
    duration: int = 10,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    text: str = "TEST LOOP",
):
    """
    Generate a test video loop using FFmpeg.

    Args:
        output_path: Path to save the output video
        duration: Duration in seconds
        width: Video width
        height: Video height
        fps: Frames per second
        text: Text to display on video
    """
    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=1000:duration={duration}",
        "-vf",
        f"drawtext=text='{text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-y",  # Overwrite output file
        output_path,
    ]

    print(f"Generating test loop: {output_path}")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✓ Generated: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to generate {output_path}")
        print(f"Error: {e.stderr.decode()}")
        return False


def main():
    """Generate test video loops."""
    # Create loops directory
    loops_dir = Path(__file__).parent / "loops"
    loops_dir.mkdir(exist_ok=True)

    # Generate test loops
    test_loops = [
        ("default.mp4", "DEFAULT LOOP"),
        ("track_123_loop.mp4", "TRACK 123"),
        ("track_456_loop.mp4", "TRACK 456"),
        ("track_789_loop.mp4", "TRACK 789"),
        ("invalid_resolution.mp4", "INVALID RES"),
    ]

    success_count = 0
    for filename, text in test_loops:
        output_path = str(loops_dir / filename)

        # Use different resolution for invalid_resolution.mp4
        if filename == "invalid_resolution.mp4":
            if generate_test_loop(output_path, duration=5, width=640, height=480, text=text):
                success_count += 1
        else:
            if generate_test_loop(output_path, duration=10, text=text):
                success_count += 1

    print(f"\n✓ Generated {success_count}/{len(test_loops)} test loops")

    # Generate a corrupt video file for testing
    corrupt_file = loops_dir / "corrupt.mp4"
    with open(corrupt_file, "wb") as f:
        f.write(b"This is not a valid MP4 file")
    print(f"✓ Generated corrupt test file: {corrupt_file}")

    return 0 if success_count == len(test_loops) else 1


if __name__ == "__main__":
    sys.exit(main())
