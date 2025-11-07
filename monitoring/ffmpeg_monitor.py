"""FFmpeg process health monitoring."""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

import psutil

from monitoring.config import MonitoringConfig

logger = logging.getLogger(__name__)


class FFmpegHealthStatus(str, Enum):
    """FFmpeg health status."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class FFmpegHealthReport:
    """FFmpeg health monitoring report."""

    status: FFmpegHealthStatus
    pid: Optional[int]
    cpu_percent: float
    memory_mb: float
    uptime_seconds: float
    frame_count: int
    bitrate_kbps: float
    warnings: list[str]
    timestamp: datetime


class FFmpegMonitor:
    """Monitors FFmpeg process health and performance.

    Features:
    - CPU and memory monitoring
    - Frame rate and bitrate analysis
    - Frozen stream detection
    - Resource threshold alerts
    """

    def __init__(self, config: Optional[MonitoringConfig] = None):
        """Initialize FFmpeg monitor.

        Args:
            config: Monitoring configuration
        """
        if config is None:
            from monitoring.config import get_config
            config = get_config()

        self.config = config

        # State tracking
        self._last_frame_count: int = 0
        self._last_frame_time: Optional[datetime] = None
        self._last_bitrate: float = 0.0

        logger.info("FFmpeg monitor initialized")

    async def check_process_health(
        self,
        pid: Optional[int],
        uptime_seconds: float = 0.0,
        process_state: str = "stopped",
    ) -> FFmpegHealthReport:
        """Check FFmpeg process health.

        Args:
            pid: Process ID (None if not running)
            uptime_seconds: Process uptime in seconds
            process_state: Current process state

        Returns:
            FFmpegHealthReport with health status
        """
        warnings = []
        cpu_percent = 0.0
        memory_mb = 0.0
        frame_count = 0
        bitrate_kbps = 0.0

        if pid is None or process_state not in ["running", "starting"]:
            return FFmpegHealthReport(
                status=FFmpegHealthStatus.CRITICAL,
                pid=pid,
                cpu_percent=0.0,
                memory_mb=0.0,
                uptime_seconds=uptime_seconds,
                frame_count=0,
                bitrate_kbps=0.0,
                warnings=["FFmpeg process not running"],
                timestamp=datetime.now(),
            )

        try:
            # Get process metrics using psutil
            process = psutil.Process(pid)

            # CPU usage
            cpu_percent = process.cpu_percent(interval=0.1)
            if cpu_percent > self.config.cpu_threshold_percent:
                warnings.append(
                    f"CPU usage high: {cpu_percent:.1f}% "
                    f"(threshold: {self.config.cpu_threshold_percent}%)"
                )

            # Memory usage
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            if memory_mb > self.config.memory_threshold_mb:
                warnings.append(
                    f"Memory usage high: {memory_mb:.1f}MB "
                    f"(threshold: {self.config.memory_threshold_mb}MB)"
                )

            # Check if process is zombie
            if process.status() == psutil.STATUS_ZOMBIE:
                warnings.append("Process is zombie")

        except psutil.NoSuchProcess:
            warnings.append("Process not found")
            return FFmpegHealthReport(
                status=FFmpegHealthStatus.CRITICAL,
                pid=pid,
                cpu_percent=0.0,
                memory_mb=0.0,
                uptime_seconds=uptime_seconds,
                frame_count=0,
                bitrate_kbps=0.0,
                warnings=warnings,
                timestamp=datetime.now(),
            )
        except psutil.AccessDenied:
            warnings.append("Access denied to process metrics")
        except Exception as e:
            logger.error(f"Error checking process health: {e}")
            warnings.append(f"Error checking process: {str(e)}")

        # Determine overall status
        if warnings:
            if any("not running" in w or "Process not found" in w for w in warnings):
                status = FFmpegHealthStatus.CRITICAL
            elif any("high" in w for w in warnings):
                status = FFmpegHealthStatus.WARNING
            else:
                status = FFmpegHealthStatus.WARNING
        else:
            status = FFmpegHealthStatus.HEALTHY

        return FFmpegHealthReport(
            status=status,
            pid=pid,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            uptime_seconds=uptime_seconds,
            frame_count=frame_count,
            bitrate_kbps=bitrate_kbps,
            warnings=warnings,
            timestamp=datetime.now(),
        )

    async def check_stream_freeze(
        self,
        current_frame_count: int,
    ) -> bool:
        """Check if stream has frozen (no new frames).

        Args:
            current_frame_count: Current frame count from FFmpeg

        Returns:
            True if stream appears frozen
        """
        now = datetime.now()

        # First check - initialize
        if self._last_frame_time is None:
            self._last_frame_count = current_frame_count
            self._last_frame_time = now
            return False

        # Check if frames have increased
        if current_frame_count > self._last_frame_count:
            # Frames increasing - stream is healthy
            self._last_frame_count = current_frame_count
            self._last_frame_time = now
            return False

        # No new frames - check timeout
        time_since_last_frame = (now - self._last_frame_time).total_seconds()
        if time_since_last_frame > self.config.stream_freeze_timeout:
            logger.warning(
                f"Stream appears frozen: no new frames for {time_since_last_frame:.1f}s"
            )
            return True

        return False

    async def check_bitrate_drop(
        self,
        current_bitrate_kbps: float,
    ) -> bool:
        """Check for significant bitrate drop.

        Args:
            current_bitrate_kbps: Current bitrate in kbps

        Returns:
            True if bitrate has dropped significantly
        """
        if self._last_bitrate == 0.0:
            self._last_bitrate = current_bitrate_kbps
            return False

        # Calculate percentage drop
        if self._last_bitrate > 0:
            drop_percent = (
                (self._last_bitrate - current_bitrate_kbps) / self._last_bitrate * 100
            )

            if drop_percent > self.config.bitrate_drop_threshold_percent:
                logger.warning(
                    f"Bitrate dropped {drop_percent:.1f}%: "
                    f"{self._last_bitrate:.0f} -> {current_bitrate_kbps:.0f} kbps"
                )
                self._last_bitrate = current_bitrate_kbps
                return True

        self._last_bitrate = current_bitrate_kbps
        return False

    def get_health_summary(self, report: FFmpegHealthReport) -> Dict:
        """Get health report as dictionary.

        Args:
            report: FFmpeg health report

        Returns:
            Dictionary representation
        """
        return {
            "status": report.status,
            "pid": report.pid,
            "cpu_percent": round(report.cpu_percent, 2),
            "memory_mb": round(report.memory_mb, 2),
            "uptime_seconds": round(report.uptime_seconds, 2),
            "frame_count": report.frame_count,
            "bitrate_kbps": round(report.bitrate_kbps, 2),
            "warnings": report.warnings,
            "timestamp": report.timestamp.isoformat(),
        }

    def reset_tracking(self) -> None:
        """Reset tracking state (useful after recovery)."""
        self._last_frame_count = 0
        self._last_frame_time = None
        self._last_bitrate = 0.0
        logger.debug("FFmpeg monitor tracking reset")



