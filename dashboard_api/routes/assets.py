"""Video asset management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import os
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime

from database import get_db
from dependencies import get_current_user, require_operator
from models.asset import VideoAsset, VideoAssetResponse
from services.auth_service import AuthService

router = APIRouter()

# Configuration
# Upload directly to /srv/loops which is mounted from host ./loops directory
UPLOAD_DIR = "/srv/loops"
THUMBNAILS_DIR = "/tmp/thumbnails"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Ensure directories exist
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)
except OSError as e:
    print(f"Warning: Could not create directories: {e}")


@router.get("/", response_model=List[VideoAssetResponse])
async def list_assets(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """List all video assets.

    Args:
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        List[VideoAssetResponse]: List of video assets.
    """
    assets = db.query(VideoAsset).order_by(VideoAsset.uploaded_at.desc()).all()
    return assets


@router.post("/upload", response_model=VideoAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    current_user=Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Upload a video asset.

    Args:
        request: FastAPI request.
        file: Uploaded video file.
        current_user: Current authenticated user (operator or admin).
        db: Database session.

    Returns:
        VideoAssetResponse: Uploaded asset details.

    Raises:
        HTTPException: If upload fails or file is invalid.
    """
    # Check file extension
    if not file.filename.endswith((".mp4", ".MP4")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only MP4 files are allowed"
        )

    # Check if file already exists
    existing = db.query(VideoAsset).filter(VideoAsset.filename == file.filename).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"File already exists: {file.filename}"
        )

    # Save file
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Check file size
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB",
            )

        # Validate video (basic check - ffprobe validation can be added later)
        is_valid = True
        validation_errors = None

        # Create asset record
        asset = VideoAsset(
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            is_valid=is_valid,
            validation_errors=validation_errors,
            uploaded_by=current_user.id,
        )

        db.add(asset)
        db.commit()
        db.refresh(asset)

        # Log action
        auth_service = AuthService(db)
        auth_service.log_audit(
            user_id=current_user.id,
            action="asset_uploaded",
            resource_type="asset",
            resource_id=str(asset.id),
            details={"filename": file.filename, "size": file_size},
            ip_address=request.client.host if request.client else None,
        )

        return asset

    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload failed: {str(e)}"
        )


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    request: Request,
    filename: str,
    current_user=Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Delete a video asset.

    Args:
        request: FastAPI request.
        filename: Asset filename.
        current_user: Current authenticated user (operator or admin).
        db: Database session.

    Raises:
        HTTPException: If asset not found.
    """
    asset = db.query(VideoAsset).filter(VideoAsset.filename == filename).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset not found: {filename}"
        )

    # Delete file
    if os.path.exists(asset.file_path):
        os.remove(asset.file_path)

    # Delete thumbnail if exists
    if asset.thumbnail_path and os.path.exists(asset.thumbnail_path):
        os.remove(asset.thumbnail_path)

    # Delete database record
    db.delete(asset)
    db.commit()

    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="asset_deleted",
        resource_type="asset",
        resource_id=str(asset.id),
        details={"filename": filename},
        ip_address=request.client.host if request.client else None,
    )


@router.post("/{filename}/validate")
async def validate_asset(
    request: Request,
    filename: str,
    current_user=Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Validate a video asset using ffprobe.

    Args:
        request: FastAPI request.
        filename: Asset filename.
        current_user: Current authenticated user (operator or admin).
        db: Database session.

    Returns:
        dict: Validation results.

    Raises:
        HTTPException: If asset not found or validation fails.
    """
    asset = db.query(VideoAsset).filter(VideoAsset.filename == filename).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset not found: {filename}"
        )

    try:
        # Run ffprobe (if available)
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                asset.file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            probe_data = json.loads(result.stdout)

            # Extract video stream info
            video_stream = next(
                (s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"), None
            )

            audio_stream = next(
                (s for s in probe_data.get("streams", []) if s.get("codec_type") == "audio"), None
            )

            # Update asset metadata
            if video_stream:
                asset.resolution = f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}"
                asset.frame_rate = eval(video_stream.get("r_frame_rate", "0/1"))
                asset.video_codec = video_stream.get("codec_name", "unknown")
                asset.pixel_format = video_stream.get("pix_fmt", "unknown")

            if audio_stream:
                asset.audio_codec = audio_stream.get("codec_name", "unknown")

            if "format" in probe_data:
                asset.duration = float(probe_data["format"].get("duration", 0))
                asset.bitrate = int(probe_data["format"].get("bit_rate", 0)) // 1000  # kbps

            asset.is_valid = True
            asset.validation_errors = None
        else:
            asset.is_valid = False
            asset.validation_errors = {"error": "FFprobe failed", "stderr": result.stderr}

    except FileNotFoundError:
        # ffprobe not available
        asset.is_valid = True  # Assume valid if ffprobe not installed
        asset.validation_errors = {"warning": "ffprobe not available"}
    except Exception as e:
        asset.is_valid = False
        asset.validation_errors = {"error": str(e)}

    db.commit()
    db.refresh(asset)

    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="asset_validated",
        resource_type="asset",
        resource_id=str(asset.id),
        details={"filename": filename, "is_valid": asset.is_valid},
        ip_address=request.client.host if request.client else None,
    )

    return {
        "filename": filename,
        "is_valid": asset.is_valid,
        "metadata": {
            "resolution": asset.resolution,
            "duration": asset.duration,
            "frame_rate": asset.frame_rate,
            "video_codec": asset.video_codec,
            "audio_codec": asset.audio_codec,
            "bitrate": asset.bitrate,
            "pixel_format": asset.pixel_format,
        },
        "validation_errors": asset.validation_errors,
    }


@router.get("/{filename}/thumbnail")
async def get_thumbnail(
    filename: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get thumbnail for a video asset.

    Args:
        filename: Asset filename.
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        FileResponse: Thumbnail image.

    Raises:
        HTTPException: If asset or thumbnail not found.
    """
    asset = db.query(VideoAsset).filter(VideoAsset.filename == filename).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset not found: {filename}"
        )

    if not asset.thumbnail_path or not os.path.exists(asset.thumbnail_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not available")

    return FileResponse(asset.thumbnail_path)


@router.get("/stats", response_model=dict)
async def get_asset_stats(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Get video asset statistics.

    Args:
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        dict: Asset statistics.
    """
    total_assets = db.query(VideoAsset).count()
    valid_assets = db.query(VideoAsset).filter(VideoAsset.is_valid == True).count()

    # Calculate total storage
    total_size = db.query(VideoAsset).with_entities(func.sum(VideoAsset.file_size)).scalar() or 0

    return {
        "total_assets": total_assets,
        "valid_assets": valid_assets,
        "invalid_assets": total_assets - valid_assets,
        "total_storage_bytes": int(total_size) if total_size else 0,
        "total_storage_mb": float(round(total_size / 1024 / 1024, 2)) if total_size else 0.0,
    }
