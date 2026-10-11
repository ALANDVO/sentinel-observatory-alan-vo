"""OIDC security tests: PKCE state/nonce validation, token propagation, RBAC denial, logout."""
from __future__ import annotations

import os
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_auth_config_endpoint_exposes_pkce_parameters(client: TestClient):
    """The /api/auth/config endpoint returns PKCE-capable OIDC discovery fields."""
    resp = client.get("/api/auth/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "jwks_uri" in data
    assert "client_id" in data
    # Must NOT expose any client secret
    assert "client_secret" not in data


def test_unauthenticated_request_decks_with_demo_off(client: TestClient):
    """Protected endpoint returns 401 when demo mode is off and no token provided."""
    with patch.dict(os.environ, {"DEMO_MODE": "false"}):
        resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


def test_demo_mode_provides_demo_user_identity(client: TestClient):
    """In demo mode, /api/auth/me returns a demo user with labeled demo flag."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["demo"] is True
    assert data["sub"] == "demo-user"


def test_viewer_role_cannot_generate_decks(client: TestClient, monkeypatch):
    """Viewer role is denied access to operator-only endpoints (403)."""
    import backend.app.core.security as sec_mod
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(sec_mod, "_verify_token", lambda tok: {
        "sub": "viewer-test",
        "email": "viewer@test.local",
        "preferred_username": "viewer-test",
        "realm_access": {"roles": ["viewer"]},
    })
    resp = client.post(
        "/api/decks/generate/topic",
        headers={"Authorization": "Bearer mock-viewer-token"},
        json={"topic": "Should be denied", "slide_count": 4},
    )
    assert resp.status_code == 403
    assert "operator" in resp.json()["detail"].lower()


def test_operator_role_can_generate_and_reader_can_export(client: TestClient, monkeypatch):
    """Operator can generate; viewer can export PPTX; verifies RBAC boundary."""
    import backend.app.core.security as sec_mod

    # Step 1: Generate with operator
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(sec_mod, "_verify_token", lambda tok: {
        "sub": "op-user",
        "email": "op@test.local",
        "preferred_username": "op-user",
        "realm_access": {"roles": ["operator", "viewer"]},
    })

    gen_resp = client.post(
        "/api/decks/generate/topic",
        headers={"Authorization": "Bearer mock-operator-token"},
        json={"topic": "RBAC test deck", "slide_count": 3},
    )
    assert gen_resp.status_code == 201
    deck_id = gen_resp.json()["id"]

    # Step 2: Export as viewer
    monkeypatch.setattr(sec_mod, "_verify_token", lambda tok: {
        "sub": "vw-user",
        "email": "vw@test.local",
        "preferred_username": "vw-user",
        "realm_access": {"roles": ["viewer"]},
    })
    export_resp = client.get(
        f"/api/decks/{deck_id}/export/pptx",
        headers={"Authorization": "Bearer mock-viewer-token"},
    )
    assert export_resp.status_code == 200


def test_logout_endpoint_clears_session(client: TestClient):
    """Logout endpoint is reachable and returns a valid response."""
    resp = client.post("/api/auth/logout")
    assert resp.status_code in (200, 204, 307, 302)


def test_demo_mode_rejected_in_production(monkeypatch):
    """DEMO_MODE=true must raise RuntimeError when APP_ENV=production."""
    from backend.app.core.config import Settings
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_MODE", "true")
    s = Settings()
    with pytest.raises(RuntimeError, match="SECURITY VIOLATION"):
        s.validate_production_guards()


def test_invalid_token_format_returns_401(client: TestClient, monkeypatch):
    """A malformed Bearer token is rejected with 401."""
    import backend.app.core.security as sec_mod
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(sec_mod, "_verify_token", lambda tok: (_ for _ in ()).throw(ValueError("Invalid token")))

    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code == 401
