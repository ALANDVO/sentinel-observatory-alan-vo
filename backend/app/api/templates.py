"""Templates API: template registry CRUD and upload."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import Role, get_current_user, require_role
from backend.app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])
_template_svc = TemplateService()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class TemplateOut(BaseModel):
    id: str
    name: str
    description: str | None
    theme_color: str | None
    slide_count: int
    layout_names: list[str] = []
    placeholder_map: dict = {}
    is_builtin: str
    created_at: Any

    model_config = {"from_attributes": True}


class TemplateListResponse(BaseModel):
    total: int
    items: list[TemplateOut]


class TemplateCreateBody(BaseModel):
    name: str
    description: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.on_event("startup")  # type: ignore[attr-defined]
def _seed() -> None:
    """No-op: seeding happens in app startup event."""
    pass


@router.get("", response_model=TemplateListResponse)
def list_templates(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> TemplateListResponse:
    templates, total = _template_svc.list_templates(db, skip=skip, limit=limit)
    return TemplateListResponse(total=total, items=templates)


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> TemplateOut:
    tmpl = _template_svc.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template {template_id!r} not found")
    return TemplateOut.model_validate(tmpl)


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(
    name: str = Form(...),
    description: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(Role.OPERATOR)),
) -> TemplateOut:
    pptx_bytes: bytes | None = None
    if file:
        if not file.filename or not file.filename.lower().endswith(".pptx"):
            raise HTTPException(status_code=400, detail="Only .pptx template files are accepted")
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:  # 20 MB max
            raise HTTPException(status_code=413, detail="Template file exceeds 20 MB limit")
        pptx_bytes = content

    try:
        tmpl = _template_svc.create_template(
            db,
            name=name,
            description=description,
            author_sub=user.get("sub"),
            pptx_bytes=pptx_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return TemplateOut.model_validate(tmpl)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(Role.ADMIN)),
) -> None:
    ok = _template_svc.delete_template(db, template_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Template {template_id!r} not found")
