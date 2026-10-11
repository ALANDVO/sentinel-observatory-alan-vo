"""Decks API: create, list, read, delete, compile to PPTX, export, and audio narration."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import Role, get_current_user, require_role
from backend.app.models.deck import Deck, Slide
from backend.app.services.audit_service import AuditService
from backend.app.services.audio_narration import AudioNarrationService
from backend.app.services.pptx_compiler import PptxCompiler
from backend.app.services.slide_generator import SlideGeneratorService
from backend.app.services.template_service import TemplateService
from backend.app.services.layout_engine import SlideLayoutEngine

router = APIRouter(prefix="/decks", tags=["decks"])
_gen, _comp, _audit, _narr, _tmpls, _layout = SlideGeneratorService(), PptxCompiler(), AuditService(), AudioNarrationService(), TemplateService(), SlideLayoutEngine()
_DB, _U = Depends(get_db), Depends(get_current_user)
_OP, _VW, _ADM = Depends(require_role(Role.OPERATOR)), Depends(require_role(Role.VIEWER)), Depends(require_role(Role.ADMIN))
class _Base(BaseModel):
    model_config = {"from_attributes": True}

class SlideOut(_Base):
    id: str; position: int; slide_type: str; title: str | None; body_text: str | None; speaker_notes: str | None; chart_data: dict | None = None; table_data: dict | None = None; layout_config: dict = {}

class DeckOut(_Base):
    id: str; title: str; topic: str | None; source_type: str; status: str; slide_count: int; template_id: str | None = None; meta: dict = {}; created_at: Any; updated_at: Any; slides: list[SlideOut] = []

class DeckSummary(_Base):
    id: str; title: str; source_type: str; status: str; slide_count: int; created_at: Any

class DeckListResponse(BaseModel):
    total: int; items: list[DeckSummary]

class GenerateTopicRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=2000); slide_count: int = Field(8, ge=3, le=30); template_id: str | None = None

class GenerateDocumentRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=50000); slide_count: int = Field(10, ge=3, le=30); template_id: str | None = None

class SlideCreateRequest(BaseModel):
    slide_type: str = "content"; title: str = Field("", max_length=512); body_text: str = Field("", max_length=4000); speaker_notes: str = Field("", max_length=2000); chart_data: dict | None = None; table_data: dict | None = None

class SlideUpdateRequest(BaseModel):
    slide_type: str | None = None; title: str | None = None; body_text: str | None = None; speaker_notes: str | None = None; chart_data: dict | None = None; table_data: dict | None = None

class SlideSearchResult(BaseModel):
    deck_id: str; deck_title: str; slide_id: str; position: int; slide_type: str; title: str | None; snippet: str | None; match_fields: list[str]

class SlideSearchResponse(BaseModel):
    query: str; total: int; results: list[SlideSearchResult]

def _get_deck(db: Session, did: str) -> Deck:
    if not (d := db.query(Deck).filter(Deck.id == did).first()): raise HTTPException(404, f"Deck {did!r} not found")
    return d

def _safe_fn(t: str, ext: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in t)[:50] + f".{ext}"

def _deck_slides(d: Deck) -> list[dict]:
    return [{"id": s.id, "position": s.position, "slide_type": s.slide_type, "title": s.title, "body_text": s.body_text, "bullets": (s.body_text or "").split("\n") if s.body_text else [], "speaker_notes": s.speaker_notes, "chart_data": s.chart_data, "table_data": s.table_data} for s in sorted(d.slides, key=lambda x: x.position)]

def _audit_log(db: Session, act: str, u: dict, did: str, det: dict) -> None:
    _audit.log(db, act, actor_sub=u.get("sub"), actor_email=u.get("email"), resource_type="deck", resource_id=did, detail=det); db.commit()

def _finish_deck_create(db: Session, deck: Deck, user: dict, src: str) -> DeckOut:
    _audit_log(db, "create_deck", user, deck.id, {"source_type": src}); db.refresh(deck); return DeckOut.model_validate(deck)

def _wav_res(b: bytes, fn: str) -> Response:
    return Response(content=b, media_type="audio/wav", headers={"Content-Disposition": f'inline; filename="{fn}"'})

@router.get("/search/slides", response_model=SlideSearchResponse)
def search_slides(q: str = Query(..., min_length=2, max_length=200), limit: int = Query(20, ge=1, le=50), db: Session = _DB, user: dict = _U) -> SlideSearchResponse:
    t = q.strip().lower()
    slides = db.query(Slide).join(Deck).filter(or_(Slide.title.ilike(f"%{t}%"), Slide.body_text.ilike(f"%{t}%"), Slide.speaker_notes.ilike(f"%{t}%"))).order_by(Deck.created_at.desc()).limit(limit).all()
    res = [SlideSearchResult(deck_id=s.deck_id, deck_title=s.deck.title if s.deck else "", slide_id=s.id, position=s.position, slide_type=s.slide_type, title=s.title, snippet=((("…" + (b := (s.body_text or "")[:200])[max(0, (i := b.lower().find(t)) - 40):i + 80] + "…").strip() if i >= 0 else b[:120]) or None), match_fields=[f for f, c in [("title", s.title), ("body", s.body_text), ("notes", s.speaker_notes)] if c and t in c.lower()]) for s in slides]
    return SlideSearchResponse(query=q, total=len(res), results=res)

@router.get("", response_model=DeckListResponse)
def list_decks(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), source_type: str | None = None, status: str | None = Query(None, alias="status"), search: str | None = Query(None, max_length=200), db: Session = _DB, user: dict = _U) -> DeckListResponse:
    q = db.query(Deck)
    if source_type: q = q.filter(Deck.source_type == source_type)
    if status: q = q.filter(Deck.status == status)
    if search: q = q.filter(Deck.title.ilike(f"%{search.strip()}%"))
    return DeckListResponse(total=q.count(), items=q.order_by(Deck.created_at.desc()).offset(skip).limit(limit).all())

@router.post("/generate/topic", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
def generate_from_topic(body: GenerateTopicRequest, db: Session = _DB, user: dict = _OP) -> DeckOut:
    return _finish_deck_create(db, _gen.generate_from_topic(db, body.topic, author_sub=user.get("sub"), template_id=body.template_id, slide_count=body.slide_count), user, "topic")

@router.post("/generate/document", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
def generate_from_document(body: GenerateDocumentRequest, db: Session = _DB, user: dict = _OP) -> DeckOut:
    return _finish_deck_create(db, _gen.generate_from_document(db, body.text, author_sub=user.get("sub"), template_id=body.template_id, slide_count=body.slide_count), user, "document")

@router.get("/{deck_id}", response_model=DeckOut)
def get_deck(deck_id: str, db: Session = _DB, user: dict = _U) -> DeckOut:
    return DeckOut.model_validate(_get_deck(db, deck_id))

@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(deck_id: str, db: Session = _DB, user: dict = _ADM) -> None:
    deck = _get_deck(db, deck_id); _audit_log(db, "delete_deck", user, deck_id, {"title": deck.title}); db.delete(deck); db.commit()

@router.post("/{deck_id}/slides", response_model=SlideOut, status_code=status.HTTP_201_CREATED)
def add_slide(deck_id: str, body: SlideCreateRequest, db: Session = _DB, user: dict = _OP) -> SlideOut:
    _get_deck(db, deck_id)
    return SlideOut.model_validate(_gen.add_slide(db, deck_id, body.slide_type, body.title, body.body_text, body.speaker_notes, body.chart_data, body.table_data))

@router.patch("/{deck_id}/slides/{slide_id}", response_model=SlideOut)
def update_slide(deck_id: str, slide_id: str, body: SlideUpdateRequest, db: Session = _DB, user: dict = _OP) -> SlideOut:
    _get_deck(db, deck_id)
    if not (s := _gen.update_slide(db, slide_id, {k: v for k, v in body.model_dump().items() if v is not None})): raise HTTPException(404, f"Slide {slide_id!r} not found")
    return SlideOut.model_validate(s)

@router.get("/{deck_id}/export/pptx")
def export_pptx(deck_id: str, db: Session = _DB, user: dict = _VW) -> Response:
    deck = _get_deck(db, deck_id)
    tp = str(p) if deck.template_id and (tmpl := _tmpls.get_template(db, deck.template_id)) and (p := _tmpls.get_template_filepath(tmpl)) else None
    raw = _comp.compile_deck(deck.title, _deck_slides(deck), template_path=tp)
    _audit_log(db, "export_deck", user, deck_id, {"format": "pptx"})
    return Response(content=raw, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", headers={"Content-Disposition": f'attachment; filename="{_safe_fn(deck.title, "pptx")}"'})

@router.post("/{deck_id}/narration/synthesize")
def synthesize_narration(deck_id: str, voice: str = Query("narrator-en"), words_per_minute: int = Query(150, ge=80, le=300), db: Session = _DB, user: dict = _OP) -> dict:
    deck = _get_deck(db, deck_id)
    n = _narr.synthesize_deck(deck_id, _deck_slides(deck), voice=voice, words_per_minute=words_per_minute)
    info = {"voice": voice, "words_per_minute": words_per_minute, "total_duration_seconds": n.total_duration_seconds, "total_words": n.total_words, "slide_count": len(n.slides)}
    deck.meta = {**(deck.meta or {}), "narration": info}; _audit_log(db, "synthesize_narration", user, deck_id, {"voice": voice, "words_per_minute": words_per_minute})
    return {"deck_id": deck_id, **info, "slides": [{"slide_id": s.slide_id, "position": s.position, "transcript": s.transcript, "word_count": s.word_count, "duration_seconds": s.duration_seconds, "words_per_minute": s.words_per_minute} for s in n.slides]}

@router.get("/{deck_id}/narration/audio")
def get_deck_narration_audio(deck_id: str, voice: str = Query("narrator-en"), words_per_minute: int = Query(150, ge=80, le=300), db: Session = _DB, user: dict = _VW) -> Response:
    deck = _get_deck(db, deck_id)
    return _wav_res(_narr.synthesize_deck(deck_id, _deck_slides(deck), voice=voice, words_per_minute=words_per_minute).audio_bytes, _safe_fn(deck.title, "wav"))

@router.get("/{deck_id}/slides/{slide_id}/narration/audio")
def get_slide_narration_audio(deck_id: str, slide_id: str, voice: str = Query("narrator-en"), words_per_minute: int = Query(150, ge=80, le=300), db: Session = _DB, user: dict = _VW) -> Response:
    _get_deck(db, deck_id)
    if not (s := db.query(Slide).filter(Slide.id == slide_id, Slide.deck_id == deck_id).first()): raise HTTPException(404, f"Slide {slide_id!r} not found in deck {deck_id!r}")
    return _wav_res(_narr.synthesize_slide(s.id, s.position, s.speaker_notes, s.title, voice, words_per_minute=words_per_minute).audio_bytes, f"slide_{s.position}_narration.wav")

@router.get("/{deck_id}/layout")
def get_deck_layout(deck_id: str, db: Session = _DB, user: dict = _VW) -> dict:
    return _layout.layout_summary(_deck_slides(_get_deck(db, deck_id)))