"""Tests for evaluation API and engine."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _create_deck(client: TestClient, topic: str = "AI evaluation test") -> str:
    resp = client.post("/api/decks/generate/topic", json={"topic": topic, "slide_count": 5})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_run_full_evaluation(client: TestClient):
    deck_id = _create_deck(client)
    resp = client.post(
        f"/api/evaluations/decks/{deck_id}/run",
        json={"eval_type": "full", "request_llm_advisory": False},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["deck_id"] == deck_id
    assert data["overall_cognitive_score"] is not None
    assert 0.0 <= data["overall_cognitive_score"] <= 1.0
    assert data["attribution_pass"] in ("pass", "fail", "skip", None)
    assert data["prompt_audit_pass"] in ("pass", "fail", None)


def test_run_cognitive_load_evaluation(client: TestClient):
    deck_id = _create_deck(client, "Cognitive load test deck")
    resp = client.post(
        f"/api/evaluations/decks/{deck_id}/run",
        json={"eval_type": "cognitive_load"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["information_density_score"] is not None
    assert data["bullet_brevity_score"] is not None
    assert data["mece_alignment_score"] is not None


def test_run_data_fidelity_evaluation_no_source(client: TestClient):
    deck_id = _create_deck(client, "Data fidelity test")
    resp = client.post(
        f"/api/evaluations/decks/{deck_id}/run",
        json={"eval_type": "data_fidelity", "source_data": []},
    )
    assert resp.status_code == 201
    data = resp.json()
    # With no source data numeric claims have 0.0 fidelity (or 1.0 if no claims)
    assert data["data_fidelity_precision"] is not None


def test_run_data_fidelity_with_source(client: TestClient):
    deck_id = _create_deck(client, "Revenue grew by 25% to $500 million")
    resp = client.post(
        f"/api/evaluations/decks/{deck_id}/run",
        json={
            "eval_type": "data_fidelity",
            "source_data": [{"revenue": 500.0, "growth": 25.0}],
        },
    )
    assert resp.status_code == 201


def test_run_attribution_evaluation(client: TestClient):
    deck_id = _create_deck(client)
    resp = client.post(
        f"/api/evaluations/decks/{deck_id}/run",
        json={"eval_type": "attribution"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["attribution_pass"] == "pass"
    assert isinstance(data["attribution_diagnostics"], list)


def test_run_prompt_audit_evaluation(client: TestClient):
    deck_id = _create_deck(client)
    resp = client.post(
        f"/api/evaluations/decks/{deck_id}/run",
        json={"eval_type": "prompt_audit", "model": "gpt-4o-mini"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["prompt_audit_pass"] in ("pass", "fail")


def test_list_evaluations(client: TestClient):
    deck_id = _create_deck(client)
    client.post(f"/api/evaluations/decks/{deck_id}/run", json={"eval_type": "cognitive_load"})
    resp = client.get(f"/api/evaluations?deck_id={deck_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_get_single_evaluation(client: TestClient):
    deck_id = _create_deck(client)
    run_resp = client.post(f"/api/evaluations/decks/{deck_id}/run", json={"eval_type": "cognitive_load"})
    eval_id = run_resp.json()["id"]
    resp = client.get(f"/api/evaluations/{eval_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == eval_id


def test_locale_audit_passes_clean_dict(client: TestClient):
    resp = client.post("/api/evaluations/locale-audit", json={
        "dictionaries": {
            "en": {"title": "Presentation", "submit": "Submit"},
            "fr": {"title": "Présentation", "submit": "Soumettre"},
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True


def test_locale_audit_detects_missing_keys(client: TestClient):
    resp = client.post("/api/evaluations/locale-audit", json={
        "dictionaries": {
            "en": {"title": "Presentation", "submit": "Submit", "cancel": "Cancel"},
            "fr": {"title": "Présentation"},
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is False
    rules = [f["rule"] for f in data["findings"]]
    assert "locale_key_parity_missing" in rules


def test_compare_evaluations(client: TestClient):
    deck_id_1 = _create_deck(client, "First deck for comparison")
    deck_id_2 = _create_deck(client, "Second deck for comparison")
    # Create evaluations for both decks
    r1 = client.post(f"/api/evaluations/decks/{deck_id_1}/run", json={"eval_type": "full"})
    assert r1.status_code == 201
    eid1 = r1.json()["id"]
    r2 = client.post(f"/api/evaluations/decks/{deck_id_2}/run", json={"eval_type": "full"})
    assert r2.status_code == 201
    eid2 = r2.json()["id"]
    # Compare them
    resp = client.get(f"/api/evaluations/compare?ids={eid1},{eid2}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "evaluations" in data
    assert "comparison" in data
    assert len(data["evaluations"]) == 2
    assert set(e["id"] for e in data["evaluations"]) == {eid1, eid2}
    # Check comparison metrics exist
    assert "overall_cognitive_score" in data["comparison"]
    assert "best" in data["comparison"]["overall_cognitive_score"]
    assert "worst" in data["comparison"]["overall_cognitive_score"]


def test_compare_evaluations_invalid_count(client: TestClient):
    deck_id = _create_deck(client)
    r = client.post(f"/api/evaluations/decks/{deck_id}/run", json={"eval_type": "full"})
    eid = r.json()["id"]
    # Single ID should fail
    resp = client.get(f"/api/evaluations/compare?ids={eid}")
    assert resp.status_code == 400
    # Too many IDs should fail
    many_ids = ",".join([eid] * 11)
    resp = client.get(f"/api/evaluations/compare?ids={many_ids}")
    assert resp.status_code == 400


def test_compare_evaluations_nonexistent(client: TestClient):
    deck_id = _create_deck(client)
    r = client.post(f"/api/evaluations/decks/{deck_id}/run", json={"eval_type": "full"})
    eid = r.json()["id"]
    # Mix of valid and invalid
    resp = client.get(f"/api/evaluations/compare?ids={eid},nonexistent-id-123")
    assert resp.status_code == 404


def test_export_comparison_markdown(client: TestClient):
    deck_id_1 = _create_deck(client, "First deck for markdown export")
    deck_id_2 = _create_deck(client, "Second deck for markdown export")
    r1 = client.post(f"/api/evaluations/decks/{deck_id_1}/run", json={"eval_type": "full"})
    eid1 = r1.json()["id"]
    r2 = client.post(f"/api/evaluations/decks/{deck_id_2}/run", json={"eval_type": "full"})
    eid2 = r2.json()["id"]
    resp = client.get(f"/api/evaluations/compare/export/markdown?ids={eid1},{eid2}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/markdown; charset=utf-8"
    content = resp.text
    assert "# Evaluation Comparison Report" in content
    assert "Summary Table" in content
    assert "Per-Evaluation Details" in content
    assert eid1[:8] in content
    assert eid2[:8] in content
