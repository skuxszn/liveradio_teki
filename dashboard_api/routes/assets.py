"""Video asset management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Query, Form, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Tuple
import os
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime

from database import get_db
from dependencies import get_current_user, require_operator
from models.asset import (
    VideoAsset,
    VideoAssetResponse,
    VideoAssetUpdateRequest,
)
from services.auth_service import AuthService
from sqlalchemy import text
from sqlalchemy import cast, String
from config import settings
from pydantic import BaseModel, Field

router = APIRouter()
def get_current_user_from_header_or_query(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Allow auth via Authorization header or token query param (for <video> tag)."""
    from utils.crypto import verify_token
    from models.user import User

    raw = None
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization.split(" ", 1)[1]
    elif token:
        raw = token

    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    payload = verify_token(raw, token_type="access")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return user

# Configuration
# Upload directly to canonical base path which is mounted from host ./loops directory
UPLOAD_DIR = str(settings.loops_path)
THUMBNAILS_DIR = "/tmp/thumbnails"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Ensure directories exist
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)
except OSError as e:
    print(f"Warning: Could not create directories at {UPLOAD_DIR}: {e}")
    # Fallback to tmp for testing/local environments without /srv/loops
    try:
        UPLOAD_DIR = "/tmp/loops"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(THUMBNAILS_DIR, exist_ok=True)
        print(f"Using fallback upload dir: {UPLOAD_DIR}")
    except Exception as e2:
        print(f"Warning: Could not create fallback directories: {e2}")


@router.get("/stats", response_model=dict)
async def get_asset_stats(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Get video asset statistics."""
    total_assets = db.query(VideoAsset).count()
    valid_assets = db.query(VideoAsset).filter(VideoAsset.is_valid == True).count()
    total_size = db.query(VideoAsset).with_entities(func.sum(VideoAsset.file_size)).scalar() or 0
    return {
        "total_assets": total_assets,
        "valid_assets": valid_assets,
        "invalid_assets": total_assets - valid_assets,
        "total_storage_bytes": int(total_size) if total_size else 0,
        "total_storage_mb": float(round(total_size / 1024 / 1024, 2)) if total_size else 0.0,
    }


@router.get("/", response_model=dict)
async def list_assets(
    search: Optional[str] = Query(None, description="Search by filename or tags (fuzzy)"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    sort: str = Query(
        "created_at",
        description="Sort field",
        pattern="^(filename|created_at|file_size|duration)$",
    ),
    direction: str = Query(
        "desc", description="Sort direction", pattern="^(asc|desc)$"
    ),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List video assets with pagination, search, and server-side sorting."""
    query = db.query(VideoAsset)

    if search:
        like = f"%{search.lower()}%"
        # Build OR filters rather than UNION to avoid dialect-specific issues
        filters = [func.lower(VideoAsset.filename).like(like)]
        # Cast JSONB -> TEXT for Postgres; generic String for others
        try:
            filters.append(func.lower(cast(VideoAsset.tags, String)).like(like))
        except Exception:
            pass
        from sqlalchemy import or_
        query = query.filter(or_(*filters))

    # Sorting
    sort_column = {
        "filename": VideoAsset.filename,
        "created_at": VideoAsset.created_at,
        "file_size": VideoAsset.file_size,
        "duration": VideoAsset.duration,
    }[sort]
    order_clause = sort_column.asc() if direction == "asc" else sort_column.desc()

    total = query.count()
    items = query.order_by(order_clause).offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [VideoAssetResponse.model_validate(i) for i in items],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
        "sorting": {"sort": sort, "direction": direction},
    }


