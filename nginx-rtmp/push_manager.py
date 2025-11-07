"""Dynamic push URL manager for nginx-rtmp.

Fetches YouTube stream key from dashboard and manages nginx-rtmp push directives.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class NginxPushManager:
    """Manages nginx-rtmp push URLs dynamically."""
    
    def __init__(self, dashboard_url: str, api_token: str):
        self.dashboard_url = dashboard_url.rstrip("/")
        self.api_token = api_token
        self.current_stream_key = None
        
    async def fetch_stream_key(self) -> str:
        """Fetch YouTube stream key from dashboard."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.dashboard_url}/api/v1/config/internal/export",
                    headers={"Authorization": f"Bearer {self.api_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    stream_key = data.get("settings", {}).get("stream", {}).get("YOUTUBE_STREAM_KEY", "")
                    return stream_key
                else:
                    logger.error(f"Failed to fetch config: HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching stream key: {e}")
            return None
    
    async def update_nginx_config(self, stream_key: str) -> bool:
        """Update nginx config with new stream key and reload."""
        try:
            # Read template
            template_path = Path("/usr/local/nginx/conf/nginx.conf.template")
            output_path = Path("/usr/local/nginx/conf/nginx.conf")
            
            with open(template_path, "r") as f:
                config_content = f.read()
            
            # Replace placeholder
            config_content = config_content.replace("${YOUTUBE_STREAM_KEY}", stream_key)
            
            # Write new config
            with open(output_path, "w") as f:
                f.write(config_content)
            
            # Reload nginx
            subprocess.run(["/usr/local/nginx/sbin/nginx", "-s", "reload"], check=True)
            logger.info(f"Nginx config updated with stream key: {stream_key[:10]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update nginx config: {e}")
            return False
    
    async def run(self, interval: int = 60):
        """Main loop to check and update config."""
        logger.info(f"Starting nginx push manager (interval: {interval}s)")
        
        while True:
            try:
                stream_key = await self.fetch_stream_key()
                
                if stream_key and stream_key != self.current_stream_key:
                    logger.info("Stream key changed, updating nginx config...")
                    success = await self.update_nginx_config(stream_key)
                    
                    if success:
                        self.current_stream_key = stream_key
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in push manager loop: {e}")
                await asyncio.sleep(interval)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    dashboard_url = os.getenv("DASHBOARD_API_URL", "http://dashboard-api:9001")
    api_token = os.getenv("API_TOKEN", "")
    interval = int(os.getenv("CONFIG_REFRESH_INTERVAL", "60"))
    
    manager = NginxPushManager(dashboard_url, api_token)
    asyncio.run(manager.run(interval))

