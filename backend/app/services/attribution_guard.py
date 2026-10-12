import json, os, sys
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Literal
Severity = Literal["error", "warning", "info"]
@dataclass
class DiagnosticItem:
    check_name: str; code: str; severity: Severity; message: str; affected_path: str | None = None; remediation: str | None = None
@dataclass
class AttributionReport:
    passed: bool; check_count: int; diagnostics: list[DiagnosticItem] = field(default_factory=list)
    def to_dict(self) -> dict: return {"passed": self.passed, "check_count": self.check_count, "diagnostics": [vars(d) for d in self.diagnostics]}
def _item(n: str, c: str, s: Severity, m: str, p: str | None = None, rem: str | None = None) -> DiagnosticItem:
    return DiagnosticItem(n, c, s, m, p, rem)
class AttributionGuard:
    def validate_deck_source(self, did: str, st: str | None, sl: list[dict]) -> AttributionReport:
        d: list[DiagnosticItem] = []
        if st is not None and len(st.strip()) < 10: d.append(_item("source_text_minimum_length", "ATTR-001", "warning", "Source text < 10 chars.", rem="Provide ≥10 chars."))
        if not sl: d.append(_item("slide_count_non_zero", "ATTR-002", "error", "Deck contains zero slides.", rem="Provide ≥1 slide."))
        pos = [s.get("position", -1) for s in sl]
        if sorted(pos) != list(range(len(sl))): d.append(_item("slide_position_continuity", "ATTR-003", "error", f"Slide positions not contiguous: {sorted(pos)}.", rem="Order positions."))
        if bt := [s.get("id", f"pos-{s.get('position', '?')}") for s in sl if s.get("slide_type") == "title" and not (s.get("title") or "").strip()]:
            d.append(_item("title_slide_has_title", "ATTR-004", "error", f"Title slide(s) missing title: {bt[:5]}", rem="Provide title."))
        if bc := [s.get("id", f"pos-{s.get('position', '?')}") for s in sl if s.get("slide_type") == "chart" and (not isinstance(s.get("chart_data"), dict) or not s.get("chart_data", {}).get("categories") or not s.get("chart_data", {}).get("series"))]:
            d.append(_item("chart_data_schema", "ATTR-005", "warning", f"Chart slide(s) missing chart_data: {bc[:5]}", rem="Fix chart data."))
        ids = [s.get("id") for s in sl if s.get("id")]
        if len(ids) != len(set(ids)): d.append(_item("unique_slide_ids", "ATTR-006", "error", "Duplicate slide IDs.", rem="Use unique IDs."))
        return AttributionReport(not any(x.severity == "error" for x in d), 6, d)
    def validate_from_file(self, f: str) -> AttributionReport:
        d, np = [], str(PurePath(f))
        try:
            with open(f, "r", encoding="utf-8") as fh: c = fh.read()
            if len(c.strip()) < 5: d.append(_item("file_content_non_empty", "ATTR-FILE-001", "error", f"File '{np}' is empty.", np, "Provide non-empty file."))
        except FileNotFoundError: d.append(_item("file_exists", "ATTR-FILE-002", "error", f"File not found: '{np}'", np, "Verify path exists."))
        except PermissionError: d.append(_item("file_readable", "ATTR-FILE-003", "error", f"Permission denied: '{np}'", np, "Check read permissions."))
        except Exception as e: d.append(_item("file_readable", "ATTR-FILE-004", "error", f"Error reading '{np}': {e}", np, "Fix OS error."))
        return AttributionReport(not any(x.severity == "error" for x in d), 1, d)
    def validate_workspace(self, wp: str) -> AttributionReport:
        p, np = Path(os.path.normpath(wp)), str(PurePath(wp))
        if not p.is_dir(): return AttributionReport(False, 1, [_item("workspace_is_dir", "ATTR-DIR-001", "error", f"Workspace not found: '{np}'", np, "Valid dir.")])
        sf = sorted([*p.glob("*.json"), *p.glob("*.txt")])
        if not sf: return AttributionReport(True, 1, [_item("workspace_has_sources", "ATTR-DIR-002", "warning", f"No sources in '{np}'.", np, "Add files.")])
        d = [x for s in sf[:10] for x in self.validate_from_file(str(s)).diagnostics]
        return AttributionReport(not any(x.severity == "error" for x in d), 1 + len(sf), d)
def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Attribution Guard integrity gate")
    p.add_argument("target", nargs="?", default=".", help="Target"); p.add_argument("--json", action="store_true", help="JSON output")
    a = p.parse_args(argv)
    g, pt = AttributionGuard(), Path(os.path.normpath(a.target))
    np = str(PurePath(pt))
    if not pt.exists(): r = AttributionReport(False, 1, [_item("target_exists", "ATTR-CLI-001", "error", f"Target '{np}' not found.", np, "Verify that the specified path exists.")])
    elif pt.is_file():
        if pt.suffix.lower() == ".json":
            try:
                dt = json.loads(pt.read_text("utf-8"))
                r = g.validate_deck_source(dt.get("id", pt.stem), dt.get("source_text"), dt.get("slides", [])) if isinstance(dt, dict) and "slides" in dt else g.validate_from_file(str(pt))
            except json.JSONDecodeError as e: r = AttributionReport(False, 1, [_item("json_valid", "ATTR-CLI-002", "error", f"Malformed JSON in '{np}': {e}", np, "Fix JSON syntax.")])
        else: r = g.validate_from_file(str(pt))
    else: r = g.validate_workspace(str(pt))
    if a.json: sys.stdout.write(json.dumps(r.to_dict(), indent=2) + "\n")
    elif r.passed: sys.stdout.write(f"[AttributionGuard] PASS ({r.check_count} checks verified).\n")
    else:
        es, ws = [x for x in r.diagnostics if x.severity == "error"], [x for x in r.diagnostics if x.severity == "warning"]
        sys.stderr.write(f"[AttributionGuard] FAIL ({len(es)} error(s), {len(ws)} warning(s)):\n")
        for x in r.diagnostics:
            l = f" [{x.affected_path}]" if x.affected_path else ""
            sys.stderr.write(f"  * {x.code} ({x.severity.upper()}): {x.message}{l}\n" + (f"    Remediation: {x.remediation}\n" if x.remediation else ""))
    return 0 if r.passed else 1
if __name__ == "__main__": sys.exit(main())