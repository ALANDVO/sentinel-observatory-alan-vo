import uuid
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base, now_utc
class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deck_id = Column(String(36), ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    evaluator_sub = Column(String(256)); eval_type = Column(String(64), default="full")
    information_density_score = Column(Float); bullet_brevity_score = Column(Float)
    hierarchy_balance_score = Column(Float); readability_grade = Column(Float)
    mece_alignment_score = Column(Float); overall_cognitive_score = Column(Float)
    numeric_claims_found = Column(Float); claims_verified = Column(Float)
    data_fidelity_precision = Column(Float); data_fidelity_recall = Column(Float)
    attribution_pass = Column(String(16)); prompt_audit_pass = Column(String(16))
    attribution_diagnostics = Column(JSON); prompt_audit_findings = Column(JSON)
    llm_advisory = Column(Text); llm_provider_used = Column(String(64))
    raw_result = Column(JSON, default=dict); created_at = Column(DateTime(timezone=True), default=now_utc)
    deck = relationship("Deck", back_populates="evaluations")
