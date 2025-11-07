"""
Rate limiting implementation for API and webhook endpoints.

Implements a sliding window rate limiter with IP-based tracking
to prevent abuse and excessive requests.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import DefaultDict, Deque, Optional, Tuple

from fastapi import HTTPException, Request


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting.

    Attributes:
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds (default: 60 for per-minute limiting)
        enabled: Whether rate limiting is enabled
    """

    max_requests: int
    window_seconds: int = 60
    enabled: bool = True


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded. Please try again later.",
        retry_after: Optional[int] = None,
    ):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        super().__init__(status_code=429, detail=detail, headers=headers)


class RateLimiter:
    """Sliding window rate limiter with IP-based tracking.

    This implementation uses a sliding window algorithm to track requests
    per IP address and enforce rate limits.

    Attributes:
        config: Rate limiting configuration
        _request_times: Dict mapping IP addresses to deques of request timestamps
    """

    def __init__(self, config: RateLimitConfig):
        """Initialize rate limiter.

        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self._request_times: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request.

        Handles X-Forwarded-For header for proxied requests.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address as string
        """
        # Check X-Forwarded-For header (for proxied requests)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain (original client)
            return forwarded.split(",")[0].strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        # Default fallback (should rarely happen)
        return "unknown"

    def _cleanup_old_requests(self, ip: str, current_time: float) -> None:
        """Remove request timestamps outside the time window.

        Args:
            ip: Client IP address
            current_time: Current timestamp
        """
        cutoff_time = current_time - self.config.window_seconds

        # Remove old timestamps from the left of the deque
        while self._request_times[ip] and self._request_times[ip][0] < cutoff_time:
            self._request_times[ip].popleft()

    def check_rate_limit(self, request: Request) -> Tuple[bool, int]:
        """Check if request is within rate limit.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (is_allowed, retry_after_seconds)

        Raises:
            RateLimitExceeded: If rate limit is exceeded and enabled
        """
        if not self.config.enabled:
            return True, 0

        ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean up old requests
        self._cleanup_old_requests(ip, current_time)

        # Check if we're within the limit
        request_count = len(self._request_times[ip])

        if request_count >= self.config.max_requests:
            # Calculate retry-after time (when oldest request will expire)
            if self._request_times[ip]:
                oldest_request = self._request_times[ip][0]
                retry_after = int(oldest_request + self.config.window_seconds - current_time)
            else:
                retry_after = self.config.window_seconds

            raise RateLimitExceeded(
                detail=f"Rate limit exceeded. Maximum {self.config.max_requests} "
                f"requests per {self.config.window_seconds} seconds.",
                retry_after=retry_after,
            )

        # Record this request
        self._request_times[ip].append(current_time)

        return True, 0

    async def check_rate_limit_async(self, request: Request) -> bool:
        """Async wrapper for rate limit checking.

        Args:
            request: FastAPI request object

        Returns:
            True if request is allowed

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        return self.check_rate_limit(request)[0]

    def get_remaining_requests(self, request: Request) -> int:
        """Get number of remaining requests in current window.

        Args:
            request: FastAPI request object

        Returns:
            Number of remaining requests allowed
        """
        if not self.config.enabled:
            return self.config.max_requests

        ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean up old requests
        self._cleanup_old_requests(ip, current_time)

        # Calculate remaining
        request_count = len(self._request_times[ip])
        return max(0, self.config.max_requests - request_count)

    def reset_limits(self, ip: Optional[str] = None) -> None:
        """Reset rate limits for a specific IP or all IPs.

        Args:
            ip: IP address to reset (None to reset all)
        """
        if ip:
            if ip in self._request_times:
                del self._request_times[ip]
        else:
            self._request_times.clear()
