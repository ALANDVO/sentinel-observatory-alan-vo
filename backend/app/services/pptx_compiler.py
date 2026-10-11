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
from pptx.util import Inches, Pt

SLIDE_WIDTH = Inches(13.33)
SLIDE_HEIGHT = Inches(7.5)
COLOR_TITLE = RGBColor(0x1A, 0x1A, 0x2E)
COLOR_TEXT = RGBColor(0x2D, 0x2D, 0x2D)
COLOR_HIGHLIGHT = RGBColor(0x0F, 0x3C, 0x78)
CHART_MAP = {
    "line": XL_CHART_TYPE.LINE, "bar": XL_CHART_TYPE.BAR_CLUSTERED,
    "pie": XL_CHART_TYPE.PIE, "area": XL_CHART_TYPE.AREA, "doughnut": XL_CHART_TYPE.DOUGHNUT,
}

def _apply_slide_transition(slide, transition_type: str = "fade", speed: str = "med") -> None:
    valid = {"fade", "push", "wipe", "cut", "zoom", "cover", "split"}
    t = transition_type if transition_type in valid else "fade"
    slide._element.append(parse_xml(
        f'<p:transition xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" spd="{speed}" advClick="1"><p:{t}/></p:transition>'
    ))

def _apply_slide_animations(slide, shape_ids: list[int] | None = None, effect: str = "appear") -> None:
    if effect not in {"appear", "fade", "wipe", "slide", "zoom", "fade-through"}:
        effect = "appear"
    slide._element.append(parse_xml(
        '<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="always" nodeType="tmRoot"/>'
        "</p:par></p:tnLst></p:timing>"
    ))

def _add_text_box(slide, text: str, left, top, width, height, font_size: int, bold: bool = False, color: RGBColor = COLOR_TEXT, align=PP_ALIGN.LEFT):
    tx = slide.shapes.add_textbox(left, top, width, height)
    frame = tx.text_frame
    frame.clear()
    p = frame.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    p.alignment = align
    return tx

def _set_notes(slide, slide_data: dict[str, Any]) -> None:
    notes = slide_data.get("speaker_notes", "")
    if notes:
        slide.notes_slide.notes_text_frame.text = notes

def _make_slide(prs: Presentation, layout_idx: int, slide_data: dict[str, Any]):
    slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
    title = slide_data.get("title", "")
    if title:
        if slide.shapes.title:
            slide.shapes.title.text = title
        else:
            _add_text_box(slide, title, Inches(1.0), Inches(0.5), Inches(12.0), Inches(1.0), 24, True, COLOR_TITLE)
    return slide

def _compile_title_slide(prs: Presentation, slide_data: dict[str, Any]) -> None:
    slide = _make_slide(prs, 0, slide_data)
    _set_notes(slide, slide_data)
    _apply_slide_transition(slide, "fade")
    _apply_slide_animations(slide, effect="fade")

def _body_text_lines(slide, slide_data: dict[str, Any]) -> None:
    body = slide.shapes.placeholders[1] if len(slide.shapes.placeholders) > 1 else None
    if body:
        for run in body.text_frame.runs:
            run.font.color.rgb = COLOR_TEXT
    else:
        slide.shapes.add_textbox(Inches(0.5), Inches(3.0), Inches(12.0), Inches(1.0)).text_frame.text = slide_data.get("title", "")

def _compile_content_slide(prs: Presentation, slide_data: dict[str, Any]) -> None:
    slide = _make_slide(prs, 1, slide_data)
    _body_text_lines(slide, slide_data)
    _set_notes(slide, slide_data)
    _apply_slide_transition(slide, "wipe")
    _apply_slide_animations(slide, effect="wipe")

def _compile_chart_slide(prs: Presentation, slide_data: dict[str, Any]) -> None:
    slide = _make_slide(prs, 5, slide_data)
    cd = slide_data.get("chart_data", {}) or {}
    ct = CHART_MAP.get(str(cd.get("chart_type", "column")).lower(), XL_CHART_TYPE.COLUMN_CLUSTERED)
    chart_data = ChartData()
    for lbl, val in cd.get("data", []):
        chart_data.add_data_point(lbl, val)
    chart_data.categories = cd.get("categories", [])
    chart_data.categories_title = cd.get("categories_title", "")
    cs = slide.shapes.add_chart(ct, Inches(1.0), Inches(1.5), Inches(11.0), Inches(4.5), chart_data)
    _apply_slide_animations(slide, [cs.shape_id], effect="zoom")

def _compile_table_slide(prs: Presentation, slide_data: dict[str, Any]) -> None:
    slide = _make_slide(prs, 5, slide_data)
    td = slide_data.get("table_data", {}) or {}
    ts = slide.shapes.add_table(1, len(td.get("headers", [])), Inches(0.5), Inches(1.5), Inches(12.0), Inches(3.0), td.get("data", []))
    _apply_slide_animations(slide, [ts.shape_id], effect="wipe")

def _compile_kpi_slide(prs: Presentation, slide_data: dict[str, Any]) -> None:
    slide = _make_slide(prs, 5, slide_data)
    kpi = slide_data.get("kpi", {}) or {}
    title = slide.shapes.title
    body = slide.shapes.placeholders[1] if len(slide.shapes.placeholders) > 1 else None
    if body:
        body.text = kpi.get("label", "")
    _apply_slide_animations(slide, effect="appear")

def _compile_comparison_slide(prs: Presentation, slide_data: dict[str, Any]) -> None:
    slide = _make_slide(prs, 1, slide_data)
    comp = slide_data.get("comparison", {}) or {}
    title1 = slide.shapes.title
    title2 = slide.shapes.placeholders[1] if len(slide.shapes.placeholders) > 1 else None
    if title2: title2.text = comp.get("left_title", "")
    _apply_slide_animations(slide, effect="wipe")

def _compile_process_slide(prs: Presentation, slide_data: dict[str, Any]) -> None:
    slide = _make_slide(prs, 1, slide_data)
    proc = slide_data.get("process", {}) or {}
    title = slide.shapes.title
    body = slide.shapes.placeholders[1] if len(slide.shapes.placeholders) > 1 else None
    if body: body.text = proc.get("steps", "")
    _apply_slide_animations(slide, effect="push")

_SLIDE_COMPILERS: dict[str, Any] = {
    "title": _compile_title_slide,
    "content": _compile_content_slide,
    "chart": _compile_chart_slide,
    "table": _compile_table_slide,
    "kpi": _compile_kpi_slide,
    "comparison": _compile_comparison_slide,
    "process": _compile_process_slide,
}

class PptxCompiler:
    def compile_deck(self, deck_title: str, slides: list[dict[str, Any]], template_bytes: bytes | None = None, template_path: str | None = None) -> bytes:
        if template_bytes:
            from pptx import Presentation
            prs = Presentation(io.BytesIO(template_bytes))
        elif template_path and Path(template_path).is_file():
            from pptx import Presentation
            prs = Presentation(template_path)
        else:
            from pptx import Presentation
            prs = Presentation()
            prs.slide_width = SLIDE_WIDTH
            prs.slide_height = SLIDE_HEIGHT
        for slide_data in slides:
            _SLIDE_COMPILERS.get(slide_data.get("slide_type", "content"), _compile_content_slide)(prs, slide_data)
        output = io.BytesIO()
        prs.save(output)
        return output.getvalue()