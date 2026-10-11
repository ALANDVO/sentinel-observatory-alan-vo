"""Prompt budget and multilingual dictionary audit engine. Resolves #304, #303, #302."""
from __future__ import annotations
import json, re, sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_WIN = {"gpt-3.5-turbo": 4096, "gpt-4": 8192, "gpt-4o": 128000, "gpt-4o-mini": 128000, "claude-3-haiku-20240307": 200000, "gemini-1.5-flash": 1048576, "gemini-1.5-pro": 2097152}
_SUF, _CJK, _PH = re.compile(r"_(?:zh|en|ja|fr|de|es|pt|ko|ar)(?:_[a-z]{2})?$", re.I), re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]"), re.compile(r"\{([a-zA-Z0-9_]+)\}")
_MD_H, _MD_C, _MD_L, _MD_T = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE), re.compile(r"^```", re.MULTILINE), re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), re.compile(r"^\|.+\|$", re.MULTILINE)

def _estimate_tokens(t: str) -> int:
    c = len(_CJK.findall(t)); return int((len(t) - c) / 4 + c / 2)

@dataclass
class AuditFinding:
    rule: str; severity: str; message: str; location: str | None = None

@dataclass
class PromptAuditReport:
    passed: bool; total_tokens_estimated: int; model_window: int | None; findings: list[AuditFinding] = field(default_factory=list)
    def to_dict(self) -> dict: return {"passed": self.passed, "total_tokens_estimated": self.total_tokens_estimated, "model_window": self.model_window, "findings": [vars(f) for f in self.findings]}

