"""Tests for cross-deck search and content indexing service (unified)."""
from __future__ import annotations
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.app.services import SearchService
from backend.app.main import create_app
from backend.app.core.database import SessionLocal, init_db
from backend.app.models.deck import Deck, Slide
from backend.app.models.evaluation import Evaluation


@pytest.fixture(scope="module")
def app():
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="function")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def search_service():
    return SearchService()


def _seed_data(db: Session) -> tuple[Deck, Deck]:
    deck1 = Deck(
        title="AI Safety Evaluation Benchmarks",
        topic="Evaluating AI safety across multiple dimensions including cognitive load analysis",
        source_text="Comprehensive evaluation of AI safety including robustness, alignment, interpretability metrics, and cognitive load assessment.",
        source_type="topic",
        author_sub="user-1",
        status="draft",
        slide_count=3,
    )
    db.add(deck1)
    db.flush()

    slides1 = [
        Slide(deck_id=deck1.id, position=0, slide_type="title", title="AI Safety Overview", body_text="Introduction to AI safety challenges and evaluation frameworks including cognitive load.", speaker_notes="Welcome to the presentation on AI safety evaluation."),
        Slide(deck_id=deck1.id, position=1, slide_type="content", title="Robustness Metrics", body_text="Adversarial robustness • Distribution shift • Out-of-distribution detection", speaker_notes="Key robustness indicators for production systems."),
        Slide(deck_id=deck1.id, position=2, slide_type="kpi", title="Alignment Scores", body_text="• Helpfulness: 0.87\n• Honesty: 0.92\n• Harmlessness: 0.95", speaker_notes="HHH alignment scores from human evaluation."),
    ]
    for s in slides1:
        db.add(s)

    deck2 = Deck(
        title="Distributed ML Training Systems",
        topic="Scaling machine learning training across GPU clusters",
        source_text="Technical deep dive into distributed training architectures, communication patterns, and optimization strategies.",
        source_type="document",
        author_sub="user-2",
        status="published",
        slide_count=3,
    )
    db.add(deck2)
    db.flush()

    slides2 = [
        Slide(deck_id=deck2.id, position=0, slide_type="title", title="Distributed Training", body_text="Overview of data parallelism and model parallelism approaches.", speaker_notes="Introduction to scaling ML training."),
        Slide(deck_id=deck2.id, position=1, slide_type="content", title="Communication Patterns", body_text="All-reduce • Parameter server • Ring all-reduce • Gradient compression", speaker_notes="Comparison of gradient synchronization methods."),
        Slide(deck_id=deck2.id, position=2, slide_type="chart", title="Scaling Efficiency", body_text="", speaker_notes="Chart showing linear scaling up to 512 GPUs.", chart_data={"categories": ["64", "128", "256", "512"], "series": [{"name": "Efficiency", "values": [0.98, 0.95, 0.91, 0.87]}]}),
    ]
    for s in slides2:
        db.add(s)

    eval1 = Evaluation(
        deck_id=deck1.id,
        eval_type="cognitive",
        information_density_score=0.75,
        bullet_brevity_score=0.82,
        hierarchy_balance_score=0.78,
        readability_grade=10.5,
        mece_alignment_score=0.85,
        overall_cognitive_score=0.81,
        numeric_claims_found=3,
        claims_verified=3,
        data_fidelity_precision=1.0,
        data_fidelity_recall=0.9,
        llm_advisory="Deck shows good cognitive load balance with clear hierarchy.",
    )
    db.add(eval1)

    eval2 = Evaluation(
        deck_id=deck2.id,
        eval_type="fidelity",
        information_density_score=0.65,
        bullet_brevity_score=0.70,
        hierarchy_balance_score=0.72,
        readability_grade=12.3,
        mece_alignment_score=0.80,
        overall_cognitive_score=0.72,
        numeric_claims_found=5,
        claims_verified=4,
        data_fidelity_precision=0.8,
        data_fidelity_recall=0.85,
        llm_advisory="High technical density; consider simplifying for broader audience.",
    )
    db.add(eval2)

    db.flush()
    db.refresh(deck1)
    db.refresh(deck2)
    return deck1, deck2


# ── Integration: SearchService.search_all ──────────────────────────────────────

def test_search_all_returns_all_types(db_session: Session, search_service: SearchService):
    _seed_data(db_session)
    response = search_service.search_all(db_session, "cognitive", limit=20)
    assert response.total >= 3
    types = {r.result_type for r in response.results}
    assert "deck" in types
    assert "slide" in types
    assert "evaluation" in types


def test_search_all_facets_aggregated(db_session: Session, search_service: SearchService):
    _seed_data(db_session)
    response = search_service.search_all(db_session, "cognitive", limit=20)
    assert "deck" in response.facets["result_type"]
    assert "slide" in response.facets["result_type"]
    assert "evaluation" in response.facets["result_type"]
    assert "topic" in response.facets["source_type"]


def test_search_all_pagination(db_session: Session, search_service: SearchService):
    _seed_data(db_session)
    page1 = search_service.search_all(db_session, "AI", limit=2, offset=0)
    page2 = search_service.search_all(db_session, "AI", limit=2, offset=2)
    assert len(page1.results) == 2
    if len(page2.results) > 0:
        assert page1.results[0].id != page2.results[0].id


def test_get_index_stats(db_session: Session, search_service: SearchService):
    _seed_data(db_session)
    stats = search_service.get_index_stats(db_session)
    assert stats["decks"] >= 2
    assert stats["slides"] >= 6
    assert stats["evaluations"] >= 2
    assert stats["audit_logs"] >= 0


def test_search_all_no_results(db_session: Session, search_service: SearchService):
    _seed_data(db_session)
    response = search_service.search_all(db_session, "nonexistentquery123", limit=20)
    assert response.total == 0
    assert len(response.results) == 0


def test_search_results_sorted_by_relevance(db_session: Session, search_service: SearchService):
    _seed_data(db_session)
    response = search_service.search_all(db_session, "Benchmarks", limit=10)
    assert len(response.results) >= 1
    assert response.results[0].score >= response.results[-1].score


def test_case_insensitive_search(db_session: Session, search_service: SearchService):
    _seed_data(db_session)
    response1 = search_service.search_all(db_session, "ai safety", limit=10)
    response2 = search_service.search_all(db_session, "AI SAFETY", limit=10)
    assert len(response1.results) == len(response2.results)


# ── API Endpoint Tests ─────────────────────────────────────────────────────────

def test_unified_search_endpoint(client: TestClient):
    resp = client.get("/api/search?q=AI&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "query" in data
    assert "total" in data
    assert "results" in data
    assert "facets" in data


def test_unified_search_endpoint_with_filters(client: TestClient):
    resp = client.get("/api/search?q=training&source_type=document&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "training"


def test_search_empty_query_rejected(client: TestClient):
    resp = client.get("/api/search?q=a")
    assert resp.status_code == 422