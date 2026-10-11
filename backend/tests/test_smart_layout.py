"""Tests for the SlideLayoutEngine: bounding boxes, typography scaling, column layouts, and API."""
from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient
from pptx import Presentation

from backend.app.services.layout_engine import (
    SlideLayoutEngine,
    SlideLayout,
    BoundingBox,
    TypographySpec,
    ColumnLayout,
    _density_class,
    _scale_font,
    _column_boxes,
    _split_columns,
    SLIDE_W,
    SLIDE_H,
    _CONTENT_W,
    _CONTENT_H,
)
from backend.app.services.pptx_compiler import PptxCompiler


@pytest.fixture
def layout_engine_fixture() -> SlideLayoutEngine:
    return SlideLayoutEngine()


@pytest.fixture
def pptx_compiler_fixture() -> PptxCompiler:
    return PptxCompiler()


# ── Unit: density classification ─────────────────────────────────────────────

def test_density_sparse():
    assert _density_class(0) == "sparse"
    assert _density_class(20) == "sparse"
    assert _density_class(39) == "sparse"


def test_density_medium():
    assert _density_class(40) == "medium"
    assert _density_class(80) == "medium"
    assert _density_class(99) == "medium"


def test_density_dense():
    assert _density_class(100) == "dense"
    assert _density_class(500) == "dense"


# ── Unit: font scaling ────────────────────────────────────────────────────────

def test_scale_font_clamps_to_min():
    # Very high word count should produce minimum font size
    result = _scale_font(18, 2000, 12, 28)
    assert result == 12


def test_scale_font_clamps_to_max():
    # Zero word count should produce maximum font size
    result = _scale_font(18, 0, 12, 28)
    assert result == 28


def test_scale_font_decreases_monotonically():
    sizes = [_scale_font(18, w, 12, 28) for w in [0, 40, 80, 120, 200, 400]]
    assert sizes == sorted(sizes, reverse=True), "Font size must decrease as word count grows"


def test_scale_font_bounds_are_respected():
    for word_count in [0, 10, 50, 100, 200, 500, 1000]:
        pt = _scale_font(18, word_count, 12, 28)
        assert 12 <= pt <= 28, f"Font size {pt} out of bounds for word_count={word_count}"


# ── Unit: column computation ──────────────────────────────────────────────────

def test_split_columns_single():
    assert _split_columns(0) == 1
    assert _split_columns(3) == 1


def test_split_columns_two():
    assert _split_columns(4) == 2
    assert _split_columns(6) == 2


def test_split_columns_three():
    assert _split_columns(7) == 3
    assert _split_columns(20) == 3


def test_column_boxes_single_fills_content_width():
    boxes = _column_boxes(1)
    assert len(boxes) == 1
    assert abs(boxes[0].width - _CONTENT_W) < 0.01


def test_column_boxes_two_equal_widths():
    boxes = _column_boxes(2, gutter=0.25)
    assert len(boxes) == 2
    assert abs(boxes[0].width - boxes[1].width) < 0.01
    # Right box starts after left box + gutter
    assert abs(boxes[1].left - (boxes[0].left + boxes[0].width + 0.25)) < 0.01


def test_column_boxes_total_width_matches_content():
    for n in [1, 2, 3]:
        boxes = _column_boxes(n, gutter=0.25)
        total = sum(b.width for b in boxes) + 0.25 * (n - 1)
        assert abs(total - _CONTENT_W) < 0.02, f"Total width mismatch for {n} columns"


def test_column_boxes_no_overlap():
    boxes = _column_boxes(3, gutter=0.25)
    for i in range(len(boxes) - 1):
        assert boxes[i].left + boxes[i].width <= boxes[i + 1].left + 0.001


# ── Unit: per-slide-type layout ───────────────────────────────────────────────

def test_layout_title_sparse():
    layout = SlideLayoutEngine().compute_slide_layout({"slide_type": "title", "title": "AI Safety"})
    assert layout.slide_type == "title"
    assert layout.density_class == "sparse"
    assert layout.typography.title_pt >= 20
    assert layout.columns.count == 1
    assert "subtitle_box" in layout.extras


def test_layout_content_dense_uses_two_columns():
    # 8 bullet lines → should trigger 2-column layout
    body = "\n".join([f"Bullet point number {i} with extended description text" for i in range(8)])
    layout = SlideLayoutEngine().compute_slide_layout({"slide_type": "content", "title": "Methods", "body_text": body})
    assert layout.columns.count >= 2
    assert layout.typography.body_pt <= 24  # font should be reduced for dense content


def test_layout_content_sparse_single_column():
    layout = SlideLayoutEngine().compute_slide_layout({"slide_type": "content", "title": "Intro", "body_text": "A short intro."})
    assert layout.columns.count == 1
    assert layout.typography.body_pt >= 18  # larger font for sparse content


