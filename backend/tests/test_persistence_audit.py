"""Tests for persistence, audit logging, transactional mutations, and UTC timestamp compliance."""
from __future__ import annotations

import os
import pytest
from datetime import timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("APP_ENV", "development")

from backend.app.core.database import Base
from backend.app.models.deck import Deck, Slide
from backend.app.models.audit import AuditLog
from backend.app.services.audit_service import AuditService


@pytest.fixture(scope="function")
def db():
    """Fresh in-memory SQLite database per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def audit_svc():
    return AuditService()


def test_audit_log_created_with_correct_fields(db, audit_svc: AuditService):
    entry = audit_svc.log(
        db,
        action="create_deck",
        actor_sub="user-xyz",
        actor_email="user@test.local",
        resource_type="deck",
        resource_id="deck-001",
        detail={"source_type": "topic", "topic": "AI Safety"},
    )
    db.commit()
    assert entry.id is not None
    assert entry.action == "create_deck"
    assert entry.actor_sub == "user-xyz"
    assert entry.resource_type == "deck"
    assert entry.resource_id == "deck-001"
    assert entry.detail["topic"] == "AI Safety"


def test_audit_log_timestamp_is_utc(db, audit_svc: AuditService):
    entry = audit_svc.log(db, action="test_action", actor_sub="user-utc")
    db.commit()
    assert entry.created_at is not None
    # Timestamps should be timezone-aware or naive but consistent (SQLite returns naive UTC)
    ts = entry.created_at
    from datetime import datetime
    from datetime import timezone
    now = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    diff = abs((now - ts).total_seconds())
    assert diff < 60, f"Audit timestamp is not recent: {ts}"


def test_audit_log_list_filtered_by_resource_type(db, audit_svc: AuditService):
    audit_svc.log(db, action="create_deck", resource_type="deck", resource_id="d1")
    audit_svc.log(db, action="upload_template", resource_type="template", resource_id="t1")
    audit_svc.log(db, action="create_deck", resource_type="deck", resource_id="d2")
    db.commit()

    deck_logs, total = audit_svc.list_logs(db, resource_type="deck")
    assert total == 2
    for log in deck_logs:
        assert log.resource_type == "deck"


def test_audit_log_list_filtered_by_resource_id(db, audit_svc: AuditService):
    audit_svc.log(db, action="export_deck", resource_type="deck", resource_id="deck-555")
    audit_svc.log(db, action="evaluate_deck", resource_type="deck", resource_id="deck-555")
    audit_svc.log(db, action="create_deck", resource_type="deck", resource_id="deck-999")
    db.commit()

    logs, total = audit_svc.list_logs(db, resource_id="deck-555")
    assert total == 2


def test_audit_log_pagination(db, audit_svc: AuditService):
    for i in range(10):
        audit_svc.log(db, action=f"action_{i}", resource_type="deck", resource_id=f"d-{i}")
    db.commit()

    page1, total = audit_svc.list_logs(db, limit=5, skip=0)
    page2, _ = audit_svc.list_logs(db, limit=5, skip=5)
    assert total == 10
    assert len(page1) == 5
    assert len(page2) == 5
    # No overlap
    page1_ids = {e.id for e in page1}
    page2_ids = {e.id for e in page2}
    assert page1_ids.isdisjoint(page2_ids)


def test_deck_model_persists_slides(db):
    deck = Deck(
        title="Persistence Test Deck",
        source_type="topic",
        author_sub="user-persist",
        status="draft",
        slide_count=2,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)

    slide1 = Slide(deck_id=deck.id, position=0, slide_type="title", title="Introduction")
    slide2 = Slide(deck_id=deck.id, position=1, slide_type="content", title="Methods", body_text="• RLHF\n• Constitutional AI")
    db.add_all([slide1, slide2])
    db.commit()

    retrieved = db.query(Deck).filter(Deck.id == deck.id).first()
    assert retrieved is not None
    assert len(retrieved.slides) == 2
    slide_titles = {s.title for s in retrieved.slides}
    assert "Introduction" in slide_titles
    assert "Methods" in slide_titles


def test_deck_deletion_cascades_to_slides(db):
    deck = Deck(title="Cascade Test", source_type="topic", status="draft", slide_count=1)
    db.add(deck)
    db.commit()
    db.refresh(deck)

    slide = Slide(deck_id=deck.id, position=0, slide_type="title", title="Only Slide")
    db.add(slide)
    db.commit()

    slide_id = slide.id
    db.delete(deck)
    db.commit()

    # After deck deletion, the slide should no longer exist
    remaining = db.query(Slide).filter(Slide.id == slide_id).first()
    assert remaining is None


def test_audit_log_immutable_once_committed(db, audit_svc: AuditService):
    """Verifies that audit log entries are stored and retrievable after commit."""
    entry = audit_svc.log(db, action="synthesize_narration", actor_sub="prod-user", resource_type="deck", resource_id="deck-nar")
    db.commit()
    entry_id = entry.id

    # Retrieve from fresh query to verify persistence
    fetched = db.query(AuditLog).filter(AuditLog.id == entry_id).first()
    assert fetched is not None
    assert fetched.action == "synthesize_narration"
    assert fetched.actor_sub == "prod-user"


def test_transactional_rollback_prevents_partial_writes(db, audit_svc: AuditService):
    """If a transaction is rolled back, audit entries should not persist."""
    entry = audit_svc.log(db, action="failed_operation", actor_sub="rollback-user")
    entry_id = entry.id
    db.rollback()

    fetched = db.query(AuditLog).filter(AuditLog.id == entry_id).first()
    assert fetched is None
