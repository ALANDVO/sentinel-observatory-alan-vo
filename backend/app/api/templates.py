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

class TemplateOut(BaseModel):
    id: str; name: str; description: str | None; theme_color: str | None; slide_count: int
    layout_names: list[str] = []; placeholder_map: dict = {}; is_builtin: str; created_at: Any
    model_config = {"from_attributes": True}

class TemplateListResponse(BaseModel):
    total: int; items: list[TemplateOut]

@router.get("", response_model=TemplateListResponse)
def list_templates(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), user: dict = Depends(get_current_user)) -> TemplateListResponse:
    templates, total = _template_svc.list_templates(db, skip=skip, limit=limit)
    return TemplateListResponse(total=total, items=templates)

@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)) -> TemplateOut:
    if not (tmpl := _template_svc.get_template(db, template_id)):
        raise HTTPException(404, f"Template {template_id!r} not found")
    return TemplateOut.model_validate(tmpl)

@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(name: str = Form(...), description: str | None = Form(None), file: UploadFile | None = File(None), db: Session = Depends(get_db), user: dict = Depends(require_role(Role.OPERATOR))) -> TemplateOut:
    pptx_bytes: bytes | None = None
    if file:
        if not file.filename or not file.filename.lower().endswith(".pptx"):
            raise HTTPException(400, "Only .pptx template files are accepted")
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(413, "Template file exceeds 20 MB limit")
        pptx_bytes = content
    try:
        tmpl = _template_svc.create_template(db, name, description, user.get("sub"), pptx_bytes)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return TemplateOut.model_validate(tmpl)

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: str, db: Session = Depends(get_db), user: dict = Depends(require_role(Role.ADMIN))) -> None:
    if not _template_svc.delete_template(db, template_id):
        raise HTTPException(404, f"Template {template_id!r} not found")
