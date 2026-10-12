import json
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import Role, get_current_user, require_role
from backend.app.models.evaluation import Evaluation
from backend.app.services.attribution_guard import AttributionGuard
from backend.app.services.evaluator import EvaluationEngine
from backend.app.services.llm_adapters import LLMAdapters
from backend.app.services.prompt_audit import PromptAuditService
from backend.app.api.decks import _deck_slides
from backend.app.api.common import get_deck_or_404, audit_log
router = APIRouter(prefix="/evaluations", tags=["evaluations"])
E, A, P, L = EvaluationEngine(), AttributionGuard(), PromptAuditService(), LLMAdapters()
D, U, O = Depends(get_db), Depends(get_current_user), Depends(require_role(Role.OPERATOR))
class EO(BaseModel):
    id: str; deck_id: str; eval_type: str
    information_density_score: float | None = None; bullet_brevity_score: float | None = None
    hierarchy_balance_score: float | None = None; readability_grade: float | None = None
    mece_alignment_score: float | None = None; overall_cognitive_score: float | None = None
    numeric_claims_found: float | None = None; claims_verified: float | None = None
    data_fidelity_precision: float | None = None; data_fidelity_recall: float | None = None
    attribution_pass: str | None = None; attribution_diagnostics: Any = None
    prompt_audit_pass: str | None = None; prompt_audit_findings: Any = None
    llm_advisory: str | None = None; llm_provider_used: str | None = None
    raw_result: Any = None; created_at: Any = None
    model_config = {"from_attributes": True}
class EL(BaseModel): total: int; items: list[EO]
class RER(BaseModel): eval_type: str = "full"; source_data: list[dict] = Field(default_factory=list); model: str = "gpt-4o-mini"; request_llm_advisory: bool = False; locale_keys_per_slide: list[dict] | None = None
class PAR(BaseModel): model: str = "gpt-4o-mini"; locale_keys_per_slide: list[dict] | None = None
class LAR(BaseModel): dictionaries: dict[str, dict[str, str]]; referenced_keys: list[str] | None = None
class DAR(BaseModel): source_text: str; target_text: str; source_locale: str = "en"; target_locale: str = "zh"
@router.get("/compare")
def ce(ids: str = Query(...), db: Session = D, u: dict = U) -> dict:
    evs = [db.query(Evaluation).filter(Evaluation.id == i.strip()).first() for i in ids.split(",") if i.strip()]
    missing = [i.strip() for i in ids.split(",") if i.strip() and not db.query(Evaluation).filter(Evaluation.id == i.strip()).first()]
    if missing: raise HTTPException(404, f"Evaluations not found: {', '.join(missing)}")
    if len(evs) < 2 or len(evs) > 10: raise HTTPException(400, "At least 2 and at most 10 evaluations required")
    return _bc(evs)
