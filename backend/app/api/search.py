"""Cross-deck search API (unified)."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.core.security import require_role, Role
from backend.app.services.search_service import SS, SR, R, d
router = APIRouter(prefix="/search", tags=["search"])
_DB = Depends(get_db)
_VW = Depends(require_role(Role.VIEWER))
_S = SS()
class I(BaseModel): result_type: str; id: str; title: str; snippet: str; score: float; metadata: dict[str, Any] = {}
class F(BaseModel): result_type: dict[str, int] = {}; source_type: dict[str, int] = {}; slide_type: dict[str, int] = {}; eval_type: dict[str, int] = {}
class O(BaseModel): query: str; total: int; results: list[I]; facets: F
def mkf(rs):
    ft = {"result_type": {}, "source_type": {}, "slide_type": {}, "eval_type": {}}
    for r in rs:
        ft["result_type"][r.result_type] = ft["result_type"].get(r.result_type, 0) + 1
        if r.result_type == "deck": ft["source_type"][r.metadata.get("source_type", "?")] = ft["source_type"].get(r.metadata.get("source_type", "?"), 0) + 1
        elif r.result_type == "slide": ft["slide_type"][r.metadata.get("slide_type", "?")] = ft["slide_type"].get(r.metadata.get("slide_type", "?"), 0) + 1
        elif r.result_type == "evaluation": ft["eval_type"][r.metadata.get("eval_type", "?")] = ft["eval_type"].get(r.metadata.get("eval_type", "?"), 0) + 1
    return F(result_type=ft["result_type"], source_type=ft["source_type"], slide_type=ft["slide_type"], eval_type=ft["eval_type"])
@router.get("", response_model=O)
def us(q: str = Query(..., min_length=2, max_length=200), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
       source_type: str | None = None, status: str | None = None, deck_id: str | None = None, slide_type: str | None = None, eval_type: str | None = None, author_sub: str | None = None,
       db: Session = _DB, u: dict = _VW) -> O:
    fl = {k: v for k, v in {"source_type": source_type, "status": status, "deck_id": deck_id, "slide_type": slide_type, "eval_type": eval_type, "author_sub": author_sub}.items() if v}
    sr = _S.search_all(db, q, limit, offset, fl)
    return O(query=sr.query, total=sr.total, results=[I(**d(x)) for x in sr.results], facets=mkf(sr.results))