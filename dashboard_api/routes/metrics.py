"""Monitoring and metrics routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import datetime, timedelta
import psutil
import os

from database import get_db
from dependencies import get_current_user

router = APIRouter()


@router.get("/current")
async def get_current_metrics(
    current_user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current system metrics.

    Args:
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        dict: Current metrics.
    """
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # Get stream status (from ffmpeg_manager if available)
    stream_status = "unknown"
    stream_pid = None
    stream_uptime = 0

    # Get tracks played today
    tracks_today_result = db.execute(
        text(
            """
        SELECT COUNT(*) 
        FROM track_mappings 
        WHERE last_played_at >= CURRENT_DATE
        """
        )
    ).fetchone()
    tracks_today = tracks_today_result[0] if tracks_today_result else 0

    # Get total mappings
    total_mappings_result = db.execute(text("SELECT COUNT(*) FROM track_mappings")).fetchone()
    total_mappings = total_mappings_result[0] if total_mappings_result else 0

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "cpu_percent": round(cpu_percent, 1),
            "memory_percent": round(memory.percent, 1),
            "memory_used_mb": round(memory.used / 1024 / 1024, 0),
            "memory_total_mb": round(memory.total / 1024 / 1024, 0),
            "disk_percent": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
            "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
        },
        "stream": {
            "status": stream_status,
            "pid": stream_pid,
            "uptime_seconds": stream_uptime,
        },
        "tracks": {
            "today": tracks_today,
            "total_mappings": total_mappings,
        },
    }


@router.get("/history")
async def get_metrics_history(
    hours: int = Query(24, ge=1, le=168),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get historical metrics.

    Args:
        hours: Number of hours of history to retrieve.
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        dict: Historical metrics data.
    """
    # For MVP, return simulated historical data
    # In production, this would query a time-series database or metrics store

    now = datetime.utcnow()
    datapoints = []

    # Generate sample data points (every hour)
    for i in range(hours):
        timestamp = now - timedelta(hours=hours - i)
        datapoints.append(
            {
                "timestamp": timestamp.isoformat(),
                "cpu_percent": 45 + (i % 20),  # Simulated
                "memory_percent": 60 + (i % 15),  # Simulated
                "tracks_played": i % 10,  # Simulated
            }
        )

    return {"period_hours": hours, "datapoints": datapoints}


@router.get("/summary")
async def get_metrics_summary(
    current_user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get summary statistics.

    Args:
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        dict: Summary statistics.
    """
    # Total tracks
    total_tracks = db.execute(text("SELECT COUNT(*) FROM track_mappings")).fetchone()[0]

    # Total assets
    total_assets = db.execute(text("SELECT COUNT(*) FROM video_assets")).fetchone()[0]

    # Most played track
    most_played = db.execute(
        text(
            """
        SELECT track_key, play_count
        FROM track_mappings
        ORDER BY play_count DESC
        LIMIT 1
        """
        )
    ).fetchone()

    # Recent activity count
    recent_activity = db.execute(
        text(
            """
        SELECT COUNT(*)
        FROM audit_log
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
        """
        )
    ).fetchone()[0]

    # Active users count
    active_users = db.execute(
        text(
            """
        SELECT COUNT(DISTINCT user_id)
        FROM audit_log
        WHERE timestamp >= NOW() - INTERVAL '7 days'
        """
        )
    ).fetchone()[0]

    # Parse most played if exists
    most_played_data = None
    if most_played and most_played[0]:
        track_parts = most_played[0].split(" - ", 1)
        artist = track_parts[0] if len(track_parts) > 0 else "Unknown"
        title = track_parts[1] if len(track_parts) > 1 else track_parts[0]
        most_played_data = {
            "artist": artist,
            "title": title,
            "play_count": most_played[1] if len(most_played) > 1 else 0,
        }

    return {
        "tracks": {"total": total_tracks, "most_played": most_played_data},
        "assets": {"total": total_assets},
        "activity": {"last_24h": recent_activity, "active_users_7d": active_users},
    }


@router.get("/activity")
async def get_recent_activity(
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get recent activity feed.

    Args:
        limit: Number of activity entries to return.
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        dict: Recent activity entries.
    """
    # Get recent audit log entries
    result = db.execute(
        text(
            f"""
        SELECT 
            a.id,
            a.action,
            a.resource_type,
            a.resource_id,
            a.details,
            a.timestamp,
            a.success,
            u.username
        FROM audit_log a
        LEFT JOIN dashboard_users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC
        LIMIT {limit}
        """
        )
    ).fetchall()

    activities = []
    for row in result:
        activities.append(
            {
                "id": row[0],
                "action": row[1],
                "resource_type": row[2],
                "resource_id": row[3],
                "details": row[4],
                "timestamp": row[5].isoformat() if row[5] else None,
                "success": row[6],
                "username": row[7] or "System",
            }
        )

    return {"activities": activities, "count": len(activities)}