@router.get("/compare/export/markdown")
def cme(ids: str = Query(...), db: Session = D, u: dict = U) -> Response:
    evs = [db.query(Evaluation).filter(Evaluation.id == i.strip()).first() for i in ids.split(",") if i.strip()]
    missing = [i.strip() for i in ids.split(",") if i.strip() and not db.query(Evaluation).filter(Evaluation.id == i.strip()).first()]
    if missing: raise HTTPException(404, f"Evaluations not found: {', '.join(missing)}")
    if len(evs) < 2 or len(evs) > 10: raise HTTPException(400, "At least 2 and at most 10 evaluations required")
    return Response(content=_bm(evs), media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="evaluation_comparison_{evs[0].id[:8]}_et_al.md"'})
_K = "id deck_id eval_type created_at overall_cognitive_score information_density_score bullet_brevity_score hierarchy_balance_score readability_grade mece_alignment_score data_fidelity_precision data_fidelity_recall attribution_pass prompt_audit_pass".split()
_M = [("overall_cognitive_score","Overall Cognitive Score"),("information_density_score","Information Density"),("bullet_brevity_score","Bullet Brevity"),("hierarchy_balance_score","Hierarchy Balance"),("readability_grade","Readability Grade (lower is better)"),("mece_alignment_score","MECE Alignment"),("data_fidelity_precision","Data Fidelity Precision"),("data_fidelity_recall","Data Fidelity Recall"),("attribution_pass","Attribution Guard"),("prompt_audit_pass","Prompt Audit")]
def _bc(evs):
    comp = {"evaluations": [], "comparison": {}}
    for ev in evs:
        d = {k: getattr(ev, k) for k in _K}
        d["created_at"] = ev.created_at.isoformat() if ev.created_at else None
        d["llm_advisory"] = bool(ev.llm_advisory)
        comp["evaluations"].append(d)
    for key, label in _M:
        if key in {"attribution_pass", "prompt_audit_pass"}: continue
        vals = [(e["id"], float(e[key])) for e in comp["evaluations"] if e[key] is not None]
        if vals:
            rev = key == "readability_grade"
            best = min(vals, key=lambda x: x[1]) if rev else max(vals, key=lambda x: x[1])
            worst = max(vals, key=lambda x: x[1]) if rev else min(vals, key=lambda x: x[1])
            comp["comparison"][key] = {"label": label, "values": dict(vals), "best": {"id": best[0], "value": best[1]}, "worst": {"id": worst[0], "value": worst[1]}, "spread": round((best[1] - worst[1]) * (-1 if rev else 1), 3)}
    return comp
def _bm(evs):
    L = ["# Evaluation Comparison Report", f"**Generated:** {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}", f"**Compared:** {len(evs)} evaluations", "", "## Summary Table"]
    L.append("| Metric | " + " | ".join(f"{e.id[:8]} ({e.eval_type})" for e in evs) + " |")
    L.append("| --- | " + " | ".join("---" for _ in evs) + " |")
    for key, label in _M:
        row = [label]
        for e in evs:
            val = getattr(e, key)
            if val is None: row.append("N/A")
            elif isinstance(val, float): row.append(f"{val:.3f}")
            elif isinstance(val, bool): row.append("Yes" if val else "No")
            else: row.append(str(val))
        L.append("| " + " | ".join(row) + " |")
    L += ["", "## Per-Evaluation Details"]
    for ev in evs:
        L += [f"### Evaluation `{ev.id}` (Deck: {ev.deck_id}, Type: {ev.eval_type})", f"- **Created:** {ev.created_at.isoformat() if ev.created_at else 'N/A'}"]
        if ev.overall_cognitive_score is not None:
            L += [f"- **Overall Cognitive:** {ev.overall_cognitive_score:.3f}", f"- **Density:** {ev.information_density_score or 'N/A'}", f"- **Brevity:** {ev.bullet_brevity_score or 'N/A'}", f"- **Hierarchy:** {ev.hierarchy_balance_score or 'N/A'}", f"- **Readability:** {ev.readability_grade or 'N/A'}", f"- **MECE:** {ev.mece_alignment_score or 'N/A'}"]
        if ev.data_fidelity_precision is not None: L += [f"- **Data Fidelity Precision:** {ev.data_fidelity_precision:.3f}", f"- **Data Fidelity Recall:** {ev.data_fidelity_recall:.3f}"]
        if ev.attribution_pass: L.append(f"- **Attribution:** {ev.attribution_pass.upper()}")
        if ev.prompt_audit_pass: L.append(f"- **Prompt Audit:** {ev.prompt_audit_pass.upper()}")
        if ev.llm_advisory: L.append(f"- **LLM Advisory:** Yes ({ev.llm_provider_used or 'unknown'})")
        L.append("")
    return "\n".join(L)
@router.get("", response_model=EL)
def le(did: str | None = Query(None), sk: int = Query(0, ge=0), lim: int = Query(20, ge=1, le=100), db: Session = D, u: dict = U) -> EL:
    q = db.query(Evaluation)
    if did: q = q.filter(Evaluation.deck_id == did)
    return EL(total=q.count(), items=q.order_by(Evaluation.created_at.desc()).offset(sk).limit(lim).all())
@router.post("/decks/{did}/run", response_model=EO, status_code=status.HTTP_201_CREATED)
def re(did: str, b: RER, db: Session = D, u: dict = O) -> EO:
    d = get_deck_or_404(db, did); sd = _deck_slides(d)
    ev = E.evaluate_deck(d.id, sd) if b.eval_type in {"full", "cognitive_load"} else None
    fd = E.check_data_fidelity(sd, b.source_data) if b.eval_type in {"full", "data_fidelity"} else {"numeric_claims_found": 0, "claims_verified": 0, "data_fidelity_precision": 1.0, "data_fidelity_recall": 1.0, "unsupported_claims": []}
    ar = A.validate_deck_source(d.id, d.source_text, sd) if b.eval_type in {"full", "attribution"} else None
    pa = P.audit_slide_content(sd, model=b.model, locale_keys_per_slide=b.locale_keys_per_slide) if b.eval_type in {"full", "prompt_audit"} else None
    la = None
    if b.request_llm_advisory and L.is_configured():
        la = L.advise(d.title, {"cognitive": ev, "fidelity": fd, "attribution": ar, "prompt": pa} if ev else {"fidelity": fd, "attribution": ar, "prompt": pa})
    rec = Evaluation(deck_id=d.id, eval_type=b.eval_type, information_density_score=ev.avg_information_density if ev else None, bullet_brevity_score=ev.avg_bullet_brevity if ev else None, hierarchy_balance_score=ev.avg_hierarchy_balance if ev else None, readability_grade=ev.avg_readability_grade if ev else None, mece_alignment_score=ev.mece_alignment_score if ev else None, overall_cognitive_score=ev.overall_cognitive_score if ev else None, numeric_claims_found=fd["numeric_claims_found"], claims_verified=fd["claims_verified"], data_fidelity_precision=fd["data_fidelity_precision"], data_fidelity_recall=fd["data_fidelity_recall"], attribution_pass="pass" if ar and ar.passed else "fail" if ar else None, attribution_diagnostics=[vars(x) for x in ar.diagnostics] if ar else None, prompt_audit_pass="pass" if pa and pa.passed else "fail" if pa else None, prompt_audit_findings=[vars(x) for x in pa.findings] if pa else None, llm_advisory=la, llm_provider_used=L._provider if la else None, raw_result={"cognitive": ev.to_dict() if ev else None, "fidelity": fd, "attribution": ar.to_dict() if ar else None, "prompt": pa.to_dict() if pa else None})
    db.add(rec); db.commit(); db.refresh(rec); audit_log(db, "run_evaluation", u, "evaluation", rec.id, {"eval_type": b.eval_type})
    return EO.model_validate(rec)
@router.get("/{eid}", response_model=EO)
def ge(eid: str, db: Session = D, u: dict = U) -> EO:
    if not (ev := db.query(Evaluation).filter(Evaluation.id == eid).first()): raise HTTPException(404, f"Evaluation {eid!r} not found")
    return EO.model_validate(ev)
@router.post("/prompt-audit", status_code=status.HTTP_200_OK)
def pa(did: str = Query(...), b: PAR = Body(...), db: Session = D, u: dict = O) -> dict:
    return P.audit_slide_content(_deck_slides(get_deck_or_404(db, did)), model=b.model, locale_keys_per_slide=b.locale_keys_per_slide).to_dict()
@router.post("/locale-audit", status_code=status.HTTP_200_OK)
def la(b: LAR, u: dict = O) -> dict:
    return P.audit_locale_dictionary(b.dictionaries, referenced_keys=b.referenced_keys).to_dict()
@router.post("/doc-translation-audit", status_code=status.HTTP_200_OK)
def da(b: DAR, u: dict = O) -> dict:
    return P.audit_markdown_translation_drift(b.source_text, b.target_text, b.source_locale, b.target_locale).to_dict()
@router.get("/{eid}/export/json")
def ej(eid: str, db: Session = D, u: dict = U) -> Response:
    if not (ev := db.query(Evaluation).filter(Evaluation.id == eid).first()): raise HTTPException(404, f"Evaluation {eid!r} not found")
    return Response(content=json.dumps(EO.model_validate(ev).model_dump(), indent=2, ensure_ascii=False), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="evaluation_{ev.eval_type}_{ev.id[:8]}.json"'})
@router.get("/{eid}/export/markdown")
def em(eid: str, db: Session = D, u: dict = U) -> Response:
    if not (ev := db.query(Evaluation).filter(Evaluation.id == eid).first()): raise HTTPException(404, f"Evaluation {eid!r} not found")
    e = ev.eval_type; L = [f"# Evaluation Report: {e.title()}", f"**Generated:** {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}", f"**Deck:** {ev.deck_id}", f"**Type:** {e}", ""]
    if ev.overall_cognitive_score is not None:
        L += ["## Cognitive Load Summary", f"- **Overall:** {ev.overall_cognitive_score:.3f}", f"- **Density:** {ev.information_density_score:.3f}", f"- **Brevity:** {ev.bullet_brevity_score:.3f}", f"- **Hierarchy:** {ev.hierarchy_balance_score:.3f}", f"- **Readability:** {ev.readability_grade:.2f}", f"- **MECE:** {ev.mece_alignment_score:.3f}", ""]
    if ev.data_fidelity_precision is not None: L += ["## Data Fidelity", f"- **Precision:** {ev.data_fidelity_precision:.3f}", f"- **Recall:** {ev.data_fidelity_recall:.3f}", f"- **Claims Found:** {int(ev.numeric_claims_found)}", f"- **Claims Verified:** {int(ev.claims_verified)}", ""]
    if ev.attribution_pass: L += ["## Attribution Guard", f"- **Result:** {ev.attribution_pass.upper()}", ""]
    if ev.prompt_audit_pass: L += ["## Prompt & Locale Audit", f"- **Result:** {ev.prompt_audit_pass.upper()}", ""]
    if ev.llm_advisory: L += ["## LLM Advisory", f"- **Provider:** {ev.llm_provider_used or 'unknown'}", f"- **Notes:** {ev.llm_advisory}", ""]
    return Response(content="\n".join(L), media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="evaluation_{e}_{ev.id[:8]}.md"'})