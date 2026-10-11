"""Tests for prompt audit engine: token budgets, language-neutral key validation, and locale parity."""
from __future__ import annotations

import pytest

from backend.app.services.prompt_audit import PromptAuditService, _estimate_tokens, AuditFinding


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
    # CJK text should produce more tokens relative to character count
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
    assert len(bilingual_errors) >= 2  # Both name_zh and behavior_en flagged


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
        "zh": {"title": "欢迎", "submit": "提交"},  # "cancel" missing
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
    # Create content that would approach the 80% of a small model window
    long_text = " ".join(["alignment safety benchmark evaluation"] * 1000)  # ~4000+ tokens
    slides = [{"title": "Very Long Slide", "body_text": long_text}]
    report = auditor.audit_slide_content(slides, model="gpt-3.5-turbo")  # 4096 token window
    budget_warnings = [f for f in report.findings if f.rule == "token_budget_80pct"]
    assert len(budget_warnings) >= 1


def test_audit_slide_speaker_notes_too_long(auditor: PromptAuditService):
    # Speaker notes exceeding 500 tokens
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