class PromptAuditService:
    def audit_slide_content(self, slides: list[dict[str, Any]], model: str = "gpt-4o-mini", locale_keys_per_slide: list[dict[str, str]] | None = None) -> PromptAuditReport:
        f: list[AuditFinding] = []
        tx = " ".join(f"{s.get('title') or ''} {s.get('body_text') or ''} {s.get('speaker_notes') or ''}" for s in slides)
        tk, w = _estimate_tokens(tx), _WIN.get(model)
        if w and tk > int(w * 0.8): f.append(AuditFinding("token_budget_80pct", "warning", f"Tokens ({tk}) > 80% of {model} window ({w})."))
        if locale_keys_per_slide:
            for i, kd in enumerate(locale_keys_per_slide):
                for k in kd:
                    if _SUF.search(k): f.append(AuditFinding("bilingual_key_suffix_pollution", "error", f"Key {k} uses lang suffix", location=f"slide_index={i}"))
        for i, s in enumerate(slides):
            if _CJK.search(s.get("body_text") or "") and not s.get("locale_override"): f.append(AuditFinding("cjk_content_without_locale_override", "info", f"Slide {i} has CJK without locale_override.", location=f"slide_id={s.get('id', i)}"))
            if (nt := _estimate_tokens(s.get("speaker_notes") or "")) > 500: f.append(AuditFinding("speaker_notes_token_limit", "warning", f"Slide {i} notes ({nt} tokens) > 500.", location=f"slide_id={s.get('id', i)}"))
        return PromptAuditReport(not any(x.severity == "error" for x in f), tk, w, f)

    def audit_locale_dictionary(self, dictionaries: dict[str, dict[str, str]], referenced_keys: list[str] | set[str] | None = None) -> PromptAuditReport:
        f: list[AuditFinding] = []
        if not dictionaries: return PromptAuditReport(True, 0, None)
        ls = list(dictionaries.keys()); rd, rks = dictionaries[ls[0]], set(dictionaries[ls[0]].keys())
        for loc in ls[1:]:
            lk = set(dictionaries[loc].keys())
            if m := rks - lk: f.append(AuditFinding("locale_key_parity_missing", "error", f"Locale {loc} missing keys: {sorted(m)[:5]}", location=f"locale={loc}"))
            if e := lk - rks: f.append(AuditFinding("locale_key_parity_extra", "warning", f"Locale {loc} extra keys: {sorted(e)[:5]}", location=f"locale={loc}"))
        for k in rks:
            if _SUF.search(k): f.append(AuditFinding("bilingual_key_in_reference_locale", "error", f"Suffixed key: {k}"))
        for loc, ld in dictionaries.items():
            for k, v in ld.items():
                if not str(v).strip(): f.append(AuditFinding("empty_translation_value", "error", f"Locale {loc} empty value for {k}", location=f"locale={loc}, key={k}"))
                if k in rd:
                    rp, lp = set(_PH.findall(str(rd[k]))), set(_PH.findall(str(v)))
                    if rp != lp: f.append(AuditFinding("placeholder_parity_mismatch", "error", f"Locale '{loc}' key '{k}' placeholder mismatch: miss {sorted(rp - lp)}, extra {sorted(lp - rp)}", location=f"locale={loc}, key={k}"))
        if referenced_keys is not None:
            rs = set(referenced_keys)
            for k in sorted(rks):
                if k not in rs: f.append(AuditFinding("unused_dictionary_key", "warning", f"Key {k} not referenced", location=f"key={k}"))
        return PromptAuditReport(not any(x.severity == "error" for x in f), _estimate_tokens(str(dictionaries)), None, f)

    def audit_markdown_translation_drift(self, source_md: str, target_md: str, source_locale: str = "en", target_locale: str = "zh") -> PromptAuditReport:
        f: list[AuditFinding] = []
        sh, th = [m.group(1) for m in _MD_H.finditer(source_md)], [m.group(1) for m in _MD_H.finditer(target_md)]
        if len(sh) != len(th): f.append(AuditFinding("heading_count_drift", "warning", f"Heading drift: {source_locale}={len(sh)}, {target_locale}={len(th)}."))
        sc, tc = len(_MD_C.findall(source_md)) // 2, len(_MD_C.findall(target_md)) // 2
        if sc != tc: f.append(AuditFinding("code_block_drift", "error", f"Code block drift: {source_locale}={sc}, {target_locale}={tc}."))
        sr, tr = len(_MD_T.findall(source_md)), len(_MD_T.findall(target_md))
        if abs(sr - tr) > 1: f.append(AuditFinding("table_row_count_drift", "warning", f"Table drift: {source_locale}={sr}, {target_locale}={tr}."))
        sl, tl = _MD_L.findall(source_md), _MD_L.findall(target_md)
        if len(sl) != len(tl): f.append(AuditFinding("link_count_drift", "warning", f"Link drift: {source_locale}={len(sl)}, {target_locale}={len(tl)}."))
        ts = {re.sub(r"[^\w\-]", "", m.group(2).lower().replace(" ", "-")) for m in _MD_H.finditer(target_md)}
        for _, h in tl:
            if h.startswith("#") and len(h) > 1 and h[1:].lower() not in ts: f.append(AuditFinding("unresolved_anchor_reference", "error", f"Anchor '{h}' missing in {target_locale}.", location=f"href={h}"))
        return PromptAuditReport(not any(x.severity == "error" for x in f), _estimate_tokens(source_md) + _estimate_tokens(target_md), None, f)

    def audit_prompt_template_rules(self, templates: list[dict[str, Any]]) -> PromptAuditReport:
        f: list[AuditFinding] = []
        for i, tm in enumerate(templates):
            tr, pt = tm.get("trigger") or "", tm.get("prompt") or ""
            if _CJK.search(tr) and not tm.get("is_multilingual"): f.append(AuditFinding("bilingual_trigger_pollution", "error", f"Trigger '{tr[:30]}' has CJK chars.", location=f"index={i}"))
            if tm.get("is_fixed_template") and not tm.get("has_translate_note") and not _CJK.search(pt): f.append(AuditFinding("fixed_template_missing_translate_note", "warning", f"Template '{tm.get('name', i)}' lacks translate note.", location=f"index={i}"))
        return PromptAuditReport(not any(x.severity == "error" for x in f), _estimate_tokens(" ".join(str(t) for t in templates)), None, f)

def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Prompt audit gate")
    p.add_argument("--json", action="store_true"); p.add_argument("--dict", dest="dict_file"); p.add_argument("--doc", nargs=2, metavar=("SRC", "TGT"))
    args = p.parse_args(argv); svc = PromptAuditService()
    if args.dict_file:
        data = json.loads(Path(args.dict_file).read_text("utf-8"))
        rep = svc.audit_locale_dictionary(data.get("dictionaries", data), referenced_keys=data.get("referenced_keys"))
    elif args.doc: rep = svc.audit_markdown_translation_drift(Path(args.doc[0]).read_text("utf-8"), Path(args.doc[1]).read_text("utf-8"))
    else: rep = svc.audit_locale_dictionary({"en": {"title": "Deck", "slides": "{n} slides"}, "zh": {"title": "幻灯片", "slides": "{n} 页"}, "ja": {"title": "スライド", "slides": "{n} 枚"}})
    if args.json: sys.stdout.write(json.dumps(rep.to_dict(), indent=2) + "\n")
    else:
        out = sys.stdout if rep.passed else sys.stderr
        out.write(f"[PromptAudit] {'PASS' if rep.passed else 'FAIL'}: {len([f for f in rep.findings if f.severity == 'error'])} error(s), {len([f for f in rep.findings if f.severity == 'warning'])} warning(s).\n")
        for f in rep.findings: out.write(f"  * {f.rule} ({f.severity.upper()}): {f.message}\n")
    return 0 if rep.passed else 1

if __name__ == "__main__": sys.exit(main())