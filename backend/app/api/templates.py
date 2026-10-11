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
_ts = TemplateService()
_DB, _U = Depends(get_db), Depends(get_current_user)

class TemplateOut(BaseModel):
    id: str; name: str; description: str | None; theme_color: str | None; slide_count: int
    layout_names: list[str] = []; placeholder_map: dict = {}; is_builtin: str; created_at: Any
    model_config = {"from_attributes": True}

class TemplateListResponse(BaseModel):
    total: int; items: list[TemplateOut]

@router.get("", response_model=TemplateListResponse)
def list_templates(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: Session = _DB, user: dict = _U) -> TemplateListResponse:
    t, total = _ts.list_templates(db, skip=skip, limit=limit)
    return TemplateListResponse(total=total, items=t)

@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: str, db: Session = _DB, user: dict = _U) -> TemplateOut:
    if not (t := _ts.get_template(db, template_id)): raise HTTPException(404, f"Template {template_id!r} not found")
    return TemplateOut.model_validate(t)

@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(name: str = Form(...), description: str | None = Form(None), file: UploadFile | None = File(None), db: Session = _DB, user: dict = Depends(require_role(Role.OPERATOR))) -> TemplateOut:
    raw = None
    if file:
        if not file.filename or not file.filename.lower().endswith(".pptx"): raise HTTPException(400, "Only .pptx template files are accepted")
        raw = await file.read()
        if len(raw) > 20 * 1024 * 1024: raise HTTPException(413, "Template file exceeds 20 MB limit")
    try: return TemplateOut.model_validate(_ts.create_template(db, name, description, user.get("sub"), raw))
    except ValueError as exc: raise HTTPException(400, str(exc))

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: str, db: Session = _DB, user: dict = Depends(require_role(Role.ADMIN))) -> None:
    if not _ts.delete_template(db, template_id): raise HTTPException(404, f"Template {template_id!r} not found")
