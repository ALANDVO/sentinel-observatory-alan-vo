from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import Role, require_role
from backend.app.services.audit_service import AuditService
router = APIRouter(prefix="/audit", tags=["audit"])
_audit = AuditService()
class AuditLogOut(BaseModel):
    id: str; actor_sub: str | None; actor_email: str | None; action: str; resource_type: str | None; resource_id: str | None; detail: Any; ip_address: str | None; created_at: Any
    model_config = {"from_attributes": True}
class AuditLogListResponse(BaseModel):
    total: int; items: list[AuditLogOut]
@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(resource_type: str | None = None, resource_id: str | None = None, actor_sub: str | None = None, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), user: dict = Depends(require_role(Role.ADMIN))) -> AuditLogListResponse:
    entries, total = _audit.list_logs(db, resource_type=resource_type, resource_id=resource_id, actor_sub=actor_sub, skip=skip, limit=limit)
    return AuditLogListResponse(total=total, items=entries)
