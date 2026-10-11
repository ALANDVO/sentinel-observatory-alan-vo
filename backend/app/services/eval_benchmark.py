"""Reproducible evaluation benchmark CLI for Sentinel Observatory.

Run: python -m backend.app.services.eval_benchmark
Deterministic offline baseline; no LLM, no randomness.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Any
from pathlib import Path

from backend.app.services.evaluator import EvaluationEngine, _mece_alignment

_BENCHMARK_DATA_PATH = Path(__file__).parent / "benchmark_decks.json"
with open(_BENCHMARK_DATA_PATH, "r") as f:
    BENCHMARK_DECKS: list[dict[str, Any]] = json.load(f)


@dataclass
class BenchmarkResult:
    deck_id: str
    label: str
    overall_cognitive_score: float
    mece_alignment_score: float
    avg_information_density: float
    avg_bullet_brevity: float
    avg_readability_grade: float
    numeric_claims_found: int
    data_fidelity_precision: float
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)


@dataclass
class BenchmarkReport:
    total_decks: int
    passed: int
    failed: int
    results: list[BenchmarkResult] = field(default_factory=list)
    failure_cases: list[str] = field(default_factory=list)
    baseline_note: str = "Baseline on fixed BENCHMARK_DECKS. Reproducible: python -m backend.app.services.eval_benchmark"


def run_benchmark(decks: list[dict[str, Any]] | None = None) -> BenchmarkReport:
    """Run evaluation benchmark against the labeled dataset and return a report."""
    engine = EvaluationEngine()
    dataset = decks if decks is not None else BENCHMARK_DECKS
    results: list[BenchmarkResult] = []
    passed = 0
    failed = 0
    failure_cases: list[str] = []

    for spec in dataset:
        deck_id = spec["deck_id"]
        label = spec.get("label", deck_id)
        slides = spec["slides"]
        report = engine.evaluate_deck(deck_id, slides)
        fidelity = engine.check_data_fidelity(slides, spec.get("source_data", []))

        checks_passed: list[str] = []
        checks_failed: list[str] = []

        min_cog = spec.get("expected_cognitive_score_min")
        max_cog = spec.get("expected_cognitive_score_max")
        if min_cog is not None:
            if report.overall_cognitive_score < min_cog:
                checks_failed.append(f"cognitive_score {report.overall_cognitive_score:.3f} < {min_cog}")
            else:
                checks_passed.append(f"cognitive_score {report.overall_cognitive_score:.3f} >= {min_cog}")
        if max_cog is not None:
            if report.overall_cognitive_score > max_cog:
                checks_failed.append(f"cognitive_score {report.overall_cognitive_score:.3f} > {max_cog}")
            else:
                checks_passed.append(f"cognitive_score {report.overall_cognitive_score:.3f} <= {max_cog}")

        min_mece = spec.get("expected_mece_min")
        if min_mece is not None:
            if report.mece_alignment_score < min_mece:
                checks_failed.append(f"mece_score {report.mece_alignment_score:.3f} < {min_mece}")
            else:
                checks_passed.append(f"mece_score {report.mece_alignment_score:.3f} >= {min_mece}")

        if checks_failed:
            failed += 1
            failure_cases.append(f"{deck_id}: {'; '.join(checks_failed)}")
        else:
            passed += 1

        results.append(BenchmarkResult(
            deck_id=deck_id, label=label,
            overall_cognitive_score=report.overall_cognitive_score,
            mece_alignment_score=report.mece_alignment_score,
            avg_information_density=report.avg_information_density,
            avg_bullet_brevity=report.avg_bullet_brevity,
            avg_readability_grade=report.avg_readability_grade,
            numeric_claims_found=fidelity["numeric_claims_found"],
            data_fidelity_precision=fidelity["data_fidelity_precision"],
            checks_passed=checks_passed, checks_failed=checks_failed,
        ))

    return BenchmarkReport(total_decks=len(dataset), passed=passed, failed=failed, results=results, failure_cases=failure_cases)


def main() -> int:
    print("Sentinel Observatory — Evaluation Benchmark")
    print("=" * 50)
    report = run_benchmark()
    for r in report.results:
        status = "PASS" if not r.checks_failed else "FAIL"
        print(f"[{status}] {r.deck_id}: {r.label}")
        print(f"  cog={r.overall_cognitive_score:.3f} mece={r.mece_alignment_score:.3f} density={r.avg_information_density:.3f} brevity={r.avg_bullet_brevity:.3f} grade={r.avg_readability_grade:.1f} fidelity={r.data_fidelity_precision:.3f}")
        for chk in r.checks_passed:
            print(f"  ✓ {chk}")
        for chk in r.checks_failed:
            print(f"  ✗ {chk}")
    print(f"\nResults: {report.passed}/{report.total_decks} passed, {report.failed} failed")
    if report.failure_cases:
        for fc in report.failure_cases:
            print(f"  - {fc}")
    print(f"\n{report.baseline_note}")
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())