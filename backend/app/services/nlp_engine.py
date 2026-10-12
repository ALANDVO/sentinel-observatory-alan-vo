import hashlib, re
from dataclasses import dataclass, field
from typing import Literal
SlideType = Literal["title", "content", "kpi", "chart", "table", "comparison", "process"]
@dataclass
class SlideBlueprint:
    position: int; slide_type: SlideType; title: str; bullets: list[str] = field(default_factory=list)
    speaker_notes: str = ""; chart_data: dict | None = None; table_data: dict | None = None; layout_config: dict = field(default_factory=dict)
@dataclass
class DeckBlueprint:
    title: str; topic: str; slides: list[SlideBlueprint] = field(default_factory=list); keywords: list[str] = field(default_factory=list); reading_level: float = 0.0
_S = frozenset("a an the and or but in on at to for of with by from is are was were be been have has had do will would can as not more such like just into than over after up out so if other which while when how what where who then each every some very same here".split())
def _tok(t: str) -> list[str]: return re.findall(r"[a-z][a-z0-9'\-]*[a-z0-9]|[a-z]", t.lower())
_tokenize = _tok
def extract_keywords(t: str, top_k: int = 15) -> list[str]:
    f: dict[str, int] = {}
    for w in _tok(t):
        if w not in _S and len(w) > 3: f[w] = f.get(w, 0) + 1
    return [k for k, _ in sorted(f.items(), key=lambda x: -x[1])[:top_k]]
def _syl(w: str) -> int:
    v = re.findall(r"[aeiou]", w.lower().strip(".,;:!?\"'"))
    if w.lower().endswith("e") and len(w) > 2: v = v[:-1]
    return max(1, len(v))
def flesch_kincaid_grade(t: str) -> float:
    s = [x.strip() for x in re.split(r"[.!?]+", t) if x.strip()]
    w = _tok(t)
    if not s or not w: return 0.0
    return round(max(0.0, 0.39 * (len(w) / len(s)) + 11.8 * (sum(_syl(x) for x in w) / len(w)) - 15.59), 2)
_KP = [re.compile(r"\b\d+[\.,]?\d*\s*(?:%|percent|x|times|billion|million|k|ms|s|fps|gb|mb)\b", re.I), re.compile(r"\b(?:metric|kpi|roi|cagr|conversion|retention|churn|latency|throughput)\b", re.I)]
_CP = [re.compile(r"\b(?:chart|graph|trend|over time|growth|distribution|percentage)\b", re.I)]
_TP = [re.compile(r"\b(?:compare|comparison|versus|vs\.?|table|matrix|rows|columns)\b", re.I)]
_PP = [re.compile(r"\b(?:step\s*\d+|phase\s*\d+|stage|pipeline|workflow|process|flow)\b", re.I)]
def detect_slide_type(t: str, b: str) -> SlideType:
    c = f"{t} {b}"
    k, ch = sum(1 for p in _KP if p.search(c)), sum(1 for p in _CP if p.search(c))
    ta, pr = sum(1 for p in _TP if p.search(c)), sum(1 for p in _PP if p.search(c))
    if k >= 2: return "kpi"
    if ch >= 1 and k >= 1: return "chart"
    if ta >= 1: return "comparison"
    if pr >= 1: return "process"
    return "content"
def _split(t: str) -> list[tuple[str, str]]:
    m = list(re.compile(r"^(?:#{1,3}\s+|(?=[A-Z][A-Z\s]{4,}$))(.*)", re.MULTILINE).finditer(t))
    if not m: return [(p.split(".")[0][:80], p) for p in [p.strip() for p in re.split(r"\n\s*\n", t) if p.strip()]]
    sec = []
    for i, x in enumerate(m):
        h = (x.group(1).strip() or x.group(0).strip("# ")).strip()
        e = m[i + 1].start() if i + 1 < len(m) else len(t)
        if h: sec.append((h[:120], t[x.end():e].strip()))
    return sec
