"""Track Mapper Module - SHARD-3

Database schema and API for managing track-to-video loop mappings.
"""

__version__ = "1.0.0"
__author__ = "24/7 FFmpeg YouTube Radio Stream"

from .mapper import TrackMapper
from .config import TrackMapperConfig

__all__ = ["TrackMapper", "TrackMapperConfig"]
