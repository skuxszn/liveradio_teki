"""Configuration management for Logging & Analytics Module.

This module handles configuration loading from environment variables
and provides validated configuration objects.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LoggingConfig:
    """Configuration for Logging & Analytics Module.

    All settings can be overridden via environment variables.

    Attributes:
        postgres_host: PostgreSQL host
        postgres_port: PostgreSQL port
        postgres_user: PostgreSQL username
        postgres_password: PostgreSQL password
        postgres_db: PostgreSQL database name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_path: Directory for log files
        log_file_max_bytes: Maximum size of log file before rotation
        log_file_backup_count: Number of backup log files to keep
        db_pool_size: Database connection pool size
        db_max_overflow: Maximum overflow connections
        db_pool_timeout: Connection timeout in seconds
        db_pool_recycle: Connection recycle time in seconds
        debug: Enable debug mode
        play_history_retention_days: Days to keep play history
        error_log_retention_days: Days to keep resolved errors
        metrics_retention_days: Days to keep system metrics
    """

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "radio"
    postgres_password: str = "radio"
    postgres_db: str = "radio_db"
    
    log_level: str = "INFO"
    log_path: str = "/var/log/radio"
    log_file_max_bytes: int = 100 * 1024 * 1024  # 100 MB
    log_file_backup_count: int = 10
    
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    
    debug: bool = False
    
    play_history_retention_days: int = 90
    error_log_retention_days: int = 30
    metrics_retention_days: int = 30

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL.

        Returns:
            Database URL string for SQLAlchemy
        """
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Create configuration from environment variables.

        Environment variables:
            POSTGRES_HOST: PostgreSQL host (default: localhost)
            POSTGRES_PORT: PostgreSQL port (default: 5432)
            POSTGRES_USER: PostgreSQL username (default: radio)
            POSTGRES_PASSWORD: PostgreSQL password (default: radio)
            POSTGRES_DB: PostgreSQL database name (default: radio_db)
            LOG_LEVEL: Logging level (default: INFO)
            LOG_PATH: Log file directory (default: /var/log/radio)
            LOG_FILE_MAX_BYTES: Max log file size (default: 100MB)
            LOG_FILE_BACKUP_COUNT: Number of backup files (default: 10)
            DB_POOL_SIZE: Database pool size (default: 5)
            DB_MAX_OVERFLOW: Max overflow connections (default: 10)
            DB_POOL_TIMEOUT: Connection timeout (default: 30)
            DB_POOL_RECYCLE: Connection recycle time (default: 3600)
            DEBUG: Debug mode (default: false)
            PLAY_HISTORY_RETENTION_DAYS: Days to keep play history (default: 90)
            ERROR_LOG_RETENTION_DAYS: Days to keep errors (default: 30)
            METRICS_RETENTION_DAYS: Days to keep metrics (default: 30)

        Returns:
            LoggingConfig instance with values from environment
        """
        return cls(
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_user=os.getenv("POSTGRES_USER", "radio"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", "radio"),
            postgres_db=os.getenv("POSTGRES_DB", "radio_db"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_path=os.getenv("LOG_PATH", "/var/log/radio"),
            log_file_max_bytes=int(
                os.getenv("LOG_FILE_MAX_BYTES", str(100 * 1024 * 1024))
            ),
            log_file_backup_count=int(os.getenv("LOG_FILE_BACKUP_COUNT", "10")),
            db_pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            db_max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            db_pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            db_pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            play_history_retention_days=int(
                os.getenv("PLAY_HISTORY_RETENTION_DAYS", "90")
            ),
            error_log_retention_days=int(os.getenv("ERROR_LOG_RETENTION_DAYS", "30")),
            metrics_retention_days=int(os.getenv("METRICS_RETENTION_DAYS", "30")),
        )

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.postgres_host:
            raise ValueError("postgres_host cannot be empty")
        
        if not (1 <= self.postgres_port <= 65535):
            raise ValueError(f"Invalid postgres_port: {self.postgres_port}")
        
        if not self.postgres_user:
            raise ValueError("postgres_user cannot be empty")
        
        if not self.postgres_password:
            raise ValueError("postgres_password cannot be empty")
        
        if not self.postgres_db:
            raise ValueError("postgres_db cannot be empty")
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ValueError(
                f"Invalid log_level: {self.log_level}. Must be one of {valid_log_levels}"
            )
        
        if self.db_pool_size < 1:
            raise ValueError(f"db_pool_size must be >= 1, got {self.db_pool_size}")
        
        if self.db_max_overflow < 0:
            raise ValueError(
                f"db_max_overflow must be >= 0, got {self.db_max_overflow}"
            )
        
        if self.db_pool_timeout < 1:
            raise ValueError(
                f"db_pool_timeout must be >= 1, got {self.db_pool_timeout}"
            )
        
        if self.log_file_max_bytes < 1024:  # At least 1 KB
            raise ValueError(
                f"log_file_max_bytes must be >= 1024, got {self.log_file_max_bytes}"
            )
        
        if self.log_file_backup_count < 1:
            raise ValueError(
                f"log_file_backup_count must be >= 1, got {self.log_file_backup_count}"
            )
        
        if self.play_history_retention_days < 1:
            raise ValueError(
                f"play_history_retention_days must be >= 1, "
                f"got {self.play_history_retention_days}"
            )
        
        if self.error_log_retention_days < 1:
            raise ValueError(
                f"error_log_retention_days must be >= 1, "
                f"got {self.error_log_retention_days}"
            )
        
        if self.metrics_retention_days < 1:
            raise ValueError(
                f"metrics_retention_days must be >= 1, got {self.metrics_retention_days}"
            )

    def __repr__(self) -> str:
        """String representation with masked password.

        Returns:
            String representation of configuration
        """
        return (
            f"LoggingConfig("
            f"postgres_host='{self.postgres_host}', "
            f"postgres_port={self.postgres_port}, "
            f"postgres_user='{self.postgres_user}', "
            f"postgres_password='***', "
            f"postgres_db='{self.postgres_db}', "
            f"log_level='{self.log_level}', "
            f"debug={self.debug})"
        )



