"""Sentinel Observatory FastAPI application entry point."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api import router as api_router

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings.validate_production_guards()

    @asynccontextmanager
    async def lifespan(_a: FastAPI):
        from backend.app.core.database import init_db, SessionLocal
        from backend.app.services.template_service import TemplateService
        init_db()
        with SessionLocal() as db: TemplateService().seed_builtin_templates(db)
        yield

    app = FastAPI(title="Sentinel Observatory", description="AI presentation generation and slide-intelligence observatory", version=settings.app_version, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.include_router(api_router)
    return app

app = create_app()
