"""SQLAlchemy ORM models for Deck and Slide."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


def _now_utc():
    return datetime.now(timezone.utc)


class Deck(Base):
    __tablename__ = "decks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(512), nullable=False)
    topic = Column(Text, nullable=True)
    source_text = Column(Text, nullable=True)
    source_type = Column(String(64), default="topic")  # topic, document, template
    author_sub = Column(String(256), nullable=True)
    status = Column(String(64), default="draft")  # draft, compiled, exported
    template_id = Column(String(36), ForeignKey("templates.id"), nullable=True)
    slide_count = Column(Integer, default=0)
    version = Column(Integer, default=1)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now_utc)
    updated_at = Column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc)

    slides = relationship("Slide", back_populates="deck", cascade="all, delete-orphan", order_by="Slide.position")
    evaluations = relationship("Evaluation", back_populates="deck", cascade="all, delete-orphan")
    template = relationship("Template", back_populates="decks")


class Slide(Base):
    __tablename__ = "slides"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deck_id = Column(String(36), ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False)
    slide_type = Column(String(64), default="content")  # title, content, kpi, chart, table, comparison, process
    title = Column(String(512), nullable=True)
    body_text = Column(Text, nullable=True)
    speaker_notes = Column(Text, nullable=True)
    chart_data = Column(JSON, nullable=True)
    table_data = Column(JSON, nullable=True)
    layout_config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now_utc)

    deck = relationship("Deck", back_populates="slides")
