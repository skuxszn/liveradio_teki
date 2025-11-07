"""Logging & Analytics Module for 24/7 Radio Stream.

This module provides comprehensive logging and analytics for track play history,
error tracking, and system metrics.

Main Components:
    - RadioLogger: Main logging class for track plays and errors
    - Analytics: Analytics query engine for reporting
    - LoggingConfig: Configuration management

Example:
    >>> from logging_module import RadioLogger, LoggingConfig
    >>> config = LoggingConfig.from_env()
    >>> logger = RadioLogger(config)
    >>> logger.log_track_started({
    ...     "artist": "Artist Name",
    ...     "title": "Song Title"
    ... }, "/srv/loops/track.mp4", 12345)
"""

from logging_module.config import LoggingConfig
from logging_module.logger import RadioLogger, JsonFormatter
from logging_module.analytics import Analytics

__version__ = "1.0.0"
__all__ = ["RadioLogger", "Analytics", "LoggingConfig", "JsonFormatter"]



