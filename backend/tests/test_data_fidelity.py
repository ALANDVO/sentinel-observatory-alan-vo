"""Tests for data fidelity engine: numeric claim extraction, source verification, precision/recall."""
from __future__ import annotations

import pytest

from backend.app.services.evaluator import EvaluationEngine, _information_density, _bullet_brevity, _hierarchy_balance, _mece_alignment


@pytest.fixture
def engine():
    return EvaluationEngine()


# ------- Data Fidelity Tests -------

def test_no_numeric_claims_yields_perfect_fidelity(engine: EvaluationEngine):
    slides = [
        {"id": "s1", "position": 0, "title": "Introduction", "body_text": "AI systems require careful alignment."},
        {"id": "s2", "position": 1, "title": "Methods", "body_text": "RLHF is a promising technique."},
    ]
    result = engine.check_data_fidelity(slides, [])
    assert result["numeric_claims_found"] == 0
    assert result["data_fidelity_precision"] == 1.0
    assert result["data_fidelity_recall"] == 1.0


def test_verified_numeric_claims_high_precision(engine: EvaluationEngine):
    slides = [{"id": "s1", "position": 0, "title": "Revenue", "body_text": "Revenue grew by 25% to reach 500 million."}]
    source_data = [{"revenue_millions": 500.0, "growth_pct": 25.0}]
    result = engine.check_data_fidelity(slides, source_data)
    assert result["numeric_claims_found"] > 0
    assert result["claims_verified"] > 0
    assert result["data_fidelity_precision"] > 0.5


def test_unverified_claims_low_precision(engine: EvaluationEngine):
    slides = [{"id": "s1", "position": 0, "title": "Results", "body_text": "Accuracy improved by 99.9% over 1000 epochs."}]
    source_data = [{"accuracy": 72.5, "epochs": 200}]
    result = engine.check_data_fidelity(slides, source_data)
    # 99.9 and 1000 are very far from 72.5 and 200
    assert result["numeric_claims_found"] >= 2
    assert result["data_fidelity_precision"] < 1.0


def test_empty_slides_returns_safe_defaults(engine: EvaluationEngine):
    result = engine.check_data_fidelity([], [{"value": 100.0}])
    assert result["numeric_claims_found"] == 0
    assert result["data_fidelity_precision"] == 1.0


def test_claims_with_no_source_data_returns_zero_precision(engine: EvaluationEngine):
    slides = [{"id": "s1", "position": 0, "title": "KPIs", "body_text": "Score: 87.3 and recall: 92.1"}]
    result = engine.check_data_fidelity(slides, [])
    assert result["numeric_claims_found"] >= 2
    assert result["data_fidelity_precision"] == 0.0


def test_exact_match_in_source_verified(engine: EvaluationEngine):
    slides = [{"id": "s1", "position": 0, "title": "Metrics", "body_text": "F1 score: 0.934 on evaluation set."}]
    source_data = [{"f1_score": 0.934}]
    result = engine.check_data_fidelity(slides, source_data)
    assert result["claims_verified"] >= 1


# ------- Cognitive Load Sub-function Tests -------

def test_information_density_empty_returns_full(engine: EvaluationEngine):
    score = _information_density("")
    assert score == 1.0


def test_information_density_short_content_high_score():
    score = _information_density("• Point A\n• Point B\n• Point C")
    assert 0.7 <= score <= 1.0


def test_information_density_very_long_content_low_score():
    # 200-word single bullet: char_count ~1000, which reduces score
    # Build many bullets over 600 chars to definitely push score low
    long_body = "\n".join([f"• {'word ' * 15}complex technical concept number {i}" for i in range(10)])
    score = _information_density(long_body)
    assert score < 0.7  # High char count and many bullets should reduce score


def test_bullet_brevity_short_bullets_high_score():
    score = _bullet_brevity("• Key insight\n• Strong result\n• Clear outcome")
    assert score >= 0.7


def test_bullet_brevity_verbose_bullets_low_score():
    verbose = "• " + " ".join(["very"] * 25) + " important point that goes on and on\n" * 3
    score = _bullet_brevity(verbose)
    assert score < 0.5


def test_hierarchy_balance_good_ratio_scores_one():
    # Title "AI Safety Overview" (3 words) vs 7-word body - ratio is around 0.3 which scores ~0.83
    score = _hierarchy_balance("AI Safety Overview", "Alignment techniques reduce harmful behavior")
    assert score >= 0.8  # A reasonable hierarchy should score above 0.8


def test_mece_alignment_distinct_titles_high_score():
    titles = ["Introduction", "Methods", "Results", "Conclusion", "Future Work"]
    score = _mece_alignment(titles)
    assert score >= 0.7


def test_mece_alignment_repetitive_titles_low_score():
    titles = ["AI Safety", "AI Safety Overview", "AI Safety Methods", "AI Safety Results"]
    score = _mece_alignment(titles)
    assert score < 0.7


def test_full_deck_evaluation_returns_valid_report(engine: EvaluationEngine):
    slides = [
        {"id": "s0", "position": 0, "title": "AI Safety Introduction", "body_text": "• Alignment research\n• Robustness\n• Interpretability"},
        {"id": "s1", "position": 1, "title": "Training Methods", "body_text": "• RLHF\n• Constitutional AI\n• Debate-based training"},
        {"id": "s2", "position": 2, "title": "Benchmark Evaluation", "body_text": "• MMLU: 86%\n• HumanEval: 67%\n• BIG-Bench: 73%"},
        {"id": "s3", "position": 3, "title": "Limitations", "body_text": "• Hallucination remains a challenge\n• Context window constraints"},
    ]
    report = engine.evaluate_deck("deck-test", slides)
    assert 0.0 <= report.overall_cognitive_score <= 1.0
    assert 0.0 <= report.mece_alignment_score <= 1.0
    assert len(report.slide_scores) == 4
    assert report.avg_readability_grade >= 0.0
