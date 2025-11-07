"""
Pytest configuration and fixtures for asset_manager tests.
"""

import os
import shutil
import subprocess
import tempfile
from typing import Generator

import pytest

from asset_manager.config import AssetConfig


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_config(temp_dir: str) -> AssetConfig:
    """Create a test configuration with temporary paths."""
    loops_path = os.path.join(temp_dir, "loops")
    overlays_path = os.path.join(temp_dir, "overlays")
    templates_path = os.path.join(temp_dir, "templates")

    # Create directories
    os.makedirs(loops_path, exist_ok=True)
    os.makedirs(overlays_path, exist_ok=True)
    os.makedirs(templates_path, exist_ok=True)

    return AssetConfig(
        loops_base_path=loops_path,
        default_loop_path=os.path.join(loops_path, "default.mp4"),
        overlays_path=overlays_path,
        templates_path=templates_path,
        target_resolution="1280:720",
        min_duration_seconds=5,
        required_video_codec="h264",
        allowed_audio_codecs="aac,none",
        overlay_ttl_hours=1,
        validation_timeout_seconds=10,
    )


@pytest.fixture
def test_video_path(temp_dir: str) -> str:
    """Create a test video file."""
    video_path = os.path.join(temp_dir, "test_video.mp4")

    # Create a simple test video using ffmpeg
    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=10:size=1280x720:rate=30",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=stereo",
        "-t",
        "10",
        "-vf",
        "format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-y",
        video_path,
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        # If ffmpeg is not available or fails, skip tests that need it
        pytest.skip("FFmpeg not available or failed to create test video")

    return video_path


@pytest.fixture
def test_video_wrong_resolution(temp_dir: str) -> str:
    """Create a test video with wrong resolution."""
    video_path = os.path.join(temp_dir, "test_video_wrong_res.mp4")

    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=10:size=640x480:rate=30",
        "-t",
        "10",
        "-vf",
        "format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-y",
        video_path,
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("FFmpeg not available")

    return video_path


@pytest.fixture
def test_video_short_duration(temp_dir: str) -> str:
    """Create a test video with short duration."""
    video_path = os.path.join(temp_dir, "test_video_short.mp4")

    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=2:size=1280x720:rate=30",
        "-t",
        "2",
        "-vf",
        "format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-y",
        video_path,
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("FFmpeg not available")

    return video_path


@pytest.fixture
def test_image_path(temp_dir: str) -> str:
    """Create a test image file."""
    from PIL import Image

    image_path = os.path.join(temp_dir, "test_image.png")
    img = Image.new("RGB", (1280, 720), color="blue")
    img.save(image_path)

    return image_path
