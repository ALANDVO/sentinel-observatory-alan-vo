"""Reproducible evaluation benchmark CLI for Sentinel Observatory."""
from __future__ import annotations
import json, sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from backend.app.services.evaluator import EvaluationEngine

_BENCHMARK_DATA_PATH = Path(__file__).parent / "benchmark_decks.json"
with open(_BENCHMARK_DATA_PATH, "r") as f:
    BENCHMARK_DECKS: list[dict[str, Any]] = json.load(f)

@dataclass
class BenchmarkResult:
    deck_id: str; label: str; overall_cognitive_score: float; mece_alignment_score: float
    avg_information_density: float; avg_bullet_brevity: float; avg_readability_grade: float
    numeric_claims_found: int; data_fidelity_precision: float
    checks_passed: list[str] = field(default_factory=list); checks_failed: list[str] = field(default_factory=list)

@dataclass
class BenchmarkReport:
    total_decks: int; passed: int; failed: int
    results: list[BenchmarkResult] = field(default_factory=list)
    failure_cases: list[str] = field(default_factory=list)
    baseline_note: str = "Baseline on fixed BENCHMARK_DECKS. Reproducible: python -m backend.app.services.eval_benchmark"

def run_benchmark(decks: list[dict[str, Any]] | None = None) -> BenchmarkReport:
    engine, dataset = EvaluationEngine(), decks if decks is not None else BENCHMARK_DECKS
    results: list[BenchmarkResult] = []
    passed = failed = 0
    failure_cases: list[str] = []

    for spec in dataset:
        did, lbl, slds = spec["deck_id"], spec.get("label", spec["deck_id"]), spec["slides"]
        rep = engine.evaluate_deck(did, slds)
        fid = engine.check_data_fidelity(slds, spec.get("source_data", []))
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
            failed += 1; failure_cases.append(f"{did}: {'; '.join(ch_fail)}")
        else:
            passed += 1
        results.append(BenchmarkResult(did, lbl, rep.overall_cognitive_score, rep.mece_alignment_score,
                                       rep.avg_information_density, rep.avg_bullet_brevity, rep.avg_readability_grade,
                                       fid["numeric_claims_found"], fid["data_fidelity_precision"], ch_pass, ch_fail))
    return BenchmarkReport(len(dataset), passed, failed, results, failure_cases)

def main() -> int:
    print("Sentinel Observatory — Evaluation Benchmark\n" + "=" * 50)
    rep = run_benchmark()
    for r in rep.results:
        st = "PASS" if not r.checks_failed else "FAIL"
        print(f"[{st}] {r.deck_id}: {r.label}\n  cog={r.overall_cognitive_score:.3f} mece={r.mece_alignment_score:.3f} density={r.avg_information_density:.3f} brevity={r.avg_bullet_brevity:.3f} grade={r.avg_readability_grade:.1f} fidelity={r.data_fidelity_precision:.3f}")
        for c in r.checks_passed: print(f"  ✓ {c}")
        for c in r.checks_failed: print(f"  ✗ {c}")
    print(f"\nResults: {rep.passed}/{rep.total_decks} passed, {rep.failed} failed\n{rep.baseline_note}")
    return 0 if rep.failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())