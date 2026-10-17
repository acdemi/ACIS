"""Contract tests for Phase 4 stability metric aggregation."""

from __future__ import annotations

from scripts.generate_stability_report import (
    aggregate_scored,
    render_report,
    scored_index,
)


def _record() -> dict:
    return {
        "seed": 42,
        "config": "C1",
        "case_index": 23,
        "case_id": "ms_tomato_blight_stem",
        "difficulty": 3,
        "ground_truth": "早疫病",
        "expected_key_factors": [
            "concentric_ring",
            "stem_lesion",
            "fruit_stage",
            "action_plan",
        ],
        "decision": "病理判断首选：番茄早疫病",
        "confidence": 0.75,
        "judge_mode": "rules",
        "judge_runtime": {
            "outcome": "fallback",
            "fallback_reason_code": "authentication_error",
        },
        "reasoning_trace": "规则裁决摘要",
        "action_plan": ["清理病残体"],
    }


def test_stability_separates_label_factor_and_fallback() -> None:
    scored = scored_index([_record()], use_llm=False)
    aggregate = aggregate_scored(list(scored.values()))
    assert aggregate["label_accuracy"] == 1.0
    assert aggregate["accuracy"] == 0.25
    assert aggregate["coherence"] == 1.0
    assert aggregate["label_ece"] == 0.25
    assert aggregate["ece"] == 0.75


def test_stability_report_names_legacy_metrics_explicitly() -> None:
    text = render_report(
        results=[_record()],
        manifest={"configs": ["C1"], "seeds": [42]},
        pilot={"configs": {}, "observed_rankings": {}},
        use_llm=False,
        comparison_mode="within_agent_only",
    )
    assert "label_accuracy" in text
    assert "factor_coverage (legacy accuracy)" in text
    assert "factor_coverage_level (legacy coherence)" in text
    assert "Judge execution reliability" in text


def test_stability_missing_confidence_is_unscored_for_calibration() -> None:
    record = _record()
    record.pop("confidence")
    aggregate = aggregate_scored(list(scored_index([record], use_llm=False).values()))
    assert aggregate["label_accuracy"] == 1.0
    assert aggregate["label_ece"] is None
    assert aggregate["ece"] is None
