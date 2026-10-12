from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import Role, get_current_user, require_role
from backend.app.models.deck import Deck, Slide
from backend.app.services.audio_narration import AudioNarrationService
from backend.app.services.pptx_compiler import PptxCompiler
from backend.app.services.slide_generator import SlideGeneratorService
from backend.app.services.template_service import TemplateService
from backend.app.services.layout_engine import SlideLayoutEngine
from backend.app.api.common import get_deck_or_404, audit_log
router = APIRouter(prefix="/decks", tags=["decks"])
_g, _c, _n, _t, _l = SlideGeneratorService(), PptxCompiler(), AudioNarrationService(), TemplateService(), SlideLayoutEngine()
_D, _U = Depends(get_db), Depends(get_current_user)
_O, _V, _A = Depends(require_role(Role.OPERATOR)), Depends(require_role(Role.VIEWER)), Depends(require_role(Role.ADMIN))
class _B(BaseModel):
    model_config = {"from_attributes": True}
class SlideOut(_B):
    id: str; position: int; slide_type: str; title: str | None; body_text: str | None; speaker_notes: str | None; chart_data: dict | None = None; table_data: dict | None = None; layout_config: dict = {}
class DeckOut(_B):
    id: str; title: str; topic: str | None; source_type: str; status: str; slide_count: int; template_id: str | None = None; meta: dict = {}; created_at: Any; updated_at: Any; slides: list[SlideOut] = []
class DeckSummary(_B):
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
def _sf(t: str, e: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in t)[:50] + f".{e}"
def _ds(d: Deck) -> list[dict]:
    return [{"id": s.id, "position": s.position, "slide_type": s.slide_type, "title": s.title, "body_text": s.body_text, "bullets": (s.body_text or "").split("\n") if s.body_text else [], "speaker_notes": s.speaker_notes, "chart_data": s.chart_data, "table_data": s.table_data} for s in sorted(d.slides, key=lambda x: x.position)]
ds = _ds
_deck_slides = ds
def _fc(db: Session, d: Deck, u: dict, src: str) -> DeckOut:
    audit_log(db, "create_deck", u, "deck", d.id, {"source_type": src}); db.refresh(d); return DeckOut.model_validate(d)
def _wr(bs: bytes, fn: str) -> Response:
    return Response(content=bs, media_type="audio/wav", headers={"Content-Disposition": f'inline; filename="{fn}"'})
@router.get("/search/slides", response_model=SlideSearchResponse)
def ss(q: str = Query(..., min_length=2, max_length=200), lim: int = Query(20, ge=1, le=50), db: Session = _D, u: dict = _U) -> SlideSearchResponse:
    t = q.strip().lower()
    s = db.query(Slide).join(Deck).filter(or_(Slide.title.ilike(f"%{t}%"), Slide.body_text.ilike(f"%{t}%"), Slide.speaker_notes.ilike(f"%{t}%"))).order_by(Deck.created_at.desc()).limit(lim).all()
    res = [SlideSearchResult(deck_id=x.deck_id, deck_title=x.deck.title if x.deck else "", slide_id=x.id, position=x.position, slide_type=x.slide_type, title=x.title, snippet=((("…" + (b := (x.body_text or "")[:200])[max(0, (i := b.lower().find(t)) - 40):i + 80] + "…").strip() if i >= 0 else b[:120]) or None), match_fields=[f for f, c in [("title", x.title), ("body", x.body_text), ("notes", x.speaker_notes)] if c and t in c.lower()]) for x in s]
    return SlideSearchResponse(query=q, total=len(res), results=res)
@router.get("", response_model=DeckListResponse)
def ld(sk: int = Query(0, ge=0), lim: int = Query(20, ge=1, le=100), st: str | None = Query(None, alias="source_type"), sta: str | None = Query(None, alias="status"), se: str | None = Query(None, max_length=200), db: Session = _D, u: dict = _U) -> DeckListResponse:
    q = db.query(Deck)
    if st: q = q.filter(Deck.source_type == st)
    if sta: q = q.filter(Deck.status == sta)
    if se: q = q.filter(Deck.title.ilike(f"%{se}%"))
    return DeckListResponse(total=q.count(), items=q.order_by(Deck.created_at.desc()).offset(sk).limit(lim).all())
