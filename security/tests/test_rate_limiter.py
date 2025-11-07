"""
Tests for rate limiting module.
"""

import time
from typing import Optional
from unittest.mock import Mock

import pytest

from security.rate_limiter import (
    RateLimitConfig,
    RateLimitExceeded,
    RateLimiter,
)


class MockRequest:
    """Mock FastAPI request for testing."""

    def __init__(self, ip: str = "127.0.0.1", forwarded_for: Optional[str] = None):
        self.client = Mock()
        self.client.host = ip
        self.headers = {}
        if forwarded_for:
            self.headers["X-Forwarded-For"] = forwarded_for


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_create_config_with_defaults(self):
        """Test creating config with default values."""
        config = RateLimitConfig(max_requests=10)

        assert config.max_requests == 10
        assert config.window_seconds == 60
        assert config.enabled is True

    def test_create_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = RateLimitConfig(max_requests=100, window_seconds=300, enabled=False)

        assert config.max_requests == 100
        assert config.window_seconds == 300
        assert config.enabled is False


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_get_client_ip_direct(self):
        """Test extracting client IP from direct connection."""
        config = RateLimitConfig(max_requests=10)
        limiter = RateLimiter(config)

        request = MockRequest(ip="192.168.1.100")
        ip = limiter._get_client_ip(request)

        assert ip == "192.168.1.100"

    def test_get_client_ip_forwarded(self):
        """Test extracting client IP from X-Forwarded-For header."""
        config = RateLimitConfig(max_requests=10)
        limiter = RateLimiter(config)

        request = MockRequest(ip="10.0.0.1", forwarded_for="203.0.113.1, 198.51.100.1")
        ip = limiter._get_client_ip(request)

        # Should return the first IP in the chain (original client)
        assert ip == "203.0.113.1"

    def test_get_client_ip_no_client(self):
        """Test extracting client IP when client is None."""
        config = RateLimitConfig(max_requests=10)
        limiter = RateLimiter(config)

        request = Mock()
        request.client = None
        request.headers = {}
        ip = limiter._get_client_ip(request)

        assert ip == "unknown"

    def test_check_rate_limit_within_limit(self):
        """Test rate limiting when within limit."""
        config = RateLimitConfig(max_requests=5, window_seconds=60)
        limiter = RateLimiter(config)

        request = MockRequest(ip="192.168.1.100")

        # Make 5 requests (at the limit)
        for i in range(5):
            allowed, retry_after = limiter.check_rate_limit(request)
            assert allowed is True
            assert retry_after == 0

    def test_check_rate_limit_exceeds_limit(self):
        """Test rate limiting when exceeding limit."""
        config = RateLimitConfig(max_requests=3, window_seconds=60)
        limiter = RateLimiter(config)

        request = MockRequest(ip="192.168.1.100")

        # Make 3 requests (at the limit)
        for i in range(3):
            limiter.check_rate_limit(request)

        # 4th request should be rejected
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_rate_limit(request)

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail
        assert "Retry-After" in exc_info.value.headers

    def test_check_rate_limit_different_ips(self):
        """Test that rate limiting is per-IP."""
        config = RateLimitConfig(max_requests=2, window_seconds=60)
        limiter = RateLimiter(config)

        request1 = MockRequest(ip="192.168.1.100")
        request2 = MockRequest(ip="192.168.1.101")

        # Each IP should have its own limit
        limiter.check_rate_limit(request1)
        limiter.check_rate_limit(request1)
        limiter.check_rate_limit(request2)
        limiter.check_rate_limit(request2)

        # Both should now be at the limit
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit(request1)

        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit(request2)

    def test_check_rate_limit_window_expiry(self):
        """Test that requests expire after the time window."""
        config = RateLimitConfig(max_requests=2, window_seconds=1)
        limiter = RateLimiter(config)

        request = MockRequest(ip="192.168.1.100")

        # Make 2 requests
        limiter.check_rate_limit(request)
        limiter.check_rate_limit(request)

        # Wait for window to expire
        time.sleep(1.1)

        # Should be able to make more requests
        allowed, retry_after = limiter.check_rate_limit(request)
        assert allowed is True

    def test_check_rate_limit_disabled(self):
        """Test that rate limiting can be disabled."""
        config = RateLimitConfig(max_requests=2, enabled=False)
        limiter = RateLimiter(config)

        request = MockRequest(ip="192.168.1.100")

        # Should allow unlimited requests when disabled
        for i in range(100):
            allowed, retry_after = limiter.check_rate_limit(request)
            assert allowed is True
            assert retry_after == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_async(self):
        """Test async rate limit checking."""
        config = RateLimitConfig(max_requests=5)
        limiter = RateLimiter(config)

        request = MockRequest(ip="192.168.1.100")

        # Make requests using async method
        for i in range(5):
            result = await limiter.check_rate_limit_async(request)
            assert result is True

        # Next request should fail
        with pytest.raises(RateLimitExceeded):
            await limiter.check_rate_limit_async(request)

    def test_get_remaining_requests(self):
        """Test getting remaining request count."""
        config = RateLimitConfig(max_requests=5)
        limiter = RateLimiter(config)

        request = MockRequest(ip="192.168.1.100")

        # Initially should have all requests available
        assert limiter.get_remaining_requests(request) == 5

        # After one request
        limiter.check_rate_limit(request)
        assert limiter.get_remaining_requests(request) == 4

        # After three more requests
        limiter.check_rate_limit(request)
        limiter.check_rate_limit(request)
        limiter.check_rate_limit(request)
        assert limiter.get_remaining_requests(request) == 1

    def test_get_remaining_requests_disabled(self):
        """Test getting remaining requests when limiting is disabled."""
        config = RateLimitConfig(max_requests=5, enabled=False)
        limiter = RateLimiter(config)

        request = MockRequest(ip="192.168.1.100")

        # Should always return max_requests when disabled
        assert limiter.get_remaining_requests(request) == 5

    def test_reset_limits_specific_ip(self):
        """Test resetting limits for a specific IP."""
        config = RateLimitConfig(max_requests=2)
        limiter = RateLimiter(config)

        request1 = MockRequest(ip="192.168.1.100")
        request2 = MockRequest(ip="192.168.1.101")

        # Use up limits for both IPs
        limiter.check_rate_limit(request1)
        limiter.check_rate_limit(request1)
        limiter.check_rate_limit(request2)
        limiter.check_rate_limit(request2)

        # Reset only IP 1
        limiter.reset_limits(ip="192.168.1.100")

        # IP 1 should be able to make requests again
        allowed, _ = limiter.check_rate_limit(request1)
        assert allowed is True

        # IP 2 should still be limited
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit(request2)

    def test_reset_limits_all(self):
        """Test resetting limits for all IPs."""
        config = RateLimitConfig(max_requests=2)
        limiter = RateLimiter(config)

        request1 = MockRequest(ip="192.168.1.100")
        request2 = MockRequest(ip="192.168.1.101")

        # Use up limits for both IPs
        limiter.check_rate_limit(request1)
        limiter.check_rate_limit(request1)
        limiter.check_rate_limit(request2)
        limiter.check_rate_limit(request2)

        # Reset all
        limiter.reset_limits()

        # Both IPs should be able to make requests again
        allowed1, _ = limiter.check_rate_limit(request1)
        allowed2, _ = limiter.check_rate_limit(request2)
        assert allowed1 is True
        assert allowed2 is True

    def test_cleanup_old_requests(self):
        """Test that old requests are cleaned up."""
        config = RateLimitConfig(max_requests=5, window_seconds=1)
        limiter = RateLimiter(config)

        request = MockRequest(ip="192.168.1.100")

        # Make some requests
        limiter.check_rate_limit(request)
        limiter.check_rate_limit(request)
        limiter.check_rate_limit(request)

        # Wait for cleanup
        time.sleep(1.1)

        # Check that old requests were cleaned up
        ip = limiter._get_client_ip(request)
        current_time = time.time()
        limiter._cleanup_old_requests(ip, current_time)

        # Should have no requests left
        assert len(limiter._request_times[ip]) == 0

    def test_rate_limit_exceeded_error(self):
        """Test RateLimitExceeded error details."""
        error = RateLimitExceeded(retry_after=30)

        assert error.status_code == 429
        assert "Rate limit exceeded" in error.detail
        assert error.headers["Retry-After"] == "30"

    def test_rate_limit_exceeded_custom_message(self):
        """Test RateLimitExceeded with custom message."""
        error = RateLimitExceeded(detail="Custom rate limit message", retry_after=60)

        assert error.status_code == 429
        assert error.detail == "Custom rate limit message"
        assert error.headers["Retry-After"] == "60"