@router.get("/search", response_model=dict)
async def search_assets(
    q: Optional[str] = Query(None, description="Search text for filename contains"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search assets by filename with pagination.

    Returns a minimal payload suitable for typeahead UIs.
    """
    query = db.query(VideoAsset)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(func.lower(VideoAsset.filename).like(like))

    total = query.count()
    items = (
        query.order_by(VideoAsset.uploaded_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    results = [
        {
            "id": a.id,
            "filename": a.filename,
            "is_valid": a.is_valid,
            "resolution": a.resolution,
            "duration": a.duration,
            "file_size": a.file_size,
        }
        for a in items
    ]

    return {
        "results": results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


def _save_and_extract(
    *, db: Session, uploaded_file: UploadFile, tags_list: Optional[List[str]], current_user
) -> VideoAsset:
    """Save one uploaded file to disk, create DB row, extract metadata, and audit."""
    # Check file extension
    if not uploaded_file.filename.endswith((".mp4", ".MP4")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only MP4 files are allowed"
        )

    # Normalize filename: lowercase, underscores, strip spaces
    original_name = uploaded_file.filename
    name, ext = os.path.splitext(original_name)
    normalized = name.strip().lower().replace(" ", "_") + ext.lower()

    # Collision-safe rename: ensure neither DB nor filesystem has it
    final_name = normalized
    counter = 1
    while True:
        existing_db = db.query(VideoAsset).filter(VideoAsset.filename == final_name).first()
        existing_fs = os.path.exists(os.path.join(UPLOAD_DIR, final_name))
        if not existing_db and not existing_fs:
            break
        stem, ext2 = os.path.splitext(normalized)
        final_name = f"{stem}-{counter}{ext2}"
        counter += 1

    # Save file
    file_path = os.path.join(UPLOAD_DIR, final_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)

    # Size validation
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    # Create asset record
    asset = VideoAsset(
        filename=final_name,
        file_path=file_path,
        file_size=file_size,
        tags=tags_list or [],
        is_valid=False,
        validation_errors=None,
        uploaded_by=current_user.id if getattr(current_user, "id", None) else None,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # Try to extract metadata (best-effort)
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode == 0:
            probe = json.loads(result.stdout)
            video_stream = next(
                (s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None
            )
            audio_stream = next(
                (s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None
            )
            if video_stream:
                asset.resolution = f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}"
                try:
                    asset.frame_rate = eval(video_stream.get("r_frame_rate", "0/1"))
                except Exception:
                    asset.frame_rate = None
                asset.video_codec = video_stream.get("codec_name", "unknown")
                asset.pixel_format = video_stream.get("pix_fmt", "unknown")
            if audio_stream:
                asset.audio_codec = audio_stream.get("codec_name", "unknown")
            if "format" in probe:
                try:
                    asset.duration = float(probe["format"].get("duration", 0))
                except Exception:
                    asset.duration = None
                try:
                    asset.bitrate = int(probe["format"].get("bit_rate", 0)) // 1000
                except Exception:
                    asset.bitrate = None
            asset.is_valid = True
            asset.validation_errors = None
            db.commit()
            db.refresh(asset)
    except Exception:
        # Ignore metadata extraction failure
        pass

    return asset


@router.post("/upload", response_model=VideoAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None, description="JSON array of tags"),
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
    try:
        # Parse tags
        tags_list = None
        if tags:
            try:
                parsed = json.loads(tags)
                if isinstance(parsed, list):
                    tags_list = [str(t) for t in parsed]
            except Exception:
                tags_list = None

        asset = _save_and_extract(db=db, uploaded_file=file, tags_list=tags_list, current_user=current_user)

        # Log action
        auth_service = AuthService(db)
        auth_service.log_audit(
            user_id=current_user.id,
            action="asset_uploaded",
            resource_type="asset",
            resource_id=str(asset.id),
            details={"filename": asset.filename, "size": asset.file_size},
            ip_address=request.client.host if request.client else None,
        )

        return asset

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload failed: {str(e)}"
        )


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    request: Request,
    filename: str,
    force: bool = Query(False, description="Force delete even if referenced by mappings"),
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

    # Prevent deletion if referenced by any mapping unless forced
    ref_count = db.execute(
        text("SELECT COUNT(1) FROM track_mappings WHERE loop_file_path LIKE :lp"),
        {"lp": f"%/{filename}"},
    ).scalar() or 0

    if ref_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset is referenced by {ref_count} mapping(s). Pass force=true to override.",
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


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_asset(
    request: Request,
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(
        None, description="Use files[] to upload multiple assets in one request"
    ),
    tags: Optional[str] = Form(None, description="JSON array of tags"),
    current_user=Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Create (upload) asset(s). Supports single file with 'file' or multiple via 'files[]'."""
    # Multiple uploads
    if files and len(files) > 0:
        # Parse tags once and apply to all
        tags_list: Optional[List[str]] = None
        if tags:
            try:
                parsed = json.loads(tags)
                if isinstance(parsed, list):
                    tags_list = [str(t) for t in parsed]
            except Exception:
                tags_list = None
        results: List[VideoAsset] = []
        for uf in files:
            try:
                asset = _save_and_extract(
                    db=db, uploaded_file=uf, tags_list=tags_list, current_user=current_user
                )
                # Audit per asset
                try:
                    auth_service = AuthService(db)
                    auth_service.log_audit(
                        user_id=current_user.id,
                        action="asset_uploaded",
                        resource_type="asset",
                        resource_id=str(asset.id),
                        details={"filename": asset.filename, "size": asset.file_size},
                        ip_address=request.client.host if request.client else None,
                    )
                except Exception:
                    pass
                results.append(asset)
            finally:
                # Ensure file stream is closed
                try:
                    uf.file.close()
                except Exception:
                    pass
        return {"items": [VideoAssetResponse.model_validate(a) for a in results]}

    # Single upload fallback
    if not file:
        raise HTTPException(status_code=400, detail="No file(s) provided")
    return await upload_asset(request, file=file, tags=tags, current_user=current_user, db=db)  # type: ignore


@router.get("/{asset_id}", response_model=VideoAssetResponse)
async def get_asset(
    asset_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch a single asset by id."""
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/{asset_id}", response_model=VideoAssetResponse)
async def update_asset(
    request: Request,
    asset_id: int,
    payload: VideoAssetUpdateRequest,
    current_user=Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Update asset fields (rename, tags)."""
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    old_filename = asset.filename

    # Rename operation
    if payload.filename and payload.filename != asset.filename:
        new_name = payload.filename.strip().lower().replace(" ", "_")
        if not new_name.endswith(".mp4"):
            new_name += ".mp4"
        # Ensure not taken
        exists = db.query(VideoAsset).filter(VideoAsset.filename == new_name).first()
        if exists:
            raise HTTPException(status_code=409, detail="Filename already exists")
        # Perform filesystem rename
        new_path = os.path.join(UPLOAD_DIR, new_name)
        try:
            os.rename(asset.file_path, new_path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Original file missing on disk")
        asset.filename = new_name
        asset.file_path = new_path

    # Tags update
    if payload.tags is not None:
        asset.tags = [str(t) for t in payload.tags]

    asset.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(asset)

    # Audit
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="asset_updated",
        resource_type="asset",
        resource_id=str(asset.id),
        details={"old_filename": old_filename, "new_filename": asset.filename, "tags": asset.tags},
        ip_address=request.client.host if request.client else None,
    )

    return asset


@router.delete("/id/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset_by_id(
    request: Request,
    asset_id: int,
    force: bool = Query(False, description="Force delete even if referenced by mappings"),
    current_user=Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Delete a video asset by id."""
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not asset:
        # Idempotent
        return

    # Prevent deletion if referenced by any mapping unless forced
    ref_count = db.execute(
        text("SELECT COUNT(1) FROM track_mappings WHERE loop_file_path LIKE :lp"),
        {"lp": f"%/{asset.filename}"},
    ).scalar() or 0

    if ref_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset is referenced by {ref_count} mapping(s). Pass force=true to override.",
        )

    # Delete file
    if os.path.exists(asset.file_path):
        os.remove(asset.file_path)

    # Delete thumbnail if exists
    if asset.thumbnail_path and os.path.exists(asset.thumbnail_path):
        os.remove(asset.thumbnail_path)

    db.delete(asset)
    db.commit()

    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="asset_deleted",
        resource_type="asset",
        resource_id=str(asset_id),
        details={"filename": asset.filename},
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
            # Generate thumbnail (optional)
            try:
                thumb_path = os.path.join(THUMBNAILS_DIR, f"{os.path.splitext(asset.filename)[0]}.jpg")
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        asset.file_path,
                        "-frames:v",
                        "1",
                        "-q:v",
                        "2",
                        thumb_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if os.path.exists(thumb_path):
                    asset.thumbnail_path = thumb_path
            except Exception:
                pass
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


# -------------------------
# Batch operations
# -------------------------


class BatchIds(BaseModel):
    ids: List[int] = Field(..., description="Asset IDs to operate on")
    force: bool = False


class BatchUpdatePayload(BaseModel):
    ids: List[int]
    filename_prefix: Optional[str] = None
    filename_suffix: Optional[str] = None
    tags: Optional[List[str]] = None  # replace tags when provided


class BatchTagsPayload(BaseModel):
    ids: List[int]
    add: Optional[List[str]] = None
    remove: Optional[List[str]] = None
    replace: Optional[List[str]] = None


@router.post("/batch/delete", response_model=dict)
async def batch_delete_assets(
    request: Request,
    payload: BatchIds,
    current_user=Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Batch delete assets by IDs. Returns per-item result."""
    results: List[dict] = []
    for asset_id in payload.ids:
        try:
            asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
            if not asset:
                results.append({"id": asset_id, "success": True, "skipped": True})
                continue
            # Reference protection (match path only; there is no separate filename column)
            ref_count = db.execute(
                text("SELECT COUNT(1) FROM track_mappings WHERE loop_file_path LIKE :lp"),
                {"lp": f"%/{asset.filename}"},
            ).scalar() or 0
            if ref_count > 0 and not payload.force:
                results.append(
                    {
                        "id": asset_id,
                        "success": False,
                        "error": f"Referenced by {ref_count} mapping(s)",
                    }
                )
                continue
            # Delete files
            try:
                if asset.file_path and os.path.exists(asset.file_path):
                    os.remove(asset.file_path)
                if asset.thumbnail_path and os.path.exists(asset.thumbnail_path):
                    os.remove(asset.thumbnail_path)
            except Exception:
                pass
            db.delete(asset)
            db.commit()
            # Audit
            try:
                auth_service = AuthService(db)
                auth_service.log_audit(
                    user_id=current_user.id,
                    action="asset_deleted",
                    resource_type="asset",
                    resource_id=str(asset_id),
                    details={"filename": asset.filename},
                    ip_address=request.client.host if request.client else None,
                )
            except Exception:
                pass
            results.append({"id": asset_id, "success": True})
        except Exception as e:
            results.append({"id": asset_id, "success": False, "error": str(e)})
    return {"results": results}


@router.post("/batch/update", response_model=dict)
async def batch_update_assets(
    request: Request,
    payload: BatchUpdatePayload,
    current_user=Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Batch update filename prefix/suffix and optionally replace tags."""
    results: List[dict] = []
    for asset_id in payload.ids:
        try:
            asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
            if not asset:
                results.append({"id": asset_id, "success": False, "error": "Not found"})
                continue
            old_filename = asset.filename
            # Rename with prefix/suffix if provided
            if payload.filename_prefix is not None or payload.filename_suffix is not None:
                name, ext = os.path.splitext(asset.filename)
                new_name = f"{payload.filename_prefix or ''}{name}{payload.filename_suffix or ''}{ext}"
                new_name = new_name.strip().lower().replace(" ", "_")
                if not new_name.endswith(".mp4"):
                    new_name += ".mp4"
                if new_name != asset.filename:
                    exists = db.query(VideoAsset).filter(VideoAsset.filename == new_name).first()
                    if exists:
                        results.append(
                            {"id": asset_id, "success": False, "error": "Filename exists"}
                        )
                        continue
                    new_path = os.path.join(UPLOAD_DIR, new_name)
                    try:
                        os.rename(asset.file_path, new_path)
                    except FileNotFoundError:
                        results.append(
                            {"id": asset_id, "success": False, "error": "File missing on disk"}
                        )
                        continue
                    asset.filename = new_name
                    asset.file_path = new_path
            # Replace tags when provided
            if payload.tags is not None:
                asset.tags = [str(t) for t in payload.tags]
            asset.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(asset)
            # Audit
            try:
                auth_service = AuthService(db)
                auth_service.log_audit(
                    user_id=current_user.id,
                    action="asset_updated",
                    resource_type="asset",
                    resource_id=str(asset.id),
                    details={
                        "old_filename": old_filename,
                        "new_filename": asset.filename,
                        "tags": asset.tags,
                    },
                    ip_address=request.client.host if request.client else None,
                )
            except Exception:
                pass
            results.append({"id": asset_id, "success": True})
        except Exception as e:
            results.append({"id": asset_id, "success": False, "error": str(e)})
    return {"results": results}


@router.post("/batch/tags", response_model=dict)
async def batch_tags_assets(
    request: Request,
    payload: BatchTagsPayload,
    current_user=Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Batch tag assignment: add/remove or replace tags for selected assets."""
    results: List[dict] = []
    for asset_id in payload.ids:
        try:
            asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
            if not asset:
                results.append({"id": asset_id, "success": False, "error": "Not found"})
                continue
            existing = set([str(t) for t in (asset.tags or [])])
            if payload.replace is not None:
                asset.tags = [str(t) for t in payload.replace]
            else:
                tags = set(existing)
                if payload.add:
                    tags.update(str(t) for t in payload.add)
                if payload.remove:
                    remove_set = set(str(t) for t in payload.remove)
                    tags = {t for t in tags if t not in remove_set}
                asset.tags = sorted(tags)
            asset.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(asset)
            # Audit
            try:
                auth_service = AuthService(db)
                auth_service.log_audit(
                    user_id=current_user.id,
                    action="asset_tags_updated",
                    resource_type="asset",
                    resource_id=str(asset.id),
                    details={"tags": asset.tags},
                    ip_address=request.client.host if request.client else None,
                )
            except Exception:
                pass
            results.append({"id": asset_id, "success": True})
        except Exception as e:
            results.append({"id": asset_id, "success": False, "error": str(e)})
    return {"results": results}


@router.get("/file/{asset_id}")
async def stream_asset_by_id(
    asset_id: int, current_user=Depends(get_current_user_from_header_or_query), db: Session = Depends(get_db)
):
    """Stream/download the raw video file for previews."""
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not asset or not asset.file_path or not os.path.exists(asset.file_path):
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(
        asset.file_path,
        media_type="video/mp4",
        filename=asset.filename,
    )


@router.get("/file/by-filename/{filename}")
async def stream_asset_by_filename(
    filename: str, current_user=Depends(get_current_user_from_header_or_query), db: Session = Depends(get_db)
):
    """Stream/download the raw video file for previews by filename."""
    asset = db.query(VideoAsset).filter(VideoAsset.filename == filename).first()
    if not asset or not asset.file_path or not os.path.exists(asset.file_path):
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(
        asset.file_path,
        media_type="video/mp4",
        filename=asset.filename,
    )

@router.post("/{filename}/increment_usage")
async def increment_usage(
    request: Request,
    filename: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Increment usage_count and update last_used_at for an asset by filename."""
    asset = db.query(VideoAsset).filter(VideoAsset.filename == filename).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset not found: {filename}")

    asset.usage_count = (asset.usage_count or 0) + 1
    asset.last_used_at = datetime.utcnow()
    db.commit()
    db.refresh(asset)
    return {"success": True, "usage_count": asset.usage_count, "last_used_at": asset.last_used_at}


@router.get("/{filename}/usage", response_model=dict)
async def get_asset_usage(
    filename: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """List mappings referencing a given asset filename."""
    rows = db.execute(
        text(
            """
        SELECT id, track_key, azuracast_song_id, play_count, last_played_at
        FROM track_mappings
        WHERE loop_file_path LIKE :lp
        ORDER BY play_count DESC
        """
        ),
        {"lp": f"%/{filename}"},
    ).fetchall()

    usage = []
    for r in rows:
        track_parts = r[1].split(" - ", 1) if r[1] else ["Unknown", "Unknown"]
        usage.append(
            {
                "id": r[0],
                "artist": track_parts[0],
                "title": track_parts[1] if len(track_parts) > 1 else track_parts[0],
                "azuracast_song_id": r[2],
                "play_count": r[3] or 0,
                "last_played_at": r[4].isoformat() if r[4] else None,
            }
        )

    return {"filename": filename, "usage": usage, "count": len(usage)}


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
    """Get video asset statistics."""
    total_assets = db.query(VideoAsset).count()
    valid_assets = db.query(VideoAsset).filter(VideoAsset.is_valid == True).count()
    total_size = db.query(VideoAsset).with_entities(func.sum(VideoAsset.file_size)).scalar() or 0
    return {
        "total_assets": total_assets,
        "valid_assets": valid_assets,
        "invalid_assets": total_assets - valid_assets,
        "total_storage_bytes": int(total_size) if total_size else 0,
        "total_storage_mb": float(round(total_size / 1024 / 1024, 2)) if total_size else 0.0,
    }
