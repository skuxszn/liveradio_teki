"""
Asset Manager - Video Asset Management for 24/7 FFmpeg YouTube Radio Stream.

This module provides video loop validation, metadata extraction, dynamic overlay
generation, and asset management for the radio streaming system.
"""

from asset_manager.manager import AssetManager
from asset_manager.validator import VideoValidator, ValidationResult
from asset_manager.overlay_generator import OverlayGenerator

__version__ = "1.0.0"
__all__ = ["AssetManager", "VideoValidator", "ValidationResult", "OverlayGenerator"]
