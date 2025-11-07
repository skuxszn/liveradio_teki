"""Metadata Watcher Service for 24/7 FFmpeg YouTube Radio Stream.

This module provides the webhook receiver that listens for AzuraCast track
changes and orchestrates FFmpeg process lifecycle with graceful handovers.

Author: SHARD-2 Development Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "SHARD-2 Development Team"

from .config import Config
from .ffmpeg_manager import FFmpegManager

__all__ = ["Config", "FFmpegManager"]
