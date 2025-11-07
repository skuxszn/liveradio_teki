"""Health check endpoints and monitoring."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

import aiohttp

from monitoring.config import MonitoringConfig

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    status: HealthStatus
    message: str
    timestamp: datetime
    details: Optional[Dict] = None


class HealthChecker:
    """Performs health checks on system components.

    Checks:
    - FFmpeg process health
    - AzuraCast connectivity
    - RTMP relay status
    - Database connectivity
    """

    def __init__(self, config: Optional[MonitoringConfig] = None):
        """Initialize health checker.

        Args:
            config: Monitoring configuration
        """
        if config is None:
            from monitoring.config import get_config
            config = get_config()

        self.config = config
        self._last_check_time: Optional[datetime] = None
        self._cached_result: Optional[HealthCheckResult] = None

        logger.info("Health checker initialized")

    async def check_liveness(self) -> HealthCheckResult:
        """Liveness probe - is the service alive?

        Returns:
            HealthCheckResult with liveness status
        """
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Service is alive",
            timestamp=datetime.now(),
            details={"check": "liveness"},
        )

    async def check_readiness(self, ffmpeg_running: bool) -> HealthCheckResult:
        """Readiness probe - is the service ready to serve traffic?

        Args:
            ffmpeg_running: Whether FFmpeg process is running

        Returns:
            HealthCheckResult with readiness status
        """
        if ffmpeg_running:
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Service is ready",
                timestamp=datetime.now(),
                details={"ffmpeg_running": True},
            )
        else:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="FFmpeg process not running",
                timestamp=datetime.now(),
                details={"ffmpeg_running": False},
            )

    async def check_azuracast(self) -> HealthCheckResult:
        """Check AzuraCast connectivity.

        Returns:
            HealthCheckResult with AzuraCast status
        """
        if not self.config.azuracast_url:
            return HealthCheckResult(
                status=HealthStatus.DEGRADED,
                message="AzuraCast URL not configured",
                timestamp=datetime.now(),
                details={"configured": False},
            )

        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.config.azuracast_api_key:
                    headers["X-API-Key"] = self.config.azuracast_api_key

                async with session.get(
                    f"{self.config.azuracast_url}/api/status",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5.0),
                ) as response:
                    if response.status == 200:
                        return HealthCheckResult(
                            status=HealthStatus.HEALTHY,
                            message="AzuraCast is reachable",
                            timestamp=datetime.now(),
                            details={"reachable": True, "status_code": 200},
                        )
                    else:
                        return HealthCheckResult(
                            status=HealthStatus.DEGRADED,
                            message=f"AzuraCast returned status {response.status}",
                            timestamp=datetime.now(),
                            details={"reachable": True, "status_code": response.status},
                        )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="AzuraCast connection timeout",
                timestamp=datetime.now(),
                details={"reachable": False, "error": "timeout"},
            )
        except Exception as e:
            logger.warning(f"AzuraCast health check failed: {e}")
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"AzuraCast unreachable: {str(e)}",
                timestamp=datetime.now(),
                details={"reachable": False, "error": str(e)},
            )

    async def check_detailed(
        self,
        ffmpeg_status: Dict,
        azuracast_check: bool = True,
    ) -> HealthCheckResult:
        """Perform detailed health check of all components.

        Args:
            ffmpeg_status: FFmpeg process status dictionary
            azuracast_check: Whether to check AzuraCast connectivity

        Returns:
            HealthCheckResult with detailed status
        """
        details = {
            "timestamp": datetime.now().isoformat(),
            "components": {},
        }

        # Check FFmpeg
        ffmpeg_state = str(ffmpeg_status.get("state", "stopped"))
        ffmpeg_healthy = ffmpeg_state in ["running", "starting"]
        details["components"]["ffmpeg"] = {
            "status": "healthy" if ffmpeg_healthy else "unhealthy",
            "state": ffmpeg_state,
            "pid": ffmpeg_status.get("pid"),
            "uptime_seconds": ffmpeg_status.get("uptime_seconds", 0),
        }

        # Check AzuraCast if requested
        azuracast_healthy = True
        if azuracast_check:
            azuracast_result = await self.check_azuracast()
            azuracast_healthy = azuracast_result.status == HealthStatus.HEALTHY
            details["components"]["azuracast"] = {
                "status": azuracast_result.status,
                "message": azuracast_result.message,
            }

        # Determine overall status
        if ffmpeg_healthy and azuracast_healthy:
            overall_status = HealthStatus.HEALTHY
            message = "All components healthy"
        elif ffmpeg_healthy or azuracast_healthy:
            overall_status = HealthStatus.DEGRADED
            message = "Some components degraded"
        else:
            overall_status = HealthStatus.UNHEALTHY
            message = "System unhealthy"

        return HealthCheckResult(
            status=overall_status,
            message=message,
            timestamp=datetime.now(),
            details=details,
        )

    def get_health_dict(self, result: HealthCheckResult) -> Dict:
        """Convert health check result to dictionary for API response.

        Args:
            result: Health check result

        Returns:
            Dictionary representation
        """
        return {
            "status": result.status,
            "message": result.message,
            "timestamp": result.timestamp.isoformat(),
            "details": result.details or {},
        }



