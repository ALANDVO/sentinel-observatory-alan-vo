import logging, os
from enum import Enum
from typing import Any
import httpx, jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
logger = logging.getLogger(__name__)
_bearer_scheme = HTTPBearer(auto_error=False)
_jwks_cache: dict[str, Any] | None = None
def _get_jwks() -> dict[str, Any]:
    global _jwks_cache
    if _jwks_cache is not None: return _jwks_cache
    url = os.getenv("OIDC_JWKS_URL", "http://127.0.0.1:8080/realms/sentinel/protocol/openid-connect/certs")
    try:
        resp = httpx.get(url, timeout=5.0); resp.raise_for_status(); _jwks_cache = resp.json()
    except Exception as exc:
        logger.warning("Failed to fetch JWKS: %s", exc); _jwks_cache = {"keys": []}
    return _jwks_cache
def _reset_jwks_cache() -> None:
    global _jwks_cache
    _jwks_cache = None
class Role(str, Enum):
    VIEWER, OPERATOR, ADMIN = "viewer", "operator", "admin"
ROLE_HIERARCHY: dict[str, int] = {Role.VIEWER: 0, Role.OPERATOR: 1, Role.ADMIN: 2}
DEMO_TOKEN_SUBJECT = "demo-user"
DEMO_TOKEN_ROLES = [Role.OPERATOR, Role.ADMIN]
def _make_demo_user() -> dict[str, Any]:
    return {"sub": DEMO_TOKEN_SUBJECT, "email": "demo@sentinel.local", "preferred_username": "demo-operator", "realm_access": {"roles": [r.value for r in DEMO_TOKEN_ROLES]}, "demo": True}
def _verify_token(token: str) -> dict[str, Any]:
    issuer, audience = os.getenv("OIDC_ISSUER_URL", "http://127.0.0.1:8080/realms/sentinel"), os.getenv("OIDC_AUDIENCE", "sentinel-client")
    jwks = jwt.PyJWKSet.from_dict(_get_jwks())
    kid = jwt.get_unverified_header(token).get("kid")
    key = next((k for k in jwks.keys if k.key_id == kid), jwks.keys[0] if jwks.keys else None)
    if not key: raise jwt.InvalidTokenError("No matching signing key in JWKS")
    return jwt.decode(token, key, algorithms=["RS256", "ES256"], issuer=issuer, audience=audience, options={"verify_exp": True})
def _is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
def get_current_user(credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme)) -> dict[str, Any]:
    if credentials is None:
        if _is_demo_mode(): return _make_demo_user()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Authorization header", headers={"WWW-Authenticate": "Bearer"})
    token = credentials.credentials
    if _is_demo_mode() and token == "demo": return _make_demo_user()
    try: return _verify_token(token)
    except jwt.ExpiredSignatureError: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired", headers={"WWW-Authenticate": "Bearer"})
    except Exception as exc:
        logger.warning("Token verification failed: %s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or unverifiable token", headers={"WWW-Authenticate": "Bearer"})
def _get_user_roles(payload: dict[str, Any]) -> list[str]:
    return payload.get("realm_access", {}).get("roles", [])
def require_role(minimum_role: Role):
    def _dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        ml = ROLE_HIERARCHY.get(minimum_role.value, 0)
        if any(ROLE_HIERARCHY.get(r, -1) >= ml for r in _get_user_roles(user)): return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {minimum_role.value}")
    return _dependency