@router.post("/generate/topic", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
def gt(b: GenerateTopicRequest, db: Session = _D, u: dict = _O) -> DeckOut:
    return _fc(db, _g.generate_from_topic(db, b.topic, author_sub=u.get("sub"), template_id=b.template_id, slide_count=b.slide_count), u, "topic")
@router.post("/generate/document", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
def gd(b: GenerateDocumentRequest, db: Session = _D, u: dict = _O) -> DeckOut:
    return _fc(db, _g.generate_from_document(db, b.text, author_sub=u.get("sub"), template_id=b.template_id, slide_count=b.slide_count), u, "document")
@router.get("/{did}", response_model=DeckOut)
def gde(did: str, db: Session = _D, u: dict = _U) -> DeckOut:
    return DeckOut.model_validate(get_deck_or_404(db, did))
@router.delete("/{did}", status_code=status.HTTP_204_NO_CONTENT)
def dd(did: str, db: Session = _D, u: dict = _A) -> None:
    d = get_deck_or_404(db, did); audit_log(db, "delete_deck", u, "deck", did, {"title": d.title}); db.delete(d); db.commit()
@router.post("/{did}/slides", response_model=SlideOut, status_code=status.HTTP_201_CREATED)
def asl(did: str, b: SlideCreateRequest, db: Session = _D, u: dict = _O) -> SlideOut:
    get_deck_or_404(db, did)
    return SlideOut.model_validate(_g.add_slide(db, did, b.slide_type, b.title, b.body_text, b.speaker_notes, b.chart_data, b.table_data))
@router.patch("/{did}/slides/{sid}", response_model=SlideOut)
def usl(did: str, sid: str, b: SlideUpdateRequest, db: Session = _D, u: dict = _O) -> SlideOut:
    get_deck_or_404(db, did)
    if not (s := _g.update_slide(db, sid, {k: v for k, v in b.model_dump().items() if v is not None})): raise HTTPException(404, f"Slide {sid!r} not found")
    return SlideOut.model_validate(s)
@router.get("/{did}/export/pptx")
def ep(did: str, db: Session = _D, u: dict = _V) -> Response:
    d = get_deck_or_404(db, did)
    return Response(content=_c.compile_deck(d.title, ds(d)), media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", headers={"Content-Disposition": f'attachment; filename="{_sf(d.title, "pptx")}"'})
@router.post("/{did}/narration/synthesize")
def sn(did: str, voice: str = Query("narrator-en"), words_per_minute: int = Query(150, ge=80, le=300), db: Session = _D, u: dict = _O) -> dict:
    d = get_deck_or_404(db, did)
    n = _n.synthesize_deck(did, ds(d), voice=voice, words_per_minute=words_per_minute)
    d.meta = {**(d.meta or {}), "narration": {"voice": voice, "words_per_minute": words_per_minute, "total_duration_seconds": n.total_duration_seconds, "total_words": n.total_words}}; audit_log(db, "synthesize_narration", u, "deck", did, {"voice": voice, "words_per_minute": words_per_minute})
    return {"deck_id": did, "voice": voice, "words_per_minute": words_per_minute, "total_duration_seconds": n.total_duration_seconds, "total_words": n.total_words, "slides": [{"slide_id": s.slide_id, "position": s.position, "transcript": s.transcript, "word_count": s.word_count, "duration_seconds": s.duration_seconds, "words_per_minute": s.words_per_minute} for s in n.slides]}
@router.get("/{did}/narration/audio")
def gdna(did: str, voice: str = Query("narrator-en"), words_per_minute: int = Query(150, ge=80, le=300), db: Session = _D, u: dict = _V) -> Response:
    d = get_deck_or_404(db, did)
    return _wr(_n.synthesize_deck(did, ds(d), voice=voice, words_per_minute=words_per_minute).audio_bytes, _sf(d.title, "wav"))
@router.get("/{did}/slides/{sid}/narration/audio")
def gsna(did: str, sid: str, voice: str = Query("narrator-en"), words_per_minute: int = Query(150, ge=80, le=300), db: Session = _D, u: dict = _V) -> Response:
    get_deck_or_404(db, did)
    if not (s := db.query(Slide).filter(Slide.id == sid, Slide.deck_id == did).first()): raise HTTPException(404, f"Slide {sid!r} not found in deck {did!r}")
    return _wr(_n.synthesize_slide(s.id, s.position, s.speaker_notes, s.title, voice, words_per_minute=words_per_minute).audio_bytes, f"slide_{s.position}_narration.wav")
@router.get("/{did}/layout")
def gdl(did: str, db: Session = _D, u: dict = _V) -> dict:
    return _l.layout_summary(ds(get_deck_or_404(db, did)))