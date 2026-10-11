"""Attribution guard: validates deck source integrity with cross-platform diagnostics.

Resolves upstream issue #311 (silent exit 1 on Windows) with structured reports.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import PurePath
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


class AttributionGuard:
    """Validates deck source integrity and generates structured cross-platform diagnostics."""

    def validate_deck_source(self, deck_id: str, source_text: str | None, slides: list[dict]) -> AttributionReport:
        diag: list[DiagnosticItem] = []
        checks = 0

        checks += 1
        if source_text is not None and len(source_text.strip()) < 10:
            diag.append(DiagnosticItem("source_text_minimum_length", "ATTR-001", "warning", "Source text is shorter than 10 characters.", remediation="Provide ≥ 10 characters."))

        checks += 1
        if len(slides) == 0:
            diag.append(DiagnosticItem("slide_count_non_zero", "ATTR-002", "error", "Deck contains zero slides.", remediation="Provide at least one slide."))

        checks += 1
        positions = [s.get("position", -1) for s in slides]
        if sorted(positions) != list(range(len(slides))):
            diag.append(DiagnosticItem("slide_position_continuity", "ATTR-003", "error", f"Slide positions not contiguous 0..N-1: {sorted(positions)}.", remediation="Re-order positions sequentially."))

        checks += 1
        missing_titles = [s.get("id", f"pos-{s.get('position', '?')}") for s in slides if s.get("slide_type") == "title" and not (s.get("title") or "").strip()]
        if missing_titles:
            diag.append(DiagnosticItem("title_slide_has_title", "ATTR-004", "error", f"Title slide(s) missing title: {missing_titles[:5]}", remediation="Provide non-empty title."))

        checks += 1
        bad_charts = [s.get("id", f"pos-{s.get('position', '?')}") for s in slides if s.get("slide_type") == "chart" and (not isinstance(s.get("chart_data"), dict) or not s.get("chart_data", {}).get("categories") or not s.get("chart_data", {}).get("series"))]
        if bad_charts:
            diag.append(DiagnosticItem("chart_data_schema", "ATTR-005", "warning", f"Chart slide(s) missing valid chart_data: {bad_charts[:5]}", remediation="Ensure categories and series are populated."))

        checks += 1
        ids = [s.get("id") for s in slides if s.get("id")]
        if len(ids) != len(set(ids)):
            diag.append(DiagnosticItem("unique_slide_ids", "ATTR-006", "error", "Duplicate slide IDs detected.", remediation="Ensure unique IDs."))

        return AttributionReport(passed=not any(d.severity == "error" for d in diag), check_count=checks, diagnostics=diag)

    def validate_from_file(self, source_file: str) -> AttributionReport:
        diag: list[DiagnosticItem] = []
        np = str(PurePath(source_file))
        try:
            with open(source_file, "r", encoding="utf-8") as fh:
                content = fh.read()
            if len(content.strip()) < 5:
                diag.append(DiagnosticItem("file_content_non_empty", "ATTR-FILE-001", "error", f"File '{np}' is empty.", affected_path=np, remediation="Provide non-empty file."))
        except FileNotFoundError:
            diag.append(DiagnosticItem("file_exists", "ATTR-FILE-002", "error", f"File not found: '{np}'", affected_path=np, remediation="Verify path exists."))
        except PermissionError:
            diag.append(DiagnosticItem("file_readable", "ATTR-FILE-003", "error", f"Permission denied: '{np}'", affected_path=np, remediation="Check read permissions."))
        except Exception as exc:
            diag.append(DiagnosticItem("file_readable", "ATTR-FILE-004", "error", f"Error reading '{np}': {type(exc).__name__}: {exc}", affected_path=np, remediation="Fix underlying OS error."))
        return AttributionReport(passed=not any(d.severity == "error" for d in diag), check_count=1, diagnostics=diag)
