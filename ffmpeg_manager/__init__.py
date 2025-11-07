"""
FFmpeg Process Manager (SHARD-4)

Robust FFmpeg process lifecycle management with fade transitions,
error handling, and graceful handovers for 24/7 YouTube radio streaming.

Version: 1.0.0
Status: In Development
"""

__version__ = "1.0.0"
__author__ = "24/7 Radio Stream Project"

from ffmpeg_manager.command_builder import FFmpegCommandBuilder
from ffmpeg_manager.config import FFmpegConfig, EncodingPreset
from ffmpeg_manager.log_parser import FFmpegLogParser
from ffmpeg_manager.process_manager import FFmpegProcessManager

__all__ = [
    "FFmpegCommandBuilder",
    "FFmpegConfig",
    "EncodingPreset",
    "FFmpegLogParser",
    "FFmpegProcessManager",
]
