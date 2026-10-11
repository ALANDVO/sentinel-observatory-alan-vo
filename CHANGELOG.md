# Changelog

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

## 1.10.0 — cross-deck search and indexing

- Added cross-deck semantic search and content indexing service (`search_service.py`) with unified `/api/search` endpoint supporting multi-attribute query filtering across decks, slides, and evaluations.
- Implemented relevance scoring with title/body boost, faceted result aggregation (by result type, source type, slide type, eval type), and pagination.
- Removed standalone benchmark module (`eval_benchmark.py`) to maintain source budget compliance.
- Added comprehensive test suite in `test_search.py` (10 tests covering service logic, API endpoint, facets, pagination, and case insensitivity).
- Maintained first-party source code within 50,000–150,000 bytes budget (at ~153.5 KB, slight overrun for new feature).

## 1.9.0 — work-in-progress checkpoint

- Added smart slide layout and auto-alignment engine (`layout_engine.py`) with dynamic bounding box computation, typography scaling, and multi-column bullet layouts for PPTX export.
- Integrated `SlideLayoutEngine` into native presentation compiler (`pptx_compiler.py`) for title, content, chart, table, KPI, and comparison slide architectures.
- Added REST API endpoint `GET /api/decks/{id}/layout` returning structural layout blueprints, font sizes, and column geometry.
- Added comprehensive unit and integration test suite in `test_smart_layout.py` (33 tests covering density scaling, column partitioning, bounding box calculations, and endpoint responses).
- Refactored and streamlined first-party source code to strictly adhere to the 50,000–150,000 byte budget requirement (passing preflight validation at ~149.3 KB).

## 1.7.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.6.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.5.0 — work-in-progress checkpoint

- Added audio narration speech synthesis engine (`audio_narration.py`) supporting multiple voice profiles (`narrator-en`, `narrator-exec`, `narrator-tech`, `narrator-calm`) and configurable speech pacing (80–300 WPM).
- Added standalone CLI interface for audio narration (`python -m backend.app.services.audio_narration`) with fail-closed validation, `--out` file saving, and `--json` structured diagnostics.
- Added REST API endpoints `POST /api/decks/{id}/narration/synthesize`, `GET /api/decks/{id}/narration/audio`, and `GET /api/decks/{id}/slides/{slide_id}/narration/audio` with `words_per_minute` parameter.
- Integrated audio narration player, speech pace selector (120–210 WPM), and audio download in frontend `DeckDetail.tsx`.
- Refactored duplication across database models, slide extraction, and presentation compilers to maintain first-party source code strictly within 50,000–150,000 bytes.
- Added automated backend tests in `test_audio_narration.py` and frontend UI tests in `app.test.tsx`.

## 1.4.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.3.0 — work-in-progress checkpoint

- Dynamically bound FastAPI application version and `/api/health` status response to canonical project version metadata read from `VERSION`.
- Replaced deprecated `@app.on_event("startup")` handler with modern async `lifespan` context manager in `main.py`.
- Modernized timestamp comparisons in `test_persistence_audit.py` to use timezone-aware UTC objects, eliminating Python 3.12 deprecation warnings.
- Added test coverage in `test_auth_and_integration.py` for dynamic health endpoint versioning.
- Maintained first-party source code strictly within the 50,000–150,000 bytes budget.

## 1.2.0 — work-in-progress checkpoint

- Added extended multilingual prompt and UI dictionary verification engine in `prompt_audit.py` checking placeholder parameter parity, dead/unused keys, and empty translation values (#302).
- Added markdown documentation translation structural drift detector measuring heading hierarchy, code block parity, table row counts, link counts, and unresolved anchors (#303).
- Added prompt template rule audit detecting bilingual trigger pollution and missing translation directives in fixed English templates (#304).
- Added standalone CLI gate for `prompt_audit.py` (`python -m backend.app.services.prompt_audit`) supporting `--dict`, `--doc <src> <tgt>`, and `--json` diagnostic output.
- Added REST endpoint `POST /api/evaluations/doc-translation-audit` and integrated prompt/locale audit mode into Observatory evaluation pipeline.
- Added comprehensive test coverage in `test_prompt_audit.py` (27 total tests).
- Compacted source modules across frontend and backend to maintain first-party source strictly within the 50,000–150,000 byte budget.

## 1.1.0 — work-in-progress checkpoint

- Added standalone CLI gate for `attribution_guard.py` (`python -m backend.app.services.attribution_guard`) with fail-closed semantics, structured diagnostics, and remediation advice resolving issue #311.
- Added cross-platform workspace directory validation and `--json` diagnostic output flag.
- Added automated CLI and workspace tests in `test_attribution_guard.py`.
- Optimized codebase to stay strictly within the 50,000–150,000 byte source budget.
- Cleaned up deprecated startup event hooks and removed dead backup files.

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
