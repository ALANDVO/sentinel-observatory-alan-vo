"""Prompt budget and multilingual dictionary audit engine. Resolves #304, #303, #302."""
from __future__ import annotations
import json, re, sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_MODEL_WINDOWS: dict[str, int] = {
    "gpt-3.5-turbo": 4096, "gpt-4": 8192, "gpt-4o": 128000, "gpt-4o-mini": 128000,
    "claude-3-haiku-20240307": 200000, "claude-3-sonnet-20240229": 200000,
    "gemini-1.5-flash": 1048576, "gemini-1.5-pro": 2097152,
}
_BILINGUAL_SUFFIX_RE = re.compile(r"_(?:zh|en|ja|fr|de|es|pt|ko|ar)(?:_[a-z]{2})?$", re.I)
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")
_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_MD_CODE_BLOCK_RE = re.compile(r"^```", re.MULTILINE)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_MD_TABLE_ROW_RE = re.compile(r"^\|.+\|$", re.MULTILINE)

def _estimate_tokens(text: str) -> int:
    c = len(_CJK_RE.findall(text))
    return int((len(text) - c) / 4 + c / 2)

@dataclass
class AuditFinding:
    rule: str; severity: str; message: str; location: str | None = None; suggestion: str | None = None

@dataclass
class PromptAuditReport:
    passed: bool; total_tokens_estimated: int; model_window: int | None
    findings: list[AuditFinding] = field(default_factory=list)
    def to_dict(self) -> dict:
        return {"passed": self.passed, "total_tokens_estimated": self.total_tokens_estimated,
                "model_window": self.model_window, "findings": [vars(f) for f in self.findings]}

class PromptAuditService:
    def audit_slide_content(self, slides: list[dict[str, Any]], model: str = "gpt-4o-mini", locale_keys_per_slide: list[dict[str, str]] | None = None) -> PromptAuditReport:
        fnd: list[AuditFinding] = []
        full = " ".join(f"{s.get('title') or ''} {s.get('body_text') or ''} {s.get('speaker_notes') or ''}" for s in slides)
        toks, win = _estimate_tokens(full), _MODEL_WINDOWS.get(model)
        if win and toks > int(win * 0.8):
            fnd.append(AuditFinding("token_budget_80pct", "warning", f"Tokens ({toks}) exceeds 80% of {model} window ({win}).", suggestion="Condense content."))
        if locale_keys_per_slide:
            for i, kd in enumerate(locale_keys_per_slide):
                for k in kd:
                    if _BILINGUAL_SUFFIX_RE.search(k):
                        fnd.append(AuditFinding("bilingual_key_suffix_pollution", "error", f"Key '{k}' uses language suffix violating schema.", location=f"slide_index={i}", suggestion="Use neutral keys."))
        for i, s in enumerate(slides):
            if _CJK_RE.search(s.get("body_text") or "") and not s.get("locale_override"):
                fnd.append(AuditFinding("cjk_content_without_locale_override", "info", f"Slide {i} has CJK chars without locale_override.", location=f"slide_id={s.get('id', i)}"))
            if (nt := _estimate_tokens(s.get("speaker_notes") or "")) > 500:
                fnd.append(AuditFinding("speaker_notes_token_limit", "warning", f"Speaker notes for slide {i} ({nt} tokens) exceeds 500.", location=f"slide_id={s.get('id', i)}", suggestion="Trim notes."))
        return PromptAuditReport(not any(x.severity == "error" for x in fnd), toks, win, fnd)

    def audit_locale_dictionary(self, dictionaries: dict[str, dict[str, str]], referenced_keys: list[str] | set[str] | None = None) -> PromptAuditReport:
        fnd: list[AuditFinding] = []
        if not dictionaries: return PromptAuditReport(True, 0, None)
        locs = list(dictionaries.keys())
        r_loc, r_dict = locs[0], dictionaries[locs[0]]
        r_keys = set(r_dict.keys())
        for loc in locs[1:]:
            lk = set(dictionaries[loc].keys())
            if miss := r_keys - lk: fnd.append(AuditFinding("locale_key_parity_missing", "error", f"Locale '{loc}' missing keys vs '{r_loc}': {sorted(miss)[:10]}", location=f"locale={loc}"))
            if extra := lk - r_keys: fnd.append(AuditFinding("locale_key_parity_extra", "warning", f"Locale '{loc}' extra keys: {sorted(extra)[:10]}", location=f"locale={loc}"))
        for k in r_keys:
            if _BILINGUAL_SUFFIX_RE.search(k): fnd.append(AuditFinding("bilingual_key_in_reference_locale", "error", f"Reference locale contains suffixed key: '{k}'"))
        for loc, ld in dictionaries.items():
            for k, val in ld.items():
                if not str(val).strip(): fnd.append(AuditFinding("empty_translation_value", "error", f"Locale '{loc}' empty value for '{k}'.", location=f"locale={loc}, key={k}"))
                if k in r_dict:
                    rp, lp = set(_PLACEHOLDER_RE.findall(str(r_dict[k]))), set(_PLACEHOLDER_RE.findall(str(val)))
                    if rp != lp: fnd.append(AuditFinding("placeholder_parity_mismatch", "error", f"Locale '{loc}' key '{k}' placeholder mismatch: missing {sorted(rp - lp)}, extra {sorted(lp - rp)} (expected {sorted(rp)}).", location=f"locale={loc}, key={k}"))
        if referenced_keys is not None:
            r_set = set(referenced_keys)
            for k in sorted(r_keys):
                if k not in r_set: fnd.append(AuditFinding("unused_dictionary_key", "warning", f"Key '{k}' not in referenced_keys.", location=f"key={k}"))
        return PromptAuditReport(not any(x.severity == "error" for x in fnd), _estimate_tokens(str(dictionaries)), None, fnd)

    def audit_markdown_translation_drift(self, source_md: str, target_md: str, source_locale: str = "en", target_locale: str = "zh") -> PromptAuditReport:
        fnd: list[AuditFinding] = []
        sh = [m.group(1) for m in _MD_HEADING_RE.finditer(source_md)]
        th = [m.group(1) for m in _MD_HEADING_RE.finditer(target_md)]
        if len(sh) != len(th): fnd.append(AuditFinding("heading_count_drift", "warning", f"Heading drift: {source_locale}={len(sh)}, {target_locale}={len(th)}."))
        sc, tc = len(_MD_CODE_BLOCK_RE.findall(source_md)) // 2, len(_MD_CODE_BLOCK_RE.findall(target_md)) // 2
        if sc != tc: fnd.append(AuditFinding("code_block_drift", "error", f"Code block drift: {source_locale}={sc}, {target_locale}={tc}."))
        sr, tr = len(_MD_TABLE_ROW_RE.findall(source_md)), len(_MD_TABLE_ROW_RE.findall(target_md))
        if abs(sr - tr) > 1: fnd.append(AuditFinding("table_row_count_drift", "warning", f"Table drift: {source_locale}={sr}, {target_locale}={tr}."))
        sl, tl = _MD_LINK_RE.findall(source_md), _MD_LINK_RE.findall(target_md)
        if len(sl) != len(tl): fnd.append(AuditFinding("link_count_drift", "warning", f"Link drift: {source_locale}={len(sl)}, {target_locale}={len(tl)}."))
        ts = {re.sub(r"[^\w\-]", "", m.group(2).lower().replace(" ", "-")) for m in _MD_HEADING_RE.finditer(target_md)}
        for txt, href in tl:
            if href.startswith("#") and len(href) > 1 and href[1:].lower() not in ts:
                fnd.append(AuditFinding("unresolved_anchor_reference", "error", f"Anchor '{href}' missing in {target_locale} doc.", location=f"href={href}"))
        return PromptAuditReport(not any(x.severity == "error" for x in fnd), _estimate_tokens(source_md) + _estimate_tokens(target_md), None, fnd)

    def audit_prompt_template_rules(self, templates: list[dict[str, Any]]) -> PromptAuditReport:
        fnd: list[AuditFinding] = []
        for i, t in enumerate(templates):
            trig, ptext = t.get("trigger") or "", t.get("prompt") or ""
            if _CJK_RE.search(trig) and not t.get("is_multilingual"):
                fnd.append(AuditFinding("bilingual_trigger_pollution", "error", f"Trigger '{trig[:30]}' has CJK chars.", location=f"index={i}"))
            if t.get("is_fixed_template") and not t.get("has_translate_note") and not _CJK_RE.search(ptext):
                fnd.append(AuditFinding("fixed_template_missing_translate_note", "warning", f"Template '{t.get('name', i)}' lacks translate note.", location=f"index={i}"))
        return PromptAuditReport(not any(x.severity == "error" for x in fnd), _estimate_tokens(" ".join(str(t) for t in templates)), None, fnd)

