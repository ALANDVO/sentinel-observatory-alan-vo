"""Auth endpoint: OIDC discovery and PKCE flow metadata.

The SPA implements the full PKCE flow client-side; this endpoint
provides configuration and validates tokens for testing purposes.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class OIDCConfig(BaseModel):
    issuer: str; client_id: str; authorization_endpoint: str; token_endpoint: str; jwks_uri: str; end_session_endpoint: str

@router.get("/config", response_model=OIDCConfig)
def get_oidc_config() -> OIDCConfig:
    issuer = os.getenv("OIDC_ISSUER_URL", "http://127.0.0.1:8080/realms/sentinel")
    client_id = os.getenv("OIDC_CLIENT_ID", "sentinel-client")
    return OIDCConfig(issuer=issuer, client_id=client_id, authorization_endpoint=f"{issuer}/protocol/openid-connect/auth", token_endpoint=f"{issuer}/protocol/openid-connect/token", jwks_uri=f"{issuer}/protocol/openid-connect/certs", end_session_endpoint=f"{issuer}/protocol/openid-connect/logout")

class UserInfo(BaseModel):
    sub: str; email: str | None = None; preferred_username: str | None = None; roles: list[str] = []; demo: bool = False


@router.get("/me", response_model=UserInfo)
def get_me(user: dict = Depends(get_current_user)) -> UserInfo:
    """Return the current authenticated user's profile."""
    return UserInfo(
        sub=user.get("sub", "unknown"),
        email=user.get("email"),
        preferred_username=user.get("preferred_username"),
        roles=user.get("realm_access", {}).get("roles", []),
        demo=user.get("demo", False),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    """Explicit logout endpoint.

    For SPA PKCE clients, access tokens are held in memory only.
    The client must discard the in-memory token on this response.
    For a full OIDC session termination, redirect the user to end_session_endpoint
    from the /config response.
    """
    return None
