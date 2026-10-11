"""Tests for prompt audit engine: token budgets, language-neutral key validation, and locale parity."""
from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from backend.app.services.prompt_audit import PromptAuditService, _estimate_tokens, AuditFinding, main as prompt_audit_main


@pytest.fixture
def auditor():
    return PromptAuditService()


def test_token_estimation_ascii():
    text = "The quick brown fox jumps over the lazy dog"
    tokens = _estimate_tokens(text)
    assert 8 <= tokens <= 15


def test_token_estimation_cjk_counted_differently():
    cjk_text = "人工智能安全研究"
    ascii_text = "AI safety research"
    cjk_tokens = _estimate_tokens(cjk_text)
    ascii_tokens = _estimate_tokens(ascii_text)
    assert cjk_tokens > 0
    assert ascii_tokens > 0


def test_audit_slide_content_passes_for_clean_slides(auditor: PromptAuditService):
    slides = [
        {"title": "AI Alignment Methods", "body_text": "• RLHF\n• Constitutional AI\n• Debate", "speaker_notes": "Overview of alignment techniques."},
        {"title": "Benchmark Results", "body_text": "• GPT-4: 86% MMLU\n• Claude-3: 85% MMLU", "speaker_notes": "Performance comparison."},
    ]
    report = auditor.audit_slide_content(slides, model="gpt-4o-mini")
    errors = [f for f in report.findings if f.severity == "error"]
    assert len(errors) == 0
    assert report.passed is True


def test_audit_detects_bilingual_suffix_in_locale_keys(auditor: PromptAuditService):
    slides = [{"title": "Test Slide", "body_text": "Content."}]
    locale_keys = [{"name_zh": "AI 安全", "behavior_en": "RLHF Training"}]
    report = auditor.audit_slide_content(slides, locale_keys_per_slide=locale_keys)
    bilingual_errors = [f for f in report.findings if f.rule == "bilingual_key_suffix_pollution"]
    assert len(bilingual_errors) >= 2


def test_audit_locale_dictionary_passes_identical_keys(auditor: PromptAuditService):
    dicts = {
        "en": {"title": "Welcome", "submit": "Submit", "cancel": "Cancel"},
        "zh": {"title": "欢迎", "submit": "提交", "cancel": "取消"},
        "ja": {"title": "ようこそ", "submit": "送信", "cancel": "キャンセル"},
    }
    report = auditor.audit_locale_dictionary(dicts)
    errors = [f for f in report.findings if f.severity == "error"]
    assert len(errors) == 0
    assert report.passed is True


def test_audit_locale_dictionary_detects_missing_keys(auditor: PromptAuditService):
    dicts = {
        "en": {"title": "Welcome", "submit": "Submit", "cancel": "Cancel"},
        "zh": {"title": "欢迎", "submit": "提交"},
    }
    report = auditor.audit_locale_dictionary(dicts)
    errors = [f for f in report.findings if f.severity == "error"]
    assert any(f.rule == "locale_key_parity_missing" for f in errors)
    assert report.passed is False


def test_audit_locale_dictionary_detects_extra_keys(auditor: PromptAuditService):
    dicts = {
        "en": {"title": "Welcome", "submit": "Submit"},
        "zh": {"title": "欢迎", "submit": "提交", "extra_key": "额外的"},
    }
    report = auditor.audit_locale_dictionary(dicts)
    warnings = [f for f in report.findings if f.severity == "warning"]
    assert any(f.rule == "locale_key_parity_extra" for f in warnings)


def test_audit_detects_bilingual_reference_key(auditor: PromptAuditService):
    dicts = {
        "en": {"name_zh": "AI Safety", "submit": "Submit"},
        "zh": {"name_zh": "AI 安全", "submit": "提交"},
    }
    report = auditor.audit_locale_dictionary(dicts)
    bilingual_ref_errors = [f for f in report.findings if f.rule == "bilingual_key_in_reference_locale"]
    assert len(bilingual_ref_errors) >= 1
    assert report.passed is False


def test_audit_token_budget_warning_near_limit(auditor: PromptAuditService):
    long_text = " ".join(["alignment safety benchmark evaluation"] * 1000)
    slides = [{"title": "Very Long Slide", "body_text": long_text}]
    report = auditor.audit_slide_content(slides, model="gpt-3.5-turbo")
    budget_warnings = [f for f in report.findings if f.rule == "token_budget_80pct"]
    assert len(budget_warnings) >= 1


