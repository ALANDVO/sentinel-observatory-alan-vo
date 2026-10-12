import re
from dataclasses import dataclass, field
from typing import Any
from backend.app.services.nlp_engine import flesch_kincaid_grade, _tokenize
@dataclass
class SlideScore:
    slide_id: str; position: int; title: str; information_density: float; bullet_brevity: float
    hierarchy_balance: float; readability_grade: float; notes: list[str] = field(default_factory=list)
    def to_dict(self) -> dict: return {"slide_id": self.slide_id, "position": self.position, "title": self.title, "information_density": self.information_density, "bullet_brevity": self.bullet_brevity, "hierarchy_balance": self.hierarchy_balance, "readability_grade": self.readability_grade, "notes": self.notes}
@dataclass
class DeckCognitiveReport:
    deck_id: str; slide_scores: list[SlideScore]; avg_information_density: float
    avg_bullet_brevity: float; avg_hierarchy_balance: float; avg_readability_grade: float
    mece_alignment_score: float; overall_cognitive_score: float; observations: list[str] = field(default_factory=list)
    def to_dict(self) -> dict: return {"deck_id": self.deck_id, "slide_scores": [s.to_dict() for s in self.slide_scores], "avg_information_density": self.avg_information_density, "avg_bullet_brevity": self.avg_bullet_brevity, "avg_hierarchy_balance": self.avg_hierarchy_balance, "avg_readability_grade": self.avg_readability_grade, "mece_alignment_score": self.mece_alignment_score, "overall_cognitive_score": self.overall_cognitive_score, "observations": self.observations}
def _id(b: str) -> float:
    if not b: return 1.0
    bs = re.findall(r"(?:^[\*\-•]\s+.+|(?<=[.!?])\s+[A-Z])", b, re.MULTILINE)
    bc, cc = max(1, len(bs)), len(b)
    return round(max(0.0, min(1.0, max(0.0, 1.0 - (cc - 600) / 1200 - max(0, bc - 7) * 0.05) if cc > 600 or bc > 7 else 1.0 - (cc / 1200))), 3)
def _bb(b: str) -> float:
    if not b: return 1.0
    items = [m.group(1) for m in re.compile(r"^[\*\-•]\s+(.+)", re.MULTILINE).finditer(b)]
    items = items if items else re.split(r"(?<=[.!?])\s+", b)
    if not items: return 1.0
    return round(max(0.0, 1.0 - max(0.0, sum(len(_tokenize(it)) for it in items) / len(items) - 10) / 20.0), 3)
def _hb(t: str, b: str) -> float:
    tw, bw = len(_tokenize(t)), len(_tokenize(b)) if b else 0
    if bw == 0: return 0.8
    r = tw / (tw + bw)
    return round(r / 0.05 if r < 0.05 else max(0.0, 1.0 - (r - 0.25) / 0.75), 3) if not (0.05 <= r <= 0.25) else 1.0
def _ma(ts: list[str]) -> float:
    if len(ts) < 2: return 1.0
    ov = []
    for i in range(len(ts) - 1):
        s1, s2 = set(_tokenize(ts[i])), set(_tokenize(ts[i + 1]))
        ov.append(1.0 if not s1 or not s2 else 1.0 - len(s1 & s2) / len(s1 | s2))
    return round(sum(ov) / len(ov), 3)
_information_density = _id
_bullet_brevity = _bb
_hierarchy_balance = _hb
_mece_alignment = _ma
class EvaluationEngine:
    def evaluate_deck(self, did: str, slides: list[dict[str, Any]]) -> DeckCognitiveReport:
        scs, ts = [], []
        for s in slides:
            sid, pos = s.get("id", ""), s.get("position", 0)
            t, b = s.get("title") or "", s.get("body_text") or ""
            d, br, h, r = _id(b), _bb(b), _hb(t, b), flesch_kincaid_grade(f"{t}. {b}")
            ns = [m for c, m in ((d < 0.5, "High information density; consider splitting slide."), (br < 0.5, "Bullets are verbose; aim for ≤ 10 words."), (r > 12, "Reading grade level is high; simplify language.")) if c]
            scs.append(SlideScore(sid, pos, t, d, br, h, r, ns))
            ts.append(t)
        if not scs: return DeckCognitiveReport(did, [], 1.0, 1.0, 1.0, 0.0, 1.0, 1.0)
        n = len(scs)
        ad, ab, ah, ar = sum(s.information_density for s in scs) / n, sum(s.bullet_brevity for s in scs) / n, sum(s.hierarchy_balance for s in scs) / n, sum(s.readability_grade for s in scs) / n
        mece = _ma(ts)
        rs = max(0.0, 1.0 - max(0.0, ar - 6.0) / 12.0)
        ov = round(0.25 * ad + 0.25 * ab + 0.15 * ah + 0.20 * rs + 0.15 * mece, 3)
        obs = [m for c, m in ((ad < 0.6, "Overall deck information density is high; consider reducing slide content."), (mece < 0.6, "Slide titles show topic overlap; review MECE structure."), (ar > 14, "Deck reading level is graduate-level; simplify for wider audiences.")) if c]
        return DeckCognitiveReport(did, scs, round(ad, 3), round(ab, 3), round(ah, 3), round(ar, 2), mece, ov, obs)
    def check_data_fidelity(self, slides: list[dict[str, Any]], src: list[dict[str, Any]]) -> dict[str, Any]:
        nr = re.compile(r"\b(\d[\d,]*\.?\d*)\s*(?:%|x|times|k|M|B)?\b")
        cs = []
        for s in slides:
            for m in nr.finditer(f"{s.get('body_text') or ''} {s.get('title') or ''}"):
                try: cs.append(float(m.group(1).replace(",", "")))
                except ValueError: pass
        def _o(f: int, v: int, p: float, r: float, u: list) -> dict[str, Any]:
            return {"numeric_claims_found": f, "claims_verified": v, "data_fidelity_precision": round(p, 3), "data_fidelity_recall": round(r, 3), "unsupported_claims": u}
        if not cs: return _o(0, 0, 1.0, 1.0, [])
        sv = [float(v) for r in src for v in r.values() if isinstance(v, (int, float))]
        if not sv: return _o(len(cs), 0, 0.0, 0.0, [str(v) for v in cs[:10]])
        vd, un = 0, []
        for cv in cs:
            if any(abs(cv - sv) / max(abs(sv), 1.0) < 0.05 for sv in sv): vd += 1
            else: un.append(str(cv))
        pr = vd / len(cs) if cs else 1.0
        rc = vd / len(sv) if sv else 0.0
        return _o(len(cs), vd, pr, rc, un[:20])