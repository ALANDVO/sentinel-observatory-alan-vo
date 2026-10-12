from __future__ import annotations
import json
from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import Response
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
from backend.app.api.decks import _deck_slides
router = APIRouter(prefix="/evaluations", tags=["evaluations"])
_eng, _att, _pa, _llm, _audit = EvaluationEngine(), AttributionGuard(), PromptAuditService(), LLMAdapters(), AuditService()
_DB, _U, _OP = Depends(get_db), Depends(get_current_user), Depends(require_role(Role.OPERATOR))
class EvaluationOut(BaseModel):
    id: str; deck_id: str; eval_type: str; information_density_score: float | None = None; bullet_brevity_score: float | None = None; hierarchy_balance_score: float | None = None; readability_grade: float | None = None; mece_alignment_score: float | None = None; overall_cognitive_score: float | None = None; numeric_claims_found: float | None = None; claims_verified: float | None = None; data_fidelity_precision: float | None = None; data_fidelity_recall: float | None = None; attribution_pass: str | None = None; attribution_diagnostics: Any = None; prompt_audit_pass: str | None = None; prompt_audit_findings: Any = None; llm_advisory: str | None = None; llm_provider_used: str | None = None; raw_result: Any = None; created_at: Any = None
    model_config = {"from_attributes": True}
class EvaluationListResponse(BaseModel):
    total: int; items: list[EvaluationOut]
class RunEvaluationRequest(BaseModel):
    eval_type: str = "full"; source_data: list[dict] = Field(default_factory=list); model: str = "gpt-4o-mini"; request_llm_advisory: bool = False
class PromptAuditRequest(BaseModel):
    model: str = "gpt-4o-mini"; locale_keys_per_slide: list[dict] | None = None
class LocaleDictAuditRequest(BaseModel):
    dictionaries: dict[str, dict[str, str]]; referenced_keys: list[str] | None = None
class DocTranslationAuditRequest(BaseModel):
    source_text: str; target_text: str; source_locale: str = "en"; target_locale: str = "zh"
def _gdd(db: Session, did: str) -> Deck:
    if not (d := db.query(Deck).filter(Deck.id == did).first()): raise HTTPException(404, f"Deck {did!r} not found")
    return d
@router.get("", response_model=EvaluationListResponse)
def list_evaluations(deck_id: str | None = Query(None), skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = _DB, user: dict = _U) -> EvaluationListResponse:
    q = db.query(Evaluation)
    if deck_id: q = q.filter(Evaluation.deck_id == deck_id)
    return EvaluationListResponse(total=q.count(), items=q.order_by(Evaluation.created_at.desc()).offset(skip).limit(limit).all())
