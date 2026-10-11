"""Decks API: create, list, read, delete, compile to PPTX, export, and audio narration."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import Role, get_current_user, require_role
from backend.app.models.deck import Deck, Slide
from backend.app.services.audit_service import AuditService
from backend.app.services.audio_narration import AudioNarrationService
from backend.app.services.pptx_compiler import PptxCompiler
from backend.app.services.slide_generator import SlideGeneratorService
from backend.app.services.template_service import TemplateService

router = APIRouter(prefix="/decks", tags=["decks"])

_generator = SlideGeneratorService()
_compiler = PptxCompiler()
_audit = AuditService()
_narration = AudioNarrationService()
_templates = TemplateService()


class SlideOut(BaseModel):
    id: str
    position: int
    slide_type: str
    title: str | None
    body_text: str | None
    speaker_notes: str | None
    chart_data: dict | None = None
    table_data: dict | None = None
    layout_config: dict = {}
    model_config = {"from_attributes": True}


class DeckOut(BaseModel):
    id: str
    title: str
    topic: str | None
    source_type: str
    status: str
    slide_count: int
    template_id: str | None = None
    meta: dict = {}
    created_at: Any
    updated_at: Any
    slides: list[SlideOut] = []
    model_config = {"from_attributes": True}


class DeckSummary(BaseModel):
    id: str
    title: str
    source_type: str
    status: str
    slide_count: int
    created_at: Any
    model_config = {"from_attributes": True}


class DeckListResponse(BaseModel):
    total: int
    items: list[DeckSummary]


class GenerateTopicRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=2000)
    slide_count: int = Field(default=8, ge=3, le=30)
    template_id: str | None = None


class GenerateDocumentRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=50000)
    slide_count: int = Field(default=10, ge=3, le=30)
    template_id: str | None = None


class SlideCreateRequest(BaseModel):
    slide_type: str = Field(default="content")
    title: str = Field(default="", max_length=512)
    body_text: str = Field(default="", max_length=4000)
    speaker_notes: str = Field(default="", max_length=2000)
    chart_data: dict | None = None
    table_data: dict | None = None


class SlideUpdateRequest(BaseModel):
    slide_type: str | None = None
    title: str | None = None
    body_text: str | None = None
    speaker_notes: str | None = None
    chart_data: dict | None = None
    table_data: dict | None = None


def _get_deck_or_404(db: Session, deck_id: str) -> Deck:
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id!r} not found")
    return deck


@router.get("", response_model=DeckListResponse)
def list_decks(skip: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100), source_type: str | None = None, status_filter: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db), user: dict = Depends(get_current_user)) -> DeckListResponse:
    q = db.query(Deck)
    if source_type:
        q = q.filter(Deck.source_type == source_type)
    if status_filter:
        q = q.filter(Deck.status == status_filter)
    return DeckListResponse(total=q.count(), items=q.order_by(Deck.created_at.desc()).offset(skip).limit(limit).all())


@router.post("/generate/topic", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
def generate_from_topic(body: GenerateTopicRequest, db: Session = Depends(get_db), user: dict = Depends(require_role(Role.OPERATOR))) -> DeckOut:
    deck = _generator.generate_from_topic(db, topic=body.topic, author_sub=user.get("sub"), template_id=body.template_id, slide_count=body.slide_count)
    _audit.log(db, "create_deck", actor_sub=user.get("sub"), actor_email=user.get("email"), resource_type="deck", resource_id=deck.id, detail={"source_type": "topic", "topic": body.topic[:100]})
    db.commit()
    db.refresh(deck)
    return DeckOut.model_validate(deck)


@router.post("/generate/document", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
def generate_from_document(body: GenerateDocumentRequest, db: Session = Depends(get_db), user: dict = Depends(require_role(Role.OPERATOR))) -> DeckOut:
    deck = _generator.generate_from_document(db, text_content=body.text, author_sub=user.get("sub"), template_id=body.template_id, slide_count=body.slide_count)
    _audit.log(db, "create_deck", actor_sub=user.get("sub"), actor_email=user.get("email"), resource_type="deck", resource_id=deck.id, detail={"source_type": "document", "text_length": len(body.text)})
    db.commit()
    db.refresh(deck)
    return DeckOut.model_validate(deck)


@router.get("/{deck_id}", response_model=DeckOut)
def get_deck(deck_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)) -> DeckOut:
    return DeckOut.model_validate(_get_deck_or_404(db, deck_id))


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(deck_id: str, db: Session = Depends(get_db), user: dict = Depends(require_role(Role.ADMIN))) -> None:
    deck = _get_deck_or_404(db, deck_id)
    _audit.log(db, "delete_deck", actor_sub=user.get("sub"), actor_email=user.get("email"), resource_type="deck", resource_id=deck_id, detail={"title": deck.title})
    db.delete(deck)
    db.commit()


@router.post("/{deck_id}/slides", response_model=SlideOut, status_code=status.HTTP_201_CREATED)
def add_slide(deck_id: str, body: SlideCreateRequest, db: Session = Depends(get_db), user: dict = Depends(require_role(Role.OPERATOR))) -> SlideOut:
    _get_deck_or_404(db, deck_id)
    slide = _generator.add_slide(db, deck_id, slide_type=body.slide_type, title=body.title, body_text=body.body_text, speaker_notes=body.speaker_notes, chart_data=body.chart_data, table_data=body.table_data)
    return SlideOut.model_validate(slide)


@router.patch("/{deck_id}/slides/{slide_id}", response_model=SlideOut)
def update_slide(deck_id: str, slide_id: str, body: SlideUpdateRequest, db: Session = Depends(get_db), user: dict = Depends(require_role(Role.OPERATOR))) -> SlideOut:
    _get_deck_or_404(db, deck_id)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    slide = _generator.update_slide(db, slide_id, updates)
    if not slide:
        raise HTTPException(status_code=404, detail=f"Slide {slide_id!r} not found")
    return SlideOut.model_validate(slide)


@router.get("/{deck_id}/export/pptx")
def export_pptx(deck_id: str, db: Session = Depends(get_db), user: dict = Depends(require_role(Role.VIEWER))) -> Response:
    deck = _get_deck_or_404(db, deck_id)
    slides_data = [
        {"id": s.id, "position": s.position, "slide_type": s.slide_type, "title": s.title, "body_text": s.body_text, "bullets": (s.body_text or "").split("\n") if s.body_text else [], "speaker_notes": s.speaker_notes, "chart_data": s.chart_data, "table_data": s.table_data}
        for s in sorted(deck.slides, key=lambda s: s.position)
    ]
    template_path = None
    if deck.template_id:
        tmpl = _templates.get_template(db, deck.template_id)
        if tmpl:
            p = _templates.get_template_filepath(tmpl)
            if p:
                template_path = str(p)
    pptx_bytes = _compiler.compile_deck(deck.title, slides_data, template_path=template_path)
    _audit.log(db, "export_deck", actor_sub=user.get("sub"), actor_email=user.get("email"), resource_type="deck", resource_id=deck_id, detail={"format": "pptx", "template_id": deck.template_id})
    db.commit()
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in deck.title)[:50]
    return Response(content=pptx_bytes, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", headers={"Content-Disposition": f'attachment; filename="{safe_title}.pptx"'})


@router.post("/{deck_id}/narration/synthesize")
def synthesize_narration(deck_id: str, voice: str = Query("narrator-en"), db: Session = Depends(get_db), user: dict = Depends(require_role(Role.OPERATOR))) -> dict:
    deck = _get_deck_or_404(db, deck_id)
    slides_data = [{"id": s.id, "position": s.position, "title": s.title, "speaker_notes": s.speaker_notes} for s in sorted(deck.slides, key=lambda s: s.position)]
    narration = _narration.synthesize_deck(deck_id, slides_data, voice=voice)
    current_meta = dict(deck.meta or {})
    current_meta["narration"] = {"voice": voice, "total_duration_seconds": narration.total_duration_seconds, "total_words": narration.total_words, "slide_count": len(narration.slides)}
    deck.meta = current_meta
    _audit.log(db, "synthesize_narration", actor_sub=user.get("sub"), actor_email=user.get("email"), resource_type="deck", resource_id=deck_id, detail={"voice": voice, "duration": narration.total_duration_seconds})
    db.commit()
    return {"deck_id": deck_id, "voice": voice, "total_duration_seconds": narration.total_duration_seconds, "total_words": narration.total_words, "slides": [{"slide_id": s.slide_id, "position": s.position, "transcript": s.transcript, "word_count": s.word_count, "duration_seconds": s.duration_seconds} for s in narration.slides]}


@router.get("/{deck_id}/narration/audio")
def get_deck_narration_audio(deck_id: str, voice: str = Query("narrator-en"), db: Session = Depends(get_db), user: dict = Depends(require_role(Role.VIEWER))) -> Response:
    deck = _get_deck_or_404(db, deck_id)
    slides_data = [{"id": s.id, "position": s.position, "title": s.title, "speaker_notes": s.speaker_notes} for s in sorted(deck.slides, key=lambda s: s.position)]
    narration = _narration.synthesize_deck(deck_id, slides_data, voice=voice)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in deck.title)[:50]
    return Response(content=narration.audio_bytes, media_type="audio/wav", headers={"Content-Disposition": f'inline; filename="{safe_title}_narration.wav"'})


@router.get("/{deck_id}/slides/{slide_id}/narration/audio")
def get_slide_narration_audio(deck_id: str, slide_id: str, voice: str = Query("narrator-en"), db: Session = Depends(get_db), user: dict = Depends(require_role(Role.VIEWER))) -> Response:
    _get_deck_or_404(db, deck_id)
    slide = db.query(Slide).filter(Slide.id == slide_id, Slide.deck_id == deck_id).first()
    if not slide:
        raise HTTPException(status_code=404, detail=f"Slide {slide_id!r} not found in deck {deck_id!r}")
    sn = _narration.synthesize_slide(slide_id=slide.id, position=slide.position, speaker_notes=slide.speaker_notes, title=slide.title, voice=voice)
    return Response(content=sn.audio_bytes, media_type="audio/wav", headers={"Content-Disposition": f'inline; filename="slide_{slide.position}_narration.wav"'})