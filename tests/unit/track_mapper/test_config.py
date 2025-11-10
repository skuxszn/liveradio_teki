"""Unit tests for Track Mapper configuration"""

import os
import pytest
from unittest.mock import patch

from track_mapper.config import TrackMapperConfig


class TestTrackMapperConfig:
    """Test TrackMapperConfig class"""

    def test_default_values(self):
        """Test default configuration values"""
        config = TrackMapperConfig()

        assert config.postgres_host == "localhost"
        assert config.postgres_port == 5432
        assert config.postgres_user == "radio"
        assert config.postgres_db == "radio_db"
        assert config.loops_path == "/srv/loops"
        assert config.default_loop == "/srv/loops/default.mp4"
        assert config.cache_size == 1000
        assert config.cache_ttl_seconds == 3600
        assert config.log_level == "INFO"
        assert config.debug is False

    def test_from_env(self):
        """Test loading configuration from environment"""
        env_vars = {
            "POSTGRES_HOST": "db.example.com",
            "POSTGRES_PORT": "5433",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_DB": "testdb",
            "LOOPS_PATH": "/custom/loops",
            "DEFAULT_LOOP": "/custom/default.mp4",
            "CACHE_SIZE": "2000",
            "CACHE_TTL_SECONDS": "7200",
            "LOG_LEVEL": "DEBUG",
            "DEBUG": "true",
            "ENVIRONMENT": "testing",
        }

        with patch.dict(os.environ, env_vars):
            config = TrackMapperConfig.from_env()

        assert config.postgres_host == "db.example.com"
        assert config.postgres_port == 5433
        assert config.postgres_user == "testuser"
        assert config.postgres_password == "testpass"
        assert config.postgres_db == "testdb"
        assert config.loops_path == "/custom/loops"
        assert config.default_loop == "/custom/default.mp4"
        assert config.cache_size == 2000
        assert config.cache_ttl_seconds == 7200
        assert config.log_level == "DEBUG"
        assert config.debug is True
        assert config.environment == "testing"

    def test_database_url(self):
        """Test database URL generation"""
        config = TrackMapperConfig(
            postgres_host="testhost",
            postgres_port=5432,
            postgres_user="testuser",
            postgres_password="testpass",
            postgres_db="testdb",
        )

        expected = "postgresql://testuser:testpass@testhost:5432/testdb"
        assert config.database_url == expected

    def test_validate_success(self):
        """Test validation with valid configuration"""
        config = TrackMapperConfig(
            postgres_password="password123",
            loops_path="/srv/loops",
            default_loop="/srv/loops/default.mp4",
        )

        # Should not raise
        config.validate()

    def test_validate_missing_password(self):
        """Test validation fails without password"""
        config = TrackMapperConfig(postgres_password="")

        with pytest.raises(ValueError, match="POSTGRES_PASSWORD is required"):
            config.validate()

    def test_validate_invalid_pool_size(self):
        """Test validation fails with invalid pool size"""
        config = TrackMapperConfig(postgres_password="password", db_pool_size=0)

        with pytest.raises(ValueError, match="DB_POOL_SIZE must be at least 1"):
            config.validate()

    def test_validate_invalid_cache_size(self):
        """Test validation fails with invalid cache size"""
        config = TrackMapperConfig(postgres_password="password", cache_size=0)

        with pytest.raises(ValueError, match="CACHE_SIZE must be at least 1"):
            config.validate()

    def test_validate_missing_loops_path(self):
        """Test validation fails without loops path"""
        config = TrackMapperConfig(postgres_password="password", loops_path="")

        with pytest.raises(ValueError, match="LOOPS_PATH is required"):
            config.validate()

    def test_validate_missing_default_loop(self):
        """Test validation fails without default loop"""
        config = TrackMapperConfig(postgres_password="password", default_loop="")

        with pytest.raises(ValueError, match="DEFAULT_LOOP is required"):
            config.validate()

    def test_repr(self):
        """Test string representation (should hide password)"""
        config = TrackMapperConfig(
            postgres_host="testhost",
            postgres_port=5432,
            postgres_db="testdb",
            postgres_password="secret123",
        )

        repr_str = repr(config)
        assert "testhost" in repr_str
        assert "5432" in repr_str
        assert "testdb" in repr_str
        assert "secret123" not in repr_str  # Password should not appear

    def test_pool_configuration(self):
        """Test database pool configuration"""
        config = TrackMapperConfig(
            db_pool_size=10, db_max_overflow=20, db_pool_timeout=60, db_pool_recycle=7200
        )

        assert config.db_pool_size == 10
        assert config.db_max_overflow == 20
        assert config.db_pool_timeout == 60
        assert config.db_pool_recycle == 7200

