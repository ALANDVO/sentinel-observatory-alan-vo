"""Slide evaluation engine: cognitive load, data fidelity, and MECE alignment metrics."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any
from backend.app.services.nlp_engine import flesch_kincaid_grade, _tokenize

@dataclass
class SlideScore:
    slide_id: str; position: int; title: str; information_density: float; bullet_brevity: float
    hierarchy_balance: float; readability_grade: float; notes: list[str] = field(default_factory=list)

@dataclass
class DeckCognitiveReport:
    deck_id: str; slide_scores: list[SlideScore]; avg_information_density: float
    avg_bullet_brevity: float; avg_hierarchy_balance: float; avg_readability_grade: float
    mece_alignment_score: float; overall_cognitive_score: float; observations: list[str] = field(default_factory=list)

def _information_density(body: str) -> float:
    if not body: return 1.0
    bullets = re.findall(r"(?:^[\*\-•]\s+.+|(?<=[.!?])\s+[A-Z])", body, re.MULTILINE)
    bc, cc = max(1, len(bullets)), len(body)
    score = max(0.0, 1.0 - (cc - 600) / 1200 - max(0, bc - 7) * 0.05) if cc > 600 or bc > 7 else 1.0 - (cc / 1200)
    return round(max(0.0, min(1.0, score)), 3)

def _bullet_brevity(body: str) -> float:
    if not body: return 1.0
    b = [m.group(1) for m in re.compile(r"^[\*\-•]\s+(.+)", re.MULTILINE).finditer(body)]
    items = b if b else re.split(r"(?<=[.!?])\s+", body)
    if not items: return 1.0
    return round(max(0.0, 1.0 - max(0.0, sum(len(_tokenize(it)) for it in items) / len(items) - 10) / 20.0), 3)

def _hierarchy_balance(title: str, body: str) -> float:
    tw, bw = len(_tokenize(title)), len(_tokenize(body)) if body else 0
    if bw == 0: return 0.8
    ratio = tw / (tw + bw)
    if 0.05 <= ratio <= 0.25: return 1.0
    return round(ratio / 0.05 if ratio < 0.05 else max(0.0, 1.0 - (ratio - 0.25) / 0.75), 3)

def _mece_alignment(titles: list[str]) -> float:
    if len(titles) < 2: return 1.0
    overlaps = []
    for i in range(len(titles) - 1):
        s1, s2 = set(_tokenize(titles[i])), set(_tokenize(titles[i + 1]))
        overlaps.append(1.0 if not s1 or not s2 else 1.0 - len(s1 & s2) / len(s1 | s2))
    return round(sum(overlaps) / len(overlaps), 3)

class EvaluationEngine:
    def evaluate_deck(self, deck_id: str, slides: list[dict[str, Any]]) -> DeckCognitiveReport:
        scores, titles = [], []
        for s in slides:
            sid, pos = s.get("id", ""), s.get("position", 0)
            t, b = s.get("title") or "", s.get("body_text") or ""
            d, br, h, r = _information_density(b), _bullet_brevity(b), _hierarchy_balance(t, b), flesch_kincaid_grade(f"{t}. {b}")
            notes = [msg for cond, msg in ((d < 0.5, "High information density; consider splitting slide."), (br < 0.5, "Bullets are verbose; aim for ≤ 10 words."), (r > 12, "Reading grade level is high; simplify language.")) if cond]
            scores.append(SlideScore(sid, pos, t, d, br, h, r, notes))
            titles.append(t)
        if not scores: return DeckCognitiveReport(deck_id, [], 1.0, 1.0, 1.0, 0.0, 1.0, 1.0)
        n = len(scores)
        ad, ab, ah, ar = sum(s.information_density for s in scores) / n, sum(s.bullet_brevity for s in scores) / n, sum(s.hierarchy_balance for s in scores) / n, sum(s.readability_grade for s in scores) / n
        mece = _mece_alignment(titles)
        r_score = max(0.0, 1.0 - max(0.0, ar - 6.0) / 12.0)
        overall = round(0.25 * ad + 0.25 * ab + 0.15 * ah + 0.20 * r_score + 0.15 * mece, 3)
        obs = [msg for cond, msg in ((ad < 0.6, "Overall deck information density is high; consider reducing slide content."), (mece < 0.6, "Slide titles show topic overlap; review MECE structure."), (ar > 14, "Deck reading level is graduate-level; simplify for wider audiences.")) if cond]
        return DeckCognitiveReport(deck_id, scores, round(ad, 3), round(ab, 3), round(ah, 3), round(ar, 2), mece, overall, obs)

    def check_data_fidelity(self, slides: list[dict[str, Any]], source_data: list[dict[str, Any]]) -> dict[str, Any]:
        num_re = re.compile(r"\b(\d[\d,]*\.?\d*)\s*(?:%|x|times|k|M|B)?\b")
        claims: list[float] = []
        for s in slides:
            for m in num_re.finditer(f"{s.get('body_text') or ''} {s.get('title') or ''}"):
                try: claims.append(float(m.group(1).replace(",", "")))
                except ValueError: pass
        def _out(f: int, v: int, p: float, r: float, u: list) -> dict[str, Any]:
            return {"numeric_claims_found": f, "claims_verified": v, "data_fidelity_precision": round(p, 3), "data_fidelity_recall": round(r, 3), "unsupported_claims": u}
        if not claims: return _out(0, 0, 1.0, 1.0, [])
        src_vals = [float(v) for r in source_data for v in r.values() if isinstance(v, (int, float))]
        if not src_vals: return _out(len(claims), 0, 0.0, 0.0, [str(v) for v in claims[:10]])
        verified, unsupported = 0, []
        for cv in claims:
            if any(abs(cv - sv) / max(abs(sv), 1.0) < 0.05 for sv in src_vals): verified += 1
            else: unsupported.append(str(cv))
        prec = verified / len(claims) if claims else 1.0
        rec = verified / len(src_vals) if src_vals else 0.0
        return _out(len(claims), verified, prec, rec, unsupported[:20])