def _bullets(b: str, max_b: int = 6) -> list[str]:
    bs = [x.group(1).strip() for x in re.compile(r"^[\*\-•]\s+(.+)", re.MULTILINE).finditer(b)]
    if not bs: bs = [x.strip() for x in re.split(r"(?<=[.!?])\s+", b) if 10 < len(x.strip()) < 200]
    return bs[:max_b]
def _notes(t: str, b: list[str]) -> str:
    if not b: return f"Discuss {t.lower()} with the audience."
    n = f'In this slide on "{t}", key points include: ' + "; ".join(b[:3]) + "."
    if len(b) > 3: n += f" Additional considerations: {'; '.join(b[3:])}."
    return n[:800]
def _chart(t: str, k: list[str]) -> dict:
    c = k[:5] if k else ["Category A", "Category B", "Category C"]
    def v(l: str, s: str) -> float: return round(20.0 + (int(hashlib.md5(f"{l}:{s}".encode()).hexdigest(), 16) % 800) / 10.0, 1)
    return {"chart_type": "bar", "title": t, "categories": c, "series": [{"name": "Value", "values": [v(x, t) for x in c]}]}
def _table(cols: list[str], rc: int = 4) -> dict:
    h = cols[:4] if cols else ["Criterion", "Option A", "Option B", "Option C"]
    cr, rt = ["Performance", "Cost", "Scalability", "Reliability"], ["High", "Medium", "Low", "Very High", "Excellent"]
    rows = []
    for i in range(min(rc, len(cr))):
        rows.append([cr[i]] + [rt[int(hashlib.md5(f"{cr[i]}:{x}".encode()).hexdigest(), 16) % len(rt)] for x in h[1:]])
    return {"headers": h, "rows": rows}
class NLPEngine:
    def decompose_topic(self, t: str, sc: int = 8) -> DeckBlueprint:
        k = extract_keywords(t, top_k=15)
        sl = [SlideBlueprint(0, "title", t[:100], speaker_notes=f"Welcome. Today we explore: {t[:200]}")]
        for i, kw in enumerate(k[:min(sc - 2, 8)], start=1):
            st = detect_slide_type(kw, f"Analysis of {kw}")
            b = [f"Key insight {j + 1} about {kw}" for j in range(3)]
            ch = _chart(kw, k) if st == "chart" else None
            tb = _table(k) if st in ("comparison", "table") else None
            sl.append(SlideBlueprint(i, st, kw.title(), b, _notes(kw.title(), b), ch, tb))
        sl.append(SlideBlueprint(len(sl), "content", "Summary & Next Steps", [f"Key takeaway: {k[0].title() if k else t[:30]}", "Validate findings with data", "Schedule follow-up review"], speaker_notes="Summarize findings and agree on next steps."))
        return DeckBlueprint(t[:100], t, sl, k, flesch_kincaid_grade(t))
    def decompose_document(self, t: str, sc: int = 10) -> DeckBlueprint:
        k, fl = extract_keywords(t, top_k=20), t.strip().split("\n")[0][:120] or "Presentation"
        sl = [SlideBlueprint(0, "title", fl, speaker_notes=f"This presentation covers: {fl}")]
        for i, (h, b) in enumerate(_split(t)[:sc - 2], start=1):
            bts, st = _bullets(b), detect_slide_type(h, b)
            ch = _chart(h, k) if st == "chart" else None
            tb = _table(k[:4]) if st in ("comparison", "table") else None
            sl.append(SlideBlueprint(i, st, h[:120], bts, _notes(h, bts), ch, tb))
        sl.append(SlideBlueprint(len(sl), "content", "Conclusions", [f"Top finding: {x.title()}" for x in k[:4]], speaker_notes="Review conclusions and open floor for questions."))
        return DeckBlueprint(fl, t[:200], sl, k, flesch_kincaid_grade(t))