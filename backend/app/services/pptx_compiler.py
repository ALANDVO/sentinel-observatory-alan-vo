"""Native PPTX compiler: shapes, transitions, animations, speaker notes, tables, charts, templates."""
from __future__ import annotations
import io
from pathlib import Path
from typing import Any
from pptx import Presentation
from pptx.chart.data import ChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml import parse_xml
from pptx.util import Inches as _in, Pt
from backend.app.services.layout_engine import SlideLayoutEngine
SLIDE_WIDTH, SLIDE_HEIGHT = _in(13.33), _in(7.5)
COLOR_TITLE, COLOR_TEXT, COLOR_HIGHLIGHT = RGBColor(26, 26, 46), RGBColor(45, 45, 45), RGBColor(15, 60, 120)
CHART_MAP = {"line": XL_CHART_TYPE.LINE, "bar": XL_CHART_TYPE.BAR_CLUSTERED, "pie": XL_CHART_TYPE.PIE, "area": XL_CHART_TYPE.AREA, "doughnut": XL_CHART_TYPE.DOUGHNUT}
_XMLNS = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
_LE = SlideLayoutEngine()
def _apply_slide_transition(slide: Any, transition_type: str = "fade", speed: str = "med") -> None:
    t = transition_type if transition_type in {"fade", "push", "wipe", "cut", "zoom", "cover", "split"} else "fade"
    slide._element.append(parse_xml(f'<p:transition {_XMLNS} spd="{speed}" advClick="1"><p:{t}/></p:transition>'))
def _apply_slide_animations(slide: Any, shape_ids: list[int] | None = None, effect: str = "appear") -> None:
    slide._element.append(parse_xml(f'<p:timing {_XMLNS}><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="always" nodeType="tmRoot"/></p:par></p:tnLst></p:timing>'))
def _add_text_box(slide: Any, text: str, left: Any, top: Any, width: Any, height: Any, font_size: int = 18, bold: bool = False, color: RGBColor = COLOR_TEXT, align: Any = PP_ALIGN.LEFT) -> Any:
    tx = slide.shapes.add_textbox(left, top, width, height)
    p = tx.text_frame.paragraphs[0]; p.alignment = align
    run = p.add_run(); run.text = text
    run.font.size, run.font.bold, run.font.color.rgb = Pt(font_size), bold, color
    return tx
def _set_notes(slide: Any, slide_data: dict[str, Any]) -> None:
    if notes := slide_data.get("speaker_notes", ""): slide.notes_slide.notes_text_frame.text = notes
def _make_slide(prs: Presentation, layout_idx: int, slide_data: dict[str, Any]) -> Any:
    slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
    if title := slide_data.get("title", ""):
        if slide.shapes.title: slide.shapes.title.text = title
        else: _add_text_box(slide, title, _in(1.0), _in(0.5), _in(12.0), _in(1.0), 24, True, COLOR_TITLE)
    return slide
def _finish(s: Any, d: dict[str, Any], trans: str = "wipe", anim: str = "wipe", shape_ids: list[int] | None = None) -> None:
    _set_notes(s, d); _apply_slide_transition(s, trans); _apply_slide_animations(s, shape_ids, effect=anim)
def _compile_title_slide(prs: Presentation, d: dict[str, Any]) -> None:
    _finish(_make_slide(prs, 0, d), d, "fade", "fade")
