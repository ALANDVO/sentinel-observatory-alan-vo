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
_e, _a, _p, _l = EvaluationEngine(), AttributionGuard(), PromptAuditService(), LLMAdapters()
_D, _U, _O = Depends(get_db), Depends(get_current_user), Depends(require_role(Role.OPERATOR))
class EO(BaseModel):
    id: str; deck_id: str; eval_type: str; information_density_score: float | None = None; bullet_brevity_score: float | None = None; hierarchy_balance_score: float | None = None; readability_grade: float | None = None; mece_alignment_score: float | None = None; overall_cognitive_score: float | None = None; numeric_claims_found: float | None = None; claims_verified: float | None = None; data_fidelity_precision: float | None = None; data_fidelity_recall: float | None = None; attribution_pass: str | None = None; attribution_diagnostics: Any = None; prompt_audit_pass: str | None = None; prompt_audit_findings: Any = None; llm_advisory: str | None = None; llm_provider_used: str | None = None; raw_result: Any = None; created_at: Any = None
    model_config = {"from_attributes": True}
class EL(BaseModel):
    total: int; items: list[EO]
class RER(BaseModel):
    eval_type: str = "full"; source_data: list[dict] = Field(default_factory=list); model: str = "gpt-4o-mini"; request_llm_advisory: bool = False
class PAR(BaseModel):
    model: str = "gpt-4o-mini"; locale_keys_per_slide: list[dict] | None = None
class LAR(BaseModel):
    dictionaries: dict[str, dict[str, str]]; referenced_keys: list[str] | None = None
class DAR(BaseModel):
    source_text: str; target_text: str; source_locale: str = "en"; target_locale: str = "zh"
@router.get("/compare")
def compare_evaluations(ids: str = Query(...), db: Session = _D, u: dict = _U) -> dict:
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if len(id_list) not in range(2, 11): raise HTTPException(400, "Provide 2 to 10 evaluation IDs")
    evs = db.query(Evaluation).filter(Evaluation.id.in_(id_list)).all()
    if len(evs) != len(id_list): raise HTTPException(404, f"Evaluations not found: {', '.join(set(id_list) - {e.id for e in evs})}")
    return _bc(evs)
