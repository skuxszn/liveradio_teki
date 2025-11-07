"""Unit tests for logging_module.config."""

import os
import pytest

from logging_module.config import LoggingConfig


class TestLoggingConfig:
    """Tests for LoggingConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LoggingConfig()

        assert config.postgres_host == "localhost"
        assert config.postgres_port == 5432
        assert config.postgres_user == "radio"
        assert config.postgres_db == "radio_db"
        assert config.log_level == "INFO"
        assert config.db_pool_size == 5
        assert config.debug is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LoggingConfig(
            postgres_host="custom-host",
            postgres_port=6543,
            postgres_user="custom-user",
            log_level="DEBUG",
            debug=True,
        )

        assert config.postgres_host == "custom-host"
        assert config.postgres_port == 6543
        assert config.postgres_user == "custom-user"
        assert config.log_level == "DEBUG"
        assert config.debug is True

    def test_database_url(self):
        """Test database URL generation."""
        config = LoggingConfig(
            postgres_host="testhost",
            postgres_port=5432,
            postgres_user="testuser",
            postgres_password="testpass",
            postgres_db="testdb",
        )

        expected = "postgresql://testuser:testpass@testhost:5432/testdb"
        assert config.database_url == expected

    def test_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("POSTGRES_HOST", "env-host")
        monkeypatch.setenv("POSTGRES_PORT", "7654")
        monkeypatch.setenv("POSTGRES_USER", "env-user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "env-pass")
        monkeypatch.setenv("POSTGRES_DB", "env-db")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DB_POOL_SIZE", "10")

        config = LoggingConfig.from_env()

        assert config.postgres_host == "env-host"
        assert config.postgres_port == 7654
        assert config.postgres_user == "env-user"
        assert config.postgres_password == "env-pass"
        assert config.postgres_db == "env-db"
        assert config.log_level == "WARNING"
        assert config.debug is True
        assert config.db_pool_size == 10

    def test_validate_valid_config(self):
        """Test validation with valid configuration."""
        config = LoggingConfig()
        config.validate()  # Should not raise

    def test_validate_empty_host(self):
        """Test validation fails with empty host."""
        config = LoggingConfig(postgres_host="")

        with pytest.raises(ValueError, match="postgres_host cannot be empty"):
            config.validate()

    def test_validate_invalid_port(self):
        """Test validation fails with invalid port."""
        config = LoggingConfig(postgres_port=99999)

        with pytest.raises(ValueError, match="Invalid postgres_port"):
            config.validate()

    def test_validate_invalid_log_level(self):
        """Test validation fails with invalid log level."""
        config = LoggingConfig(log_level="INVALID")

        with pytest.raises(ValueError, match="Invalid log_level"):
            config.validate()

    def test_validate_invalid_pool_size(self):
        """Test validation fails with invalid pool size."""
        config = LoggingConfig(db_pool_size=0)

        with pytest.raises(ValueError, match="db_pool_size must be >= 1"):
            config.validate()

    def test_validate_invalid_timeout(self):
        """Test validation fails with invalid timeout."""
        config = LoggingConfig(db_pool_timeout=0)

        with pytest.raises(ValueError, match="db_pool_timeout must be >= 1"):
            config.validate()

    def test_validate_invalid_retention_days(self):
        """Test validation fails with invalid retention days."""
        config = LoggingConfig(play_history_retention_days=0)

        with pytest.raises(ValueError, match="play_history_retention_days must be >= 1"):
            config.validate()

    def test_repr_masks_password(self):
        """Test __repr__ masks password."""
        config = LoggingConfig(postgres_password="secret123")

        repr_str = repr(config)
        assert "secret123" not in repr_str
        assert "***" in repr_str
        assert "postgres_host" in repr_str

    def test_log_file_max_bytes_validation(self):
        """Test validation of log file max bytes."""
        config = LoggingConfig(log_file_max_bytes=500)

        with pytest.raises(ValueError, match="log_file_max_bytes must be >= 1024"):
            config.validate()

    def test_log_file_backup_count_validation(self):
        """Test validation of log file backup count."""
        config = LoggingConfig(log_file_backup_count=0)

        with pytest.raises(ValueError, match="log_file_backup_count must be >= 1"):
            config.validate()
