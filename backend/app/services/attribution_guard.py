"""Attribution guard: validates deck source integrity with cross-platform diagnostics. Resolves #311."""
from __future__ import annotations
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

def _item(name: str, code: str, sev: Severity, msg: str, path: str | None = None, rem: str | None = None) -> DiagnosticItem:
    return DiagnosticItem(name, code, sev, msg, path, rem)

class AttributionGuard:
    def validate_deck_source(self, deck_id: str, source_text: str | None, slides: list[dict]) -> AttributionReport:
        diag: list[DiagnosticItem] = []
        if source_text is not None and len(source_text.strip()) < 10: diag.append(_item("source_text_minimum_length", "ATTR-001", "warning", "Source text < 10 chars.", rem="Provide ≥10 chars."))
        if not slides: diag.append(_item("slide_count_non_zero", "ATTR-002", "error", "Deck contains zero slides.", rem="Provide ≥1 slide."))
        pos = [s.get("position", -1) for s in slides]
        if sorted(pos) != list(range(len(slides))): diag.append(_item("slide_position_continuity", "ATTR-003", "error", f"Slide positions not contiguous: {sorted(pos)}.", rem="Order positions."))
        if bad_t := [s.get("id", f"pos-{s.get('position', '?')}") for s in slides if s.get("slide_type") == "title" and not (s.get("title") or "").strip()]:
            diag.append(_item("title_slide_has_title", "ATTR-004", "error", f"Title slide(s) missing title: {bad_t[:5]}", rem="Provide title."))
        if bad_c := [s.get("id", f"pos-{s.get('position', '?')}") for s in slides if s.get("slide_type") == "chart" and (not isinstance(s.get("chart_data"), dict) or not s.get("chart_data", {}).get("categories") or not s.get("chart_data", {}).get("series"))]:
            diag.append(_item("chart_data_schema", "ATTR-005", "warning", f"Chart slide(s) missing chart_data: {bad_c[:5]}", rem="Fix chart data."))
        ids = [s.get("id") for s in slides if s.get("id")]
        if len(ids) != len(set(ids)): diag.append(_item("unique_slide_ids", "ATTR-006", "error", "Duplicate slide IDs.", rem="Use unique IDs."))
        return AttributionReport(not any(d.severity == "error" for d in diag), 6, diag)

    def validate_from_file(self, source_file: str) -> AttributionReport:
        diag, np = [], str(PurePath(source_file))
        try:
            with open(source_file, "r", encoding="utf-8") as fh: content = fh.read()
            if len(content.strip()) < 5: diag.append(_item("file_content_non_empty", "ATTR-FILE-001", "error", f"File '{np}' is empty.", np, "Provide non-empty file."))
        except FileNotFoundError: diag.append(_item("file_exists", "ATTR-FILE-002", "error", f"File not found: '{np}'", np, "Verify path exists."))
        except PermissionError: diag.append(_item("file_readable", "ATTR-FILE-003", "error", f"Permission denied: '{np}'", np, "Check read permissions."))
        except Exception as exc: diag.append(_item("file_readable", "ATTR-FILE-004", "error", f"Error reading '{np}': {exc}", np, "Fix OS error."))
        return AttributionReport(not any(d.severity == "error" for d in diag), 1, diag)

    def validate_workspace(self, workspace_path: str) -> AttributionReport:
        p, np = Path(os.path.normpath(workspace_path)), str(PurePath(workspace_path))
        if not p.is_dir(): return AttributionReport(False, 1, [_item("workspace_is_dir", "ATTR-DIR-001", "error", f"Workspace not found: '{np}'", np, "Valid dir.")])
        sfiles = sorted([*p.glob("*.json"), *p.glob("*.txt")])
        if not sfiles: return AttributionReport(True, 1, [_item("workspace_has_sources", "ATTR-DIR-002", "warning", f"No sources in '{np}'.", np, "Add files.")])
        diag = [d for sf in sfiles[:10] for d in self.validate_from_file(str(sf)).diagnostics]
        return AttributionReport(not any(d.severity == "error" for d in diag), 1 + len(sfiles), diag)

def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Attribution Guard integrity gate")
    parser.add_argument("target", nargs="?", default=".", help="Target"); parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)
    guard, p = AttributionGuard(), Path(os.path.normpath(args.target))
    np = str(PurePath(p))
    if not p.exists(): rep = AttributionReport(False, 1, [_item("target_exists", "ATTR-CLI-001", "error", f"Target '{np}' not found.", np, "Verify that the specified path exists.")])
    elif p.is_file():
        if p.suffix.lower() == ".json":
            try:
                data = json.loads(p.read_text("utf-8"))
                rep = guard.validate_deck_source(data.get("id", p.stem), data.get("source_text"), data.get("slides", [])) if isinstance(data, dict) and "slides" in data else guard.validate_from_file(str(p))
            except json.JSONDecodeError as err: rep = AttributionReport(False, 1, [_item("json_valid", "ATTR-CLI-002", "error", f"Malformed JSON in '{np}': {err}", np, "Fix JSON syntax.")])
        else: rep = guard.validate_from_file(str(p))
    else: rep = guard.validate_workspace(str(p))
    if args.json: sys.stdout.write(json.dumps(rep.to_dict(), indent=2) + "\n")
    elif rep.passed: sys.stdout.write(f"[AttributionGuard] PASS ({rep.check_count} checks verified).\n")
    else:
        errs, warns = [d for d in rep.diagnostics if d.severity == "error"], [d for d in rep.diagnostics if d.severity == "warning"]
        sys.stderr.write(f"[AttributionGuard] FAIL ({len(errs)} error(s), {len(warns)} warning(s)):\n")
        for d in rep.diagnostics:
            loc = f" [{d.affected_path}]" if d.affected_path else ""
            sys.stderr.write(f"  * {d.code} ({d.severity.upper()}): {d.message}{loc}\n" + (f"    Remediation: {d.remediation}\n" if d.remediation else ""))
    return 0 if rep.passed else 1

if __name__ == "__main__": sys.exit(main())
