"""Configuration for monitoring module."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class MonitoringConfig:
    """Configuration for monitoring and health checks."""

    # Metrics
    metrics_port: int = 9090
    metrics_path: str = "/metrics"

    # Health checks
    health_check_interval: float = 5.0  # seconds
    ffmpeg_check_interval: float = 1.0  # seconds
    stream_freeze_timeout: float = 30.0  # seconds (no new frames)

    # Auto-recovery
    enable_auto_recovery: bool = True
    max_restart_attempts: int = 3
    restart_cooldown: float = 60.0  # seconds between restarts
    audio_stream_retry_interval: float = 30.0  # seconds
    audio_stream_max_retries: int = 20  # 10 minutes total

    # FFmpeg monitoring
    cpu_threshold_percent: float = 90.0
    memory_threshold_mb: float = 2048.0
    bitrate_drop_threshold_percent: float = 50.0

    # External services
    azuracast_url: Optional[str] = None
    azuracast_api_key: Optional[str] = None
    rtmp_endpoint: Optional[str] = None

    # Logging
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "MonitoringConfig":
        """Create configuration from environment variables.

        Returns:
            MonitoringConfig instance
        """
        return cls(
            metrics_port=int(os.getenv("METRICS_PORT", "9090")),
            metrics_path=os.getenv("METRICS_PATH", "/metrics"),
            health_check_interval=float(os.getenv("HEALTH_CHECK_INTERVAL", "5.0")),
            ffmpeg_check_interval=float(os.getenv("FFMPEG_CHECK_INTERVAL", "1.0")),
            stream_freeze_timeout=float(os.getenv("STREAM_FREEZE_TIMEOUT", "30.0")),
            enable_auto_recovery=os.getenv("ENABLE_AUTO_RECOVERY", "true").lower() == "true",
            max_restart_attempts=int(os.getenv("MAX_RESTART_ATTEMPTS", "3")),
            restart_cooldown=float(os.getenv("RESTART_COOLDOWN", "60.0")),
            audio_stream_retry_interval=float(os.getenv("AUDIO_STREAM_RETRY_INTERVAL", "30.0")),
            audio_stream_max_retries=int(os.getenv("AUDIO_STREAM_MAX_RETRIES", "20")),
            cpu_threshold_percent=float(os.getenv("CPU_THRESHOLD_PERCENT", "90.0")),
            memory_threshold_mb=float(os.getenv("MEMORY_THRESHOLD_MB", "2048.0")),
            bitrate_drop_threshold_percent=float(
                os.getenv("BITRATE_DROP_THRESHOLD_PERCENT", "50.0")
            ),
            azuracast_url=os.getenv("AZURACAST_URL"),
            azuracast_api_key=os.getenv("AZURACAST_API_KEY"),
            rtmp_endpoint=os.getenv("RTMP_ENDPOINT"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.metrics_port < 1 or self.metrics_port > 65535:
            raise ValueError(f"Invalid metrics_port: {self.metrics_port}")

        if self.health_check_interval <= 0:
            raise ValueError(f"Invalid health_check_interval: {self.health_check_interval}")

        if self.max_restart_attempts < 0:
            raise ValueError(f"Invalid max_restart_attempts: {self.max_restart_attempts}")


def get_config() -> MonitoringConfig:
    """Get monitoring configuration from environment.

    Returns:
        MonitoringConfig instance
    """
    config = MonitoringConfig.from_env()
    config.validate()
    return config
