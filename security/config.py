"""
Security configuration management for the radio stream application.

This module handles security-related configuration settings including:
- Webhook authentication secrets
- API token management
- Rate limiting thresholds
- License manifest paths
"""

import os
from dataclasses import dataclass


@dataclass
class SecurityConfig:
    """Security configuration for the application.

    Attributes:
        webhook_secret: Secret for validating AzuraCast webhooks
        api_token: Bearer token for API authentication
        webhook_rate_limit: Max webhook requests per minute per IP
        api_rate_limit: Max API requests per minute per IP
        license_manifest_path: Path to license manifest JSON file
        enable_rate_limiting: Whether to enforce rate limits
        enable_license_tracking: Whether to track license compliance
    """

    webhook_secret: str
    api_token: str
    webhook_rate_limit: int = 10
    api_rate_limit: int = 60
    license_manifest_path: str = "/srv/config/license_manifest.json"
    enable_rate_limiting: bool = True
    enable_license_tracking: bool = True

    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """Load security configuration from environment variables.

        Returns:
            SecurityConfig instance populated from environment

        Raises:
            ValueError: If required environment variables are missing
        """
        webhook_secret = os.getenv("WEBHOOK_SECRET")
        api_token = os.getenv("API_TOKEN")

        if not webhook_secret:
            raise ValueError("WEBHOOK_SECRET environment variable is required")
        if not api_token:
            raise ValueError("API_TOKEN environment variable is required")

        return cls(
            webhook_secret=webhook_secret,
            api_token=api_token,
            webhook_rate_limit=int(os.getenv("WEBHOOK_RATE_LIMIT", "10")),
            api_rate_limit=int(os.getenv("API_RATE_LIMIT", "60")),
            license_manifest_path=os.getenv(
                "LICENSE_MANIFEST_PATH", "/srv/config/license_manifest.json"
            ),
            enable_rate_limiting=os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true",
            enable_license_tracking=os.getenv("ENABLE_LICENSE_TRACKING", "true").lower() == "true",
        )

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration is invalid
        """
        if len(self.webhook_secret) < 16:
            raise ValueError("WEBHOOK_SECRET must be at least 16 characters")
        if len(self.api_token) < 32:
            raise ValueError("API_TOKEN must be at least 32 characters")
        if self.webhook_rate_limit < 1:
            raise ValueError("WEBHOOK_RATE_LIMIT must be positive")
        if self.api_rate_limit < 1:
            raise ValueError("API_RATE_LIMIT must be positive")


def get_config() -> SecurityConfig:
    """Get validated security configuration.

    Returns:
        Validated SecurityConfig instance

    Raises:
        ValueError: If configuration is invalid
    """
    config = SecurityConfig.from_env()
    config.validate()
    return config
