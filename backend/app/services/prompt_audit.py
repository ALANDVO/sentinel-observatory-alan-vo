"""Prompt budget and language audit engine.

Validates prompt token budgets and enforces language-neutral schemas.
Addresses upstream issues #304 and #302.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_MODEL_WINDOWS: dict[str, int] = {
    "gpt-3.5-turbo": 4096, "gpt-4": 8192, "gpt-4o": 128000, "gpt-4o-mini": 128000,
    "claude-3-haiku-20240307": 200000, "claude-3-sonnet-20240229": 200000,
    "gemini-1.5-flash": 1048576, "gemini-1.5-pro": 2097152,
}
_BILINGUAL_SUFFIX_RE = re.compile(r"_(?:zh|en|ja|fr|de|es|pt|ko|ar)(?:_[a-z]{2})?$", re.I)
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")


def _estimate_tokens(text: str) -> int:
    cjk = len(_CJK_RE.findall(text))
    return int((len(text) - cjk) / 4 + cjk / 2)


@dataclass
class AuditFinding:
    rule: str
    severity: str
    message: str
    location: str | None = None
    suggestion: str | None = None


@dataclass
class PromptAuditReport:
    passed: bool
    total_tokens_estimated: int
    model_window: int | None
    findings: list[AuditFinding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"passed": self.passed, "total_tokens_estimated": self.total_tokens_estimated, "model_window": self.model_window, "findings": [vars(f) for f in self.findings]}


class PromptAuditService:
    """Audits slide content and prompt text for budget and language compliance."""

    def audit_slide_content(self, slides: list[dict[str, Any]], model: str = "gpt-4o-mini", locale_keys_per_slide: list[dict[str, str]] | None = None) -> PromptAuditReport:
        findings: list[AuditFinding] = []
        full_text = " ".join(f"{s.get('title') or ''} {s.get('body_text') or ''} {s.get('speaker_notes') or ''}" for s in slides)
        tokens = _estimate_tokens(full_text)
        window = _MODEL_WINDOWS.get(model)

        if window and tokens > int(window * 0.80):
            findings.append(AuditFinding("token_budget_80pct", "warning", f"Estimated tokens ({tokens}) exceeds 80% of {model} window ({window}).", suggestion="Condense content."))

        if locale_keys_per_slide:
            for i, kdict in enumerate(locale_keys_per_slide):
                for k in kdict:
                    if _BILINGUAL_SUFFIX_RE.search(k):
                        findings.append(AuditFinding("bilingual_key_suffix_pollution", "error", f"Key '{k}' uses language suffix violating language-neutral schema.", location=f"slide_index={i}", suggestion="Use language-neutral keys."))

        for i, s in enumerate(slides):
            if _CJK_RE.search(s.get("body_text") or "") and not s.get("locale_override"):
                findings.append(AuditFinding("cjk_content_without_locale_override", "info", f"Slide at index {i} has CJK chars without locale_override.", location=f"slide_id={s.get('id', i)}"))
            n_tok = _estimate_tokens(s.get("speaker_notes") or "")
            if n_tok > 500:
                findings.append(AuditFinding("speaker_notes_token_limit", "warning", f"Speaker notes for slide {i} estimated at {n_tok} tokens (>500).", location=f"slide_id={s.get('id', i)}", suggestion="Trim speaker notes."))

        errors = [f for f in findings if f.severity == "error"]
        return PromptAuditReport(passed=len(errors) == 0, total_tokens_estimated=tokens, model_window=window, findings=findings)

    def audit_locale_dictionary(self, dictionaries: dict[str, dict[str, str]]) -> PromptAuditReport:
        findings: list[AuditFinding] = []
        if not dictionaries:
            return PromptAuditReport(passed=True, total_tokens_estimated=0, model_window=None)

        locales = list(dictionaries.keys())
        ref_loc = locales[0]
        ref_keys = set(dictionaries[ref_loc].keys())

        for loc in locales[1:]:
            loc_keys = set(dictionaries[loc].keys())
            missing = ref_keys - loc_keys
            extra = loc_keys - ref_keys
            if missing:
                findings.append(AuditFinding("locale_key_parity_missing", "error", f"Locale '{loc}' missing keys vs '{ref_loc}': {sorted(missing)[:10]}", location=f"locale={loc}"))
            if extra:
                findings.append(AuditFinding("locale_key_parity_extra", "warning", f"Locale '{loc}' has extra keys: {sorted(extra)[:10]}", location=f"locale={loc}"))

        for k in ref_keys:
            if _BILINGUAL_SUFFIX_RE.search(k):
                findings.append(AuditFinding("bilingual_key_in_reference_locale", "error", f"Reference locale contains suffixed key: '{k}'"))

        errors = [f for f in findings if f.severity == "error"]
        return PromptAuditReport(passed=len(errors) == 0, total_tokens_estimated=_estimate_tokens(str(dictionaries)), model_window=None, findings=findings)
