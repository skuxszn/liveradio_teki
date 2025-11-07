"""
Pytest configuration and fixtures for FFmpeg manager tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from ffmpeg_manager.config import EncodingPreset, FFmpegConfig
from ffmpeg_manager.command_builder import FFmpegCommandBuilder
from ffmpeg_manager.log_parser import FFmpegLogParser
from ffmpeg_manager.process_manager import FFmpegProcessManager


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_loop_file(temp_dir: Path) -> Path:
    """Create a test video loop file."""
    loop_file = temp_dir / "test_loop.mp4"
    loop_file.touch()  # Create empty file for testing
    return loop_file


@pytest.fixture
def test_config() -> FFmpegConfig:
    """Create a test configuration."""
    return FFmpegConfig(
        rtmp_endpoint="rtmp://test-server:1935/live/test",
        audio_url="http://test-audio:8000/stream",
        encoding_preset=EncodingPreset.PRESET_480P_TEST,
        fade_in_duration=1.0,
        overlap_duration=2.0,
        max_restart_attempts=3,
        process_timeout=10,
        ffmpeg_binary="ffmpeg",
        log_level="info",
    )


@pytest.fixture
def command_builder(test_config: FFmpegConfig) -> FFmpegCommandBuilder:
    """Create a command builder for testing."""
    return FFmpegCommandBuilder(test_config)


@pytest.fixture
def log_parser() -> FFmpegLogParser:
    """Create a log parser for testing."""
    return FFmpegLogParser()


@pytest.fixture
def process_manager(test_config: FFmpegConfig) -> FFmpegProcessManager:
    """Create a process manager for testing."""
    return FFmpegProcessManager(config=test_config)


@pytest.fixture
def sample_ffmpeg_output() -> str:
    """Sample FFmpeg output for testing log parser."""
    return """
frame=  100 fps= 30 q=28.0 size=     512kB time=00:00:03.33 bitrate=1258.3kbits/s speed=1.00x
frame=  200 fps= 30 q=28.0 size=    1024kB time=00:00:06.66 bitrate=1258.3kbits/s dup=0 drop=0 speed=1.00x
[error] Connection refused
[warning] Dropped 5 frames
frame=  300 fps= 30 q=28.0 size=    1536kB time=00:00:10.00 bitrate=1258.3kbits/s speed=1.00x
"""


@pytest.fixture
def sample_error_lines() -> list:
    """Sample FFmpeg error lines for testing."""
    return [
        "[error] Connection refused",
        "[fatal] No such file or directory: /path/to/missing.mp4",
        "[error] RTMP connection error: stream closed",
        "[error] Encoding failed",
        "[error] Cannot allocate memory",
        "[error] Audio error: invalid stream",
    ]
