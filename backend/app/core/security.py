"""Security utilities: OIDC token verification and RBAC for Sentinel Observatory."""
from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)
_jwks_cache: dict[str, Any] | None = None


def _get_jwks() -> dict[str, Any]:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    jwks_url = os.getenv("OIDC_JWKS_URL", "http://127.0.0.1:8080/realms/sentinel/protocol/openid-connect/certs")
    try:
        resp = httpx.get(jwks_url, timeout=5.0)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    except Exception as exc:
        logger.warning("Failed to fetch JWKS: %s", exc)
        _jwks_cache = {"keys": []}
    return _jwks_cache


def _reset_jwks_cache() -> None:
    global _jwks_cache
    _jwks_cache = None


class Role(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


ROLE_HIERARCHY: dict[str, int] = {Role.VIEWER: 0, Role.OPERATOR: 1, Role.ADMIN: 2}

DEMO_TOKEN_SUBJECT = "demo-user"
DEMO_TOKEN_ROLES = [Role.OPERATOR, Role.ADMIN]


def _make_demo_user() -> dict[str, Any]:
    return {
        "sub": DEMO_TOKEN_SUBJECT,
        "email": "demo@sentinel.local",
        "preferred_username": "demo-operator",
        "realm_access": {"roles": [r.value for r in DEMO_TOKEN_ROLES]},
        "demo": True,
    }


def _verify_token(token: str) -> dict[str, Any]:
    """Verify a JWT bearer token against the Keycloak JWKS."""
    issuer = os.getenv("OIDC_ISSUER_URL", "http://127.0.0.1:8080/realms/sentinel")
    audience = os.getenv("OIDC_AUDIENCE", "sentinel-client")

    jwks_data = _get_jwks()
    jwks = jwt.PyJWKSet.from_dict(jwks_data)

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    signing_key = None
    for key in jwks.keys:
        if key.key_id == kid:
            signing_key = key
            break

    if signing_key is None and jwks.keys:
        signing_key = jwks.keys[0]

    if signing_key is None:
        raise jwt.InvalidTokenError("No matching signing key in JWKS")

    payload = jwt.decode(
        token, signing_key, algorithms=["RS256", "ES256"],
        issuer=issuer, audience=audience, options={"verify_exp": True},
    )
    return payload


def _is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme)) -> dict[str, Any]:
    """Extract and verify the calling user from the Authorization header."""
    if credentials is None:
        if _is_demo_mode():
            return _make_demo_user()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header", headers={"WWW-Authenticate": "Bearer"})

    token = credentials.credentials
    if _is_demo_mode() and token == "demo":
        return _make_demo_user()

    try:
        return _verify_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired", headers={"WWW-Authenticate": "Bearer"})
    except Exception as exc:
        logger.warning("Token verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or unverifiable token", headers={"WWW-Authenticate": "Bearer"})


def _get_user_roles(payload: dict[str, Any]) -> list[str]:
    return payload.get("realm_access", {}).get("roles", [])


def require_role(minimum_role: Role):
    """Return a FastAPI dependency that enforces a minimum role level."""

    def _dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        user_roles = _get_user_roles(user)
        min_level = ROLE_HIERARCHY.get(minimum_role.value, 0)
        for role in user_roles:
            if ROLE_HIERARCHY.get(role, -1) >= min_level:
                return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires role: {minimum_role.value}")

    return _dependency