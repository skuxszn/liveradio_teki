"""Video asset models."""

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import Boolean, Column, DateTime, Integer, String, BigInteger, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel

from database import Base


class VideoAsset(Base):
    """Video asset database model."""

    __tablename__ = "video_assets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(512), unique=True, nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    duration = Column(Float, nullable=True)
    resolution = Column(String(32), nullable=True)
    frame_rate = Column(Float, nullable=True)
    video_codec = Column(String(64), nullable=True)
    audio_codec = Column(String(64), nullable=True)
    bitrate = Column(Integer, nullable=True)
    pixel_format = Column(String(32), nullable=True)
    is_valid = Column(Boolean, default=False, index=True)
    validation_errors = Column(JSONB, nullable=True)
    thumbnail_path = Column(String(1024), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("dashboard_users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)


# Pydantic models for API


class VideoAssetResponse(BaseModel):
    """Video asset response model."""

    id: int
    filename: str
    file_path: str
    file_size: Optional[int]
    duration: Optional[float]
    resolution: Optional[str]
    frame_rate: Optional[float]
    video_codec: Optional[str]
    audio_codec: Optional[str]
    bitrate: Optional[int]
    pixel_format: Optional[str]
    is_valid: bool
    validation_errors: Optional[Any]
    thumbnail_path: Optional[str]
    uploaded_at: datetime
    usage_count: int

    class Config:
        from_attributes = True


class VideoMetadata(BaseModel):
    """Video metadata from validation."""

    duration: float
    resolution: str
    frame_rate: float
    video_codec: str
    audio_codec: str
    bitrate: int
    pixel_format: str
    file_size: int
