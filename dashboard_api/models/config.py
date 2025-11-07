"""Configuration settings models."""

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel, Field

from database import Base


class Setting(Base):
    """Dashboard settings database model."""

    __tablename__ = "dashboard_settings"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(64), nullable=False, index=True)
    key = Column(String(128), nullable=False)
    value = Column(Text, nullable=True)
    value_type = Column(String(32), nullable=False)
    default_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False)
    validation_regex = Column(Text, nullable=True)
    validation_min = Column(Numeric, nullable=True)
    validation_max = Column(Numeric, nullable=True)
    allowed_values = Column(JSONB, nullable=True)
    is_required = Column(Boolean, default=False)
    requires_restart = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models for API

class SettingResponse(BaseModel):
    """Setting response model."""
    id: int
    category: str
    key: str
    value: Optional[str]
    value_type: str
    default_value: Optional[str]
    description: Optional[str]
    is_secret: bool
    is_required: bool
    requires_restart: bool
    validation_regex: Optional[str] = None
    validation_min: Optional[float] = None
    validation_max: Optional[float] = None
    allowed_values: Optional[Any] = None

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    """Setting update request."""
    value: str = Field(..., description="New setting value")


class SettingsBulkUpdate(BaseModel):
    """Bulk settings update request."""
    updates: dict[str, str] = Field(..., description="Map of 'category.key' to new value")


class ConfigExport(BaseModel):
    """Configuration export model."""
    settings: dict[str, dict[str, str]]
    exported_at: datetime
    version: str = "1.0.0"

