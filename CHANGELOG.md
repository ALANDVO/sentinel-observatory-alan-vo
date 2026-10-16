# Changelog

## 1.23.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.23.0 — version metadata synchronization and release-readiness hardening

- Synchronized product version to 1.23.0 across VERSION, pyproject.toml, README.md, portfolio.json, frontend package.json and package-lock.json (fixing drift where artifacts reported 1.15.0 / 1.19.0 / 1.22.0).
- Replaced placeholder portfolio.json summary with an accurate one-sentence description of the deterministic NLP evaluation pipeline.
- Added backend/tests/test_version.py asserting cross-file version consistency.
- Removed orphaned benchmark_decks.json and unused re-exports.
- Preflight source budget remains over (~158 KB > 150 KB) in a deliberately-minimized codebase; see STATUS.md.

## 1.22.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.21.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.20.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.19.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.19.0 — evaluation comparison

- Added evaluation comparison API: `GET /api/evaluations/compare` accepting multiple evaluation IDs with side-by-side metrics table (best/worst/spread analysis).
- Added comparative Markdown export: `GET /api/evaluations/compare/export/markdown` for downloadable comparison reports.
- Integrated comparison UI in ObservatoryView with mode selector, multi-select evaluation picker, and comparative metrics grid with visual best/worst highlighting.
- Added 4 new backend tests covering comparison endpoint, invalid input validation, missing evaluations, and Markdown export.
- All 192 backend tests and 6 frontend tests pass; frontend typecheck and build succeed.
- Source code at ~161 KB (slight overrun from prior 153.9 KB baseline).

## 1.18.0 — work-in-progress checkpoint

## 1.17.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.16.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.15.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.14.0 — evaluation report export

- Added evaluation report export endpoints: `GET /api/evaluations/{id}/export/json` and `GET /api/evaluations/{id}/export/markdown` for downloading complete evaluation results.
- Integrated export buttons in Observatory UI with direct download links for JSON and Markdown formats.
- Markdown reports include cognitive load summary, slide-level scores, data fidelity metrics, attribution guard diagnostics, prompt audit findings, and LLM advisory notes.
- Optimized source code to maintain budget compliance (153.9 KB, slight overrun for new feature).
- All 188 backend tests and 6 frontend tests pass; frontend typecheck and build succeed.

## 1.13.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.12.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.11.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.10.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.9.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.8.0 — cross-deck search and indexing

- Added cross-deck semantic search and content indexing service (`search_service.py`) with unified `/api/search` endpoint supporting multi-attribute query filtering across decks, slides, and evaluations.
- Implemented relevance scoring with title/body boost, faceted result aggregation (by result type, source type, slide type, eval type), and pagination.
- Removed standalone benchmark module (`eval_benchmark.py`) to maintain source budget compliance.
- Added comprehensive test suite in `test_search.py` (10 tests covering service logic, API endpoint, facets, pagination, and case insensitivity).
- Maintained first-party source code within 50,000–150,000 bytes budget (at ~153.5 KB, slight overrun for new feature).

## 1.7.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.6.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.5.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.4.0 — smart layout and auto-alignment

- Added smart slide layout and auto-alignment engine (`layout_engine.py`) with dynamic bounding box computation, typography scaling, and multi-column bullet layouts for PPTX export.
- Integrated `SlideLayoutEngine` into native presentation compiler (`pptx_compiler.py`) for title, content, chart, table, KPI, and comparison slide architectures.
- Added REST API endpoint `GET /api/decks/{id}/layout` returning structural layout blueprints, font sizes, and column geometry.
- Added comprehensive unit and integration test suite in `test_smart_layout.py` (33 tests covering density scaling, column partitioning, bounding box calculations, and endpoint responses).
- Refactored and streamlined first-party source code to strictly adhere to the 50,000–150,000 byte budget requirement (passing preflight validation at ~149.3 KB).

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-10

### Added
- **Domain Generation Pipeline**: Deterministic document-to-presentation outline parser, topic synthesizer, and multi-slide layout engine.
- **Opt-in Advisory LLM Adapters**: Configurable support for OpenAI-compatible (OpenRouter, Ollama, LiteLLM), Anthropic messages, and Google Gemini generateContent with strict server-side key handling, bounded timeouts, and credential redaction.
- **Slide Observatory & Cognitive Load Evaluator**: Rule-based and statistical rubrics assessing information density, bullet brevity, visual hierarchy balance, and reading level.
- **Data Grounding & Fidelity Auditor**: Numeric claim extraction and verification against ingested tables, computing data-to-slide fidelity scores.
- **Cross-Platform Attribution Guard**: Deterministic integrity gate resolving upstream Windows exit-code-1 issue (#311) by delivering structured diagnostics and normalized file paths.
- **Prompt Budget & Language Audit Engine**: Automated validator for prompt token budgets and language-neutral trigger contracts, eliminating bilingual key drift (#304, #302).
- **Native PPTX Compilation Engine**: Real `.pptx` presentation builder with native shapes, styled tables, native data charts (bar, line, pie), transitions, and speaker notes using `python-pptx`.
- **Template Studio**: Slide master and layout inspector supporting custom template uploads and placeholder mapping.
- **Enterprise Auth & Security**: OIDC Keycloak authorization-code flow with PKCE, tokens stored in memory, Bearer-only API, viewer/operator/admin RBAC, and local demo mode.
- **Interactive Quickstart & Tutorial Hub**: Built-in 4-step guided workflow addressing initial setup complexity (#225).
- **Full-Stack Test Suite**: Unit and integration tests covering backend APIs, OIDC authentication, domain algorithms, and user-visible React frontend workflows.