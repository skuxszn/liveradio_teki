"""Stream control routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional

from dependencies import get_current_user, require_operator
from services.stream_service import StreamService
from database import get_db
from services.auth_service import AuthService
from sqlalchemy.orm import Session

router = APIRouter()


class ManualSwitchRequest(BaseModel):
    """Manual track switch request."""
    artist: str = Field(..., description="Artist name")
    title: str = Field(..., description="Track title")


@router.get("/status")
async def get_stream_status(current_user = Depends(get_current_user)):
    """Get current stream status.
    
    Args:
        current_user: Current authenticated user.
        
    Returns:
        dict: Stream status information.
    """
    stream_service = StreamService()
    return stream_service.get_status()


@router.post("/start")
async def start_stream(
    request: Request,
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Start the FFmpeg stream.
    
    Args:
        request: FastAPI request.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        dict: Start result.
        
    Raises:
        HTTPException: If start fails.
    """
    stream_service = StreamService()
    result = await stream_service.start_stream()
    
    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="stream_started",
        resource_type="stream",
        ip_address=request.client.host if request.client else None,
        success=result["success"],
        error_message=result.get("message") if not result["success"] else None
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return result


@router.post("/stop")
async def stop_stream(
    request: Request,
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Stop the FFmpeg stream.
    
    Args:
        request: FastAPI request.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        dict: Stop result.
        
    Raises:
        HTTPException: If stop fails.
    """
    stream_service = StreamService()
    result = await stream_service.stop_stream()
    
    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="stream_stopped",
        resource_type="stream",
        ip_address=request.client.host if request.client else None,
        success=result["success"],
        error_message=result.get("message") if not result["success"] else None
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return result


@router.post("/restart")
async def restart_stream(
    request: Request,
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Restart the FFmpeg stream.
    
    Args:
        request: FastAPI request.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        dict: Restart result.
        
    Raises:
        HTTPException: If restart fails.
    """
    stream_service = StreamService()
    result = await stream_service.restart_stream()
    
    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="stream_restarted",
        resource_type="stream",
        ip_address=request.client.host if request.client else None,
        success=result["success"],
        error_message=result.get("message") if not result["success"] else None
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return result


@router.post("/switch")
async def manual_switch(
    request: Request,
    switch_data: ManualSwitchRequest,
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Manually switch to a different track.
    
    Args:
        request: FastAPI request.
        switch_data: Track information.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        dict: Switch result.
        
    Raises:
        HTTPException: If switch fails.
    """
    stream_service = StreamService()
    result = await stream_service.switch_track(
        artist=switch_data.artist,
        title=switch_data.title
    )
    
    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="track_switched",
        resource_type="stream",
        details={"artist": switch_data.artist, "title": switch_data.title},
        ip_address=request.client.host if request.client else None,
        success=result["success"],
        error_message=result.get("message") if not result["success"] else None
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return result