def _compile_content_slide(prs: Presentation, d: dict[str, Any]) -> None:
    layout, s, body = _LE.compute_slide_layout(d), _make_slide(prs, 1, d), d.get("body_text", "")
    if layout.columns.count > 1 and body:
        lines = [l.strip() for l in body.split("\n") if l.strip()]; pc = max(1, -(-len(lines) // layout.columns.count))
        for ci, cb in enumerate(layout.columns.column_boxes):
            if cl := lines[ci * pc:(ci + 1) * pc]: _add_text_box(s, "\n".join(cl), _in(cb.left), _in(cb.top), _in(cb.width), _in(cb.height), layout.typography.body_pt, False, COLOR_TEXT)
    elif len(s.shapes.placeholders) > 1 and body: s.shapes.placeholders[1].text = body
    _finish(s, d, "wipe", "wipe")
def _compile_chart_slide(prs: Presentation, d: dict[str, Any]) -> None:
    cb, s, cd = _LE.compute_slide_layout(d).content_box, _make_slide(prs, 5, d), d.get("chart_data") or {}
    ct = CHART_MAP.get(str(cd.get("chart_type", "bar")).lower(), XL_CHART_TYPE.BAR_CLUSTERED)
    cdata = ChartData(); cdata.categories = cd.get("categories", ["Cat 1", "Cat 2"])
    for series in cd.get("series", []): cdata.add_series(series.get("name", "Series"), tuple(series.get("values", [])))
    if not cd.get("series") and cd.get("data"): cdata.add_series("Series", tuple(v for _, v in cd.get("data", [])))
    cs = s.shapes.add_chart(ct, _in(cb.left), _in(cb.top), _in(cb.width), _in(cb.height), cdata)
    _finish(s, d, "zoom", "zoom", [cs.shape_id])
def _compile_table_slide(prs: Presentation, d: dict[str, Any]) -> None:
    cb, s, td = _LE.compute_slide_layout(d).content_box, _make_slide(prs, 5, d), d.get("table_data") or {}
    headers, rows = td.get("headers", []), td.get("rows", [])
    ts = s.shapes.add_table(len(rows) + (1 if headers else 0), max(1, len(headers)), _in(cb.left), _in(cb.top), _in(cb.width), _in(cb.height))
    for ci, h in enumerate(headers): ts.table.cell(0, ci).text = str(h)
    for ri, r in enumerate(rows, start=1 if headers else 0):
        for ci, val in enumerate(r): ts.table.cell(ri, ci).text = str(val if val is not None else "")
    _finish(s, d, "wipe", "wipe", [ts.shape_id])
def _compile_kpi_slide(prs: Presentation, d: dict[str, Any]) -> None:
    layout, s = _LE.compute_slide_layout(d), _make_slide(prs, 5, d)
    bullets = d.get("bullets") or d.get("kpi", {}).get("bullets", [])
    if len(s.shapes.placeholders) > 1 and d.get("kpi", {}).get("label"): s.shapes.placeholders[1].text = d["kpi"]["label"]
    ih, gap, pc = layout.extras.get("item_height_in", 0.7), layout.extras.get("row_gap_in", 0.15), max(1, -(-len(bullets) // max(1, layout.columns.count)))
    for ci, col_box in enumerate(layout.columns.column_boxes):
        for ri, b in enumerate(bullets[ci * pc:(ci + 1) * pc]):
            _add_text_box(s, b, _in(col_box.left), _in(col_box.top + ri * (ih + gap)), _in(col_box.width), _in(ih), layout.typography.body_pt, True, COLOR_TEXT)
    _finish(s, d, "appear", "appear")
def _compile_comparison_slide(prs: Presentation, d: dict[str, Any]) -> None:
    layout, s, cmp = _LE.compute_slide_layout(d), _make_slide(prs, 5, d), d.get("comparison") or {}
    if layout.columns.count == 2 and len(layout.columns.column_boxes) == 2:
        lb, rb, bpt = layout.columns.column_boxes[0], layout.columns.column_boxes[1], layout.typography.body_pt
        for pfx, box, clr in (("left", lb, COLOR_TITLE), ("right", rb, COLOR_HIGHLIGHT)):
            if t := cmp.get(f"{pfx}_title"): _add_text_box(s, t, _in(box.left), _in(box.top), _in(box.width), _in(0.5), bpt + 2, True, clr)
            if b := cmp.get(f"{pfx}_body"): _add_text_box(s, b, _in(box.left), _in(box.top + 0.6), _in(box.width), _in(box.height - 0.6), bpt, False, COLOR_TEXT)
    elif len(s.shapes.placeholders) > 1 and cmp.get("left_title"): s.shapes.placeholders[1].text = str(cmp["left_title"])
    _finish(s, d, "wipe", "wipe")
def _compile_process_slide(prs: Presentation, d: dict[str, Any]) -> None:
    s = _make_slide(prs, 1, d)
    if len(s.shapes.placeholders) > 1 and d.get("process", {}).get("steps"): s.shapes.placeholders[1].text = str(d["process"]["steps"])
    _finish(s, d, "push", "push")
_COMPILERS = {"title": _compile_title_slide, "content": _compile_content_slide, "chart": _compile_chart_slide, "table": _compile_table_slide, "kpi": _compile_kpi_slide, "comparison": _compile_comparison_slide, "process": _compile_process_slide}
class PptxCompiler:
    def compile_deck(self, deck_title: str, slides: list[dict[str, Any]], template_bytes: bytes | None = None, template_path: str | None = None) -> bytes:
        if template_bytes: prs = Presentation(io.BytesIO(template_bytes))
        elif template_path and Path(template_path).is_file(): prs = Presentation(template_path)
        else:
            prs = Presentation(); prs.slide_width, prs.slide_height = SLIDE_WIDTH, SLIDE_HEIGHT
        for s in slides: _COMPILERS.get(s.get("slide_type", "content"), _compile_content_slide)(prs, s)
        out = io.BytesIO(); prs.save(out); return out.getvalue()