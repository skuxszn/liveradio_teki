"""Advanced FFmpeg Module - SHARD 9

This module implements Option A: Persistent FFmpeg with Dual-Input Crossfade.

Provides seamless, gapless track transitions using a single persistent FFmpeg
process with dual video inputs and dynamic crossfading.

Main Components:
- DualInputFFmpegManager: Core persistent FFmpeg manager
- FilterGraphBuilder: Dynamic xfade filter generation
- InputSwitcher: Input reload logic
- HLSAlternative: HLS-based approach for seamless transitions

Usage:
    >>> from advanced import DualInputFFmpegManager
    >>> from advanced.config import AdvancedConfig
    >>>
    >>> config = AdvancedConfig.from_env()
    >>> manager = DualInputFFmpegManager(config)
    >>> await manager.start_stream("/path/to/first/loop.mp4")
    >>> await manager.switch_track("/path/to/next/loop.mp4")

Author: AI Agent (SHARD-9)
Date: November 5, 2025
Version: 1.0.0
"""

from .config import AdvancedConfig
from .dual_input_ffmpeg import DualInputFFmpegManager
from .filter_graph_builder import FilterGraphBuilder
from .input_switcher import InputSwitcher

__version__ = "1.0.0"
__all__ = [
    "AdvancedConfig",
    "DualInputFFmpegManager",
    "FilterGraphBuilder",
    "InputSwitcher",
]
