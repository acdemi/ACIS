"""Tests for Collective Omission Detection (Phase 7A Sprint 02).

Covers the four required cases:
1. no ignored disease -> ignored_candidates == []
2. one ignored disease -> ignored_candidates contains it
3. confidence reduction works correctly (score > 0.50 -> -0.05, floor 0.50)
4. backward compatibility (legacy keys + DecisionOutput/AgentOutput shape)
plus the pure helpers in utils.omission.
"""
from __future__ import annotations

from dataclasses import fields as dataclass_fields

import pytest

from agents.judge_agent import JudgeAgent  # noqa: E402
from agents.types import AgentOutput, DebateResult, DecisionOutput, RequestContext  # noqa: E402
from utils.omission import (  # noqa: E402
    CONFIDENCE_FLOOR,
    PENALTY_MAX,
    PENALTY_STEP,
    apply_omission_penalty,
    omission_action,
    omission_reason,
    omission_score,
)


# ----------------------------- pure helpers -----------------------------


def test_omission_score_ratio_and_edges():
    assert omission_score(0, 4) == 0.0
    assert omission_score(1, 4) == 0.25
    assert omission_score(2, 4) == 0.5
    assert omission_score(4, 4) == 1.0
    # no candidates retrieved -> no blind spot
    assert omission_score(0, 0) == 0.0
    # never exceeds 1.0
    assert omission_score(5, 4) == 1.0


def test_omission_reason_language():
    assert "未发现" in omission_reason([])
    assert "Powdery Mildew" in omission_reason(["Powdery Mildew"])
    multi = omission_reason(["A", "B"])
    assert "A" in multi and "B" in multi


def test_omission_action_three_bands():
    assert omission_action(0.0)["level"] == "none"
    assert omission_action(0.19)["level"] == "none"
    assert omission_action(0.19)["append_warning"] is False

    assert omission_action(0.20)["level"] == "warn"
    assert omission_action(0.20)["append_warning"] is True
    assert omission_action(0.20)["confidence_delta"] == 0.0
    assert omission_action(0.50)["level"] == "warn"

    assert omission_action(0.51)["level"] == "penalize"
    assert omission_action(0.51)["confidence_delta"] == PENALTY_STEP
    assert omission_action(1.0)["append_warning"] is True


def test_apply_omission_penalty_bands_and_floor():
    # below warn threshold -> unchanged
    assert apply_omission_penalty(0.80, 0.10) == 0.80
    # warn band -> warning only, no confidence cut
    assert apply_omission_penalty(0.80, 0.30) == 0.80
    # penalize band -> -0.05
    assert apply_omission_penalty(0.80, 0.60) == round(0.80 - PENALTY_STEP, 2)
    # floor: never below 0.50
    assert apply_omission_penalty(0.52, 0.60) == CONFIDENCE_FLOOR
    assert apply_omission_penalty(0.50, 1.0) == CONFIDENCE_FLOOR


def test_apply_omission_penalty_respects_cap():
    # cumulative omission penalty never exceeds PENALTY_MAX
    base = 0.90
    already = PENALTY_MAX - 0.02
    after = apply_omission_penalty(base, 0.60, already_applied=already)
    assert after == round(base - 0.02, 2)


# ----------------------------- Judge integration -----------------------------


def _ctx():
    return RequestContext(query="leaf spot", greenhouse_id="gh1", crop="tomato", intent="diagnose")


def _debate():
    return DebateResult(consensus=[], conflicts=[], missing_evidence=[], risk_level="medium", critic={})


def _expert(claim, confidence=0.7):
    return AgentOutput(layer="专家层", agent="病理Agent", claim=claim, confidence=confidence)


def _kg(diseases):
    return {
        "diseases": diseases,
        "rules": [],
        "hard_constraints": [],
        "triple_strings": [],
        "backend": "memory",
        "crop": "tomato",
    }


def _no_op_kg_evolution(outputs, kg, context):
    return {"proposed": [], "drafts": [], "used_drafts": False}


