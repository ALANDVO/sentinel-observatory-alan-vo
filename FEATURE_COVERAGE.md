# Feature Coverage: Sentinel Observatory

Sentinel Observatory (`sentinel-observatory-alan-vo`) is an AI-powered presentation generation and slide-intelligence observatory designed and authored by Alan Vo (`alanvo@gmail.com`). It bridges generative document-to-presentation workflows with rigorous AI/ML quality evaluation, attribution guards, data grounding verification, and native PowerPoint (`.pptx`) compilation.

## Core Capabilities & Implementation Matrix

| Capability | Subsystem / Implementation Path | Acceptance Test Coverage | Status & Missing Behavior |
| :--- | :--- | :--- | :--- |
| **1. Document / Topic Deck Generation** | `backend/app/services/slide_generator.py`<br>`backend/app/services/nlp_engine.py`<br>`backend/app/api/decks.py` | `backend/tests/test_deck_generation.py`<br>`frontend/src/__tests__/app.test.tsx` | Complete. Deterministic outline parsing, topic decomposition, slide type categorization (title, KPI, comparison, chart, table, process), speaker notes synthesis, and narration script generation. |
| **2. Opt-in Advisory LLM Adapter** | `backend/app/services/llm_adapters.py`<br>`backend/app/core/config.py` | `backend/tests/test_llm_adapters.py` | Complete. Unified adapter supporting OpenAI-compatible (Ollama/OpenRouter/LiteLLM), Anthropic messages, and Gemini generateContent. Strict server-side `LLM_API_KEY`, bounded timeouts, credential redaction, advisory labeling. Deterministic offline fallback when unconfigured. |
| **3. Slide Observatory & Cognitive Load Evaluator** | `backend/app/services/evaluator.py`<br>`backend/app/services/eval_benchmark.py`<br>`backend/app/api/evaluations.py` | `backend/tests/test_evaluations.py` | Complete. Multi-factor rubric computing information density, bullet brevity, visual hierarchy balance, readability grade, and MECE structural alignment. Reproducible benchmark CLI included. |
| **4. Data Fidelity & Grounding Auditor** | `backend/app/services/evaluator.py`<br>`backend/app/api/evaluations.py` | `backend/tests/test_data_fidelity.py` | Complete. Extracts numeric claims and chart series, cross-validates with ingested source tables/datasets, detects unsupported claims, and outputs precision/recall confidence. |
| **5. Cross-Platform Attribution Guard** | `backend/app/services/attribution_guard.py`<br>`backend/app/api/evaluations.py` | `backend/tests/test_attribution_guard.py` | Complete. Fixes upstream issue #311. Fails closed with actionable structured diagnostics (rule code, failed constraint, platform-normalized paths, remediation advice) across Linux, macOS, and Windows. |
| **6. Prompt Budget & Language Audit Engine** | `backend/app/services/prompt_audit.py`<br>`backend/app/api/evaluations.py` | `backend/tests/test_prompt_audit.py` | Complete. Fixes upstream issue #304 & #302. Audits token length against target model windows, enforces language-neutral trigger schemas, detects conflicting bilingual suffix pollution (`_zh`/`_en`), and validates dictionary completeness. |
| **7. Native PPTX Deck Compiler & Exporter** | `backend/app/services/pptx_compiler.py`<br>`backend/app/api/decks.py` | `backend/tests/test_pptx_compiler.py` | Complete. Compiles presentation data into native binary `.pptx` files with real shapes, styled tables, native data charts (bar, line, pie), slide transitions, and speaker notes using `python-pptx`. |
| **8. Template Studio & Placeholder Inspector** | `backend/app/services/template_service.py`<br>`backend/app/api/templates.py` | `backend/tests/test_templates.py` | Complete. Custom template registration, master slide layout scanning, placeholder mapping, and visual theme palettes. |
| **9. Authentication (OIDC Keycloak + PKCE)** | `backend/app/core/security.py`<br>`backend/app/api/auth.py`<br>`frontend/src/services/auth.ts` | `backend/tests/test_auth_oidc.py`<br>`frontend/src/tests/AuthFlow.test.tsx` | Complete. OIDC authorization-code flow with state + nonce + PKCE. Access tokens stored strictly in memory. Bearer-only API authorization across all data endpoints with viewer/operator/admin RBAC. Local-only demo mode with localhost safeguards. |
| **10. Audit Logging & Transactional Storage** | `backend/app/services/audit_service.py`<br>`backend/app/core/database.py`<br>`backend/app/models/` | `backend/tests/test_persistence_audit.py` | Complete. SQLite persistent database with UTC timestamps, pagination, filtering, transactions, and immutable security audit logs for all mutations. |
| **11. Frontend Dashboard & Observatory UI** | `frontend/src/App.tsx`<br>`frontend/src/components/*`<br>`frontend/src/services/api.ts` | `frontend/src/__tests__/app.test.tsx` | Complete. React + TypeScript + Vite responsive dashboard with Deck Generator, Observatory Inspection, Evaluation Matrix, Template Studio, and Audio Narration viewer. |
| **12. Guided Quickstart & Documentation Hub** | `frontend/src/components/QuickstartModal.tsx`<br>`README.md`<br>`docs/*` | Integration & manual verification | Complete. Fixes upstream issue #225 by delivering an interactive 3-step walkthrough and ready-to-run sample deck presets. |

## User Complaint Resolution Matrix

1. **Issue #225 (Heavy Local Setup / Missing Guided Onboarding)**:
   - Implemented zero-configuration offline deterministic mode.
   - Built an interactive in-app Quickstart Walkthrough with 4 instant domain presets (Executive AI Strategy, Research Benchmarking, Quarterly Data Review, Technical Architecture).
   - Created comprehensive documentation and one-command local startup.

2. **Issue #311 (attribution_guard.py Exiting with Code 1 and No Diagnostics on Windows)**:
   - Implemented cross-platform path normalization (`pathlib.PurePath`).
   - Replaced silent exit codes with structured diagnostic payloads (`DiagnosticReport` with check name, code, severity, diagnostic reason, affected path, and remediation command).
   - Ensured fail-closed behavior while guaranteeing human-readable error output to stdout/stderr and JSON API responses.

3. **Issue #304 (Prompt Text Breaking Language Rules & Bilingual Key Drift)**:
   - Designed clean language-neutral schema contracts.
   - Implemented automated `PromptAuditService` that flags unauthorized bilingual key suffixes (`_zh`, `_en`) and verifies token budgets against model context windows.

4. **Issue #302 & #303 (UI Translations Drift & Unused Dictionary Keys)**:
   - Built a verified i18n dictionary validator checking key parity across locales and ensuring zero orphaned keys.
