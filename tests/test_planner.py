"""Unit tests for the Planner MVP (Sprint 01).

Covers the deterministic rule-based path of ``Planner.plan`` and the
``ACIS_ENABLE_PLANNER`` wiring in ``planner.build_planner``. The optional
DeepSeek LLM path is not exercised here (no API key); it mirrors JudgeAgent and
falls back to rules on failure.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.types import AgentOutput, DebateResult, DecisionOutput  # noqa: E402
from planner import ExecutionPlan, Planner, build_planner  # noqa: E402


def _trace(agent: str, claim: str, confidence: float = 0.7) -> AgentOutput:
    return AgentOutput(layer="专家层", agent=agent, claim=claim, confidence=confidence)


def _debate(conflicts=None, missing=None, risk_level="medium") -> DebateResult:
    return DebateResult(
        consensus=[],
        conflicts=conflicts or [],
        missing_evidence=missing or [],
        risk_level=risk_level,
    )


def _decision(
    decision_text="病理判断首选：番茄灰霉病",
    risk_level="medium",
    confidence=0.7,
    need_human_review=False,
    action_plan=None,
    debate=None,
    traces=None,
) -> DecisionOutput:
    return DecisionOutput(
        summary="Orchestrator 已完成 gh-a/tomato 的 diagnose 工作流",
        decision=decision_text,
        confidence=confidence,
        risk_level=risk_level,
        action_plan=action_plan or ["清除病叶并降低湿度", "喷施嘧霉胺"],
        debate=debate or _debate(),
        traces=traces or [_trace("病理Agent", decision_text)],
        judge_mode="rules",
        need_human_review=need_human_review,
        reasoning_trace="KG参照疾病：番茄灰霉病；风险等级=medium",
        judge_analysis={"kg": {"diseases": ["番茄灰霉病"], "rules": [], "backend": "memory"}},
    )


def test_plan_returns_execution_plan_with_required_fields():
    plan = Planner().plan(_decision())
    assert isinstance(plan, ExecutionPlan)
    for name in ("goal", "steps", "required_tools", "priority", "estimated_risk", "estimated_cost"):
        assert hasattr(plan, name), name
    assert plan.goal
    assert plan.steps
    assert plan.priority in {"low", "medium", "high"}
    assert plan.estimated_risk in {"low", "medium", "high"}
    assert plan.estimated_cost in {"low", "medium", "high"}


def test_disease_claim_requires_spray_workorder_tool():
    plan = Planner().plan(_decision(decision_text="病理判断首选：番茄灰霉病"))
    assert "spray_workorder" in plan.required_tools


def test_insufficient_evidence_excludes_spray_tool():
    plan = Planner().plan(_decision(decision_text="病理证据不足，需补充图像"))
    assert "spray_workorder" not in plan.required_tools


def test_missing_evidence_requires_image_capture():
    plan = Planner().plan(_decision(debate=_debate(missing=["缺少有效图像证据"])))
    assert "image_capture" in plan.required_tools


def test_irrigation_advice_requires_irrigation_tool():
    traces = [_trace("气象Agent", "当前土壤偏干，支持灌溉")]
    plan = Planner().plan(_decision(decision_text="建议灌溉", traces=traces))
    assert "irrigation_control" in plan.required_tools


def test_human_review_raises_priority_and_risk():
    plan = Planner().plan(_decision(need_human_review=True))
    assert plan.priority == "high"
    assert plan.estimated_risk == "high"
    assert "human_review" in plan.required_tools


def test_low_risk_confident_decision_is_low_priority():
    plan = Planner().plan(
        _decision(risk_level="low", confidence=0.9, debate=_debate(risk_level="low"))
    )
    assert plan.priority == "low"
    assert plan.estimated_risk == "low"


def test_steps_include_action_plan_and_review_bookends():
    plan = Planner().plan(
        _decision(
            action_plan=["第一步", "第二步"],
            need_human_review=True,
            debate=_debate(missing=["缺图"]),
        )
    )
    assert plan.steps[0] == "人工复核裁决与关键证据后再执行"
    assert "第一步" in plan.steps and "第二步" in plan.steps
    assert plan.steps[-1] == "补充缺失证据并复评"


def test_no_tools_when_clean_low_risk_decision():
    plan = Planner().plan(
        _decision(
            decision_text="继续监测",
            risk_level="low",
            confidence=0.9,
            debate=_debate(risk_level="low"),
            traces=[_trace("栽培Agent", "长势正常")],
        )
    )
    assert plan.required_tools == []


def test_planner_disabled_by_default():
    os.environ.pop("ACIS_ENABLE_PLANNER", None)
    assert build_planner() is None


def test_planner_enabled_when_env_true():
    os.environ["ACIS_ENABLE_PLANNER"] = "true"
    try:
        assert isinstance(build_planner(), Planner)
    finally:
        os.environ.pop("ACIS_ENABLE_PLANNER", None)


def test_planner_enable_env_variants():
    for value in ("1", "TRUE", "yes"):
        os.environ["ACIS_ENABLE_PLANNER"] = value
        try:
            assert build_planner() is not None, value
        finally:
            os.environ.pop("ACIS_ENABLE_PLANNER", None)
    for value in ("", "false", "0", "no"):
        os.environ["ACIS_ENABLE_PLANNER"] = value
        try:
            assert build_planner() is None, value
        finally:
            os.environ.pop("ACIS_ENABLE_PLANNER", None)