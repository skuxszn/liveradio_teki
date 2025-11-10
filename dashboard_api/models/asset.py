"""Video asset models."""

from datetime import datetime
from typing import Optional, Any, List

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    BigInteger,
    Float,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON as SQLAlchemyJSON
from pydantic import BaseModel, Field, field_validator

from database import Base


class VideoAsset(Base):
    """Video asset database model."""

    __tablename__ = "video_assets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(512), unique=True, nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    duration = Column(Float, nullable=True)  # seconds
    resolution = Column(String(32), nullable=True)
    frame_rate = Column(Float, nullable=True)
    video_codec = Column(String(64), nullable=True)
    audio_codec = Column(String(64), nullable=True)
    bitrate = Column(Integer, nullable=True)  # kbps
    pixel_format = Column(String(32), nullable=True)
    # Use JSONB in Postgres; fallback to generic JSON type for SQLite tests
    validation_errors = Column(JSONB, nullable=True)
    # Tags: list of strings
    tags = Column((JSONB if JSONB is not None else SQLAlchemyJSON), nullable=True)
    is_valid = Column(Boolean, default=False, index=True)
    thumbnail_path = Column(String(1024), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("dashboard_users.id"), nullable=True)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    uploaded_at = Column(DateTime, default=datetime.utcnow)  # kept for backward compatibility
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
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    usage_count: int

    @field_validator("tags", mode="before")
    @classmethod
    def ensure_tags_list(cls, value):
        if value is None:
            return []
        return value

    class Config:
        from_attributes = True


class VideoAssetCreateRequest(BaseModel):
    """Asset create (upload) request - used for JSON-based creation if needed."""

    filename: Optional[str] = None
    tags: Optional[List[str]] = Field(default=None)


class VideoAssetUpdateRequest(BaseModel):
    """Asset update request."""

    filename: Optional[str] = None  # rename operation
    tags: Optional[List[str]] = Field(default=None)


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
