"""Authentication, authorization, production guards, and HTTP boundary integration tests."""
from __future__ import annotations

import os
import time
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import Base, get_db
from backend.app.core.security import Role, _reset_jwks_cache
from backend.app.main import create_app


@pytest.fixture(scope="module")
def rsa_keypair():
    """Generate ephemeral RSA keypair for OIDC token signing in tests."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, pub_pem


def _generate_test_token(private_key, sub: str, roles: list[str], expired: bool = False, issuer: str = "http://127.0.0.1:8080/realms/sentinel", audience: str = "sentinel-client"):
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": f"{sub}@example.com",
        "preferred_username": sub,
        "iss": issuer,
        "aud": audience,
        "iat": now - 3600 if expired else now,
        "exp": now - 1800 if expired else now + 3600,
        "realm_access": {"roles": roles},
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key-id"})


def test_production_guard_refuses_demo_mode_in_production(monkeypatch):
    """Startup must strictly refuse DEMO_MODE=true in production environment."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_MODE", "true")
    s = Settings()
    with pytest.raises(RuntimeError, match="SECURITY VIOLATION.*prohibited in production"):
        s.validate_production_guards()


def test_production_guard_allows_production_without_demo(monkeypatch):
    """Production mode without demo mode passes validation."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_MODE", "false")
    s = Settings()
    s.validate_production_guards()  # should not raise


def test_unauthenticated_rejection_when_demo_disabled(client, monkeypatch):
    """When DEMO_MODE is false, accessing protected endpoints without token returns 401."""
    monkeypatch.setenv("DEMO_MODE", "false")
    # Calling /api/auth/me without header
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


def test_role_denial_when_insufficient_permissions(client, rsa_keypair, monkeypatch):
    """A user with only 'viewer' role must receive 403 when invoking an operator endpoint."""
    private_key, pub_pem = rsa_keypair
    monkeypatch.setenv("DEMO_MODE", "false")

    # Mock JWKS verification to return our public key
    import backend.app.core.security as sec_mod
    monkeypatch.setattr(sec_mod, "_get_jwks", lambda: {
        "keys": [{"kid": "test-key-id", "kty": "RSA", "alg": "RS256", "use": "sig", "n": "", "e": ""}]
    })
    # Mock jwt.decode or signing key
    token = _generate_test_token(private_key, sub="viewer-only", roles=["viewer"])
    monkeypatch.setattr(sec_mod, "_verify_token", lambda tok: {
        "sub": "viewer-only",
        "email": "viewer@example.com",
        "realm_access": {"roles": ["viewer"]},
    })

    # Viewer should be able to list decks
    resp_get = client.get("/api/decks", headers={"Authorization": f"Bearer {token}"})
    assert resp_get.status_code == 200

    # But viewer is forbidden from generating decks (requires OPERATOR)
    resp_post = client.post(
        "/api/decks/generate/topic",
        headers={"Authorization": f"Bearer {token}"},
        json={"topic": "Unauthorized Attempt", "slide_count": 4},
    )
    assert resp_post.status_code == 403
    assert "Requires role: operator" in resp_post.json()["detail"]


def test_oidc_config_endpoint(client):
    """OIDC config endpoint returns standard discovery endpoints for SPA PKCE."""
    resp = client.get("/api/auth/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "jwks_uri" in data
    assert data["client_id"] == "sentinel-client"


def test_complete_oidc_token_propagation(client, monkeypatch):
    """Assert token payload propagation into /api/auth/me for authenticated user."""
    monkeypatch.setenv("DEMO_MODE", "false")
    import backend.app.core.security as sec_mod
    monkeypatch.setattr(sec_mod, "_verify_token", lambda tok: {
        "sub": "analyst-123",
        "email": "analyst@sentinel.local",
        "preferred_username": "analyst",
        "realm_access": {"roles": ["operator", "viewer"]},
    })

    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-simulated-token"})
    assert resp.status_code == 200
    user_info = resp.json()
    assert user_info["sub"] == "analyst-123"
    assert "operator" in user_info["roles"]
    assert user_info["demo"] is False


def test_real_http_boundary_core_workflow(client):
    """End-to-end integration across real HTTP boundary: generate deck, read, evaluate, export."""
    # 1. Create deck from topic
    create_resp = client.post(
        "/api/decks/generate/topic",
        json={"topic": "Neural Architecture Search and Efficient Deep Learning", "slide_count": 4},
    )
    assert create_resp.status_code == 201
    deck_data = create_resp.json()
    deck_id = deck_data["id"]
    assert deck_data["title"] == "Neural Architecture Search and Efficient Deep Learning"
    assert deck_data["slide_count"] == 4
    assert len(deck_data["slides"]) == 4

    # 2. Read deck detail
    get_resp = client.get(f"/api/decks/{deck_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == deck_id

    # 3. Run cognitive load evaluation
    eval_resp = client.post(
        f"/api/evaluations/decks/{deck_id}/run",
        json={"eval_type": "cognitive_load"},
    )
    assert eval_resp.status_code == 201
    eval_data = eval_resp.json()
    assert eval_data["deck_id"] == deck_id
    assert eval_data["overall_cognitive_score"] is not None
    assert 0.0 <= eval_data["overall_cognitive_score"] <= 1.0

    # 4. Export deck to native PPTX
    export_resp = client.get(f"/api/decks/{deck_id}/export/pptx")
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    # PPTX files start with PK zip header
    assert export_resp.content.startswith(b"PK")


def test_health_endpoint_returns_dynamic_version(client):
    """Health check endpoint must expose current product version metadata."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "sentinel-observatory"
    assert "version" in data
    assert len(data["version"]) >= 5
