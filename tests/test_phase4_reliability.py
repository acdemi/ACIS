"""Phase 4 harness/real-agent semantic reliability regressions."""

from __future__ import annotations

from scripts.run_phase4_2_real_agent import compare_decision_outputs


def test_r4_c2_abstention_is_not_compared_as_disease_confidence() -> None:
    result = compare_decision_outputs(
        real_decision="无法定论（待实验室病原鉴定）",
        real_confidence=0.2,
        real_judge_mode="deepseek",
        reference_decision="番茄叶霉病",
        reference_confidence=0.95,
        reference_execution_semantics="direct_llm_baseline",
    )
    assert result.real_label == "ABSTAIN"
    assert result.reference_label == "叶霉病"
    assert result.labels_match is False
    assert result.confidence_comparable is False
    assert result.verdict == "incomparable"


def test_r4_c0_confidence_offset_is_not_a_gate_across_different_paths() -> None:
    result = compare_decision_outputs(
        real_decision="番茄叶霉病",
        real_confidence=0.6,
        real_judge_mode="deepseek",
        reference_decision="番茄叶霉病",
        reference_confidence=0.92,
        reference_execution_semantics="direct_llm_baseline",
    )
    assert result.labels_match is True
    assert result.confidence_offset == 0.32
    assert result.confidence_comparable is False
    assert result.verdict == "incomparable"


def test_same_execution_path_flags_large_confidence_offset() -> None:
    result = compare_decision_outputs(
        real_decision="番茄叶霉病",
        real_confidence=0.6,
        real_judge_mode="deepseek",
        reference_decision="番茄叶霉病",
        reference_confidence=0.95,
        reference_execution_semantics="acis_real_agent",
    )
    assert result.confidence_comparable is True
    assert result.verdict == "confidence_offset"