def test_audit_slide_speaker_notes_too_long(auditor: PromptAuditService):
    long_notes = " ".join(["speaker notes content elaborating on key concepts"] * 60)
    slides = [{"title": "Test", "body_text": "Content.", "speaker_notes": long_notes}]
    report = auditor.audit_slide_content(slides)
    notes_warnings = [f for f in report.findings if f.rule == "speaker_notes_token_limit"]
    assert len(notes_warnings) >= 1


def test_audit_report_to_dict_serializable(auditor: PromptAuditService):
    slides = [{"title": "Clean Slide", "body_text": "• Point A"}]
    report = auditor.audit_slide_content(slides)
    report_dict = report.to_dict()
    assert "passed" in report_dict
    assert "total_tokens_estimated" in report_dict
    assert "findings" in report_dict
    assert isinstance(report_dict["findings"], list)


def test_audit_locale_dictionary_detects_placeholder_mismatch(auditor: PromptAuditService):
    dicts = {
        "en": {"greeting": "Hello {user}, your deck has {count} slides.", "done": "Done"},
        "zh": {"greeting": "你好 {user}，幻灯片已准备好。", "done": "完成"},  # missing {count}
    }
    report = auditor.audit_locale_dictionary(dicts)
    mismatches = [f for f in report.findings if f.rule == "placeholder_parity_mismatch"]
    assert len(mismatches) == 1
    assert "count" in mismatches[0].message
    assert report.passed is False


def test_audit_locale_dictionary_detects_empty_translation(auditor: PromptAuditService):
    dicts = {
        "en": {"submit": "Submit", "cancel": "Cancel"},
        "ja": {"submit": "送信", "cancel": "   "},  # empty whitespace
    }
    report = auditor.audit_locale_dictionary(dicts)
    empty_errors = [f for f in report.findings if f.rule == "empty_translation_value"]
    assert len(empty_errors) == 1
    assert "cancel" in empty_errors[0].message
    assert report.passed is False


def test_audit_locale_dictionary_detects_unused_keys(auditor: PromptAuditService):
    dicts = {
        "en": {"active_key": "Active", "legacy_dead_key": "Dead"},
        "zh": {"active_key": "活动", "legacy_dead_key": "废弃"},
    }
    report = auditor.audit_locale_dictionary(dicts, referenced_keys=["active_key"])
    unused_warns = [f for f in report.findings if f.rule == "unused_dictionary_key"]
    assert len(unused_warns) == 1
    assert "legacy_dead_key" in unused_warns[0].message
    # Warning does not fail overall report if no errors
    assert report.passed is True


def test_audit_markdown_drift_passes_synchronized(auditor: PromptAuditService):
    src = "# Title\n\nIntroduction text.\n\n## Section 1\n\n```python\nprint('hello')\n```\n\n| Col1 | Col2 |\n|---|---|\n| A | B |\n\n[Link](#section-1)"
    tgt = "# 标题\n\n介绍文本。\n\n## 第一节\n\n```python\nprint('hello')\n```\n\n| 列1 | 列2 |\n|---|---|\n| 甲 | 乙 |\n\n[链接](#第一节)"
    report = auditor.audit_markdown_translation_drift(src, tgt, "en", "zh")
    errors = [f for f in report.findings if f.severity == "error"]
    assert len(errors) == 0
    assert report.passed is True


def test_audit_markdown_drift_detects_code_block_drift(auditor: PromptAuditService):
    src = "## Usage\n\n```bash\npytest\n```\n\n```bash\nnpm test\n```"
    tgt = "## 用法\n\n```bash\npytest\n```"  # Missing second code block
    report = auditor.audit_markdown_translation_drift(src, tgt, "en", "zh")
    code_errors = [f for f in report.findings if f.rule == "code_block_drift"]
    assert len(code_errors) == 1
    assert report.passed is False


def test_audit_markdown_drift_detects_heading_count_drift(auditor: PromptAuditService):
    src = "# Title\n\n## Section 1\n\n## Section 2\n\n### Sub 1"
    tgt = "# 标题\n\n## 第一节"  # Missing Section 2 and Sub 1
    report = auditor.audit_markdown_translation_drift(src, tgt, "en", "zh")
    heading_warns = [f for f in report.findings if f.rule == "heading_count_drift"]
    assert len(heading_warns) == 1


