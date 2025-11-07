"""Shared configuration client for all services.

Fetches configuration from dashboard database via API.
Use this in any service that needs dynamic config.
"""

import asyncio
import logging
from typing import Optional, Dict, Callable

import httpx

logger = logging.getLogger(__name__)


class DashboardConfigClient:
    """Client for fetching configuration from dashboard API."""
    
    def __init__(
        self,
        dashboard_url: str,
        api_token: str,
        refresh_interval: int = 60,
        service_name: str = "unknown"
    ):
        """Initialize config client.
        
        Args:
            dashboard_url: Dashboard API base URL.
            api_token: API token for authentication.
            refresh_interval: How often to refresh (seconds).
            service_name: Name of this service for logging.
        """
        self.dashboard_url = dashboard_url.rstrip("/")
        self.api_token = api_token
        self.refresh_interval = refresh_interval
        self.service_name = service_name
        self.current_config: Optional[Dict] = None
        self._fetch_lock = asyncio.Lock()
    
    async def fetch_config(self) -> Optional[Dict]:
        """Fetch all configuration from dashboard.
        
        Returns:
            Dict with all settings by category, or None if failed.
        """
        async with self._fetch_lock:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{self.dashboard_url}/api/v1/config/internal/export",
                        headers={"Authorization": f"Bearer {self.api_token}"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        settings = data.get("settings", {})
                        self.current_config = settings
                        logger.info(f"[{self.service_name}] Successfully fetched configuration")
                        return settings
                    else:
                        logger.error(f"[{self.service_name}] Failed to fetch config: HTTP {response.status_code}")
                        return None
                        
            except httpx.RequestError as e:
                logger.error(f"[{self.service_name}] Request error: {e}")
                return None
            except Exception as e:
                logger.error(f"[{self.service_name}] Unexpected error: {e}")
                return None
    
    def get_setting(self, category: str, key: str, default: str = "") -> str:
        """Get a specific setting value.
        
        Args:
            category: Setting category (e.g. 'stream', 'encoding').
            key: Setting key.
            default: Default value if not found.
            
        Returns:
            Setting value or default.
        """
        if not self.current_config:
            return default
        
        return self.current_config.get(category, {}).get(key, default)
    
    async def start_auto_refresh(
        self,
        on_change: Optional[Callable[[Dict, Dict], None]] = None
    ):
        """Start automatic configuration refresh loop.
        
        Args:
            on_change: Optional callback(old_config, new_config) called when config changes.
        """
        logger.info(f"[{self.service_name}] Starting auto-refresh (interval: {self.refresh_interval}s)")
        
        while True:
            try:
                old_config = self.current_config.copy() if self.current_config else {}
                new_config = await self.fetch_config()
                
                if new_config and on_change and old_config != new_config:
                    await on_change(old_config, new_config)
                
                await asyncio.sleep(self.refresh_interval)
                
            except asyncio.CancelledError:
                logger.info(f"[{self.service_name}] Auto-refresh cancelled")
                break
            except Exception as e:
                logger.error(f"[{self.service_name}] Error in auto-refresh: {e}")
                await asyncio.sleep(self.refresh_interval)


