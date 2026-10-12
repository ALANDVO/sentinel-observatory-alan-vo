"""Tests for the attribution guard service."""
from __future__ import annotations

import pytest

from backend.app.services.attribution_guard import AttributionGuard, AttributionReport


@pytest.fixture
def guard():
    return AttributionGuard()


def _make_slides(count: int = 3) -> list[dict]:
    slides = [{"id": f"id-{i}", "position": i, "slide_type": "title" if i == 0 else "content", "title": f"Slide {i}", "body_text": "", "chart_data": None} for i in range(count)]
    return slides


def test_valid_deck_passes(guard):
    slides = _make_slides(5)
    report = guard.validate_deck_source("deck-001", "Full AI strategy document", slides)
    assert report.passed is True
    assert len([d for d in report.diagnostics if d.severity == "error"]) == 0


def test_empty_slides_fails(guard):
    report = guard.validate_deck_source("deck-002", "Some source", [])
    assert report.passed is False
    codes = [d.code for d in report.diagnostics]
    assert "ATTR-002" in codes


def test_non_contiguous_positions_fails(guard):
    slides = [
        {"id": "id-0", "position": 0, "slide_type": "title", "title": "T", "body_text": "", "chart_data": None},
        {"id": "id-2", "position": 2, "slide_type": "content", "title": "C", "body_text": "", "chart_data": None},
    ]
    report = guard.validate_deck_source("deck-003", "Source", slides)
    assert report.passed is False
    codes = [d.code for d in report.diagnostics]
    assert "ATTR-003" in codes


def test_title_slide_without_title_fails(guard):
    slides = [
        {"id": "id-0", "position": 0, "slide_type": "title", "title": "", "body_text": "", "chart_data": None},
        {"id": "id-1", "position": 1, "slide_type": "content", "title": "Second", "body_text": "", "chart_data": None},
    ]
    report = guard.validate_deck_source("deck-004", "Source", slides)
    assert report.passed is False
    codes = [d.code for d in report.diagnostics]
    assert "ATTR-004" in codes


def test_chart_slide_missing_data_warns(guard):
    slides = [
        {"id": "id-0", "position": 0, "slide_type": "title", "title": "T", "body_text": "", "chart_data": None},
        {"id": "id-1", "position": 1, "slide_type": "chart", "title": "Chart", "body_text": "", "chart_data": None},
    ]
    report = guard.validate_deck_source("deck-005", "Source", slides)
    warnings = [d for d in report.diagnostics if d.code == "ATTR-005"]
    assert len(warnings) > 0
    assert warnings[0].severity == "warning"


def test_valid_chart_data_passes(guard):
    slides = [
        {"id": "id-0", "position": 0, "slide_type": "title", "title": "T", "body_text": "", "chart_data": None},
        {
            "id": "id-1",
            "position": 1,
            "slide_type": "chart",
            "title": "Revenue",
            "body_text": "",
            "chart_data": {"categories": ["Q1", "Q2"], "series": [{"name": "Rev", "values": [100, 200]}]},
        },
    ]
    report = guard.validate_deck_source("deck-006", "Source", slides)
    chart_warnings = [d for d in report.diagnostics if d.code == "ATTR-005"]
    assert len(chart_warnings) == 0


def test_duplicate_slide_ids_fail(guard):
    slides = [
        {"id": "same-id", "position": 0, "slide_type": "title", "title": "T", "body_text": "", "chart_data": None},
        {"id": "same-id", "position": 1, "slide_type": "content", "title": "C", "body_text": "", "chart_data": None},
    ]
    report = guard.validate_deck_source("deck-007", "Source", slides)
    assert report.passed is False


def test_diagnostics_have_remediation(guard):
    report = guard.validate_deck_source("deck-008", "Source", [])
    for d in report.diagnostics:
        if d.severity == "error":
            assert d.remediation is not None
            assert len(d.remediation) > 0


def test_file_validation_missing_file(guard, tmp_path):
    missing = str(tmp_path / "missing_file.txt")
    report = guard.validate_from_file(missing)
    assert report.passed is False
    codes = [d.code for d in report.diagnostics]
    assert "ATTR-FILE-002" in codes
    # Diagnostics must include path information
    assert any(d.affected_path for d in report.diagnostics)


def test_file_validation_valid_file(guard, tmp_path):
    f = tmp_path / "source.txt"
    f.write_text("This is valid source text for the deck.")
    report = guard.validate_from_file(str(f))
    assert report.passed is True


def test_workspace_validation(guard, tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    rep = guard.validate_workspace(str(ws))
    assert rep.passed is True
    # Warning about no source files
    assert any(d.code == "ATTR-DIR-002" for d in rep.diagnostics)

    (ws / "notes.txt").write_text("Presentation background research notes for AI observatory.")
    rep2 = guard.validate_workspace(str(ws))
    assert rep2.passed is True
    assert rep2.check_count >= 2


def test_cli_main_valid_file(tmp_path, capsys):
    from backend.app.services.attribution_guard import main
    f = tmp_path / "source.txt"
    f.write_text("Valid presentation source documentation text.")
    exit_code = main([str(f)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[AttributionGuard] PASS" in captured.out


def test_cli_main_missing_target_fails_closed_with_diagnostics(tmp_path, capsys):
    from backend.app.services.attribution_guard import main
    missing = str(tmp_path / "nonexistent.txt")
    exit_code = main([missing])
    captured = capsys.readouterr()
    assert exit_code == 1
    # Issue #311 resolution: MUST emit actionable diagnostics, never silent exit
    assert "[AttributionGuard] FAIL" in captured.err
    assert "ATTR-CLI-001" in captured.err
    assert "Remediation:" in captured.err


def test_cli_main_json_output(tmp_path, capsys):
    import json
    from backend.app.services.attribution_guard import main
    f = tmp_path / "source.txt"
    f.write_text("Valid source text content.")
    exit_code = main([str(f), "--json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["passed"] is True
    assert "diagnostics" in data


def test_cli_main_deck_json_validation(tmp_path, capsys):
    import json
    from backend.app.services.attribution_guard import main
    deck_file = tmp_path / "deck.json"
    deck_file.write_text(json.dumps({
        "id": "deck-cli",
        "source_text": "Sufficient source text for presentation",
        "slides": [
            {"id": "s0", "position": 0, "slide_type": "title", "title": "Main Title", "body_text": "", "chart_data": None},
            {"id": "s1", "position": 1, "slide_type": "content", "title": "Body Slide", "body_text": "Point", "chart_data": None},
        ],
    }))
    exit_code = main([str(deck_file)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[AttributionGuard] PASS" in captured.out
