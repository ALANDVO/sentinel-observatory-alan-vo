"""SQLAlchemy ORM model for immutable audit log."""
from __future__ import annotations
import uuid
from sqlalchemy import JSON, Column, DateTime, String
from backend.app.core.database import Base, now_utc
class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_sub = Column(String(256)); actor_email = Column(String(512)); action = Column(String(128), nullable=False)
    resource_type = Column(String(64)); resource_id = Column(String(36)); detail = Column(JSON); ip_address = Column(String(64))
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
