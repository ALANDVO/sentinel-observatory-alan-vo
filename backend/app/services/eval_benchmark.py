"""Reproducible evaluation benchmark CLI for Sentinel Observatory.

Run: python -m backend.app.services.eval_benchmark
Deterministic offline baseline; no LLM, no randomness.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.app.services.evaluator import EvaluationEngine

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
    engine = EvaluationEngine()
    dataset = decks if decks is not None else BENCHMARK_DECKS
    results: list[BenchmarkResult] = []
    passed = failed = 0
    failure_cases: list[str] = []

    for spec in dataset:
        deck_id, label, slides = spec["deck_id"], spec.get("label", spec["deck_id"]), spec["slides"]
        rep = engine.evaluate_deck(deck_id, slides)
        fid = engine.check_data_fidelity(slides, spec.get("source_data", []))
        ch_pass, ch_fail = [], []

        checks = [
            ("expected_cognitive_score_min", rep.overall_cognitive_score, lambda v, t: v >= t, "cognitive_score", ">="),
            ("expected_cognitive_score_max", rep.overall_cognitive_score, lambda v, t: v <= t, "cognitive_score", "<="),
            ("expected_mece_min", rep.mece_alignment_score, lambda v, t: v >= t, "mece_score", ">="),
        ]
        for key, val, cond, op, sym in checks:
            if (target := spec.get(key)) is not None:
                (ch_pass if cond(val, target) else ch_fail).append(f"{op} {val:.3f} {sym} {target}")

        if ch_fail:
            failed += 1
            failure_cases.append(f"{deck_id}: {'; '.join(ch_fail)}")
        else:
            passed += 1

        results.append(BenchmarkResult(
            deck_id=deck_id, label=label,
            overall_cognitive_score=rep.overall_cognitive_score,
            mece_alignment_score=rep.mece_alignment_score,
            avg_information_density=rep.avg_information_density,
            avg_bullet_brevity=rep.avg_bullet_brevity,
            avg_readability_grade=rep.avg_readability_grade,
            numeric_claims_found=fid["numeric_claims_found"],
            data_fidelity_precision=fid["data_fidelity_precision"],
            checks_passed=ch_pass, checks_failed=ch_fail,
        ))

    return BenchmarkReport(total_decks=len(dataset), passed=passed, failed=failed, results=results, failure_cases=failure_cases)


def main() -> int:
    print("Sentinel Observatory — Evaluation Benchmark\n" + "=" * 50)
    report = run_benchmark()
    for r in report.results:
        st = "PASS" if not r.checks_failed else "FAIL"
        print(f"[{st}] {r.deck_id}: {r.label}\n  cog={r.overall_cognitive_score:.3f} mece={r.mece_alignment_score:.3f} density={r.avg_information_density:.3f} brevity={r.avg_bullet_brevity:.3f} grade={r.avg_readability_grade:.1f} fidelity={r.data_fidelity_precision:.3f}")
        for chk in r.checks_passed: print(f"  ✓ {chk}")
        for chk in r.checks_failed: print(f"  ✗ {chk}")
    print(f"\nResults: {report.passed}/{report.total_decks} passed, {report.failed} failed")
    for fc in report.failure_cases: print(f"  - {fc}")
    print(f"\n{report.baseline_note}")
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())