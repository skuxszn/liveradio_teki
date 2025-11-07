"""Stream logs endpoint."""

import os
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stream/logs")
async def get_stream_logs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get latest FFmpeg stream logs from metadata watcher.
    
    Args:
        current_user: Authenticated user (from dependency).
        db: Database session (from dependency).
    
    Returns:
        dict: Log information and content.
    
    Raises:
        HTTPException: If fetching logs fails.
    """
    try:
        # Call metadata watcher API
        async with httpx.AsyncClient() as client:
            # Get metadata watcher URL and token from environment
            metadata_url = os.getenv("METADATA_WATCHER_URL", "http://metadata-watcher:9000")
            api_token = os.getenv("API_TOKEN", "")
            
            response = await client.get(
                f"{metadata_url}/logs/latest",
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch logs: HTTP {response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch logs")
    
    except httpx.TimeoutException:
        logger.error("Timeout while fetching logs from metadata watcher")
        raise HTTPException(status_code=504, detail="Timeout fetching logs")
    except httpx.RequestError as e:
        logger.error(f"Request error while fetching logs: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot reach metadata watcher: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")

