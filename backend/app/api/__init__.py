"""API package: aggregates all routers."""
from fastapi import APIRouter

from backend.app.api.health import router as health_router
from backend.app.api.auth import router as auth_router
from backend.app.api.decks import router as decks_router
from backend.app.api.evaluations import router as evaluations_router
from backend.app.api.templates import router as templates_router
from backend.app.api.audit import router as audit_router
from backend.app.api.search import router as search_router

router = APIRouter(prefix="/api")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(decks_router)
router.include_router(evaluations_router)
router.include_router(templates_router)
router.include_router(audit_router)
router.include_router(search_router)