class _PassthroughCalibrator:
    enabled = False

    def calibrate(self, agent, raw):
        return float(raw)

    def status(self):
        return {"enabled": False, "note": "test passthrough"}


@pytest.fixture(scope="module")
def judge():
    instance = JudgeAgent(use_llm=False)
    instance.calibrator = _PassthroughCalibrator()
    instance._kg_evolution = _no_op_kg_evolution
    return instance


def _co(decision):
    return decision.judge_analysis["collective_omission"]


def test_no_ignored_disease(judge):
    decision = judge._run_rule_judge(_ctx(), [_expert("Rust")], _debate(), _kg(["Rust"]), 1)
    co = _co(decision)
    assert co["ignored_candidates"] == []
    assert co["omission_score"] == 0.0
    assert co["omission_level"] == "none"
    assert co["append_warning"] is False
    assert not any("集体忽略" in a for a in decision.action_plan)


def test_one_ignored_disease(judge):
    claim = "Rust, Leaf Blight, Anthracnose"
    decision = judge._run_rule_judge(
        _ctx(), [_expert(claim)], _debate(),
        _kg(["Rust", "Leaf Blight", "Anthracnose", "Powdery Mildew"]), 1,
    )
    co = _co(decision)
    assert co["ignored_candidates"] == ["Powdery Mildew"]
    assert co["omission_score"] == 0.25
    assert co["omission_level"] == "warn"
    assert co["append_warning"] is True
    assert "Powdery Mildew" in co["omission_reason"]
    # warn band: warning appended, confidence NOT cut (baseline 0.70)
    assert any("集体忽略" in a for a in decision.action_plan)
    assert decision.confidence == 0.70


def test_confidence_reduction_works(judge):
    decision = judge._run_rule_judge(
        _ctx(), [_expert("Rust")], _debate(),
        _kg(["Rust", "Leaf Blight", "Anthracnose", "Powdery Mildew"]), 1,
    )
    co = _co(decision)
    assert co["omission_score"] == 0.75
    assert co["omission_level"] == "penalize"
    assert decision.confidence == round(0.70 - PENALTY_STEP, 2)
    assert decision.confidence >= CONFIDENCE_FLOOR
    assert "漏检比例" in decision.reasoning_trace


def test_confidence_floor_respected(judge):
    decision = judge._run_rule_judge(
        _ctx(), [_expert("Rust", confidence=0.5)], _debate(),
        _kg(["Rust", "Leaf Blight", "Anthracnose", "Powdery Mildew"]), 1,
    )
    co = _co(decision)
    assert co["omission_level"] == "penalize"
    assert decision.confidence == CONFIDENCE_FLOOR


def test_backward_compatibility(judge):
    decision = judge._run_rule_judge(
        _ctx(), [_expert("Rust")], _debate(),
        _kg(["Rust", "Leaf Blight", "Anthracnose", "Powdery Mildew"]), 1,
    )
    co = _co(decision)
    for legacy_key in ("omitted_diseases", "penalty_applied", "controversy_delta", "counterfactuals"):
        assert legacy_key in co, legacy_key
    for new_key in ("ignored_candidates", "omission_score", "omission_reason"):
        assert new_key in co, new_key
    assert co["ignored_candidates"] == co["omitted_diseases"]
    expected = {
        "summary", "decision", "confidence", "risk_level", "action_plan",
        "debate", "traces", "judge_mode", "need_human_review",
        "reasoning_trace", "judge_analysis", "decision_id", "token_usage",
    }
    assert {f.name for f in dataclass_fields(DecisionOutput)} == expected
    out = AgentOutput(
        layer="专家层", agent="病理Agent", claim="Rust", confidence=0.7,
        counterfactual={"alternative": "X", "rejection_reason": "Y"},
        counterfactual_observations=["If Z, X would be preferred."],
    )
    assert out.counterfactual["alternative"] == "X"
    assert out.counterfactual_observations == ["If Z, X would be preferred."]