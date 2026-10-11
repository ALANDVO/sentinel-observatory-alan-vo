"""SQLAlchemy ORM model for immutable audit log."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, String, Text

from backend.app.core.database import Base


def _now_utc():
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_sub = Column(String(256), nullable=True)
    actor_email = Column(String(512), nullable=True)
    action = Column(String(128), nullable=False)  # create_deck, delete_deck, export_deck, etc.
    resource_type = Column(String(64), nullable=True)  # deck, evaluation, template
    resource_id = Column(String(36), nullable=True)
    detail = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now_utc, nullable=False)
