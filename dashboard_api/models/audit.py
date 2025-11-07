"""Audit log models."""

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, INET
from pydantic import BaseModel

from database import Base


class AuditLog(Base):
    """Audit log database model."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("dashboard_users.id"), nullable=True)
    action = Column(String(128), nullable=False, index=True)
    resource_type = Column(String(64), nullable=True, index=True)
    resource_id = Column(String(128), nullable=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# Pydantic models for API

class AuditLogResponse(BaseModel):
    """Audit log response model."""
    id: int
    user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[Any]
    ip_address: Optional[str]
    success: bool
    error_message: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

