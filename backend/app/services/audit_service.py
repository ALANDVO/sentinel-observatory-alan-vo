"""Audit service for immutable mutation logging."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.audit import AuditLog


class AuditService:
    """Writes immutable audit log entries for all data mutations."""

    def log(
        self,
        db: Session,
        action: str,
        actor_sub: str | None = None,
        actor_email: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        detail: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_sub=actor_sub,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail or {},
            ip_address=ip_address,
        )
        db.add(entry)
        db.flush()  # Assign ID without full commit (caller owns the transaction)
        return entry

    def list_logs(
        self,
        db: Session,
        resource_type: str | None = None,
        resource_id: str | None = None,
        actor_sub: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLog], int]:
        q = db.query(AuditLog)
        if resource_type:
            q = q.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            q = q.filter(AuditLog.resource_id == resource_id)
        if actor_sub:
            q = q.filter(AuditLog.actor_sub == actor_sub)
        total = q.count()
        entries = q.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
        return entries, total
