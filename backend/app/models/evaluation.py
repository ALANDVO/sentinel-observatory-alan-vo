"""SQLAlchemy ORM models for Evaluation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


def _now_utc():
    return datetime.now(timezone.utc)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deck_id = Column(String(36), ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    evaluator_sub = Column(String(256), nullable=True)
    eval_type = Column(String(64), default="full")  # full, cognitive_load, data_fidelity, attribution, prompt_audit

    # Cognitive load scores (0.0 – 1.0, higher = better)
    information_density_score = Column(Float, nullable=True)
    bullet_brevity_score = Column(Float, nullable=True)
    hierarchy_balance_score = Column(Float, nullable=True)
    readability_grade = Column(Float, nullable=True)  # Flesch-Kincaid grade
    mece_alignment_score = Column(Float, nullable=True)
    overall_cognitive_score = Column(Float, nullable=True)

    # Data fidelity scores
    numeric_claims_found = Column(Float, nullable=True)
    claims_verified = Column(Float, nullable=True)
    data_fidelity_precision = Column(Float, nullable=True)
    data_fidelity_recall = Column(Float, nullable=True)

    # Attribution guard
    attribution_pass = Column(String(16), nullable=True)  # pass, fail, skip
    attribution_diagnostics = Column(JSON, nullable=True)

    # Prompt audit
    prompt_audit_pass = Column(String(16), nullable=True)
    prompt_audit_findings = Column(JSON, nullable=True)

    # LLM advisory analysis (opt-in)
    llm_advisory = Column(Text, nullable=True)
    llm_provider_used = Column(String(64), nullable=True)

    raw_result = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now_utc)

    deck = relationship("Deck", back_populates="evaluations")
