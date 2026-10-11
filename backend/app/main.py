"""Sentinel Observatory FastAPI application entry point."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api import router as api_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns
    -------
    FastAPI
        Configured FastAPI instance with routes, middleware and startup events.
    """
    settings.validate_production_guards()

    # Startup lifespan: create DB tables and seed templates
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(_a: FastAPI):
        from backend.app.core.database import init_db, SessionLocal
        from backend.app.services.template_service import TemplateService

        logger.info("Initializing database…")
        init_db()

        with SessionLocal() as db:
            TemplateService().seed_builtin_templates(db)
        logger.info("Startup complete.")
        yield

    app = FastAPI(
        title="Sentinel Observatory",
        description=(
            "AI presentation generation and slide-intelligence observatory. "
            "Evaluates cognitive load, data grounding, and compiles native PowerPoint decks."
        ),
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS – allow configured frontend origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
