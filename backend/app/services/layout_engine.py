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
def _density(n: int) -> str: return "sparse" if n < 40 else "medium" if n < 100 else "dense"
_density_class = _density
def _sf(base: int, w: int, lo: int, hi: int) -> int: return max(lo, min(hi, round(lo + (1.0 - min(1.0, max(0.0, math.log1p(max(0, w - 40)) / math.log1p(160)))) * (hi - lo))))
_scale_font = _sf
def _split(n: int) -> int: return 3 if n >= 7 else 2 if n >= 4 else 1
_split_columns = _split
def _cols(cnt: int, gutter: float = 0.25) -> list[BoundingBox]:
    cw = (_CONTENT_W - gutter * (cnt - 1)) / cnt
    return [BoundingBox(round(_CL + i * (cw + gutter), 4), _CT, round(cw, 4), _CONTENT_H) for i in range(cnt)]
_column_boxes = _cols
def _mk(st: str, tot: int, nc: int, g: float, tp: TypographySpec, ex: dict) -> SlideLayout: return SlideLayout(st, _density(tot), tp, BoundingBox(_CL, _CT, _CONTENT_W, _CONTENT_H), ColumnLayout(nc, _cols(nc, g), g), ex)
def _lt(d: dict) -> SlideLayout:
    tot = _wc(d.get("title")) + _wc(d.get("body_text")) + _wc(d.get("subtitle"))
    th = round(_CONTENT_H * 0.42, 3)
    return SlideLayout("title", _density(tot), TypographySpec(_sf(28, tot, _FT_MIN, _FT_MAX), _sf(18, tot, 14, 22)), BoundingBox(_CL + 0.5, _CT, _CONTENT_W - 1.0, th), ColumnLayout(1, _cols(1)), {"subtitle_box": BoundingBox(_CL + 0.5, _CT + th + 0.2, _CONTENT_W - 1.0, _CONTENT_H - th - 0.2).as_dict()})
def _lc(d: dict) -> SlideLayout:
    b = _lines(d.get("body_text")); tot = _wc(d.get("title")) + _wc(d.get("body_text")); nc = _split(len(b))
    off = -0.1 if _wc(d.get("title")) < 5 else 0.0
    return SlideLayout("content", _density(tot), TypographySpec(_sf(24, tot, _F_MIN, 32), _sf(18, tot, _F_MIN, _F_MAX)), BoundingBox(_CL, _CT + off, _CONTENT_W, _CONTENT_H - off), ColumnLayout(nc, _cols(nc, 0.25), 0.25), {"bullet_count": len(b), "estimated_lines_per_col": math.ceil(len(b) / max(1, nc))})
def _lk(d: dict) -> SlideLayout:
    bu = d.get("bullets") or []; bl = _lines(bu) if isinstance(bu, str) else bu
    n = len(bl); tot = _wc(d.get("title")) + sum(_wc(x) for x in bl); nc = _split(n)
    ih = max(0.6, (_CONTENT_H - 0.15 * max(0, n - 1)) / max(1, math.ceil(n / nc)))
    return _mk("kpi", tot, nc, 0.3, TypographySpec(_sf(24, tot, _FT_MIN, 30), _sf(20, tot, 14, 26)), {"item_count": n, "item_height_in": round(ih, 3), "row_gap_in": 0.15})
def _lcmp(d: dict) -> SlideLayout:
    cm = d.get("comparison") or {}
    lw = _wc(cm.get("left_title")) + _wc(cm.get("left_body")); rw = _wc(cm.get("right_title")) + _wc(cm.get("right_body"))
    tot = _wc(d.get("title")) + lw + rw; lr = max(0.3, min(0.7, lw / max(1, lw + rw)))
    lw2, rw2 = round((_CONTENT_W - 0.3) * lr, 4), round((_CONTENT_W - 0.3) * (1.0 - lr), 4)
    return SlideLayout("comparison", _density(tot), TypographySpec(_sf(24, tot, _FT_MIN, 30), _sf(18, tot, _F_MIN, _F_MAX)), BoundingBox(_CL, _CT, _CONTENT_W, _CONTENT_H), ColumnLayout(2, [BoundingBox(_CL, _CT, lw2, _CONTENT_H), BoundingBox(_CL + lw2 + 0.3, _CT, rw2, _CONTENT_H)], 0.3), {"left_ratio": round(lr, 3), "right_ratio": round(1.0 - lr, 3)})
def _lch(d: dict) -> SlideLayout:
    cd = d.get("chart_data") or {}; ns, nc = len(cd.get("series", [])), len(cd.get("categories", []))
    return SlideLayout("chart", "medium", TypographySpec(26, 14, 11), BoundingBox(_CL, _CT, _CONTENT_W, round(_CONTENT_H - (0.3 if ns > 1 else 0.0), 3)), ColumnLayout(1, _cols(1)), {"n_series": ns, "n_categories": nc, "has_legend": ns > 1})
def _ltb(d: dict) -> SlideLayout:
    td = d.get("table_data") or {}; hdr, rows = td.get("headers", []), td.get("rows", [])
    nr, nc = len(rows) + (1 if hdr else 0), max(1, len(hdr))
    return SlideLayout("table", "dense" if nr * nc > 20 else "medium", TypographySpec(22, max(_F_MIN, min(16, round(18 - (nc - 2) * 1.5))), 11), BoundingBox(_CL, _CT, _CONTENT_W, round(min(_CONTENT_H, max(1.5, nr * 0.4)), 3)), ColumnLayout(1, _cols(1)), {"n_rows": nr, "n_table_cols": nc, "col_width_in": round(_CONTENT_W / nc, 3)})
def _lp(d: dict) -> SlideLayout:
    p = d.get("process") or {}; s = p.get("steps") or []; st = _lines(s) if isinstance(s, str) else s
    n = len(st) if isinstance(st, list) else 0; tot = _wc(d.get("title")) + n * 5
    return _mk("process", tot, min(5, max(1, n)), 0.2, TypographySpec(_sf(24, tot, _FT_MIN, 30), _sf(16, n * 8, _F_MIN, 20)), {"step_count": n, "flow_direction": "horizontal"})
_FNS = {"title": _lt, "content": _lc, "kpi": _lk, "comparison": _lcmp, "chart": _lch, "table": _ltb, "process": _lp}
class SlideLayoutEngine:
    def compute_slide_layout(self, slide_data: dict[str, Any]) -> SlideLayout: return _FNS.get((slide_data.get("slide_type") or "content").lower(), _lc)(slide_data)
    def compute_deck_layouts(self, slides: list[dict[str, Any]]) -> list[SlideLayout]: return [self.compute_slide_layout(s) for s in sorted(slides, key=lambda s: s.get("position", 0))]
    def layout_summary(self, slides: list[dict[str, Any]]) -> dict[str, Any]:
        layouts = self.compute_deck_layouts(slides)
        dc, cc, fts = {}, {}, []
        for lay in layouts:
            dc[lay.density_class] = dc.get(lay.density_class, 0) + 1
            cc[lay.columns.count] = cc.get(lay.columns.count, 0) + 1
            fts.append(lay.typography.body_pt)
        return {"slide_count": len(layouts), "density_distribution": dc, "column_distribution": {str(k): v for k, v in cc.items()}, "avg_body_font_pt": round(sum(fts) / max(1, len(fts)), 1), "layouts": [lay.as_dict() for lay in layouts]}