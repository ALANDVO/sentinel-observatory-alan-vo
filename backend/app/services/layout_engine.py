from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any
SLIDE_W, SLIDE_H = 13.33, 7.5
_CL, _CR, _CT, _CB = 0.5, 12.83, 1.6, 7.1
_CONTENT_W, _CONTENT_H = _CR - _CL, _CB - _CT
_F_MIN, _F_MAX, _FT_MIN, _FT_MAX = 12, 28, 20, 36
@dataclass
class BoundingBox:
    left: float; top: float; width: float; height: float
    def as_dict(self) -> dict[str, float]: return {"left": self.left, "top": self.top, "width": self.width, "height": self.height}
@dataclass
class TypographySpec:
    title_pt: int; body_pt: int; caption_pt: int = 12
    def as_dict(self) -> dict[str, int]: return {"title_pt": self.title_pt, "body_pt": self.body_pt, "caption_pt": self.caption_pt}
@dataclass
class ColumnLayout:
    count: int; column_boxes: list[BoundingBox] = field(default_factory=list); gutter: float = 0.25
    def as_dict(self) -> dict[str, Any]: return {"count": self.count, "gutter": self.gutter, "column_boxes": [b.as_dict() for b in self.column_boxes]}
@dataclass
class SlideLayout:
    slide_type: str; density_class: str; typography: TypographySpec; content_box: BoundingBox; columns: ColumnLayout; extras: dict[str, Any] = field(default_factory=dict)
    def as_dict(self) -> dict[str, Any]: return {"slide_type": self.slide_type, "density_class": self.density_class, "typography": self.typography.as_dict(), "content_box": self.content_box.as_dict(), "columns": self.columns.as_dict(), "extras": self.extras}
def _wc(t: str | None) -> int: return len((t or "").split())
def _lines(t: str | None) -> list[str]: return [l.strip() for l in (t or "").split("\n") if l.strip()]
def _density_class(n: int) -> str: return "sparse" if n < 40 else ("medium" if n < 100 else "dense")
def _scale_font(base: int, words: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, round(lo + (1.0 - min(1.0, max(0.0, math.log1p(max(0, words - 40)) / math.log1p(160)))) * (hi - lo))))
def _split_columns(n: int) -> int: return 3 if n >= 7 else (2 if n >= 4 else 1)
def _column_boxes(count: int, gutter: float = 0.25) -> list[BoundingBox]:
    cw = (_CONTENT_W - gutter * (count - 1)) / count
    return [BoundingBox(round(_CL + i * (cw + gutter), 4), _CT, round(cw, 4), _CONTENT_H) for i in range(count)]
def _make_layout(stype: str, total: int, nc: int, g: float, tp: TypographySpec, extras: dict) -> SlideLayout:
    return SlideLayout(stype, _density_class(total), tp, BoundingBox(_CL, _CT, _CONTENT_W, _CONTENT_H), ColumnLayout(nc, _column_boxes(nc, g), g), extras)
def _layout_title(d: dict) -> SlideLayout:
    total = _wc(d.get("title")) + _wc(d.get("body_text")) + _wc(d.get("subtitle"))
    th = round(_CONTENT_H * 0.42, 3)
    return SlideLayout("title", _density_class(total), TypographySpec(_scale_font(28, total, _FT_MIN, _FT_MAX), _scale_font(18, total, 14, 22)), BoundingBox(_CL + 0.5, _CT, _CONTENT_W - 1.0, th), ColumnLayout(1, _column_boxes(1)), {"subtitle_box": BoundingBox(_CL + 0.5, _CT + th + 0.2, _CONTENT_W - 1.0, _CONTENT_H - th - 0.2).as_dict()})
def _layout_content(d: dict) -> SlideLayout:
    bullets = _lines(d.get("body_text")); total = _wc(d.get("title")) + _wc(d.get("body_text")); nc = _split_columns(len(bullets))
    off = -0.1 if _wc(d.get("title")) < 5 else 0.0
    return SlideLayout("content", _density_class(total), TypographySpec(_scale_font(24, total, _FT_MIN, 32), _scale_font(18, total, _F_MIN, _F_MAX)), BoundingBox(_CL, _CT + off, _CONTENT_W, _CONTENT_H - off), ColumnLayout(nc, _column_boxes(nc, 0.25), 0.25), {"bullet_count": len(bullets), "estimated_lines_per_col": math.ceil(len(bullets) / max(1, nc))})
