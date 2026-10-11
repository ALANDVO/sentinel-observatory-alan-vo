# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

i18n-dictionary-completeness

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

