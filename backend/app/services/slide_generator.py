"""Slide generation service: orchestrates NLP engine to create deck + slides in DB."""
from __future__ import annotations
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.app.models.deck import Deck, Slide
from backend.app.services.nlp_engine import NLPEngine
class SlideGeneratorService:
    def __init__(self): self._nlp = NLPEngine()
    def generate_from_topic(self, db: Session, topic: str, author_sub: str | None = None, template_id: str | None = None, slide_count: int = 8) -> Deck:
        return self._persist_blueprint(db, self._nlp.decompose_topic(topic, slide_count), "topic", topic, author_sub, template_id)
    def generate_from_document(self, db: Session, text_content: str, author_sub: str | None = None, template_id: str | None = None, slide_count: int = 10) -> Deck:
        return self._persist_blueprint(db, self._nlp.decompose_document(text_content, slide_count), "document", text_content, author_sub, template_id)
    def _persist_blueprint(self, db: Session, blueprint, source_type: str, source_text: str, author_sub: str | None, template_id: str | None) -> Deck:
        deck = Deck(title=blueprint.title[:512], topic=blueprint.topic[:2000] if blueprint.topic else None, source_text=source_text[:10000], source_type=source_type, author_sub=author_sub, status="draft", template_id=template_id, slide_count=len(blueprint.slides), meta={"keywords": blueprint.keywords, "reading_level": blueprint.reading_level})
        db.add(deck); db.flush()
        for sb in blueprint.slides:
            body = "\n".join(f"• {b}" for b in sb.bullets) if sb.bullets else ""
            db.add(Slide(deck_id=deck.id, position=sb.position, slide_type=sb.slide_type, title=sb.title[:512] if sb.title else "", body_text=body[:4000], speaker_notes=sb.speaker_notes[:2000] if sb.speaker_notes else "", chart_data=sb.chart_data, table_data=sb.table_data, layout_config=sb.layout_config))
        db.commit(); db.refresh(deck); return deck
    def add_slide(self, db: Session, deck_id: str, slide_type: str, title: str, body_text: str = "", speaker_notes: str = "", chart_data: dict | None = None, table_data: dict | None = None) -> Slide:
        pos = db.query(Slide).filter(Slide.deck_id == deck_id).count()
        slide = Slide(deck_id=deck_id, position=pos, slide_type=slide_type, title=title[:512], body_text=body_text[:4000], speaker_notes=speaker_notes[:2000], chart_data=chart_data, table_data=table_data)
        db.add(slide); db.execute(text("UPDATE decks SET slide_count = slide_count + 1 WHERE id = :id"), {"id": deck_id}); db.commit(); db.refresh(slide); return slide
    def update_slide(self, db: Session, slide_id: str, updates: dict[str, Any]) -> Slide | None:
        if not (slide := db.query(Slide).filter(Slide.id == slide_id).first()): return None
        for k, v in updates.items():
            if hasattr(slide, k): setattr(slide, k, v)
        db.commit(); db.refresh(slide); return slide
