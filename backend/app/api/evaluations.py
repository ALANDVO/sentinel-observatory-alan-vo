"""Evaluations API: cognitive load analysis, data fidelity, attribution guard, prompt audit."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import Role, get_current_user, require_role
from backend.app.models.deck import Deck
from backend.app.models.evaluation import Evaluation
from backend.app.services.attribution_guard import AttributionGuard
from backend.app.services.audit_service import AuditService
from backend.app.services.evaluator import EvaluationEngine
from backend.app.services.llm_adapters import LLMAdapters
from backend.app.services.prompt_audit import PromptAuditService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])
_eval_engine = EvaluationEngine()
_attribution = AttributionGuard()
_prompt_audit = PromptAuditService()
_llm = LLMAdapters()
_audit = AuditService()


class SlideScoreOut(BaseModel):
    slide_id: str
    position: int
    title: str
    information_density: float
    bullet_brevity: float
    hierarchy_balance: float
    readability_grade: float
    notes: list[str] = []


class EvaluationOut(BaseModel):
    id: str
    deck_id: str
    eval_type: str
    information_density_score: float | None = None
    bullet_brevity_score: float | None = None
    hierarchy_balance_score: float | None = None
    readability_grade: float | None = None
    mece_alignment_score: float | None = None
    overall_cognitive_score: float | None = None
    numeric_claims_found: float | None = None
    claims_verified: float | None = None
    data_fidelity_precision: float | None = None
    data_fidelity_recall: float | None = None
    attribution_pass: str | None = None
    attribution_diagnostics: Any = None
    prompt_audit_pass: str | None = None
    prompt_audit_findings: Any = None
    llm_advisory: str | None = None
    llm_provider_used: str | None = None
    raw_result: Any = None
    created_at: Any = None
    model_config = {"from_attributes": True}


class EvaluationListResponse(BaseModel):
    total: int
    items: list[EvaluationOut]


class RunEvaluationRequest(BaseModel):
    eval_type: str = Field(default="full")
    source_data: list[dict] = Field(default_factory=list)
    model: str = Field(default="gpt-4o-mini")
    request_llm_advisory: bool = Field(default=False)


class PromptAuditRequest(BaseModel):
    model: str = Field(default="gpt-4o-mini")
    locale_keys_per_slide: list[dict] | None = None


class LocaleDictAuditRequest(BaseModel):
    dictionaries: dict[str, dict[str, str]]


def _get_deck_or_404(db: Session, deck_id: str) -> Deck:
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id!r} not found")
    return deck


def _slides_to_dicts(slides) -> list[dict]:
    return [{"id": s.id, "position": s.position, "slide_type": s.slide_type, "title": s.title or "", "body_text": s.body_text or "", "speaker_notes": s.speaker_notes or "", "chart_data": s.chart_data, "table_data": s.table_data} for s in sorted(slides, key=lambda s: s.position)]


@router.get("", response_model=EvaluationListResponse)
def list_evaluations(deck_id: str | None = Query(default=None), skip: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db), user: dict = Depends(get_current_user)) -> EvaluationListResponse:
    q = db.query(Evaluation)
    if deck_id:
        q = q.filter(Evaluation.deck_id == deck_id)
    return EvaluationListResponse(total=q.count(), items=q.order_by(Evaluation.created_at.desc()).offset(skip).limit(limit).all())


@router.post("/decks/{deck_id}/run", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
def run_evaluation(deck_id: str, body: RunEvaluationRequest, db: Session = Depends(get_db), user: dict = Depends(require_role(Role.OPERATOR))) -> EvaluationOut:
    deck = _get_deck_or_404(db, deck_id)
    slides_data = _slides_to_dicts(deck.slides)
    eval_rec = Evaluation(deck_id=deck_id, evaluator_sub=user.get("sub"), eval_type=body.eval_type)

    if body.eval_type in ("full", "cognitive_load"):
        rep = _eval_engine.evaluate_deck(deck_id, slides_data)
        eval_rec.information_density_score = rep.avg_information_density
        eval_rec.bullet_brevity_score = rep.avg_bullet_brevity
        eval_rec.hierarchy_balance_score = rep.avg_hierarchy_balance
        eval_rec.readability_grade = rep.avg_readability_grade
        eval_rec.mece_alignment_score = rep.mece_alignment_score
        eval_rec.overall_cognitive_score = rep.overall_cognitive_score
        eval_rec.raw_result = {"observations": rep.observations, "slide_scores": [vars(s) for s in rep.slide_scores]}

    if body.eval_type in ("full", "data_fidelity"):
        fid = _eval_engine.check_data_fidelity(slides_data, body.source_data)
        eval_rec.numeric_claims_found = fid["numeric_claims_found"]
        eval_rec.claims_verified = fid["claims_verified"]
        eval_rec.data_fidelity_precision = fid["data_fidelity_precision"]
        eval_rec.data_fidelity_recall = fid["data_fidelity_recall"]

    if body.eval_type in ("full", "attribution"):
        att = _attribution.validate_deck_source(deck_id, deck.source_text, slides_data)
        eval_rec.attribution_pass = "pass" if att.passed else "fail"
        eval_rec.attribution_diagnostics = att.to_dict()["diagnostics"]

    if body.eval_type in ("full", "prompt_audit"):
        pa = _prompt_audit.audit_slide_content(slides_data, model=body.model)
        eval_rec.prompt_audit_pass = "pass" if pa.passed else "fail"
        eval_rec.prompt_audit_findings = pa.to_dict()["findings"]

    if body.request_llm_advisory:
        sums = [f"{s.get('title', '')}: {(s.get('body_text') or '')[:80]}" for s in slides_data]
        adv = _llm.analyze_deck(deck.title, sums, task="review")
        eval_rec.llm_advisory = adv.get("advisory")
        eval_rec.llm_provider_used = adv.get("provider")

    db.add(eval_rec)
    _audit.log(db, "run_evaluation", actor_sub=user.get("sub"), actor_email=user.get("email"), resource_type="evaluation", resource_id=eval_rec.id, detail={"deck_id": deck_id, "eval_type": body.eval_type})
    db.commit()
    db.refresh(eval_rec)
    return EvaluationOut.model_validate(eval_rec)


@router.get("/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(evaluation_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)) -> EvaluationOut:
    ev = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evaluation {evaluation_id!r} not found")
    return EvaluationOut.model_validate(ev)


@router.post("/prompt-audit", status_code=status.HTTP_200_OK)
def run_prompt_audit(deck_id: str = Query(...), body: PromptAuditRequest = Body(...), db: Session = Depends(get_db), user: dict = Depends(require_role(Role.OPERATOR))) -> dict:
    deck = _get_deck_or_404(db, deck_id)
    return _prompt_audit.audit_slide_content(_slides_to_dicts(deck.slides), model=body.model, locale_keys_per_slide=body.locale_keys_per_slide).to_dict()


@router.post("/locale-audit", status_code=status.HTTP_200_OK)
def run_locale_audit(body: LocaleDictAuditRequest, user: dict = Depends(require_role(Role.OPERATOR))) -> dict:
    return _prompt_audit.audit_locale_dictionary(body.dictionaries).to_dict()