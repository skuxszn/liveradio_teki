"""
Tests for security configuration module.
"""

import os
from unittest.mock import patch

import pytest

from security.config import SecurityConfig, get_config


class TestSecurityConfig:
    """Tests for SecurityConfig class."""

    def test_create_config_with_valid_values(self):
        """Test creating config with valid values."""
        config = SecurityConfig(
            webhook_secret="a" * 16,
            api_token="b" * 32,
            webhook_rate_limit=10,
            api_rate_limit=60,
        )

        assert config.webhook_secret == "a" * 16
        assert config.api_token == "b" * 32
        assert config.webhook_rate_limit == 10
        assert config.api_rate_limit == 60
        assert config.enable_rate_limiting is True
        assert config.enable_license_tracking is True

    def test_from_env_with_valid_environment(self):
        """Test loading config from environment variables."""
        env_vars = {
            "WEBHOOK_SECRET": "test-webhook-secret-16",
            "API_TOKEN": "test-api-token-32-characters-long-secure",
            "WEBHOOK_RATE_LIMIT": "20",
            "API_RATE_LIMIT": "100",
            "LICENSE_MANIFEST_PATH": "/custom/path/manifest.json",
            "ENABLE_RATE_LIMITING": "true",
            "ENABLE_LICENSE_TRACKING": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = SecurityConfig.from_env()

            assert config.webhook_secret == "test-webhook-secret-16"
            assert config.api_token == "test-api-token-32-characters-long-secure"
            assert config.webhook_rate_limit == 20
            assert config.api_rate_limit == 100
            assert config.license_manifest_path == "/custom/path/manifest.json"
            assert config.enable_rate_limiting is True
            assert config.enable_license_tracking is False

    def test_from_env_missing_webhook_secret(self):
        """Test that missing WEBHOOK_SECRET raises ValueError."""
        env_vars = {
            "API_TOKEN": "test-api-token-32-characters-long",
        }

        # Clear WEBHOOK_SECRET if it exists
        with patch.dict(os.environ, env_vars, clear=False):
            if "WEBHOOK_SECRET" in os.environ:
                del os.environ["WEBHOOK_SECRET"]

            with pytest.raises(ValueError, match="WEBHOOK_SECRET"):
                SecurityConfig.from_env()

    def test_from_env_missing_api_token(self):
        """Test that missing API_TOKEN raises ValueError."""
        env_vars = {
            "WEBHOOK_SECRET": "test-webhook-secret-16",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            if "API_TOKEN" in os.environ:
                del os.environ["API_TOKEN"]

            with pytest.raises(ValueError, match="API_TOKEN"):
                SecurityConfig.from_env()

    def test_validate_short_webhook_secret(self):
        """Test validation rejects short webhook secret."""
        config = SecurityConfig(webhook_secret="short", api_token="a" * 32)

        with pytest.raises(ValueError, match="WEBHOOK_SECRET must be at least 16"):
            config.validate()

    def test_validate_short_api_token(self):
        """Test validation rejects short API token."""
        config = SecurityConfig(webhook_secret="a" * 16, api_token="short")

        with pytest.raises(ValueError, match="API_TOKEN must be at least 32"):
            config.validate()

    def test_validate_negative_rate_limits(self):
        """Test validation rejects negative rate limits."""
        config = SecurityConfig(webhook_secret="a" * 16, api_token="b" * 32, webhook_rate_limit=-1)

        with pytest.raises(ValueError, match="WEBHOOK_RATE_LIMIT must be positive"):
            config.validate()

    def test_validate_valid_config(self):
        """Test validation passes for valid config."""
        config = SecurityConfig(webhook_secret="a" * 16, api_token="b" * 32)

        # Should not raise
        config.validate()

    def test_get_config_returns_validated_config(self):
        """Test get_config returns a validated config."""
        env_vars = {
            "WEBHOOK_SECRET": "valid-webhook-secret-16-chars",
            "API_TOKEN": "valid-api-token-32-characters-long-secure",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = get_config()

            assert config.webhook_secret == "valid-webhook-secret-16-chars"
            assert config.api_token == "valid-api-token-32-characters-long-secure"

    def test_default_values(self):
        """Test default values are set correctly."""
        config = SecurityConfig(webhook_secret="a" * 16, api_token="b" * 32)

        assert config.webhook_rate_limit == 10
        assert config.api_rate_limit == 60
        assert config.license_manifest_path == "/srv/config/license_manifest.json"
        assert config.enable_rate_limiting is True
        assert config.enable_license_tracking is True


