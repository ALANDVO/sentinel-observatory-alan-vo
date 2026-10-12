"""Tests for the deck generation API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_health(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_generate_topic_deck(client: TestClient):
    resp = client.post("/api/decks/generate/topic", json={"topic": "Machine Learning in Healthcare", "slide_count": 5})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] != ""
    assert data["source_type"] == "topic"
    assert data["slide_count"] >= 3
    assert len(data["slides"]) >= 3
    assert data["slides"][0]["slide_type"] == "title"


def test_generate_document_deck(client: TestClient):
    doc = """
    # AI Safety Research Overview

    ## Introduction
    AI safety is critical for ensuring systems behave as intended.
    Key concerns include alignment, robustness, and interpretability.

    ## Technical Approaches
    - Reinforcement learning from human feedback (RLHF)
    - Constitutional AI methods
    - Formal verification techniques

    ## Current Limitations
    Current models lack guarantees of safe behavior in all scenarios.
    Interpretability tools remain limited for large models.
    """
    resp = client.post("/api/decks/generate/document", json={"text": doc, "slide_count": 6})
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_type"] == "document"
    assert data["slide_count"] >= 3


def test_get_deck(client: TestClient):
    # First create a deck
    create_resp = client.post("/api/decks/generate/topic", json={"topic": "Neural networks basics"})
    assert create_resp.status_code == 201
    deck_id = create_resp.json()["id"]

    # Then retrieve it
    resp = client.get(f"/api/decks/{deck_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == deck_id


def test_list_decks(client: TestClient):
    # Create a deck first
    client.post("/api/decks/generate/topic", json={"topic": "Quantum computing overview"})
    resp = client.get("/api/decks?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 1


def test_get_nonexistent_deck(client: TestClient):
    resp = client.get("/api/decks/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_delete_deck(client: TestClient):
    create_resp = client.post("/api/decks/generate/topic", json={"topic": "Temporary deck"})
    deck_id = create_resp.json()["id"]
    delete_resp = client.delete(f"/api/decks/{deck_id}")
    assert delete_resp.status_code == 204
    get_resp = client.get(f"/api/decks/{deck_id}")
    assert get_resp.status_code == 404


def test_add_slide_to_deck(client: TestClient):
    create_resp = client.post("/api/decks/generate/topic", json={"topic": "Slide management test"})
    deck_id = create_resp.json()["id"]
    resp = client.post(f"/api/decks/{deck_id}/slides", json={
        "slide_type": "content",
        "title": "Custom Slide",
        "body_text": "• Point one\n• Point two",
        "speaker_notes": "Elaborate on both points.",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Custom Slide"


def test_export_deck_pptx(client: TestClient):
    create_resp = client.post("/api/decks/generate/topic", json={"topic": "Export test deck"})
    deck_id = create_resp.json()["id"]
    resp = client.get(f"/api/decks/{deck_id}/export/pptx")
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats" in resp.headers["content-type"]
    assert len(resp.content) > 1000  # Valid PPTX has substantial size


def test_topic_too_short_rejected(client: TestClient):
    resp = client.post("/api/decks/generate/topic", json={"topic": "ab"})
    assert resp.status_code == 422


def test_list_decks_filter_by_source_type(client: TestClient):
    resp = client.get("/api/decks?source_type=topic")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["source_type"] == "topic"