def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Prompt budget and locale dictionary audit gate")
    p.add_argument("--json", action="store_true", help="Output in JSON")
    p.add_argument("--dict", dest="dict_file", help="Path to JSON dictionary")
    p.add_argument("--doc", nargs=2, metavar=("SRC", "TGT"), help="Paths to source and target markdown files")
    args = p.parse_args(argv)
    svc = PromptAuditService()
    if args.dict_file:
        data = json.loads(Path(args.dict_file).read_text("utf-8"))
        rep = svc.audit_locale_dictionary(data.get("dictionaries", data), referenced_keys=data.get("referenced_keys"))
    elif args.doc:
        rep = svc.audit_markdown_translation_drift(Path(args.doc[0]).read_text("utf-8"), Path(args.doc[1]).read_text("utf-8"))
    else:
        rep = svc.audit_locale_dictionary({"en": {"title": "Deck", "slides": "{n} slides"}, "zh": {"title": "幻灯片", "slides": "{n} 页"}, "ja": {"title": "スライド", "slides": "{n} 枚"}})
    if args.json:
        sys.stdout.write(json.dumps(rep.to_dict(), indent=2) + "\n")
    else:
        st = "PASS" if rep.passed else "FAIL"
        errs, warns = [f for f in rep.findings if f.severity == "error"], [f for f in rep.findings if f.severity == "warning"]
        out = sys.stdout if rep.passed else sys.stderr
        out.write(f"[PromptAudit] {st}: {len(errs)} error(s), {len(warns)} warning(s).\n")
        for f in rep.findings: out.write(f"  * {f.rule} ({f.severity.upper()}): {f.message}\n")
    return 0 if rep.passed else 1

if __name__ == "__main__":
    sys.exit(main())