def test_layout_kpi_many_bullets_multi_column():
    layout = SlideLayoutEngine().compute_slide_layout({
        "slide_type": "kpi", "title": "KPIs",
        "bullets": ["A: 99%", "B: 88%", "C: 77%", "D: 66%", "E: 55%", "F: 44%", "G: 33%"],
    })
    assert layout.columns.count >= 2
    assert layout.extras["item_count"] == 7
    assert layout.extras["item_height_in"] > 0


def test_layout_comparison_proportional_widths():
    data = {
        "slide_type": "comparison",
        "title": "Comparison",
        "comparison": {
            "left_title": "Option A",
            "left_body": "Short left body",
            "right_title": "Option B — a much longer description with extended analysis",
            "right_body": "Extended right side with lots of detailed explanation " * 5,
        },
    }
    layout = SlideLayoutEngine().compute_slide_layout(data)
    assert layout.columns.count == 2
    left_ratio = layout.extras["left_ratio"]
    right_ratio = layout.extras["right_ratio"]
    # Right has far more words → right column should be wider
    assert right_ratio > left_ratio
    assert abs(left_ratio + right_ratio - 1.0) < 0.001


def test_layout_comparison_equal_content_near_equal_split():
    data = {
        "slide_type": "comparison",
        "comparison": {"left_title": "Alpha", "left_body": "a b c d e", "right_title": "Beta", "right_body": "f g h i j"},
    }
    layout = SlideLayoutEngine().compute_slide_layout(data)
    assert abs(layout.extras["left_ratio"] - 0.5) < 0.15


def test_layout_chart_has_legend_flag():
    multi_series = {"slide_type": "chart", "title": "Multi", "chart_data": {"categories": ["X", "Y"], "series": [{"name": "A", "values": [1, 2]}, {"name": "B", "values": [3, 4]}]}}
    layout = SlideLayoutEngine().compute_slide_layout(multi_series)
    assert layout.extras["has_legend"] is True
    assert layout.extras["n_series"] == 2

    single_series = {"slide_type": "chart", "title": "Single", "chart_data": {"categories": ["X"], "series": [{"name": "A", "values": [1]}]}}
    layout2 = SlideLayoutEngine().compute_slide_layout(single_series)
    assert layout2.extras["has_legend"] is False


def test_layout_table_font_scales_with_columns():
    narrow = {"slide_type": "table", "title": "T", "table_data": {"headers": ["A", "B"], "rows": [["x", "y"]]}}
    wide = {"slide_type": "table", "title": "T", "table_data": {"headers": ["A", "B", "C", "D", "E", "F"], "rows": [["x"] * 6]}}
    narrow_layout = SlideLayoutEngine().compute_slide_layout(narrow)
    wide_layout = SlideLayoutEngine().compute_slide_layout(wide)
    assert narrow_layout.typography.body_pt >= wide_layout.typography.body_pt


def test_layout_process_horizontal_flow():
    layout = SlideLayoutEngine().compute_slide_layout({
        "slide_type": "process",
        "process": {"steps": ["Step 1", "Step 2", "Step 3", "Step 4"]},
    })
    assert layout.extras["flow_direction"] == "horizontal"
    assert layout.columns.count == 4
    assert layout.extras["step_count"] == 4


# ── Unit: as_dict serialization ───────────────────────────────────────────────

def test_bounding_box_as_dict():
    bb = BoundingBox(1.0, 2.0, 10.0, 5.0)
    d = bb.as_dict()
    assert d == {"left": 1.0, "top": 2.0, "width": 10.0, "height": 5.0}


def test_slide_layout_as_dict_complete(layout_engine_fixture: SlideLayoutEngine):
    layout = layout_engine_fixture.compute_slide_layout({"slide_type": "content", "title": "Test", "body_text": "hello world"})
    d = layout.as_dict()
    assert "slide_type" in d
    assert "density_class" in d
    assert "typography" in d
    assert "content_box" in d
    assert "columns" in d
    for key in ("title_pt", "body_pt", "caption_pt"):
        assert key in d["typography"]
    for key in ("left", "top", "width", "height"):
        assert key in d["content_box"]


# ── Unit: deck summary ────────────────────────────────────────────────────────

