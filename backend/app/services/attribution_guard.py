"""Attribution guard: validates deck source integrity with cross-platform diagnostics.

Resolves upstream issue #311 (silent exit 1 on Windows) with structured reports and CLI gate.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Literal

Severity = Literal["error", "warning", "info"]


@dataclass
class DiagnosticItem:
    check_name: str
    code: str
    severity: Severity
    message: str
    affected_path: str | None = None
    remediation: str | None = None


@dataclass
class AttributionReport:
    passed: bool
    check_count: int
    diagnostics: list[DiagnosticItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"passed": self.passed, "check_count": self.check_count, "diagnostics": [vars(d) for d in self.diagnostics]}


def _item(name: str, code: str, sev: Severity, msg: str, path: str | None = None, rem: str | None = None) -> DiagnosticItem:
    return DiagnosticItem(name, code, sev, msg, path, rem)


class AttributionGuard:
    """Validates deck source integrity and generates structured cross-platform diagnostics."""

    def validate_deck_source(self, deck_id: str, source_text: str | None, slides: list[dict]) -> AttributionReport:
        diag: list[DiagnosticItem] = []
        if source_text is not None and len(source_text.strip()) < 10:
            diag.append(_item("source_text_minimum_length", "ATTR-001", "warning", "Source text is shorter than 10 characters.", rem="Provide ≥ 10 characters."))
        if len(slides) == 0:
            diag.append(_item("slide_count_non_zero", "ATTR-002", "error", "Deck contains zero slides.", rem="Provide at least one slide."))
        positions = [s.get("position", -1) for s in slides]
        if sorted(positions) != list(range(len(slides))):
            diag.append(_item("slide_position_continuity", "ATTR-003", "error", f"Slide positions not contiguous 0..N-1: {sorted(positions)}.", rem="Re-order positions sequentially."))
        missing_titles = [s.get("id", f"pos-{s.get('position', '?')}") for s in slides if s.get("slide_type") == "title" and not (s.get("title") or "").strip()]
        if missing_titles:
            diag.append(_item("title_slide_has_title", "ATTR-004", "error", f"Title slide(s) missing title: {missing_titles[:5]}", rem="Provide non-empty title."))
        bad_charts = [s.get("id", f"pos-{s.get('position', '?')}") for s in slides if s.get("slide_type") == "chart" and (not isinstance(s.get("chart_data"), dict) or not s.get("chart_data", {}).get("categories") or not s.get("chart_data", {}).get("series"))]
        if bad_charts:
            diag.append(_item("chart_data_schema", "ATTR-005", "warning", f"Chart slide(s) missing valid chart_data: {bad_charts[:5]}", rem="Ensure categories and series are populated."))
        ids = [s.get("id") for s in slides if s.get("id")]
        if len(ids) != len(set(ids)):
            diag.append(_item("unique_slide_ids", "ATTR-006", "error", "Duplicate slide IDs detected.", rem="Ensure unique IDs."))
        return AttributionReport(passed=not any(d.severity == "error" for d in diag), check_count=6, diagnostics=diag)

    def validate_from_file(self, source_file: str) -> AttributionReport:
        diag, np = [], str(PurePath(source_file))
        try:
            with open(source_file, "r", encoding="utf-8") as fh:
                content = fh.read()
            if len(content.strip()) < 5:
                diag.append(_item("file_content_non_empty", "ATTR-FILE-001", "error", f"File '{np}' is empty.", np, "Provide non-empty file."))
        except FileNotFoundError:
            diag.append(_item("file_exists", "ATTR-FILE-002", "error", f"File not found: '{np}'", np, "Verify path exists."))
        except PermissionError:
            diag.append(_item("file_readable", "ATTR-FILE-003", "error", f"Permission denied: '{np}'", np, "Check read permissions."))
        except Exception as exc:
            diag.append(_item("file_readable", "ATTR-FILE-004", "error", f"Error reading '{np}': {type(exc).__name__}: {exc}", np, "Fix underlying OS error."))
        return AttributionReport(passed=not any(d.severity == "error" for d in diag), check_count=1, diagnostics=diag)

    def validate_workspace(self, workspace_path: str) -> AttributionReport:
        p = Path(os.path.normpath(workspace_path))
        np = str(PurePath(p))
        if not p.is_dir():
            return AttributionReport(False, 1, [_item("workspace_is_dir", "ATTR-DIR-001", "error", f"Workspace directory not found: '{np}'", np, "Specify a valid directory.")])
        diag, source_files = [], sorted(list(p.glob("*.json")) + list(p.glob("*.txt")))
        if not source_files:
            diag.append(_item("workspace_has_sources", "ATTR-DIR-002", "warning", f"No source files (.json, .txt) found in '{np}'.", np, "Place presentation source files in workspace."))
        else:
            for sf in source_files[:10]:
                diag.extend(self.validate_from_file(str(sf)).diagnostics)
        return AttributionReport(passed=not any(d.severity == "error" for d in diag), check_count=1 + len(source_files), diagnostics=diag)


def main(argv: list[str] | None = None) -> int:
    import argparse, json, sys
    parser = argparse.ArgumentParser(description="Attribution Guard integrity gate")
    parser.add_argument("target", nargs="?", default=".", help="Path to deck source file or workspace directory")
    parser.add_argument("--json", action="store_true", help="Output diagnostics in JSON format")
    args = parser.parse_args(argv)

    guard, p = AttributionGuard(), Path(os.path.normpath(args.target))
    norm_path = str(PurePath(p))
    if not p.exists():
        report = AttributionReport(False, 1, [_item("target_exists", "ATTR-CLI-001", "error", f"Target path '{norm_path}' does not exist.", norm_path, "Verify that the specified path exists.")])
    elif p.is_file():
        if p.suffix.lower() == ".json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                report = guard.validate_deck_source(data.get("id", p.stem), data.get("source_text"), data.get("slides", [])) if isinstance(data, dict) and "slides" in data else guard.validate_from_file(str(p))
            except json.JSONDecodeError as err:
                report = AttributionReport(False, 1, [_item("json_valid", "ATTR-CLI-002", "error", f"Malformed JSON in '{norm_path}': {err}", norm_path, "Fix syntax error in JSON file.")])
        else:
            report = guard.validate_from_file(str(p))
    else:
        report = guard.validate_workspace(str(p))

    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2) + "\n")
    else:
        if report.passed:
            sys.stdout.write(f"[AttributionGuard] PASS ({report.check_count} checks verified).\n")
        else:
            errs = [d for d in report.diagnostics if d.severity == "error"]
            warns = [d for d in report.diagnostics if d.severity == "warning"]
            sys.stderr.write(f"[AttributionGuard] FAIL ({len(errs)} error(s), {len(warns)} warning(s)):\n")
            for d in report.diagnostics:
                loc = f" [{d.affected_path}]" if d.affected_path else ""
                sys.stderr.write(f"  * {d.code} ({d.severity.upper()}): {d.message}{loc}\n")
                if d.remediation:
                    sys.stderr.write(f"    Remediation: {d.remediation}\n")
    return 0 if report.passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
