"""Slide evaluation engine: cognitive load, data fidelity, and MECE alignment metrics.

Deterministic offline scoring without LLM dependencies.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.app.services.nlp_engine import flesch_kincaid_grade, _tokenize


@dataclass
class SlideScore:
    slide_id: str
    position: int
    title: str
    information_density: float
    bullet_brevity: float
    hierarchy_balance: float
    readability_grade: float
    notes: list[str] = field(default_factory=list)


@dataclass
class DeckCognitiveReport:
    deck_id: str
    slide_scores: list[SlideScore]
    avg_information_density: float
    avg_bullet_brevity: float
    avg_hierarchy_balance: float
    avg_readability_grade: float
    mece_alignment_score: float
    overall_cognitive_score: float
    observations: list[str] = field(default_factory=list)


def _information_density(body: str) -> float:
    if not body:
        return 1.0
    bullets = re.findall(r"(?:^[\*\-•]\s+.+|(?<=[.!?])\s+[A-Z])", body, re.MULTILINE)
    bullet_count = max(1, len(bullets))
    char_count = len(body)
    if char_count > 600 or bullet_count > 7:
        score = max(0.0, 1.0 - (char_count - 600) / 1200 - max(0, bullet_count - 7) * 0.05)
    else:
        score = 1.0 - (char_count / 1200)
    return round(max(0.0, min(1.0, score)), 3)


def _bullet_brevity(body: str) -> float:
    if not body:
        return 1.0
    bullets = [m.group(1) for m in re.compile(r"^[\*\-•]\s+(.+)", re.MULTILINE).finditer(body)]
    items = bullets if bullets else re.split(r"(?<=[.!?])\s+", body)
    if not items:
        return 1.0
    avg_words = sum(len(_tokenize(it)) for it in items) / len(items)
    return round(max(0.0, 1.0 - max(0.0, avg_words - 10) / 20.0), 3)


def _hierarchy_balance(title: str, body: str) -> float:
    tw = len(_tokenize(title))
    bw = len(_tokenize(body)) if body else 0
    if bw == 0:
        return 0.8
    ratio = tw / (tw + bw)
    if 0.05 <= ratio <= 0.25:
        return 1.0
    elif ratio < 0.05:
        return round(ratio / 0.05, 3)
    return round(max(0.0, 1.0 - (ratio - 0.25) / 0.75), 3)


def _mece_alignment(slide_titles: list[str]) -> float:
    if len(slide_titles) < 2:
        return 1.0
    overlaps = []
    for i in range(len(slide_titles) - 1):
        s1 = set(_tokenize(slide_titles[i]))
        s2 = set(_tokenize(slide_titles[i + 1]))
        if not s1 or not s2:
            overlaps.append(1.0)
            continue
        overlaps.append(1.0 - len(s1 & s2) / len(s1 | s2))
    return round(sum(overlaps) / len(overlaps), 3)


class EvaluationEngine:
    """Computes cognitive load, data fidelity, and MECE alignment evaluations."""

    def evaluate_deck(self, deck_id: str, slides: list[dict[str, Any]]) -> DeckCognitiveReport:
        slide_scores: list[SlideScore] = []
        titles: list[str] = []
        for s in slides:
            sid = s.get("id", "")
            pos = s.get("position", 0)
            title = s.get("title") or ""
            body = s.get("body_text") or ""
            d = _information_density(body)
            b = _bullet_brevity(body)
            h = _hierarchy_balance(title, body)
            r = flesch_kincaid_grade(f"{title}. {body}")
            notes: list[str] = []
            if d < 0.5:
                notes.append("High information density; consider splitting slide.")
            if b < 0.5:
                notes.append("Bullets are verbose; aim for ≤ 10 words.")
            if r > 12:
                notes.append("Reading grade level is high; simplify language.")
            slide_scores.append(SlideScore(sid, pos, title, d, b, h, r, notes))
            titles.append(title)

        if not slide_scores:
            return DeckCognitiveReport(deck_id, [], 1.0, 1.0, 1.0, 0.0, 1.0, 1.0)

        n = len(slide_scores)
        avg_d = sum(s.information_density for s in slide_scores) / n
        avg_b = sum(s.bullet_brevity for s in slide_scores) / n
        avg_h = sum(s.hierarchy_balance for s in slide_scores) / n
        avg_r = sum(s.readability_grade for s in slide_scores) / n
        mece = _mece_alignment(titles)
        r_score = max(0.0, 1.0 - max(0.0, avg_r - 6.0) / 12.0)
        overall = round(0.25 * avg_d + 0.25 * avg_b + 0.15 * avg_h + 0.20 * r_score + 0.15 * mece, 3)

        obs: list[str] = []
        if avg_d < 0.6:
            obs.append("Overall deck information density is high; consider reducing slide content.")
        if mece < 0.6:
            obs.append("Slide titles show topic overlap; review MECE structure.")
        if avg_r > 14:
            obs.append("Deck reading level is graduate-level; simplify for wider audiences.")

        return DeckCognitiveReport(
            deck_id=deck_id, slide_scores=slide_scores,
            avg_information_density=round(avg_d, 3), avg_bullet_brevity=round(avg_b, 3),
            avg_hierarchy_balance=round(avg_h, 3), avg_readability_grade=round(avg_r, 2),
            mece_alignment_score=mece, overall_cognitive_score=overall, observations=obs,
        )

    def check_data_fidelity(self, slides: list[dict[str, Any]], source_data: list[dict[str, Any]]) -> dict[str, Any]:
        numeric_re = re.compile(r"\b(\d[\d,]*\.?\d*)\s*(?:%|x|times|k|M|B)?\b")
        claim_values: list[float] = []
        for s in slides:
            body = f"{s.get('body_text') or ''} {s.get('title') or ''}"
            for m in numeric_re.finditer(body):
                try:
                    claim_values.append(float(m.group(1).replace(",", "")))
                except ValueError:
                    pass

        if not claim_values:
            return {"numeric_claims_found": 0, "claims_verified": 0, "data_fidelity_precision": 1.0, "data_fidelity_recall": 1.0, "unsupported_claims": []}

        source_values = [float(v) for r in source_data for v in r.values() if isinstance(v, (int, float))]
        if not source_values:
            return {"numeric_claims_found": len(claim_values), "claims_verified": 0, "data_fidelity_precision": 0.0, "data_fidelity_recall": 0.0, "unsupported_claims": [str(v) for v in claim_values[:10]]}

        verified = 0
        unsupported = []
        for cv in claim_values:
            if any(abs(cv - sv) / max(abs(sv), 1.0) < 0.05 for sv in source_values):
                verified += 1
            else:
                unsupported.append(str(cv))

        prec = verified / len(claim_values) if claim_values else 1.0
        rec = verified / len(source_values) if source_values else 0.0
        return {"numeric_claims_found": len(claim_values), "claims_verified": verified, "data_fidelity_precision": round(prec, 3), "data_fidelity_recall": round(rec, 3), "unsupported_claims": unsupported[:20]}