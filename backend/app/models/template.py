"""SQLAlchemy ORM model for Templates."""
from __future__ import annotations

import uuid
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base, now_utc

class Template(Base):
    __tablename__ = "templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    author_sub = Column(String(256), nullable=True)
    filename = Column(String(512), nullable=True)  # stored pptx filename
    theme_color = Column(String(32), nullable=True)
    slide_count = Column(Integer, default=0)
    layout_names = Column(JSON, default=list)  # list of layout names
    placeholder_map = Column(JSON, default=dict)  # layout -> placeholder list
    is_builtin = Column(String(8), default="false")
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    decks = relationship("Deck", back_populates="template")
