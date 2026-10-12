"""Application configuration and environment settings for Sentinel Observatory."""
from __future__ import annotations
import os
from pathlib import Path
class Settings:
    def __init__(self):
        self.app_name = "sentinel-observatory-alan-vo"
        self.app_version = self._read_version()
        self.app_env = os.getenv("APP_ENV", "development")
        self.host = os.getenv("HOST", "127.0.0.1")
        self.port = int(os.getenv("PORT", "8000"))
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./data/sentinel.db")
        self.llm_provider = os.getenv("LLM_PROVIDER", "openai-compatible")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "")
        self.llm_request_timeout = float(os.getenv("LLM_TIMEOUT", "20.0"))
        self.oidc_issuer_url = os.getenv("OIDC_ISSUER_URL", "http://127.0.0.1:8080/realms/sentinel")
        self.oidc_client_id = os.getenv("OIDC_CLIENT_ID", "sentinel-client")
        self.oidc_audience = os.getenv("OIDC_AUDIENCE", "sentinel-client")
        self.oidc_jwks_url = os.getenv("OIDC_JWKS_URL", "http://127.0.0.1:8080/realms/sentinel/protocol/openid-connect/certs")
        raw = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
        self.cors_origins = [o.strip() for o in raw.split(",") if o.strip()]
    def _read_version(self) -> str:
        try: return (Path(__file__).parents[3] / "VERSION").read_text().strip()
        except Exception: return "1.0.0"
    def validate_production_guards(self) -> None:
        if self.app_env.lower() in ("production", "prod") and self.demo_mode:
            raise RuntimeError("SECURITY VIOLATION: DEMO_MODE=true is strictly prohibited in production environment.")
        if self.demo_mode and self.host not in {"127.0.0.1", "localhost", "0.0.0.0", "testserver"}:
            raise RuntimeError(f"SECURITY VIOLATION: DEMO_MODE must bind localhost only, got host={self.host}")
settings = Settings()
APP_TITLE, APP_DESCRIPTION, APP_VERSION = settings.app_name, "AI presentation generation and slide-intelligence observatory", settings.app_version
