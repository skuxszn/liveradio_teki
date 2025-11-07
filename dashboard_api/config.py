"""Configuration management for dashboard API."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Radio Stream Dashboard API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False
    environment: str = "production"

    # Database
    postgres_user: str = "radio"
    postgres_password: str
    postgres_db: str = "radio_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Security
    jwt_secret: str
    api_token: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Server
    host: str = "0.0.0.0"
    port: int = 9001

    # Paths
    loops_path: Path = Path("/srv/loops")
    log_path: Path = Path("/var/log/radio")

    # File uploads
    max_upload_size_mb: int = 100
    allowed_video_extensions: list[str] = [".mp4", ".avi", ".mov", ".mkv"]

    # Rate limiting
    rate_limit_per_minute: int = 100

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        """Get async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Global settings instance
settings = Settings()