def _layout_kpi(d: dict) -> SlideLayout:
    b = d.get("bullets") or []; bullets = _lines(b) if isinstance(b, str) else b
    n = len(bullets); total = _wc(d.get("title")) + sum(_wc(x) for x in bullets); nc = _split_columns(n)
    ih = max(0.6, (_CONTENT_H - 0.15 * max(0, n - 1)) / max(1, math.ceil(n / nc)))
    return _make_layout("kpi", total, nc, 0.3, TypographySpec(_scale_font(24, total, _FT_MIN, 30), _scale_font(20, total, 14, 26)), {"item_count": n, "item_height_in": round(ih, 3), "row_gap_in": 0.15})
def _layout_comparison(d: dict) -> SlideLayout:
    cmp = d.get("comparison") or {}
    lw, rw = _wc(cmp.get("left_title")) + _wc(cmp.get("left_body")), _wc(cmp.get("right_title")) + _wc(cmp.get("right_body"))
    total, lr = _wc(d.get("title")) + lw + rw, max(0.3, min(0.7, lw / max(1, lw + rw)))
    lw2, rw2 = round((_CONTENT_W - 0.3) * lr, 4), round((_CONTENT_W - 0.3) * (1.0 - lr), 4)
    return SlideLayout("comparison", _density_class(total), TypographySpec(_scale_font(24, total, _FT_MIN, 30), _scale_font(18, total, _F_MIN, _F_MAX)), BoundingBox(_CL, _CT, _CONTENT_W, _CONTENT_H), ColumnLayout(2, [BoundingBox(_CL, _CT, lw2, _CONTENT_H), BoundingBox(_CL + lw2 + 0.3, _CT, rw2, _CONTENT_H)], 0.3), {"left_ratio": round(lr, 3), "right_ratio": round(1.0 - lr, 3)})
def _layout_chart(d: dict) -> SlideLayout:
    cd = d.get("chart_data") or {}; ns, nc = len(cd.get("series", [])), len(cd.get("categories", []))
    return SlideLayout("chart", "medium", TypographySpec(26, 14, 11), BoundingBox(_CL, _CT, _CONTENT_W, round(_CONTENT_H - (0.3 if ns > 1 else 0.0), 3)), ColumnLayout(1, _column_boxes(1)), {"n_series": ns, "n_categories": nc, "has_legend": ns > 1})
def _layout_table(d: dict) -> SlideLayout:
    td = d.get("table_data") or {}; hdr, rows = td.get("headers", []), td.get("rows", [])
    nr, nc = len(rows) + (1 if hdr else 0), max(1, len(hdr))
    return SlideLayout("table", "dense" if nr * nc > 20 else "medium", TypographySpec(22, max(_F_MIN, min(16, round(18 - (nc - 2) * 1.5))), 11), BoundingBox(_CL, _CT, _CONTENT_W, round(min(_CONTENT_H, max(1.5, nr * 0.4)), 3)), ColumnLayout(1, _column_boxes(1)), {"n_rows": nr, "n_table_cols": nc, "col_width_in": round(_CONTENT_W / nc, 3)})
def _layout_process(d: dict) -> SlideLayout:
    p = d.get("process") or {}; s = p.get("steps") or []; steps = _lines(s) if isinstance(s, str) else s
    n = len(steps) if isinstance(steps, list) else 0; total = _wc(d.get("title")) + n * 5
    return _make_layout("process", total, min(5, max(1, n)), 0.2, TypographySpec(_scale_font(24, total, _FT_MIN, 30), _scale_font(16, n * 8, _F_MIN, 20)), {"step_count": n, "flow_direction": "horizontal"})
_FNS: dict[str, Any] = {"title": _layout_title, "content": _layout_content, "kpi": _layout_kpi, "comparison": _layout_comparison, "chart": _layout_chart, "table": _layout_table, "process": _layout_process}
class SlideLayoutEngine:
    def compute_slide_layout(self, slide_data: dict[str, Any]) -> SlideLayout:
        return _FNS.get((slide_data.get("slide_type") or "content").lower(), _layout_content)(slide_data)
    def compute_deck_layouts(self, slides: list[dict[str, Any]]) -> list[SlideLayout]:
        return [self.compute_slide_layout(s) for s in sorted(slides, key=lambda s: s.get("position", 0))]
    def layout_summary(self, slides: list[dict[str, Any]]) -> dict[str, Any]:
        layouts = self.compute_deck_layouts(slides)
        dc: dict[str, int] = {}; cc: dict[int, int] = {}; fts: list[int] = []
        for lay in layouts:
            dc[lay.density_class] = dc.get(lay.density_class, 0) + 1
            cc[lay.columns.count] = cc.get(lay.columns.count, 0) + 1
            fts.append(lay.typography.body_pt)
        return {"slide_count": len(layouts), "density_distribution": dc, "column_distribution": {str(k): v for k, v in cc.items()}, "avg_body_font_pt": round(sum(fts) / max(1, len(fts)), 1), "layouts": [lay.as_dict() for lay in layouts]}