def test_layout_summary_structure(layout_engine_fixture: SlideLayoutEngine):
    slides = [
        {"id": "s1", "position": 0, "slide_type": "title", "title": "Intro", "body_text": None},
        {"id": "s2", "position": 1, "slide_type": "content", "title": "Methods", "body_text": "A\nB\nC\nD\nE\nF\nG\nH"},
        {"id": "s3", "position": 2, "slide_type": "kpi", "title": "KPIs", "bullets": ["M1", "M2", "M3"]},
        {"id": "s4", "position": 3, "slide_type": "chart", "title": "Chart", "chart_data": {"categories": ["X"], "series": [{"name": "S", "values": [1]}]}},
    ]
    summary = layout_engine_fixture.layout_summary(slides)
    assert summary["slide_count"] == 4
    assert "density_distribution" in summary
    assert "column_distribution" in summary
    assert "avg_body_font_pt" in summary
    assert len(summary["layouts"]) == 4
    assert isinstance(summary["avg_body_font_pt"], float)


def test_layout_summary_density_sums_to_slide_count(layout_engine_fixture: SlideLayoutEngine):
    slides = [{"id": str(i), "position": i, "slide_type": "content", "title": "T", "body_text": "x " * (i * 20)} for i in range(5)]
    summary = layout_engine_fixture.layout_summary(slides)
    total_density = sum(summary["density_distribution"].values())
    assert total_density == 5


# ── Integration: PPTX compiler uses layout engine ────────────────────────────

def test_content_slide_dense_uses_column_textboxes(pptx_compiler_fixture: PptxCompiler):
    """Dense content slide should produce multiple textbox shapes (column layout)."""
    body = "\n".join([f"Bullet {i}: extended technical description of component" for i in range(8)])
    slides = [{"slide_type": "content", "title": "Architecture", "body_text": body}]
    pptx_bytes = pptx_compiler_fixture.compile_deck("Test", slides)
    prs = Presentation(io.BytesIO(pptx_bytes))
    slide = prs.slides[0]
    # With 8 bullets, layout engine triggers 2+ columns → multiple text boxes added
    text_shapes = [s for s in slide.shapes if s.has_text_frame]
    assert len(text_shapes) >= 2


def test_kpi_slide_multi_column_layout(pptx_compiler_fixture: PptxCompiler):
    """KPI slides with many bullets use column layout from the layout engine."""
    slides = [{"slide_type": "kpi", "title": "KPIs", "bullets": ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]}]
    pptx_bytes = pptx_compiler_fixture.compile_deck("KPIs", slides)
    prs = Presentation(io.BytesIO(pptx_bytes))
    slide = prs.slides[0]
    text_shapes = [s for s in slide.shapes if s.has_text_frame]
    # At least as many text boxes as KPI bullets
    assert len(text_shapes) >= 7


def test_comparison_slide_two_column_text_boxes(pptx_compiler_fixture: PptxCompiler):
    """Comparison slides emit left/right column text boxes via layout engine."""
    slides = [{
        "slide_type": "comparison", "title": "Side by Side",
        "comparison": {
            "left_title": "Approach A", "left_body": "Fast but less accurate.",
            "right_title": "Approach B", "right_body": "Slower but more precise.",
        },
    }]
    pptx_bytes = pptx_compiler_fixture.compile_deck("Compare", slides)
    prs = Presentation(io.BytesIO(pptx_bytes))
    slide = prs.slides[0]
    text_shapes = [s for s in slide.shapes if s.has_text_frame]
    # Title + 2 col titles + 2 col bodies = 5 shapes minimum
    assert len(text_shapes) >= 4


# ── API endpoint: /api/decks/{id}/layout ──────────────────────────────────────

def test_get_deck_layout_api_success(client: TestClient):
    create_resp = client.post("/api/decks/generate/topic", json={"topic": "AI Safety Evaluation Benchmarks", "slide_count": 5})
    assert create_resp.status_code == 201
    deck_id = create_resp.json()["id"]

    layout_resp = client.get(f"/api/decks/{deck_id}/layout")
    assert layout_resp.status_code == 200
    data = layout_resp.json()
    assert data["slide_count"] >= 3
    assert "density_distribution" in data
    assert "column_distribution" in data
    assert "avg_body_font_pt" in data
    assert len(data["layouts"]) == data["slide_count"]
    # Each layout must have required keys
    for lay in data["layouts"]:
        assert "slide_type" in lay
        assert "density_class" in lay
        assert lay["density_class"] in ("sparse", "medium", "dense")
        assert "typography" in lay
        assert "content_box" in lay
        assert "columns" in lay


def test_get_deck_layout_api_404(client: TestClient):
    resp = client.get("/api/decks/00000000-0000-0000-0000-000000000000/layout")
    assert resp.status_code == 404


def test_deck_layout_unauthenticated(client: TestClient, monkeypatch):
    """Layout endpoint requires auth; unauthenticated requests are rejected when demo mode off."""
    monkeypatch.setenv("DEMO_MODE", "false")
    resp = client.get("/api/decks/any-deck-id/layout")
    assert resp.status_code in (401, 403)
