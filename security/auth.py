"""
Authentication middleware for webhook and API endpoints.

Provides:
- Webhook secret validation (X-Webhook-Secret header)
- Bearer token authentication for API endpoints
- FastAPI dependency injection support
"""

import secrets
from typing import Optional

from fastapi import Header, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from security.config import SecurityConfig


class WebhookAuthError(HTTPException):
    """Exception raised when webhook authentication fails."""

    def __init__(self, detail: str = "Invalid or missing webhook secret"):
        super().__init__(status_code=401, detail=detail)


class APIAuthError(HTTPException):
    """Exception raised when API authentication fails."""

    def __init__(self, detail: str = "Invalid or missing API token"):
        super().__init__(status_code=401, detail=detail)


# HTTP Bearer token scheme for API authentication
security_scheme = HTTPBearer()


def validate_webhook_secret(
    x_webhook_secret: Optional[str] = Header(None),
    config: Optional[SecurityConfig] = None,
) -> bool:
    """Validate AzuraCast webhook secret from X-Webhook-Secret header.

    Args:
        x_webhook_secret: Value from X-Webhook-Secret header
        config: Security configuration (uses env if not provided)

    Returns:
        True if authentication is successful

    Raises:
        WebhookAuthError: If secret is missing or invalid
    """
    if config is None:
        config = SecurityConfig.from_env()

    if not x_webhook_secret:
        raise WebhookAuthError("Missing X-Webhook-Secret header")

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(x_webhook_secret, config.webhook_secret):
        raise WebhookAuthError("Invalid webhook secret")

    return True


def require_api_token(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
    config: Optional[SecurityConfig] = None,
) -> bool:
    """Validate Bearer token for API endpoints.

    Args:
        credentials: HTTP Bearer credentials from Authorization header
        config: Security configuration (uses env if not provided)

    Returns:
        True if authentication is successful

    Raises:
        APIAuthError: If token is missing or invalid
    """
    if config is None:
        config = SecurityConfig.from_env()

    if not credentials:
        raise APIAuthError("Missing Authorization header")

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(credentials.credentials, config.api_token):
        raise APIAuthError("Invalid API token")

    return True


async def validate_webhook_request(
    request: Request, config: Optional[SecurityConfig] = None
) -> bool:
    """Async wrapper for webhook validation with request context.

    Args:
        request: FastAPI request object
        config: Security configuration (uses env if not provided)

    Returns:
        True if authentication is successful

    Raises:
        WebhookAuthError: If secret is missing or invalid
    """
    x_webhook_secret = request.headers.get("X-Webhook-Secret")
    return validate_webhook_secret(x_webhook_secret, config)


async def validate_api_request(request: Request, config: Optional[SecurityConfig] = None) -> bool:
    """Async wrapper for API token validation with request context.

    Args:
        request: FastAPI request object
        config: Security configuration (uses env if not provided)

    Returns:
        True if authentication is successful

    Raises:
        APIAuthError: If token is missing or invalid
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise APIAuthError("Missing or invalid Authorization header format")

    token = auth_header.replace("Bearer ", "", 1)

    if config is None:
        config = SecurityConfig.from_env()

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(token, config.api_token):
        raise APIAuthError("Invalid API token")

    return True


