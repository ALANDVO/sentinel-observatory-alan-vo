"""Application configuration and environment settings for Sentinel Observatory."""
from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """Runtime configuration settings loaded from environment variables."""

    def __init__(self):
        self.app_name: str = "sentinel-observatory-alan-vo"
        self.app_version: str = self._read_version()
        self.app_env: str = os.getenv("APP_ENV", "development")
        self.host: str = os.getenv("HOST", "127.0.0.1")
        self.port: int = int(os.getenv("PORT", "8000"))
        self.demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/sentinel.db")

        # LLM Settings (Keys only server-side)
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "openai-compatible")
        self.llm_api_key: str = os.getenv("LLM_API_KEY", "")
        self.llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.llm_base_url: str = os.getenv("LLM_BASE_URL", "")
        self.llm_request_timeout: float = float(os.getenv("LLM_TIMEOUT", "20.0"))

        # OIDC Keycloak settings
        self.oidc_issuer_url: str = os.getenv(
            "OIDC_ISSUER_URL", "http://127.0.0.1:8080/realms/sentinel"
        )
        self.oidc_client_id: str = os.getenv("OIDC_CLIENT_ID", "sentinel-client")
        self.oidc_audience: str = os.getenv("OIDC_AUDIENCE", "sentinel-client")
        self.oidc_jwks_url: str = os.getenv(
            "OIDC_JWKS_URL",
            "http://127.0.0.1:8080/realms/sentinel/protocol/openid-connect/certs",
        )

        # CORS origins
        raw_origins = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
        self.cors_origins: list[str] = [o.strip() for o in raw_origins.split(",") if o.strip()]

    def _read_version(self) -> str:
        version_file = Path(__file__).parents[3] / "VERSION"
        try:
            return version_file.read_text().strip()
        except Exception:
            return "1.0.0"

    def validate_production_guards(self) -> None:
        """Enforce security boundaries: demo mode refused in production."""
        is_production = self.app_env.lower() in ("production", "prod")
        if is_production and self.demo_mode:
            raise RuntimeError(
                "SECURITY VIOLATION: DEMO_MODE=true is strictly prohibited in production environment."
            )
        if self.demo_mode:
            allowed_demo_hosts = {"127.0.0.1", "localhost", "0.0.0.0", "testserver"}
            if self.host not in allowed_demo_hosts:
                raise RuntimeError(
                    f"SECURITY VIOLATION: DEMO_MODE must bind localhost only, got host={self.host}"
                )


settings = Settings()

# Convenience aliases
APP_TITLE = settings.app_name
APP_DESCRIPTION = "AI presentation generation and slide-intelligence observatory"
APP_VERSION = settings.app_version
