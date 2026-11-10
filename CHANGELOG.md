# Changelog

## 1.27.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.26.0 — Version synchronization and PPTX Compiler CLI

- Fixed version synchronization across all artifacts: VERSION (1.26.0), pyproject.toml, frontend/package.json, frontend/package-lock.json, and portfolio.json now all report 1.26.0; backend/tests/test_version.py passes.
- PPTX Compiler CLI (`python -m backend.app.services.pptx_compiler`) validated: executes via CLI with JSON input file, supports --output for PPTX file and --json for base64-encoded JSON output, fails closed on errors with actionable diagnostics, supports template_path in input JSON for custom templates.
- All 194 backend tests pass; 6 frontend tests pass.

## 1.25.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.25.0 — PPTX Compiler CLI enhancement and version synchronization

- Enhanced PPTX Compiler CLI (`python -m backend.app.services.pptx_compiler`) to accept both `template_path` (per acceptance criteria) and `template` (legacy compatibility) keys in input JSON for custom template loading; updated help text to document `template_path`.
- Fixed version synchronization across all artifacts: VERSION (1.25.0), pyproject.toml, frontend/package.json, frontend/package-lock.json, and portfolio.json now all report 1.25.0; backend/tests/test_version.py passes.
- All 194 backend tests pass; 6 frontend tests pass.

## 1.24.0 — work-in-progress checkpoint

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
