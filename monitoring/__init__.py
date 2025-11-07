"""Monitoring & Health Checks module.

Provides Prometheus metrics, health checks, FFmpeg monitoring, and auto-recovery.
"""

from .auto_recovery import AutoRecovery
from .ffmpeg_monitor import FFmpegMonitor
from .health_checks import HealthChecker
from .metrics import MetricsExporter

__all__ = [
    "MetricsExporter",
    "HealthChecker",
    "FFmpegMonitor",
    "AutoRecovery",
]

__version__ = "1.0.0"
