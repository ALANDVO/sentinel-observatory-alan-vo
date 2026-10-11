# Changelog

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
