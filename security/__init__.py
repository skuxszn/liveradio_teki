"""
Security module for 24/7 FFmpeg YouTube Radio Stream.

This module provides:
- Webhook authentication (AzuraCast X-Webhook-Secret validation)
- API authentication (Bearer token)
- Rate limiting (IP-based throttling)
- License manifest tracking for music rights compliance
- Security configuration management

Usage:
    from security.auth import validate_webhook_secret, require_api_token
    from security.rate_limiter import RateLimiter
    from security.license_manager import LicenseManager
    from security.config import SecurityConfig
"""

from security.auth import require_api_token, validate_webhook_secret
from security.config import SecurityConfig
from security.license_manager import LicenseManager
from security.rate_limiter import RateLimiter

__version__ = "1.0.0"
__all__ = [
    "validate_webhook_secret",
    "require_api_token",
    "RateLimiter",
    "LicenseManager",
    "SecurityConfig",
]
