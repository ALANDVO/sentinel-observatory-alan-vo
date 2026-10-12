"""Auth endpoint: OIDC discovery and PKCE flow metadata."""
from __future__ import annotations
import os
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from backend.app.core.security import get_current_user
router = APIRouter(prefix="/auth", tags=["auth"])
class OIDCConfig(BaseModel):
    issuer: str; client_id: str; authorization_endpoint: str; token_endpoint: str; jwks_uri: str; end_session_endpoint: str
@router.get("/config", response_model=OIDCConfig)
def get_oidc_config() -> OIDCConfig:
    iss = os.getenv("OIDC_ISSUER_URL", "http://127.0.0.1:8080/realms/sentinel")
    cid = os.getenv("OIDC_CLIENT_ID", "sentinel-client")
    return OIDCConfig(issuer=iss, client_id=cid, authorization_endpoint=f"{iss}/protocol/openid-connect/auth", token_endpoint=f"{iss}/protocol/openid-connect/token", jwks_uri=f"{iss}/protocol/openid-connect/certs", end_session_endpoint=f"{iss}/protocol/openid-connect/logout")
class UserInfo(BaseModel):
    sub: str; email: str | None = None; preferred_username: str | None = None; roles: list[str] = []; demo: bool = False
@router.get("/me", response_model=UserInfo)
def get_me(user: dict = Depends(get_current_user)) -> UserInfo:
    return UserInfo(sub=user.get("sub", "unknown"), email=user.get("email"), preferred_username=user.get("preferred_username"), roles=user.get("realm_access", {}).get("roles", []), demo=user.get("demo", False))
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    return None
