"""Auto-recovery logic for FFmpeg process and stream failures."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional

from monitoring.config import MonitoringConfig

logger = logging.getLogger(__name__)


class RecoveryAction(str, Enum):
    """Recovery actions that can be taken."""

    NONE = "none"
    RESTART_FFMPEG = "restart_ffmpeg"
    RETRY_AUDIO_STREAM = "retry_audio_stream"
    RECONNECT_RTMP = "reconnect_rtmp"
    ESCALATE_ALERT = "escalate_alert"


@dataclass
class RecoveryAttempt:
    """Record of a recovery attempt."""

    action: RecoveryAction
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None


class AutoRecovery:
    """Automatic recovery system for stream failures.

    Features:
    - FFmpeg crash recovery with retry limits
    - Audio stream retry logic
    - RTMP reconnection handling
    - Escalation to critical alerts after max retries
    """

    def __init__(self, config: Optional[MonitoringConfig] = None):
        """Initialize auto-recovery system.

        Args:
            config: Monitoring configuration
        """
        if config is None:
            from monitoring.config import get_config

            config = get_config()

        self.config = config

        # Recovery state tracking
        self._restart_count: int = 0
        self._last_restart_time: Optional[datetime] = None
        self._audio_retry_count: int = 0
        self._last_audio_retry_time: Optional[datetime] = None
        self._recovery_history: list[RecoveryAttempt] = []

        # Callbacks
        self._restart_callback: Optional[Callable] = None
        self._alert_callback: Optional[Callable] = None

        logger.info(f"Auto-recovery initialized (enabled: {self.config.enable_auto_recovery})")

    def set_restart_callback(self, callback: Callable) -> None:
        """Set callback for FFmpeg restart.

        Args:
            callback: Async function to call for restart
        """
        self._restart_callback = callback
        logger.debug("Restart callback set")

    def set_alert_callback(self, callback: Callable) -> None:
        """Set callback for sending alerts.

        Args:
            callback: Async function to call for alerts
        """
        self._alert_callback = callback
        logger.debug("Alert callback set")

    async def handle_ffmpeg_crash(self, error_message: str = "") -> RecoveryAction:
        """Handle FFmpeg process crash.

        Args:
            error_message: Error message from crash

        Returns:
            RecoveryAction taken
        """
        if not self.config.enable_auto_recovery:
            logger.info("Auto-recovery disabled, skipping FFmpeg restart")
            return RecoveryAction.NONE

        now = datetime.now()

        # Check cooldown period
        if self._last_restart_time:
            time_since_last = (now - self._last_restart_time).total_seconds()
            if time_since_last < self.config.restart_cooldown:
                logger.warning(
                    f"Restart cooldown active: {time_since_last:.1f}s / "
                    f"{self.config.restart_cooldown}s"
                )
                return RecoveryAction.NONE

        # Check restart limit
        if self._restart_count >= self.config.max_restart_attempts:
            logger.error(f"Max restart attempts ({self.config.max_restart_attempts}) reached")

            # Send critical alert
            await self._send_alert(
                "critical",
                f"FFmpeg crashed {self._restart_count} times, max retries exhausted",
            )

            return RecoveryAction.ESCALATE_ALERT

        # Attempt restart
        self._restart_count += 1
        self._last_restart_time = now

        logger.warning(
            f"Attempting FFmpeg restart (attempt {self._restart_count}/"
            f"{self.config.max_restart_attempts})"
        )

        success = False
        try:
            if self._restart_callback:
                await self._restart_callback()
                success = True
                logger.info("FFmpeg restart successful")
            else:
                logger.error("No restart callback configured")

        except Exception as e:
            logger.error(f"FFmpeg restart failed: {e}")
            error_message = str(e)

        # Record attempt
        self._recovery_history.append(
            RecoveryAttempt(
                action=RecoveryAction.RESTART_FFMPEG,
                timestamp=now,
                success=success,
                error_message=error_message if not success else None,
            )
        )

        if success:
            # Send info alert
            await self._send_alert(
                "warning",
                f"FFmpeg restarted automatically (attempt {self._restart_count})",
            )
            return RecoveryAction.RESTART_FFMPEG
        else:
            # Escalate if restart failed
            await self._send_alert(
                "critical",
                f"FFmpeg restart failed: {error_message}",
            )
            return RecoveryAction.ESCALATE_ALERT

    async def handle_audio_stream_unavailable(self) -> RecoveryAction:
        """Handle audio stream unavailability.

        Returns:
            RecoveryAction taken
        """
        if not self.config.enable_auto_recovery:
            logger.info("Auto-recovery disabled, skipping audio stream retry")
            return RecoveryAction.NONE

        now = datetime.now()

        # Check retry cooldown
        if self._last_audio_retry_time:
            time_since_last = (now - self._last_audio_retry_time).total_seconds()
            if time_since_last < self.config.audio_stream_retry_interval:
                logger.debug(
                    f"Audio retry cooldown active: {time_since_last:.1f}s / "
                    f"{self.config.audio_stream_retry_interval}s"
                )
                return RecoveryAction.NONE

        # Check retry limit
        if self._audio_retry_count >= self.config.audio_stream_max_retries:
            logger.error(
                f"Max audio stream retries ({self.config.audio_stream_max_retries}) " f"reached"
            )

            # Send critical alert
            await self._send_alert(
                "critical",
                "Audio stream unavailable, max retries exhausted",
            )

            return RecoveryAction.ESCALATE_ALERT

        # Attempt retry
        self._audio_retry_count += 1
        self._last_audio_retry_time = now

        logger.warning(
            f"Retrying audio stream (attempt {self._audio_retry_count}/"
            f"{self.config.audio_stream_max_retries})"
        )

        # Record attempt
        self._recovery_history.append(
            RecoveryAttempt(
                action=RecoveryAction.RETRY_AUDIO_STREAM,
                timestamp=now,
                success=True,  # We don't know yet, will be updated
            )
        )

        # Send warning alert every 5 retries
        if self._audio_retry_count % 5 == 0:
            await self._send_alert(
                "warning",
                f"Audio stream still unavailable after {self._audio_retry_count} retries",
            )

        return RecoveryAction.RETRY_AUDIO_STREAM

    async def handle_rtmp_connection_lost(self) -> RecoveryAction:
        """Handle RTMP connection loss.

        Returns:
            RecoveryAction taken
        """
        if not self.config.enable_auto_recovery:
            logger.info("Auto-recovery disabled, skipping RTMP reconnection")
            return RecoveryAction.NONE

        logger.error("RTMP connection lost, restarting FFmpeg")

        # RTMP connection loss usually requires FFmpeg restart
        await self._send_alert(
            "critical",
            "RTMP connection lost, restarting stream",
        )

        # Record attempt
        self._recovery_history.append(
            RecoveryAttempt(
                action=RecoveryAction.RECONNECT_RTMP,
                timestamp=datetime.now(),
                success=True,
            )
        )

        # Trigger restart
        if self._restart_callback:
            try:
                await self._restart_callback()
                logger.info("FFmpeg restarted for RTMP reconnection")
            except Exception as e:
                logger.error(f"Failed to restart FFmpeg for RTMP: {e}")

        return RecoveryAction.RECONNECT_RTMP

    def reset_restart_counter(self) -> None:
        """Reset restart counter (call on successful recovery)."""
        if self._restart_count > 0:
            logger.info(f"Resetting restart counter (was {self._restart_count})")
        self._restart_count = 0
        self._last_restart_time = None

    def reset_audio_retry_counter(self) -> None:
        """Reset audio retry counter (call when audio stream recovers)."""
        if self._audio_retry_count > 0:
            logger.info(f"Audio stream recovered after {self._audio_retry_count} retries")
        self._audio_retry_count = 0
        self._last_audio_retry_time = None

    async def _send_alert(self, severity: str, message: str) -> None:
        """Send alert via callback.

        Args:
            severity: Alert severity (info, warning, error, critical)
            message: Alert message
        """
        if self._alert_callback:
            try:
                await self._alert_callback(severity, message)
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
        else:
            logger.warning(f"No alert callback configured for: [{severity}] {message}")

    def get_recovery_stats(self) -> dict:
        """Get recovery statistics.

        Returns:
            Dictionary with recovery stats
        """
        # Get recent attempts (last hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_attempts = [a for a in self._recovery_history if a.timestamp > one_hour_ago]

        return {
            "restart_count": self._restart_count,
            "last_restart_time": (
                self._last_restart_time.isoformat() if self._last_restart_time else None
            ),
            "audio_retry_count": self._audio_retry_count,
            "last_audio_retry_time": (
                self._last_audio_retry_time.isoformat() if self._last_audio_retry_time else None
            ),
            "recent_attempts": len(recent_attempts),
            "total_attempts": len(self._recovery_history),
            "auto_recovery_enabled": self.config.enable_auto_recovery,
        }

    def get_recovery_history(self, limit: int = 10) -> list[dict]:
        """Get recent recovery history.

        Args:
            limit: Maximum number of attempts to return

        Returns:
            List of recovery attempts
        """
        recent = self._recovery_history[-limit:] if limit > 0 else self._recovery_history

        return [
            {
                "action": attempt.action,
                "timestamp": attempt.timestamp.isoformat(),
                "success": attempt.success,
                "error_message": attempt.error_message,
            }
            for attempt in reversed(recent)
        ]