@router.post("/decks/{deck_id}/run", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
def run_evaluation(deck_id: str, body: RunEvaluationRequest, db: Session = _DB, user: dict = _OP) -> EvaluationOut:
    deck = _gdd(db, deck_id); sd = _deck_slides(deck)
    ev = Evaluation(deck_id=deck_id, evaluator_sub=user.get("sub"), eval_type=body.eval_type)
    if body.eval_type in ("full", "cognitive_load"):
        r = _eng.evaluate_deck(deck_id, sd)
        ev.information_density_score, ev.bullet_brevity_score, ev.hierarchy_balance_score, ev.readability_grade, ev.mece_alignment_score, ev.overall_cognitive_score = r.avg_information_density, r.avg_bullet_brevity, r.avg_hierarchy_balance, r.avg_readability_grade, r.mece_alignment_score, r.overall_cognitive_score
        ev.raw_result = {"observations": r.observations, "slide_scores": [vars(s) for s in r.slide_scores]}
    if body.eval_type in ("full", "data_fidelity"):
        f = _eng.check_data_fidelity(sd, body.source_data)
        ev.numeric_claims_found, ev.claims_verified, ev.data_fidelity_precision, ev.data_fidelity_recall = f["numeric_claims_found"], f["claims_verified"], f["data_fidelity_precision"], f["data_fidelity_recall"]
    if body.eval_type in ("full", "attribution"):
        att = _att.validate_deck_source(deck_id, deck.source_text, sd)
        ev.attribution_pass, ev.attribution_diagnostics = ("pass" if att.passed else "fail"), att.to_dict()["diagnostics"]
    if body.eval_type in ("full", "prompt_audit"):
        pa = _pa.audit_slide_content(sd, model=body.model)
        ev.prompt_audit_pass, ev.prompt_audit_findings = ("pass" if pa.passed else "fail"), pa.to_dict()["findings"]
    if body.request_llm_advisory:
        adv = _llm.analyze_deck(deck.title, [f"{s.get('title', '')}: {(s.get('body_text') or '')[:80]}" for s in sd], task="review")
        ev.llm_advisory, ev.llm_provider_used = adv.get("advisory"), adv.get("provider")
    db.add(ev)
    _audit.log(db, "run_evaluation", actor_sub=user.get("sub"), actor_email=user.get("email"), resource_type="evaluation", resource_id=ev.id, detail={"deck_id": deck_id, "eval_type": body.eval_type})
    db.commit(); db.refresh(ev)
    return EvaluationOut.model_validate(ev)
@router.get("/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(evaluation_id: str, db: Session = _DB, user: dict = _U) -> EvaluationOut:
    if not (ev := db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()): raise HTTPException(404, f"Evaluation {evaluation_id!r} not found")
    return EvaluationOut.model_validate(ev)
@router.post("/prompt-audit", status_code=status.HTTP_200_OK)
def run_prompt_audit(deck_id: str = Query(...), body: PromptAuditRequest = Body(...), db: Session = _DB, user: dict = _OP) -> dict:
    return _pa.audit_slide_content(_deck_slides(_gdd(db, deck_id)), model=body.model, locale_keys_per_slide=body.locale_keys_per_slide).to_dict()
@router.post("/locale-audit", status_code=status.HTTP_200_OK)
def run_locale_audit(body: LocaleDictAuditRequest, user: dict = _OP) -> dict:
    return _pa.audit_locale_dictionary(body.dictionaries, referenced_keys=body.referenced_keys).to_dict()
@router.post("/doc-translation-audit", status_code=status.HTTP_200_OK)
def run_doc_translation_audit(body: DocTranslationAuditRequest, user: dict = _OP) -> dict:
    return _pa.audit_markdown_translation_drift(body.source_text, body.target_text, body.source_locale, body.target_locale).to_dict()
@router.get("/{evaluation_id}/export/json")
def export_evaluation_json(evaluation_id: str, db: Session = _DB, user: dict = _U) -> Response:
    if not (ev := db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()): raise HTTPException(404, f"Evaluation {evaluation_id!r} not found")
    data = {c.key: getattr(ev, c.key) for c in ev.__table__.columns}
    data["created_at"] = ev.created_at.isoformat() if ev.created_at else None
    return Response(content=json.dumps(data, indent=2, ensure_ascii=False), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="evaluation_{ev.eval_type}_{ev.id[:8]}.json"'})
@router.get("/{evaluation_id}/export/markdown")
def export_evaluation_markdown(evaluation_id: str, db: Session = _DB, user: dict = _U) -> Response:
    if not (ev := db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()): raise HTTPException(404, f"Evaluation {evaluation_id!r} not found")
    e = ev.eval_type
    L = [f"# Evaluation Report: {e.title()}", f"**ID:** {ev.id}", f"**Deck:** {ev.deck_id}", f"**Created:** {ev.created_at.isoformat() if ev.created_at else 'N/A'}", f"**Model:** {ev.llm_provider_used or 'N/A'}", f"**Advisory:** {'Yes' if ev.llm_advisory else 'No'}", ""]
    if e in ("full", "cognitive_load"):
        L += ["## Cognitive Load", f"- **Overall:** {ev.overall_cognitive_score or 'N/A'}", f"- **Density:** {ev.information_density_score or 'N/A'}", f"- **Brevity:** {ev.bullet_brevity_score or 'N/A'}", f"- **Hierarchy:** {ev.hierarchy_balance_score or 'N/A'}", f"- **Readability:** {ev.readability_grade or 'N/A'}", f"- **MECE:** {ev.mece_alignment_score or 'N/A'}", "", "## Slides"]
        for s in (ev.raw_result or {}).get("slide_scores", []):
            L += [f"### Slide {s.get('position','?')}: {s.get('title','Untitled')}", f"- Density: {s.get('information_density','N/A')}", f"- Brevity: {s.get('bullet_brevity','N/A')}", f"- Hierarchy: {s.get('hierarchy_balance','N/A')}", f"- Readability: {s.get('readability_grade','N/A')}", f"- Notes: {', '.join(s.get('notes',[])) or 'None'}", ""]
        for o in (ev.raw_result or {}).get("observations", []): L.append(f"- {o}")
        L.append("")
    if e in ("full", "data_fidelity"):
        L += ["## Data Fidelity", f"- **Claims:** {ev.numeric_claims_found or 'N/A'}", f"- **Verified:** {ev.claims_verified or 'N/A'}", f"- **Precision:** {ev.data_fidelity_precision or 'N/A'}", f"- **Recall:** {ev.data_fidelity_recall or 'N/A'}", ""]
    if e in ("full", "attribution"):
        L += ["## Attribution", f"- **Passed:** {'Yes' if ev.attribution_pass == 'pass' else 'No'}", ""]
        for d in ev.attribution_diagnostics or []: L += [f"### {d.get('code','UNKNOWN')}: {d.get('message','')}", f"- Severity: {d.get('severity','')}", f"- Fix: {d.get('remediation','')}", ""]
    if e in ("full", "prompt_audit"):
        L += ["## Prompt Audit", f"- **Passed:** {'Yes' if ev.prompt_audit_pass == 'pass' else 'No'}", ""]
        for f in ev.prompt_audit_findings or []: L.append(f"- {f.get('type','Issue')}: {f.get('message','')}")
        L.append("")
    if ev.llm_advisory: L += ["## LLM Advisory", ev.llm_advisory, ""]
    return Response(content="\n".join(L), media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="evaluation_{e}_{ev.id[:8]}.md"'})
