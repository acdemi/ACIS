"""Unit tests for the Phase 4 challenge scorer (openmetaphysics.evaluation).

Exercises the three metrics with simulated agent outputs:

- :func:`calc_confidence_calibration` — ECE stays in [0, 1], ~0 for a
  perfectly calibrated set, > 0 for an overconfident set, and tolerates
  unlabeled outputs.
- :func:`calc_abstention_rate` — percentage in [0, 100] for abstaining,
  committed, and mixed outputs.
- :func:`calc_reasoning_coherence` — 0-3 scale via the deterministic rule
  fallback (no API key) and via a stubbed LLM judge, with automatic fallback
  when the LLM path fails.

The rule fallback is kept deterministic by ensuring ``DEEPSEEK_API_KEY`` is
absent, so these tests never hit the network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openmetaphysics.evaluation.challenge_scorer import (
    FACTOR_ALIASES,
    ChallengeScoringError,
    calc_abstention_rate,
    calc_confidence_calibration,
    calc_reasoning_coherence,
)

CHALLENGE_PATH = Path(__file__).resolve().parent.parent / "benchmarks" / (
    "challenge_set_v1.json"
)


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the deterministic rule fallback for coherence scoring."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("AGRI_AI_COHERENCE_MODEL", raising=False)


# ---------------------------------------------------------------------------
# calc_confidence_calibration
# ---------------------------------------------------------------------------


def _outputs(confidences: list[float], correctness: list[bool]) -> list[dict]:
    return [
        {"decision": "诊断A", "confidence": conf, "correct": correct}
        for conf, correct in zip(confidences, correctness)
    ]


def test_calibration_perfectly_calibrated_near_zero() -> None:
    """Confidence equals accuracy in every bin -> ECE == 0."""
    outputs = _outputs(
        confidences=[1.0, 1.0, 0.0],
        correctness=[True, True, False],
    )
    ece = calc_confidence_calibration(outputs)
    assert 0.0 <= ece <= 0.01


def test_calibration_overconfident_wrong_is_positive() -> None:
    outputs = _outputs(
        confidences=[0.95, 0.95, 0.95, 0.95],
        correctness=[True, False, False, False],
    )
    ece = calc_confidence_calibration(outputs)
    assert ece > 0.1


def test_calibration_range_and_repeatability() -> None:
    outputs = _outputs(
        confidences=[0.7, 0.6, 0.8, 0.4, 0.9, 0.3, 0.2, 0.1, 0.5, 0.85],
        correctness=[True, False, True, True, True, False, False, True, True, True],
    )
    ece = calc_confidence_calibration(outputs)
    assert 0.0 <= ece <= 1.0
    assert calc_confidence_calibration(outputs) == ece


def test_calibration_derives_correctness_from_expected() -> None:
    outputs = [
        {"decision": "病理判断首选：早疫病", "confidence": 0.8, "expected": "早疫病"},
        {"decision": "病理判断首选：叶霉病", "confidence": 0.9, "expected": "早疫病"},
    ]
    ece = calc_confidence_calibration(outputs)
    assert ece > 0.0


def test_calibration_evidence_insufficient_convention() -> None:
    outputs = [
        {"decision": "病理证据不足，不能确认具体病害", "confidence": 0.3, "expected": "证据不足"},
        {"decision": "病理证据不足，不能确认具体病害", "confidence": 0.9, "expected": "证据不足"},
    ]
    ece = calc_confidence_calibration(outputs)
    assert ece > 0.0


def test_calibration_unlabeled_outputs_excluded() -> None:
    outputs = [
        {"decision": "诊断B", "confidence": 0.1},  # no label
        {"confidence": 0.8},  # no decision, no label
    ]
    assert calc_confidence_calibration(outputs) == 0.0
    # a single labeled output deviates by |acc - conf| only
    single = [{"decision": "诊断A", "confidence": 0.9, "correct": True}]
    assert calc_confidence_calibration(single) == 0.1


def test_calibration_empty_inputs_zero() -> None:
    assert calc_confidence_calibration([]) == 0.0
    assert calc_confidence_calibration([{"decision": "x"}]) == 0.0


def test_calibration_rejects_non_numeric_confidence() -> None:
    with pytest.raises(ChallengeScoringError):
        calc_confidence_calibration(
            [{"decision": "x", "confidence": "high", "correct": True}]
        )


def test_calibration_rejects_invalid_bins() -> None:
    outputs = _outputs([0.5], [True])
    with pytest.raises(ChallengeScoringError):
        calc_confidence_calibration(outputs, bins=0)


# ---------------------------------------------------------------------------
# calc_abstention_rate
# ---------------------------------------------------------------------------


def test_abstention_rate_percentage() -> None:
    outputs = [
        {"decision": "病理证据不足，不能确认具体病害"},
        {"decision": "病理判断首选：叶霉病"},
        {"decision": "无法定论，建议继续采集证据"},
        {"decision": "病理判断首选：早疫病"},
    ]
    assert calc_abstention_rate(outputs) == 50.0


def test_abstention_rate_honors_explicit_flag() -> None:
    outputs = [
        {"decision": "病理判断首选：叶霉病", "abstained": True},
        {"decision": "病理判断首选：早疫病", "abstained": False},
    ]
    assert calc_abstention_rate(outputs) == 50.0


def test_abstention_rate_claim_field() -> None:
    outputs = [{"claim": "继续采集证据后再决策"}, {"claim": "病理判断首选：霜霉病"}]
    assert calc_abstention_rate(outputs) == 50.0


def test_abstention_rate_all_or_none() -> None:
    assert calc_abstention_rate([{"decision": "不确定"}]) == 100.0
    assert calc_abstention_rate([{"decision": "诊断A"}, {"decision": "诊断B"}]) == 0.0
    assert calc_abstention_rate([]) == 0.0


# ---------------------------------------------------------------------------
# calc_reasoning_coherence
# ---------------------------------------------------------------------------


def test_coherence_rule_fallback_full_coverage() -> None:
    output = {
        "decision": "病理判断首选：番茄叶霉病",
        "reasoning_trace": (
            "叶背灰色霉层为决定性特征；棚内湿度高利于发病；"
            "排除早疫病（无同心轮纹）。"
        ),
    }
    score = calc_reasoning_coherence(
        output, ["backside_mold", "high_humidity", "differential"]
    )
    assert score == 3


def test_coherence_rule_fallback_partial_coverage() -> None:
    output = {
        "decision": "病理证据不足，不能确诊霜霉病",
        "reasoning_trace": "需要补充病斑形状信息才能与灰霉类病害鉴别。",
    }
    score = calc_reasoning_coherence(
        output, ["evidence_insufficient", "info_request", "angular_lesion"]
    )
    assert score == 2


def test_coherence_rule_fallback_zero_coverage() -> None:
    output = {"decision": "病理判断首选：叶霉病", "reasoning_trace": ""}
    score = calc_reasoning_coherence(
        output, ["concentric_ring", "soil_dry", "quarantine"]
    )
    assert score == 0


def test_coherence_score_always_in_range() -> None:
    texts = [
        "病理判断首选：黄瓜霜霉病",
        "证据不足，需要补充多角形病斑形状与结露情况，排除灰霉病。",
        "维管束褐变，叶缘发黄，未见半边黄化，排除枯萎病。",
    ]
    factors = ["backside_mold", "angular_lesion", "leaf_dew", "differential"]
    for text in texts:
        score = calc_reasoning_coherence(
            {"decision": text, "reasoning_trace": text}, factors
        )
        assert score in (0, 1, 2, 3)


def test_coherence_llm_path_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stub the LLM judge to verify the 0-3 mapping from coverage fractions."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    calls: list[tuple[str, list[str]]] = []

    def fake_llm(text: str, factors: list[str]) -> dict[str, bool]:
        calls.append((text, factors))
        return {factor: factor != "leaf_dew" for factor in factors}

    monkeypatch.setattr(
        "openmetaphysics.evaluation.challenge_scorer._llm_factor_coverage",
        fake_llm,
    )
    factors = ["backside_mold", "angular_lesion", "leaf_dew", "differential"]
    score = calc_reasoning_coherence({"decision": "x", "reasoning_trace": "y"}, factors)
    assert score == 2  # 3/4 covered -> round(2.25) = 2
    assert len(calls) == 1
    assert calls[0][1] == factors


def test_coherence_llm_failure_falls_back_to_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    def broken_llm(text: str, factors: list[str]) -> dict[str, bool]:
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(
        "openmetaphysics.evaluation.challenge_scorer._llm_factor_coverage",
        broken_llm,
    )
    output = {
        "decision": "证据不足，无法确诊",
        "reasoning_trace": "需要补充霉层位置与病斑形状。",
    }
    score = calc_reasoning_coherence(
        output, ["evidence_insufficient", "info_request", "backside_mold"]
    )
    assert score == 3  # rule fallback covers all three factors


def test_coherence_rejects_empty_factors() -> None:
    with pytest.raises(ChallengeScoringError):
        calc_reasoning_coherence({"decision": "x"}, [])


# ---------------------------------------------------------------------------
# integration: rule fallback vocabulary covers the shipped challenge set
# ---------------------------------------------------------------------------


def test_every_shipped_factor_has_rule_alias() -> None:
    data = json.loads(CHALLENGE_PATH.read_text(encoding="utf-8"))
    factors = {
        factor
        for spec in data["groups"].values()
        for case in spec["cases"]
        for factor in case["expected_key_factors"]
    }
    missing = sorted(factors - set(FACTOR_ALIASES))
    assert not missing, f"factors without rule aliases: {missing}"
