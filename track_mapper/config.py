"""Track Mapper Configuration

Configuration management for the Track Mapper module.
"""

import os
from dataclasses import dataclass


@dataclass
class TrackMapperConfig:
    """Configuration for Track Mapper module.

    All configuration is loaded from environment variables with sensible defaults.
    """

    # Database configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "radio"
    postgres_password: str = ""
    postgres_db: str = "radio_db"

    # Pool configuration
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600  # Recycle connections after 1 hour

    # Loop file paths
    loops_path: str = "/srv/loops"
    default_loop: str = "/srv/loops/default.mp4"

    # Cache configuration
    cache_size: int = 1000
    cache_ttl_seconds: int = 3600

    # Logging
    log_level: str = "INFO"
    debug: bool = False

    # Environment
    environment: str = "production"

    @classmethod
    def from_env(cls) -> "TrackMapperConfig":
        """Load configuration from environment variables.

        Returns:
            TrackMapperConfig instance populated from environment
        """
        return cls(
            # Database
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_user=os.getenv("POSTGRES_USER", "radio"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
            postgres_db=os.getenv("POSTGRES_DB", "radio_db"),
            # Pool
            db_pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            db_max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            db_pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            db_pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            # Paths
            loops_path=os.getenv("LOOPS_PATH", "/srv/loops"),
            default_loop=os.getenv("DEFAULT_LOOP", "/srv/loops/default.mp4"),
            # Cache
            cache_size=int(os.getenv("CACHE_SIZE", "1000")),
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600")),
            # Logging
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            # Environment
            environment=os.getenv("ENVIRONMENT", "production"),
        )

    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL.

        Returns:
            PostgreSQL connection string in format:
            postgresql://user:password@host:port/database
        """
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.postgres_password:
            raise ValueError("POSTGRES_PASSWORD is required")

        if self.db_pool_size < 1:
            raise ValueError("DB_POOL_SIZE must be at least 1")

        if self.cache_size < 1:
            raise ValueError("CACHE_SIZE must be at least 1")

        if not self.loops_path:
            raise ValueError("LOOPS_PATH is required")

        if not self.default_loop:
            raise ValueError("DEFAULT_LOOP is required")

    def __repr__(self) -> str:
        """String representation (hides password)."""
        return (
            f"TrackMapperConfig("
            f"host={self.postgres_host}, "
            f"port={self.postgres_port}, "
            f"db={self.postgres_db}, "
            f"pool_size={self.db_pool_size}, "
            f"cache_size={self.cache_size})"
        )
