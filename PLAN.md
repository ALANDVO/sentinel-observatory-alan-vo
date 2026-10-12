# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

evaluation-report-export

## Roadmap

### attribution-guard-cli — Attribution Guard Standalone CLI and Diagnostic Integrity Gate (#311)

Status: done

Acceptance:
- attribution_guard.py executes directly via CLI with normalized cross-platform paths, fails closed on errors with actionable diagnostics printed to stderr/stdout (never silent exit 1), and supports --json reporting

Implementation: `backend/app/services/attribution_guard.py`

Tests: `backend/tests/test_attribution_guard.py`

### source-budget-optimization — Source Budget Optimization and Deprecation Cleanup

Status: done

Acceptance:
- Maintain first-party source code strictly within 50,000–150,000 bytes budget and pass preflight inspection

Implementation: `backend/app/services/pptx_compiler.py`, `backend/app/api/decks.py`, `backend/app/services/evaluator.py`, `backend/app/services/eval_benchmark.py`

Tests: `backend/tests/test_pptx_compiler.py`, `backend/tests/test_deck_generation.py`, `backend/tests/test_evaluations.py`

### i18n-dictionary-completeness — Extended Multilingual Prompt and UI Dictionary Verification (#302, #303)

Status: done

Acceptance:
- Validate additional language mappings and synchronizations across locale bundles, checking placeholder parity, unused keys, empty values, markdown structural drift, and prompt template trigger pollution

Implementation: `backend/app/services/prompt_audit.py`, `backend/app/api/evaluations.py`

Tests: `backend/tests/test_prompt_audit.py`

### dynamic-version-and-lifespan — Dynamic Version Exposure and FastAPI Lifespan Handler Migration

Status: done

Acceptance:
- Expose dynamic product version metadata in /api/health and FastAPI OpenAPI specs read from VERSION, and migrate deprecated on_event startup handler to async lifespan context manager with clean timezone-aware UTC tests

Implementation: `backend/app/main.py`, `backend/app/api/health.py`

Tests: `backend/tests/test_auth_and_integration.py`, `backend/tests/test_persistence_audit.py`

### audio-narration-pacing — Audio Narration Speech Synthesis and Variable Pacing Engine

Status: done

Acceptance:
- Synthesize offline deterministic RIFF/WAVE PCM audio tracks for deck speaker notes with multiple voices (narrator-en, narrator-exec, narrator-tech, narrator-calm) and configurable speech pacing (80-300 WPM)
- Provide standalone CLI (python -m backend.app.services.audio_narration) with fail-closed diagnostics, --out, and --json reporting
- Expose REST API endpoints /api/decks/{id}/narration/synthesize and /api/decks/{id}/narration/audio with words_per_minute parameter
- Support UI narration player, WPM pace selector, and audio download in DeckDetail.tsx
- Maintain first-party source code strictly within 50,000–150,000 bytes budget and pass preflight inspection

Implementation: `backend/app/services/audio_narration.py`, `backend/app/api/decks.py`, `frontend/src/components/DeckDetail.tsx`

Tests: `backend/tests/test_audio_narration.py`, `frontend/src/__tests__/app.test.tsx`

### export-pptx-smart-layout — Smart Layout and Auto-Alignment Engine for PPTX Export

Status: done

Acceptance:
- Calculate dynamic bounding boxes and proportional typography scaling based on bullet text density for complex shapes during PPTX generation
- Integrate dynamic bounding boxes into native presentation compilation for all slide types (title, content, chart, table, KPI, comparison)
- Expose GET /api/decks/{deck_id}/layout endpoint returning slide typography specs, density classes, and column boxes
- Maintain first-party source code strictly within 50,000–150,000 bytes budget and pass preflight inspection

Implementation: `backend/app/services/layout_engine.py`, `backend/app/services/pptx_compiler.py`, `backend/app/api/decks.py`

Tests: `backend/tests/test_smart_layout.py`

### cross-deck-search-and-indexing — Cross-Deck Semantic Search and Content Indexing

Status: done

Acceptance:
- Enable indexed multi-attribute query filtering across generated presentations, slide transcripts, and evaluation benchmarks via unified /api/search endpoint with relevance scoring, faceted results, and pagination

Implementation: `backend/app/services/search_service.py`, `backend/app/api/search.py`

Tests: `backend/tests/test_search.py`

### evaluation-report-export — Evaluation Report Export (JSON & Markdown)

Status: done

Acceptance:
- Add GET /api/evaluations/{id}/export/json and GET /api/evaluations/{id}/export/markdown endpoints for downloading complete evaluation results
- Integrate export buttons in Observatory UI with direct download links
- Markdown reports include cognitive load summary, slide-level scores, data fidelity metrics, attribution guard diagnostics, prompt audit findings, and LLM advisory notes
- Maintain first-party source code within 50,000–150,000 bytes budget
- All backend and frontend tests pass

Implementation: `backend/app/api/evaluations.py`, `frontend/src/components/ObservatoryView.tsx`, `frontend/src/api.ts`

Tests: `backend/tests/test_evaluations.py`, `frontend/src/__tests__/app.test.tsx`

