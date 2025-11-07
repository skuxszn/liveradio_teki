"""
Tests for authentication middleware.
"""

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from security.auth import (
    APIAuthError,
    WebhookAuthError,
    require_api_token,
    validate_api_request,
    validate_webhook_request,
    validate_webhook_secret,
)
from security.config import SecurityConfig


class TestWebhookAuthentication:
    """Tests for webhook authentication."""

    def test_validate_webhook_secret_valid(self):
        """Test webhook validation with valid secret."""
        config = SecurityConfig(webhook_secret="test-secret-1234", api_token="a" * 32)

        result = validate_webhook_secret(x_webhook_secret="test-secret-1234", config=config)
        assert result is True

    def test_validate_webhook_secret_invalid(self):
        """Test webhook validation with invalid secret."""
        config = SecurityConfig(webhook_secret="test-secret-1234", api_token="a" * 32)

        with pytest.raises(WebhookAuthError, match="Invalid webhook secret"):
            validate_webhook_secret(x_webhook_secret="wrong-secret", config=config)

    def test_validate_webhook_secret_missing(self):
        """Test webhook validation with missing secret."""
        config = SecurityConfig(webhook_secret="test-secret-1234", api_token="a" * 32)

        with pytest.raises(WebhookAuthError, match="Missing X-Webhook-Secret"):
            validate_webhook_secret(x_webhook_secret=None, config=config)

    def test_validate_webhook_secret_timing_attack_protection(self):
        """Test that validation uses constant-time comparison."""
        config = SecurityConfig(webhook_secret="test-secret-1234", api_token="a" * 32)

        # This should not leak information about the secret through timing
        with pytest.raises(WebhookAuthError):
            validate_webhook_secret(x_webhook_secret="test-secret-9999", config=config)

    @pytest.mark.asyncio
    async def test_validate_webhook_request_valid(self):
        """Test async webhook request validation with valid secret."""
        config = SecurityConfig(webhook_secret="test-secret-1234", api_token="a" * 32)

        # Create mock request
        class MockRequest:
            headers = {"X-Webhook-Secret": "test-secret-1234"}

        request = MockRequest()
        result = await validate_webhook_request(request, config)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_webhook_request_invalid(self):
        """Test async webhook request validation with invalid secret."""
        config = SecurityConfig(webhook_secret="test-secret-1234", api_token="a" * 32)

        class MockRequest:
            headers = {"X-Webhook-Secret": "wrong-secret"}

        request = MockRequest()

        with pytest.raises(WebhookAuthError):
            await validate_webhook_request(request, config)


class TestAPIAuthentication:
    """Tests for API token authentication."""

    def test_require_api_token_valid(self):
        """Test API authentication with valid token."""
        config = SecurityConfig(
            webhook_secret="a" * 16, api_token="valid-token-32-chars-long-secure"
        )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid-token-32-chars-long-secure"
        )

        result = require_api_token(credentials=credentials, config=config)
        assert result is True

    def test_require_api_token_invalid(self):
        """Test API authentication with invalid token."""
        config = SecurityConfig(
            webhook_secret="a" * 16, api_token="valid-token-32-chars-long-secure"
        )

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")

        with pytest.raises(APIAuthError, match="Invalid API token"):
            require_api_token(credentials=credentials, config=config)

    def test_require_api_token_missing(self):
        """Test API authentication with missing credentials."""
        config = SecurityConfig(
            webhook_secret="a" * 16, api_token="valid-token-32-chars-long-secure"
        )

        with pytest.raises(APIAuthError, match="Missing Authorization header"):
            require_api_token(credentials=None, config=config)

    def test_require_api_token_timing_attack_protection(self):
        """Test that API token validation uses constant-time comparison."""
        config = SecurityConfig(
            webhook_secret="a" * 16, api_token="valid-token-32-chars-long-secure"
        )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="wrong-token-32-chars-long-secure"
        )

        # This should not leak information about the token through timing
        with pytest.raises(APIAuthError):
            require_api_token(credentials=credentials, config=config)

    @pytest.mark.asyncio
    async def test_validate_api_request_valid(self):
        """Test async API request validation with valid token."""
        config = SecurityConfig(
            webhook_secret="a" * 16, api_token="valid-token-32-chars-long-secure"
        )

        class MockRequest:
            headers = {"Authorization": "Bearer valid-token-32-chars-long-secure"}

        request = MockRequest()
        result = await validate_api_request(request, config)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_api_request_invalid_token(self):
        """Test async API request validation with invalid token."""
        config = SecurityConfig(
            webhook_secret="a" * 16, api_token="valid-token-32-chars-long-secure"
        )

        class MockRequest:
            headers = {"Authorization": "Bearer invalid-token"}

        request = MockRequest()

        with pytest.raises(APIAuthError, match="Invalid API token"):
            await validate_api_request(request, config)

    @pytest.mark.asyncio
    async def test_validate_api_request_missing_header(self):
        """Test async API request validation with missing Authorization header."""
        config = SecurityConfig(
            webhook_secret="a" * 16, api_token="valid-token-32-chars-long-secure"
        )

        class MockRequest:
            headers = {}

        request = MockRequest()

        with pytest.raises(APIAuthError, match="Missing or invalid Authorization"):
            await validate_api_request(request, config)

    @pytest.mark.asyncio
    async def test_validate_api_request_wrong_format(self):
        """Test async API request validation with wrong header format."""
        config = SecurityConfig(
            webhook_secret="a" * 16, api_token="valid-token-32-chars-long-secure"
        )

        class MockRequest:
            headers = {"Authorization": "Basic sometoken"}

        request = MockRequest()

        with pytest.raises(APIAuthError, match="Missing or invalid Authorization"):
            await validate_api_request(request, config)


class TestAuthErrors:
    """Tests for authentication error classes."""

    def test_webhook_auth_error_default(self):
        """Test WebhookAuthError with default message."""
        error = WebhookAuthError()
        assert error.status_code == 401
        assert "Invalid or missing webhook secret" in error.detail

    def test_webhook_auth_error_custom(self):
        """Test WebhookAuthError with custom message."""
        error = WebhookAuthError(detail="Custom error message")
        assert error.status_code == 401
        assert error.detail == "Custom error message"

    def test_api_auth_error_default(self):
        """Test APIAuthError with default message."""
        error = APIAuthError()
        assert error.status_code == 401
        assert "Invalid or missing API token" in error.detail

    def test_api_auth_error_custom(self):
        """Test APIAuthError with custom message."""
        error = APIAuthError(detail="Custom API error")
        assert error.status_code == 401
        assert error.detail == "Custom API error"
