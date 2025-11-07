"""Tests for monitoring configuration."""

import os
import pytest

from monitoring.config import MonitoringConfig, get_config


class TestMonitoringConfig:
    """Test cases for MonitoringConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MonitoringConfig()

        assert config.metrics_port == 9090
        assert config.metrics_path == "/metrics"
        assert config.health_check_interval == 5.0
        assert config.enable_auto_recovery is True
        assert config.max_restart_attempts == 3

    def test_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("METRICS_PORT", "8080")
        monkeypatch.setenv("HEALTH_CHECK_INTERVAL", "10.0")
        monkeypatch.setenv("ENABLE_AUTO_RECOVERY", "false")
        monkeypatch.setenv("MAX_RESTART_ATTEMPTS", "5")

        config = MonitoringConfig.from_env()

        assert config.metrics_port == 8080
        assert config.health_check_interval == 10.0
        assert config.enable_auto_recovery is False
        assert config.max_restart_attempts == 5

    def test_validate_invalid_port(self):
        """Test validation with invalid port."""
        config = MonitoringConfig(metrics_port=99999)

        with pytest.raises(ValueError, match="Invalid metrics_port"):
            config.validate()

    def test_validate_invalid_interval(self):
        """Test validation with invalid interval."""
        config = MonitoringConfig(health_check_interval=-1.0)

        with pytest.raises(ValueError, match="Invalid health_check_interval"):
            config.validate()

    def test_validate_invalid_restart_attempts(self):
        """Test validation with invalid restart attempts."""
        config = MonitoringConfig(max_restart_attempts=-1)

        with pytest.raises(ValueError, match="Invalid max_restart_attempts"):
            config.validate()

    def test_validate_valid_config(self):
        """Test validation with valid configuration."""
        config = MonitoringConfig()
        # Should not raise any exception
        config.validate()

    def test_get_config(self, monkeypatch):
        """Test get_config helper function."""
        monkeypatch.setenv("METRICS_PORT", "9000")

        config = get_config()

        assert isinstance(config, MonitoringConfig)
        assert config.metrics_port == 9000