def test_audit_markdown_drift_detects_table_row_count_drift(auditor: PromptAuditService):
    src = "| Metric | Weight |\n|---|---|\n| A | 1 |\n| B | 2 |\n| C | 3 |"
    tgt = "| 指标 | 权重 |\n|---|---|\n| 甲 | 1 |"  # Missing 2 rows
    report = auditor.audit_markdown_translation_drift(src, tgt, "en", "zh")
    table_warns = [f for f in report.findings if f.rule == "table_row_count_drift"]
    assert len(table_warns) == 1


def test_audit_markdown_drift_detects_unresolved_anchor(auditor: PromptAuditService):
    src = "## Quickstart\n\nSee [details](#quickstart)"
    tgt = "## 快速开始\n\n参见 [详情](#unresolved-anchor)"  # anchor doesn't match translated heading slug
    report = auditor.audit_markdown_translation_drift(src, tgt, "en", "zh")
    anchor_errors = [f for f in report.findings if f.rule == "unresolved_anchor_reference"]
    assert len(anchor_errors) == 1
    assert report.passed is False


def test_audit_prompt_template_rules_flags_bilingual_trigger_pollution(auditor: PromptAuditService):
    templates = [
        {"name": "beautify", "trigger": "beautify / re-layout / 重新排版 / 美化", "prompt": "Enhance deck design."},
    ]
    report = auditor.audit_prompt_template_rules(templates)
    errors = [f for f in report.findings if f.rule == "bilingual_trigger_pollution"]
    assert len(errors) == 1
    assert report.passed is False


def test_audit_prompt_template_rules_passes_multilingual_flag(auditor: PromptAuditService):
    templates = [
        {"name": "beautify", "trigger": "beautify / re-layout / 重新排版", "prompt": "Enhance deck.", "is_multilingual": True},
    ]
    report = auditor.audit_prompt_template_rules(templates)
    errors = [f for f in report.findings if f.rule == "bilingual_trigger_pollution"]
    assert len(errors) == 0


def test_audit_prompt_template_rules_warns_missing_translate_note(auditor: PromptAuditService):
    templates = [
        {"name": "handoff", "trigger": "planning done", "prompt": "Type resume command.", "is_fixed_template": True, "has_translate_note": False},
    ]
    report = auditor.audit_prompt_template_rules(templates)
    warns = [f for f in report.findings if f.rule == "fixed_template_missing_translate_note"]
    assert len(warns) == 1


def test_prompt_audit_cli_defaults_passes(capsys):
    rc = prompt_audit_main([])
    assert rc == 0
    captured = capsys.readouterr()
    assert "[PromptAudit] PASS" in captured.out


def test_prompt_audit_cli_dict_file(tmp_path, capsys):
    dict_file = tmp_path / "locales.json"
    dict_file.write_text(json.dumps({
        "dictionaries": {
            "en": {"ok": "OK", "cancel": "Cancel"},
            "zh": {"ok": "确定", "cancel": "取消"},
        },
        "referenced_keys": ["ok", "cancel"],
    }))
    rc = prompt_audit_main(["--dict", str(dict_file), "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["passed"] is True


def test_prompt_audit_cli_detects_drift_failure(tmp_path, capsys):
    src_file = tmp_path / "en.md"
    tgt_file = tmp_path / "zh.md"
    src_file.write_text("## Intro\n\n```bash\ncode1\n```\n\n```bash\ncode2\n```")
    tgt_file.write_text("## 介绍\n\n```bash\ncode1\n```")  # missing 1 code block -> error
    rc = prompt_audit_main(["--doc", str(src_file), str(tgt_file)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "[PromptAudit] FAIL" in captured.err


def test_api_locale_audit_endpoint(client: TestClient):
    payload = {
        "dictionaries": {
            "en": {"title": "Title", "greeting": "Hello {name}"},
            "zh": {"title": "标题", "greeting": "你好 {name}"},
        },
        "referenced_keys": ["title", "greeting"],
    }
    resp = client.post("/api/evaluations/locale-audit", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True


def test_api_doc_translation_audit_endpoint(client: TestClient):
    payload = {
        "source_text": "# Guide\n\n```python\nrun()\n```",
        "target_text": "# 指南\n\n```python\nrun()\n```",
        "source_locale": "en",
        "target_locale": "zh",
    }
    resp = client.post("/api/evaluations/doc-translation-audit", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
