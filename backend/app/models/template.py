"""SQLAlchemy ORM model for Templates."""
from __future__ import annotations
import uuid
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base, now_utc

class Template(Base):
    __tablename__ = "templates"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(256), nullable=False); description = Column(Text); author_sub = Column(String(256))
    filename = Column(String(512)); theme_color = Column(String(32)); slide_count = Column(Integer, default=0)
    layout_names = Column(JSON, default=list); placeholder_map = Column(JSON, default=dict)
    is_builtin = Column(String(8), default="false"); created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    decks = relationship("Deck", back_populates="template")