@router.get("/compare/export/markdown")
def export_comparison_markdown(ids: str = Query(...), db: Session = _D, u: dict = _U) -> Response:
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if len(id_list) not in range(2, 11): raise HTTPException(400, "Provide 2 to 10 evaluation IDs")
    evs = db.query(Evaluation).filter(Evaluation.id.in_(id_list)).all()
    if len(evs) != len(id_list): raise HTTPException(404, f"Evaluations not found: {', '.join(set(id_list) - {e.id for e in evs})}")
    return Response(content=_bm(evs), media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="evaluation_comparison_{evs[0].id[:8]}_et_al.md"'})
_K = ["id","deck_id","eval_type","created_at","overall_cognitive_score","information_density_score","bullet_brevity_score","hierarchy_balance_score","readability_grade","mece_alignment_score","data_fidelity_precision","data_fidelity_recall","attribution_pass","prompt_audit_pass"]
_M = [("overall_cognitive_score","Overall Cognitive Score"),("information_density_score","Information Density"),("bullet_brevity_score","Bullet Brevity"),("hierarchy_balance_score","Hierarchy Balance"),("readability_grade","Readability Grade (lower is better)"),("mece_alignment_score","MECE Alignment"),("data_fidelity_precision","Data Fidelity Precision"),("data_fidelity_recall","Data Fidelity Recall")]
_MD = [("overall_cognitive_score","Overall Cognitive Score"),("information_density_score","Information Density"),("bullet_brevity_score","Bullet Brevity"),("hierarchy_balance_score","Hierarchy Balance"),("readability_grade","Readability Grade"),("mece_alignment_score","MECE Alignment"),("data_fidelity_precision","Data Fidelity Precision"),("data_fidelity_recall","Data Fidelity Recall"),("attribution_pass","Attribution Guard"),("prompt_audit_pass","Prompt Audit")]
def _bc(evs: list[Evaluation]) -> dict:
    comp = {"evaluations": [], "comparison": {}}
    for ev in evs:
        d = {k: getattr(ev, k) for k in _K}
        d["created_at"] = ev.created_at.isoformat() if ev.created_at else None
        d["llm_advisory"] = bool(ev.llm_advisory)
        comp["evaluations"].append(d)
    for key, label in _M:
        vals = [(e["id"], e[key]) for e in comp["evaluations"] if e[key] is not None]
        if vals:
            rev = key == "readability_grade"
            best = min(vals, key=lambda x: x[1]) if rev else max(vals, key=lambda x: x[1])
            worst = max(vals, key=lambda x: x[1]) if rev else min(vals, key=lambda x: x[1])
            comp["comparison"][key] = {"label": label, "values": dict(vals), "best": {"id": best[0], "value": best[1]}, "worst": {"id": worst[0], "value": worst[1]}, "spread": round((best[1] - worst[1]) * (-1 if rev else 1), 3)}
    return comp
def _bm(evs: list[Evaluation]) -> str:
    L = ["# Evaluation Comparison Report", f"**Generated:** {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}", f"**Compared:** {len(evs)} evaluations", "", "## Summary Table"]
    L.append("| Metric | " + " | ".join(f"{e.id[:8]} ({e.eval_type})" for e in evs) + " |")
    L.append("| --- | " + " | ".join("---" for _ in evs) + " |")
    for key, label in _MD:
        row = [label]
        for e in evs:
            val = getattr(e, key)
            if val is None: row.append("N/A")
            elif isinstance(val, float): row.append(f"{val:.3f}")
            elif isinstance(val, bool): row.append("Yes" if val else "No")
            else: row.append(str(val))
        L.append("| " + " | ".join(row) + " |")
    L.append(""); L.append("## Per-Evaluation Details")
    for ev in evs:
        L.append(f"### Evaluation `{ev.id}` (Deck: {ev.deck_id}, Type: {ev.eval_type})")
        L.append(f"- **Created:** {ev.created_at.isoformat() if ev.created_at else 'N/A'}")
        if ev.overall_cognitive_score is not None:
            L += [f"- **Overall Cognitive:** {ev.overall_cognitive_score:.3f}", f"- **Density:** {ev.information_density_score or 'N/A'}", f"- **Brevity:** {ev.bullet_brevity_score or 'N/A'}", f"- **Hierarchy:** {ev.hierarchy_balance_score or 'N/A'}", f"- **Readability:** {ev.readability_grade or 'N/A'}", f"- **MECE:** {ev.mece_alignment_score or 'N/A'}"]
        if ev.data_fidelity_precision is not None:
            L += [f"- **Data Fidelity Precision:** {ev.data_fidelity_precision:.3f}", f"- **Data Fidelity Recall:** {ev.data_fidelity_recall:.3f}"]
        if ev.attribution_pass: L.append(f"- **Attribution:** {ev.attribution_pass.upper()}")
        if ev.prompt_audit_pass: L.append(f"- **Prompt Audit:** {ev.prompt_audit_pass.upper()}")
        if ev.llm_advisory: L.append(f"- **LLM Advisory:** Yes ({ev.llm_provider_used or 'unknown'})")
        L.append("")
    return "\n".join(L)
@router.get("", response_model=EL)
def le(did: str | None = Query(None), sk: int = Query(0, ge=0), lim: int = Query(20, ge=1, le=100), db: Session = _D, u: dict = _U) -> EL:
    q = db.query(Evaluation)
    if did: q = q.filter(Evaluation.deck_id == did)
    return EL(total=q.count(), items=q.order_by(Evaluation.created_at.desc()).offset(sk).limit(lim).all())
@router.post("/decks/{did}/run", response_model=EO, status_code=status.HTTP_201_CREATED)
def re(did: str, b: RER, db: Session = _D, u: dict = _O) -> EO:
    d = get_deck_or_404(db, did); sd = _deck_slides(d)
    ev = Evaluation(deck_id=did, evaluator_sub=u.get("sub"), eval_type=b.eval_type)
    if b.eval_type in ("full", "cognitive_load"):
        r = _e.evaluate_deck(did, sd)
        ev.information_density_score, ev.bullet_brevity_score, ev.hierarchy_balance_score, ev.readability_grade, ev.mece_alignment_score, ev.overall_cognitive_score = r.avg_information_density, r.avg_bullet_brevity, r.avg_hierarchy_balance, r.avg_readability_grade, r.mece_alignment_score, r.overall_cognitive_score
        ev.raw_result = {"observations": r.observations, "slide_scores": [vars(s) for s in r.slide_scores]}
    if b.eval_type in ("full", "data_fidelity"):
        f = _e.check_data_fidelity(sd, b.source_data)
        ev.numeric_claims_found, ev.claims_verified, ev.data_fidelity_precision, ev.data_fidelity_recall = f["numeric_claims_found"], f["claims_verified"], f["data_fidelity_precision"], f["data_fidelity_recall"]
    if b.eval_type in ("full", "attribution"):
        ar = _a.validate_deck_source(did, d.source_text, sd)
        ev.attribution_pass, ev.attribution_diagnostics = ("pass" if ar.passed else "fail"), ar.to_dict()["diagnostics"]
    if b.eval_type in ("full", "prompt_audit"):
        pa = _p.audit_slide_content(sd, model=b.model)
        ev.prompt_audit_pass, ev.prompt_audit_findings = ("pass" if pa.passed else "fail"), pa.to_dict()["findings"]
    if b.request_llm_advisory:
        ad = _l.analyze_deck(d.title, [f"{s.get('title','')}: {(s.get('body_text') or '')[:80]}" for s in sd], task="review")
        ev.llm_advisory, ev.llm_provider_used = ad.get("advisory"), ad.get("provider")
    db.add(ev); audit_log(db, "run_evaluation", u, "evaluation", ev.id, {"deck_id": did, "eval_type": b.eval_type}, commit=False); db.commit(); db.refresh(ev)
    return EO.model_validate(ev)
@router.get("/{eid}", response_model=EO)
def ge(eid: str, db: Session = _D, u: dict = _U) -> EO:
    if not (ev := db.query(Evaluation).filter(Evaluation.id == eid).first()): raise HTTPException(404, f"Evaluation {eid!r} not found")
    return EO.model_validate(ev)
@router.post("/prompt-audit", status_code=status.HTTP_200_OK)
def pa(did: str = Query(...), b: PAR = Body(...), db: Session = _D, u: dict = _O) -> dict:
    return _p.audit_slide_content(_deck_slides(get_deck_or_404(db, did)), model=b.model, locale_keys_per_slide=b.locale_keys_per_slide).to_dict()
@router.post("/locale-audit", status_code=status.HTTP_200_OK)
def la(b: LAR, u: dict = _O) -> dict:
    return _p.audit_locale_dictionary(b.dictionaries, referenced_keys=b.referenced_keys).to_dict()
@router.post("/doc-translation-audit", status_code=status.HTTP_200_OK)
def da(b: DAR, u: dict = _O) -> dict:
    return _p.audit_markdown_translation_drift(b.source_text, b.target_text, b.source_locale, b.target_locale).to_dict()
@router.get("/{eid}/export/json")
def ej(eid: str, db: Session = _D, u: dict = _U) -> Response:
    if not (ev := db.query(Evaluation).filter(Evaluation.id == eid).first()): raise HTTPException(404, f"Evaluation {eid!r} not found")
    dt = {c.key: getattr(ev, c.key) for c in ev.__table__.columns}
    dt["created_at"] = ev.created_at.isoformat() if ev.created_at else None
    return Response(content=json.dumps(dt, indent=2, ensure_ascii=False), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="evaluation_{ev.eval_type}_{ev.id[:8]}.json"'})
@router.get("/{eid}/export/markdown")
def em(eid: str, db: Session = _D, u: dict = _U) -> Response:
    if not (ev := db.query(Evaluation).filter(Evaluation.id == eid).first()): raise HTTPException(404, f"Evaluation {eid!r} not found")
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