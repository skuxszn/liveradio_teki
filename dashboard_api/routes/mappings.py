"""Track mapping management routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text
from typing import List, Optional
import csv
import json
import io
from datetime import datetime

from database import get_db
from dependencies import get_current_user, require_operator
from services.auth_service import AuthService

router = APIRouter()


# Pydantic models
from pydantic import BaseModel, Field


class TrackMappingBase(BaseModel):
    """Base track mapping model."""
    artist: str = Field(..., min_length=1, description="Artist name")
    title: str = Field(..., min_length=1, description="Track title")
    video_loop: str = Field(..., description="Video loop filename")
    azuracast_song_id: Optional[str] = None
    notes: Optional[str] = None


class TrackMappingCreate(TrackMappingBase):
    """Track mapping creation model."""
    pass


class TrackMappingUpdate(TrackMappingBase):
    """Track mapping update model."""
    pass


class TrackMappingResponse(TrackMappingBase):
    """Track mapping response model."""
    id: int
    created_at: datetime
    play_count: int
    last_played_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/", response_model=dict)
async def list_mappings(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    filter_by: Optional[str] = None,
    sort_by: str = Query("track_key", regex="^(track_key|play_count|created_at|last_played_at)$"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all track mappings with pagination and filtering.
    
    Args:
        page: Page number (1-based).
        limit: Items per page.
        search: Search query (artist or title).
        filter_by: Filter criterion (mapped, unmapped, most_played).
        sort_by: Sort field.
        sort_order: Sort order (asc or desc).
        current_user: Current authenticated user.
        db: Database session.
        
    Returns:
        dict: Paginated mappings with metadata.
    """
    # Search filter
    where_clauses = []
    params = {}
    
    if search:
        where_clauses.append("LOWER(track_key) LIKE :search")
        params['search'] = f"%{search.lower()}%"
    
    # Build WHERE clause
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
    
    # Count total
    count_sql = f"""
        SELECT COUNT(*) as total
        FROM track_mappings
        {where_sql}
    """
    
    total_result = db.execute(text(count_sql), params).fetchone()
    total = total_result[0] if total_result else 0
    
    # Get paginated data
    offset = (page - 1) * limit
    order_clause = f"ORDER BY {sort_by} {'DESC' if sort_order == 'desc' else 'ASC'}"
    
    data_sql = f"""
        SELECT 
            id, track_key, loop_file_path, azuracast_song_id, notes,
            created_at, play_count, last_played_at
        FROM track_mappings
        {where_sql}
        {order_clause}
        LIMIT :limit OFFSET :offset
    """
    
    params.update({'limit': limit, 'offset': offset})
    result = db.execute(text(data_sql), params).fetchall()
    
    # Format results
    mappings = []
    for row in result:
        # Parse track_key into artist and title
        track_parts = row[1].split(' - ', 1) if row[1] else ['Unknown', 'Unknown']
        artist = track_parts[0] if len(track_parts) > 0 else 'Unknown'
        title = track_parts[1] if len(track_parts) > 1 else track_parts[0]
        
        mappings.append({
            'id': row[0],
            'artist': artist,
            'title': title,
            'video_loop': row[2],
            'azuracast_song_id': row[3],
            'notes': row[4],
            'created_at': row[5].isoformat() if row[5] else None,
            'play_count': row[6] or 0,
            'last_played_at': row[7].isoformat() if row[7] else None,
        })
    
    return {
        "mappings": mappings,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@router.get("/stats", response_model=dict)
async def get_mapping_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get track mapping statistics.
    
    Args:
        current_user: Current authenticated user.
        db: Database session.
        
    Returns:
        dict: Statistics.
    """
    # Total mappings
    total_result = db.execute(text("SELECT COUNT(*) FROM track_mappings")).fetchone()
    total = total_result[0] if total_result else 0
    
    # Most played
    most_played_result = db.execute(
        text("""
        SELECT track_key, play_count
        FROM track_mappings
        ORDER BY play_count DESC
        LIMIT 10
        """)
    ).fetchall()
    
    most_played = []
    for row in most_played_result:
        track_parts = row[0].split(' - ', 1) if row[0] else ['Unknown', 'Unknown']
        artist = track_parts[0] if len(track_parts) > 0 else 'Unknown'
        title = track_parts[1] if len(track_parts) > 1 else track_parts[0]
        most_played.append({"artist": artist, "title": title, "play_count": row[1]})
    
    # Recently added
    recent_result = db.execute(
        text("""
        SELECT track_key, created_at
        FROM track_mappings
        ORDER BY created_at DESC
        LIMIT 10
        """)
    ).fetchall()
    
    recently_added = []
    for row in recent_result:
        track_parts = row[0].split(' - ', 1) if row[0] else ['Unknown', 'Unknown']
        artist = track_parts[0] if len(track_parts) > 0 else 'Unknown'
        title = track_parts[1] if len(track_parts) > 1 else track_parts[0]
        recently_added.append({"artist": artist, "title": title, "created_at": row[1].isoformat()})
    
    return {
        "total_mappings": total,
        "most_played": most_played,
        "recently_added": recently_added
    }


@router.get("/{mapping_id}", response_model=dict)
async def get_mapping(
    mapping_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single track mapping by ID.
    
    Args:
        mapping_id: Mapping ID.
        current_user: Current authenticated user.
        db: Database session.
        
    Returns:
        dict: Track mapping.
        
    Raises:
        HTTPException: If mapping not found.
    """
    result = db.execute(
        text("""
        SELECT 
            id, track_key, loop_file_path, azuracast_song_id, notes,
            created_at, play_count, last_played_at
        FROM track_mappings
        WHERE id = :id
        """),
        {'id': mapping_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mapping not found: {mapping_id}"
        )
    
    # Parse track_key into artist and title
    track_parts = result[1].split(' - ', 1) if result[1] else ['Unknown', 'Unknown']
    artist = track_parts[0] if len(track_parts) > 0 else 'Unknown'
    title = track_parts[1] if len(track_parts) > 1 else track_parts[0]
    
    return {
        'id': result[0],
        'artist': artist,
        'title': title,
        'video_loop': result[2],
        'azuracast_song_id': result[3],
        'notes': result[4],
        'created_at': result[5].isoformat() if result[5] else None,
        'play_count': result[6] or 0,
        'last_played_at': result[7].isoformat() if result[7] else None,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_mapping(
    request: Request,
    mapping_data: TrackMappingCreate,
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Create a new track mapping.
    
    Args:
        request: FastAPI request.
        mapping_data: Mapping data.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        dict: Created mapping.
    """
    # Combine artist and title into track_key
    track_key = f"{mapping_data.artist} - {mapping_data.title}"
    
    # Insert mapping
    result = db.execute(
        text("""
        INSERT INTO track_mappings 
        (track_key, loop_file_path, azuracast_song_id, notes, created_at, play_count)
        VALUES (:track_key, :loop_file_path, :azuracast_song_id, :notes, NOW(), 0)
        RETURNING id, created_at
        """),
        {
            'track_key': track_key,
            'loop_file_path': mapping_data.video_loop,
            'azuracast_song_id': mapping_data.azuracast_song_id,
            'notes': mapping_data.notes
        }
    )
    
    row = result.fetchone()
    db.commit()
    
    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="mapping_created",
        resource_type="mapping",
        resource_id=str(row[0]),
        details={"track_key": track_key},
        ip_address=request.client.host if request.client else None
    )
    
    return {
        'id': row[0],
        'artist': mapping_data.artist,
        'title': mapping_data.title,
        'video_loop': mapping_data.video_loop,
        'azuracast_song_id': mapping_data.azuracast_song_id,
        'notes': mapping_data.notes,
        'created_at': row[1].isoformat(),
        'play_count': 0,
        'last_played_at': None,
    }


@router.put("/{mapping_id}")
async def update_mapping(
    request: Request,
    mapping_id: int,
    mapping_data: TrackMappingUpdate,
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Update a track mapping.
    
    Args:
        request: FastAPI request.
        mapping_id: Mapping ID.
        mapping_data: Updated mapping data.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        dict: Updated mapping.
        
    Raises:
        HTTPException: If mapping not found.
    """
    # Check if exists
    check = db.execute(
        text("SELECT id FROM track_mappings WHERE id = :id"),
        {'id': mapping_id}
    ).fetchone()
    
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mapping not found: {mapping_id}"
        )
    
    # Combine artist and title into track_key
    track_key = f"{mapping_data.artist} - {mapping_data.title}"
    
    # Update mapping
    db.execute(
        text("""
        UPDATE track_mappings
        SET track_key = :track_key,
            loop_file_path = :loop_file_path,
            azuracast_song_id = :azuracast_song_id,
            notes = :notes
        WHERE id = :id
        """),
        {
            'id': mapping_id,
            'track_key': track_key,
            'loop_file_path': mapping_data.video_loop,
            'azuracast_song_id': mapping_data.azuracast_song_id,
            'notes': mapping_data.notes
        }
    )
    db.commit()
    
    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="mapping_updated",
        resource_type="mapping",
        resource_id=str(mapping_id),
        details={"artist": mapping_data.artist, "title": mapping_data.title},
        ip_address=request.client.host if request.client else None
    )
    
    # Return updated mapping
    return await get_mapping(mapping_id, current_user, db)


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    request: Request,
    mapping_id: int,
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Delete a track mapping.
    
    Args:
        request: FastAPI request.
        mapping_id: Mapping ID.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Raises:
        HTTPException: If mapping not found.
    """
    # Check if exists
    check = db.execute(
        text("SELECT id FROM track_mappings WHERE id = :id"),
        {'id': mapping_id}
    ).fetchone()
    
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mapping not found: {mapping_id}"
        )
    
    # Delete mapping
    db.execute(
        text("DELETE FROM track_mappings WHERE id = :id"),
        {'id': mapping_id}
    )
    db.commit()
    
    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="mapping_deleted",
        resource_type="mapping",
        resource_id=str(mapping_id),
        ip_address=request.client.host if request.client else None
    )


@router.post("/bulk-import")
async def bulk_import_mappings(
    request: Request,
    file: UploadFile = File(...),
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Bulk import track mappings from CSV or JSON.
    
    Args:
        request: FastAPI request.
        file: Uploaded file (CSV or JSON).
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        dict: Import results.
    """
    content = await file.read()
    content_str = content.decode('utf-8')
    
    imported = []
    errors = []
    
    try:
        if file.filename.endswith('.csv'):
            # Parse CSV
            reader = csv.DictReader(io.StringIO(content_str))
            
            for i, row in enumerate(reader, start=1):
                try:
                    track_key = f"{row.get('artist', '')} - {row.get('title', '')}"
                    result = db.execute(
                        text("""
                        INSERT INTO track_mappings 
                        (track_key, loop_file_path, azuracast_song_id, notes, created_at, play_count)
                        VALUES (:track_key, :loop_file_path, :azuracast_song_id, :notes, NOW(), 0)
                        RETURNING id
                        """),
                        {
                            'track_key': track_key,
                            'loop_file_path': row.get('video_loop', ''),
                            'azuracast_song_id': row.get('azuracast_song_id'),
                            'notes': row.get('notes')
                        }
                    )
                    imported.append(result.fetchone()[0])
                except Exception as e:
                    errors.append(f"Row {i}: {str(e)}")
        
        elif file.filename.endswith('.json'):
            # Parse JSON
            data = json.loads(content_str)
            
            for i, item in enumerate(data, start=1):
                try:
                    track_key = f"{item.get('artist', '')} - {item.get('title', '')}"
                    result = db.execute(
                        text("""
                        INSERT INTO track_mappings 
                        (track_key, loop_file_path, azuracast_song_id, notes, created_at, play_count)
                        VALUES (:track_key, :loop_file_path, :azuracast_song_id, :notes, NOW(), 0)
                        RETURNING id
                        """),
                        {
                            'track_key': track_key,
                            'loop_file_path': item.get('video_loop', ''),
                            'azuracast_song_id': item.get('azuracast_song_id'),
                            'notes': item.get('notes')
                        }
                    )
                    imported.append(result.fetchone()[0])
                except Exception as e:
                    errors.append(f"Item {i}: {str(e)}")
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be CSV or JSON"
            )
        
        db.commit()
        
        # Log action
        auth_service = AuthService(db)
        auth_service.log_audit(
            user_id=current_user.id,
            action="mappings_bulk_imported",
            resource_type="mappings",
            details={"imported_count": len(imported), "error_count": len(errors)},
            ip_address=request.client.host if request.client else None
        )
        
        return {
            "success": True,
            "imported": imported,
            "imported_count": len(imported),
            "errors": errors,
            "error_count": len(errors)
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Import failed: {str(e)}"
        )


@router.post("/bulk-delete")
async def bulk_delete_mappings(
    request: Request,
    mapping_ids: List[int],
    current_user = Depends(require_operator),
    db: Session = Depends(get_db)
):
    """Bulk delete track mappings.
    
    Args:
        request: FastAPI request.
        mapping_ids: List of mapping IDs to delete.
        current_user: Current authenticated user (operator or admin).
        db: Database session.
        
    Returns:
        dict: Deletion results.
    """
    deleted = 0
    
    for mapping_id in mapping_ids:
        result = db.execute(
            text("DELETE FROM track_mappings WHERE id = :id"),
            {'id': mapping_id}
        )
        if result.rowcount > 0:
            deleted += 1
    
    db.commit()
    
    # Log action
    auth_service = AuthService(db)
    auth_service.log_audit(
        user_id=current_user.id,
        action="mappings_bulk_deleted",
        resource_type="mappings",
        details={"deleted_count": deleted},
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "success": True,
        "deleted_count": deleted
    }


@router.get("/export", response_model=dict)
async def export_mappings(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all track mappings to CSV format.
    
    Args:
        current_user: Current authenticated user.
        db: Database session.
        
    Returns:
        dict: CSV data.
    """
    result = db.execute(
        text("""
        SELECT track_key, loop_file_path, azuracast_song_id, notes, play_count
        FROM track_mappings
        ORDER BY track_key
        """)
    ).fetchall()
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['artist', 'title', 'video_loop', 'azuracast_song_id', 'notes', 'play_count'])
    
    for row in result:
        track_parts = row[0].split(' - ', 1) if row[0] else ['Unknown', 'Unknown']
        artist = track_parts[0] if len(track_parts) > 0 else 'Unknown'
        title = track_parts[1] if len(track_parts) > 1 else track_parts[0]
        writer.writerow([artist, title, row[1], row[2], row[3], row[4]])
    
    return {
        "csv_data": output.getvalue(),
        "row_count": len(result)
    }

