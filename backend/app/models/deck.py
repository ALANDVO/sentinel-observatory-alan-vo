"""SQLAlchemy ORM models for Deck and Slide."""
from __future__ import annotations
import uuid
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base, now_utc

class Deck(Base):
    __tablename__ = "decks"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(512), nullable=False)
    topic = Column(Text); source_text = Column(Text); source_type = Column(String(64), default="topic")
    author_sub = Column(String(256)); status = Column(String(64), default="draft")
    template_id = Column(String(36), ForeignKey("templates.id"))
    slide_count = Column(Integer, default=0); version = Column(Integer, default=1)
    meta = Column(JSON, default=dict); created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    slides = relationship("Slide", back_populates="deck", cascade="all, delete-orphan", order_by="Slide.position")
    evaluations = relationship("Evaluation", back_populates="deck", cascade="all, delete-orphan")
    template = relationship("Template", back_populates="decks")

class Slide(Base):
    __tablename__ = "slides"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deck_id = Column(String(36), ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False); slide_type = Column(String(64), default="content")
    title = Column(String(512)); body_text = Column(Text); speaker_notes = Column(Text)
    chart_data = Column(JSON); table_data = Column(JSON); layout_config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    deck = relationship("Deck", back_populates="slides")
