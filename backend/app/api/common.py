"""Common API utilities shared across routers."""
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models.deck import Deck
from backend.app.services.audit_service import AuditService
_audit = AuditService()
def get_deck_or_404(db: Session, deck_id: str) -> Deck:
    if not (d := db.query(Deck).filter(Deck.id == deck_id).first()):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Deck {deck_id!r} not found")
    return d
def audit_log(db: Session, action: str, user: dict[str, Any], rt: str, rid: str, detail: dict[str, Any] | None = None, *, commit: bool = True) -> None:
    _audit.log(db, action, user.get("sub"), user.get("email"), rt, rid, detail or {})
    if commit: db.commit()