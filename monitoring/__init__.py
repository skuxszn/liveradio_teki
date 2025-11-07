"""Monitoring & Health Checks module.

Provides Prometheus metrics, health checks, FFmpeg monitoring, and auto-recovery.
"""

from monitoring.auto_recovery import AutoRecovery
from monitoring.ffmpeg_monitor import FFmpegMonitor
from monitoring.health_checks import HealthChecker
from monitoring.metrics import MetricsExporter

__all__ = [
    "MetricsExporter",
    "HealthChecker",
    "FFmpegMonitor",
    "AutoRecovery",
]

__version__ = "1.0.0"
