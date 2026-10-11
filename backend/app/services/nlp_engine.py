"""NLP Engine: deterministic outline decomposition, topic categorization, and keyword extraction."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal

SlideType = Literal["title", "content", "kpi", "chart", "table", "comparison", "process"]

@dataclass
class SlideBlueprint:
    position: int
    slide_type: SlideType
    title: str
    bullets: list[str] = field(default_factory=list)
    speaker_notes: str = ""
    chart_data: dict | None = None
    table_data: dict | None = None
    layout_config: dict = field(default_factory=dict)

@dataclass
class DeckBlueprint:
    title: str
    topic: str
    slides: list[SlideBlueprint] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    reading_level: float = 0.0

_STOP_WORDS = frozenset(
    "a an the and or but in on at to for of with by from is are was were be been being have has had do does did will would could should may might this that these those it its we they he she you your our their his her s t can also all as not more most such like just into through than over after about up out so if no only other which while when how what where who whom then both either each every few some many very too same here there".split()
)

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z0-9'\-]*[a-z0-9]|[a-z]", text.lower())

def extract_keywords(text: str, top_k: int = 15) -> list[str]:
    freq: dict[str, int] = {}
    for tok in _tokenize(text):
        if tok not in _STOP_WORDS and len(tok) > 3:
            freq[tok] = freq.get(tok, 0) + 1
    return [t for t, _ in sorted(freq.items(), key=lambda x: -x[1])[:top_k]]

def _count_syllables(word: str) -> int:
    w = word.lower().strip(".,;:!?\"'")
    vowels = re.findall(r"[aeiou]", w)
    if w.endswith("e") and len(w) > 2:
        vowels = vowels[:-1]
    return max(1, len(vowels))

def flesch_kincaid_grade(text: str) -> float:
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    words = _tokenize(text)
    if not sentences or not words:
        return 0.0
    asl, asw = len(words) / len(sentences), sum(_count_syllables(w) for w in words) / len(words)
    return round(max(0.0, 0.39 * asl + 11.8 * asw - 15.59), 2)

_KPI_PATTERNS = [re.compile(r"\b\d+[\.,]?\d*\s*(?:%|percent|x|times|billion|million|k|ms|s|fps|gb|mb)\b", re.I), re.compile(r"\b(?:metric|kpi|roi|cagr|conversion|retention|churn|latency|throughput)\b", re.I)]
_CHART_PATTERNS = [re.compile(r"\b(?:chart|graph|trend|over time|growth|distribution|percentage)\b", re.I)]
_TABLE_PATTERNS = [re.compile(r"\b(?:compare|comparison|versus|vs\.?|table|matrix|rows|columns)\b", re.I)]
_PROCESS_PATTERNS = [re.compile(r"\b(?:step\s*\d+|phase\s*\d+|stage|pipeline|workflow|process|flow)\b", re.I)]

def detect_slide_type(title: str, body: str) -> SlideType:
    comb = f"{title} {body}"
    kpis = sum(1 for p in _KPI_PATTERNS if p.search(comb))
    charts = sum(1 for p in _CHART_PATTERNS if p.search(comb))
    tables = sum(1 for p in _TABLE_PATTERNS if p.search(comb))
    proc = sum(1 for p in _PROCESS_PATTERNS if p.search(comb))
    if kpis >= 2: return "kpi"
    if charts >= 1 and kpis >= 1: return "chart"
    if tables >= 1: return "comparison"
    if proc >= 1: return "process"
    return "content"

def _split_into_sections(text: str) -> list[tuple[str, str]]:
    heading_re = re.compile(r"^(?:#{1,3}\s+|(?=[A-Z][A-Z\s]{4,}$))(.*)", re.MULTILINE)
    matches = list(heading_re.finditer(text))
    if not matches:
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return [(p.split(".")[0][:80], p) for p in paras]
    sections = []
    for i, m in enumerate(matches):
        heading = m.group(1).strip() if m.group(1).strip() else m.group(0).strip("# ").strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        if heading:
            sections.append((heading[:120], text[start:end].strip()))
    return sections

def _extract_bullets(body: str, max_bullets: int = 6) -> list[str]:
    bullets = [m.group(1).strip() for m in re.compile(r"^[\*\-•]\s+(.+)", re.MULTILINE).finditer(body)]
    if not bullets:
        bullets = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if 10 < len(s.strip()) < 200]
    return bullets[:max_bullets]

def _synthesize_speaker_notes(title: str, bullets: list[str]) -> str:
    if not bullets:
        return f"Discuss {title.lower()} with the audience."
    notes = f'In this slide on "{title}", key points include: ' + "; ".join(bullets[:3]) + "."
    if len(bullets) > 3:
        notes += f" Additional considerations: {'; '.join(bullets[3:])}."
    return notes[:800]

def _make_sample_chart_data(title: str, keywords: list[str]) -> dict:
    cats = keywords[:5] if keywords else ["Category A", "Category B", "Category C"]
    def _val(label: str, seed: str) -> float:
        h = int(hashlib.md5(f"{label}:{seed}".encode()).hexdigest(), 16)
        return round(20.0 + (h % 800) / 10.0, 1)
    return {"chart_type": "bar", "title": title, "categories": cats, "series": [{"name": "Value", "values": [_val(c, title) for c in cats]}]}

def _make_sample_table_data(columns: list[str], rows_count: int = 4) -> dict:
    headers = columns[:4] if columns else ["Criterion", "Option A", "Option B", "Option C"]
    criteria = ["Performance", "Cost", "Scalability", "Reliability"]
    ratings = ["High", "Medium", "Low", "Very High", "Excellent"]
    rows = []
    for i in range(min(rows_count, len(criteria))):
        row = [criteria[i]]
        for j in range(len(headers) - 1):
            h = int(hashlib.md5(f"{criteria[i]}:{headers[j+1]}".encode()).hexdigest(), 16)
            row.append(ratings[h % len(ratings)])
        rows.append(row)
    return {"headers": headers, "rows": rows}

class NLPEngine:
    """Deterministic document and topic to slide outline engine."""

    def decompose_topic(self, topic: str, slide_count: int = 8) -> DeckBlueprint:
        keywords = extract_keywords(topic, top_k=15)
        reading_level = flesch_kincaid_grade(topic)
        slides = [SlideBlueprint(position=0, slide_type="title", title=topic[:100], speaker_notes=f"Welcome. Today we explore: {topic[:200]}")]
        for i, kw in enumerate(keywords[:min(slide_count - 2, 8)], start=1):
            stype = detect_slide_type(kw, f"Analysis of {kw}")
            bullets = [f"Key insight {j + 1} about {kw}" for j in range(3)]
            chart = _make_sample_chart_data(kw, keywords) if stype == "chart" else None
            table = _make_sample_table_data(keywords) if stype in ("comparison", "table") else None
            slides.append(SlideBlueprint(position=i, slide_type=stype, title=kw.title(), bullets=bullets, speaker_notes=_synthesize_speaker_notes(kw.title(), bullets), chart_data=chart, table_data=table))
        slides.append(SlideBlueprint(position=len(slides), slide_type="content", title="Summary & Next Steps", bullets=[f"Key takeaway: {keywords[0].title() if keywords else topic[:30]}", "Validate findings with data", "Schedule follow-up review"], speaker_notes="Summarize findings and agree on next steps."))
        return DeckBlueprint(title=topic[:100], topic=topic, slides=slides, keywords=keywords, reading_level=reading_level)

    def decompose_document(self, text: str, slide_count: int = 10) -> DeckBlueprint:
        keywords = extract_keywords(text, top_k=20)
        reading_level = flesch_kincaid_grade(text)
        sections = _split_into_sections(text)
        first_line = text.strip().split("\n")[0][:120] or "Presentation"
        slides = [SlideBlueprint(position=0, slide_type="title", title=first_line, speaker_notes=f"This presentation covers: {first_line}")]
        for i, (heading, body) in enumerate(sections[:slide_count - 2], start=1):
            bullets = _extract_bullets(body)
            stype = detect_slide_type(heading, body)
            chart = _make_sample_chart_data(heading, keywords) if stype == "chart" else None
            table = _make_sample_table_data(keywords[:4]) if stype in ("comparison", "table") else None
            slides.append(SlideBlueprint(position=i, slide_type=stype, title=heading[:120], bullets=bullets, speaker_notes=_synthesize_speaker_notes(heading, bullets), chart_data=chart, table_data=table))
        slides.append(SlideBlueprint(position=len(slides), slide_type="content", title="Conclusions", bullets=[f"Top finding: {kw.title()}" for kw in keywords[:4]], speaker_notes="Review conclusions and open floor for questions."))
        return DeckBlueprint(title=first_line, topic=text[:200], slides=slides, keywords=keywords, reading_level=reading_level)