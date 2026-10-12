"""Health check endpoint."""
from fastapi import APIRouter
from backend.app.core.config import settings
router = APIRouter(tags=["health"])
@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "sentinel-observatory", "version": settings.app_version}
