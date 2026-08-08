"""Unit tests for the capability evaluation engine (Phase 2.1E, Sprint 04.5C).

Covers the Trace-driven scoring logic for all seven capabilities, missing
evidence handling, declared-capability satisfaction, and the metrics-layer
aggregation of capability scores.
"""

from __future__ import annotations

import pytest

from trace import Trace, TraceEvent

from evals.capability_metrics import (
    CAPABILITY_SCORE_KEYS,
    compute_capability_scores,
    declared_capabilities,
    declared_capability_satisfaction,
)
from evals.config import EvalCase
from evals.metrics import (
    CaseMetrics,
    aggregate_capability_scores,
    compute_trace_metrics,
)

FIXED_TIME = "2026-01-01T00:00:00+00:00"


def _event(stage: str, payload: dict) -> TraceEvent:
    return TraceEvent(stage=stage, timestamp=FIXED_TIME, payload=payload)


def _trace(*events: TraceEvent) -> Trace:
    trace = Trace(trace_id="t", timestamp=FIXED_TIME)
    for event in events:
        trace.append(event)
    return trace


def _case(
    ground_truth: str | None = None,
    raw: dict | None = None,
) -> EvalCase:
    return EvalCase(id="case-1", query="q", ground_truth=ground_truth, raw=raw or {})


def _request() -> TraceEvent:
    return _event("request", {"query": "q", "greenhouse_id": "gh-a", "crop": "tomato"})


def _planner(enabled: bool, steps: list[str] | None = None) -> TraceEvent:
    payload: dict = {"enabled": enabled}
    if enabled:
        payload.update(
            {
                "goal": "执行 Judge 裁决：病理判断首选：番茄叶霉病",
                "steps": steps or ["按裁决建议执行"],
                "required_tools": ["spray_workorder"],
            }
        )
    return _event("planner", payload)


def _memory(confidence: float) -> TraceEvent:
    return _event(
        "memory",
        {
            "layer": "记忆层",
            "agent": "RAG",
            "claim": "症状最匹配：叶霉病",
            "confidence": confidence,
        },
    )


def _debate(conflicts: list[str] | None = None) -> TraceEvent:
    return _event(
        "debate",
        {
            "consensus": ["共识1"],
            "conflicts": conflicts or [],
            "missing_evidence": [],
            "risk_level": "medium",
        },
    )


def _critic(triggered: bool) -> TraceEvent:
    return _event(
        "critic",
        {"triggered": triggered, "resolution": "已降权"} if triggered else {},
    )


def _experts(counterfactual: dict | None = None) -> TraceEvent:
    return _event(
        "experts",
        {
            "layer": "专家层",
            "agent": "病理Agent",
            "claim": "病理判断首选：番茄叶霉病",
            "confidence": 0.7,
            "counterfactual": counterfactual or {},
        },
    )


def _judge(
    confidence: float,
    action_plan: list[str] | None = None,
    sensor_readings: dict | None = None,
) -> TraceEvent:
    payload: dict = {
        "decision": "病理判断首选：番茄叶霉病",
        "confidence": confidence,
        "action_plan": action_plan or ["按裁决建议执行"],
        "judge_analysis": {"sensor_readings": sensor_readings or {}},
    }
    return _event("judge", payload)


def _sensor(anomalous: bool) -> TraceEvent:
    return _event(
        "perception",
        {
            "layer": "感知层",
            "agent": "传感器Agent",
            "claim": "传感器检测到异常" if anomalous else "传感器读数整体正常",
            "confidence": 0.75 if anomalous else 0.65,
            "evidence": {
                "reading": {"readings": {"air_humidity": 40.0}},
                "anomaly": {"detection_result": {"is_anomalous": anomalous}},
            },
        },
    )


def _tool_router(tool_names: list[str]) -> TraceEvent:
    return _event(
        "tool_router",
        {
            "enabled": True,
            "requests": [
                {"tool_name": name, "parameters": {}} for name in tool_names
            ],
            "unresolved": [],
        },
    )


# --------------------------- score shape / safety --------------------------


def test_all_seven_scores_present_on_minimal_trace() -> None:
    scores = compute_capability_scores(_trace(_request()), _case())
    assert set(scores) == set(CAPABILITY_SCORE_KEYS)
    assert all(isinstance(value, float) and 0.0 <= value <= 1.0 for value in scores.values())


def test_declared_capabilities_reads_metadata_and_case_level() -> None:
    metadata_case = _case(raw={"metadata": {"capabilities": ["information_gathering"]}})
    assert declared_capabilities(metadata_case) == ("information_gathering",)
    case_level = _case(raw={"capabilities": ["knowledge_retrieval"]})
    assert declared_capabilities(case_level) == ("knowledge_retrieval",)
    assert declared_capabilities(_case()) == ()


def test_declared_capability_satisfaction() -> None:
    scores = {
        "information_gathering": 1.0,
        "knowledge_retrieval": 0.0,
    }
    satisfaction = declared_capability_satisfaction(
        scores, ("information_gathering", "knowledge_retrieval")
    )
    assert satisfaction == {"information_gathering": True, "knowledge_retrieval": False}


# ------------------------- per-capability scoring --------------------------


def test_information_gathering_score() -> None:
    base = _case(ground_truth="证据不足")
    asked = _trace(
        _request(),
        _planner(True, steps=["按裁决建议执行", "补充缺失证据并复评"]),
        _judge(0.6, action_plan=["补充叶片近景图像"]),
    )
    assert compute_capability_scores(asked, base)["information_gathering"] == 1.0
    silent = _trace(
        _request(),
        _planner(True, steps=["按裁决建议执行"]),
        _judge(0.6, action_plan=["按裁决建议执行"]),
    )
    assert compute_capability_scores(silent, base)["information_gathering"] == 0.0
    planner_off = _trace(_request(), _planner(False))
    assert compute_capability_scores(planner_off, base)["information_gathering"] == 0.0


def test_knowledge_retrieval_score() -> None:
    hit = _trace(_request(), _memory(0.8))
    assert compute_capability_scores(hit, _case())["knowledge_retrieval"] == 1.0
    miss = _trace(_request(), _memory(0.3))
    assert compute_capability_scores(miss, _case())["knowledge_retrieval"] == 0.0


def test_conflict_resolution_score() -> None:
    resolved = _trace(_request(), _debate(conflicts=["冲突1"]), _critic(True))
    assert compute_capability_scores(resolved, _case())["conflict_resolution"] == 1.0
    not_resolved = _trace(_request(), _debate(conflicts=["冲突1"]), _critic(False))
    assert compute_capability_scores(not_resolved, _case())["conflict_resolution"] == 0.0
    no_debate = _trace(_request())
    assert compute_capability_scores(no_debate, _case())["conflict_resolution"] == 0.0


def test_counterfactual_reasoning_score() -> None:
    with_alternative = _trace(
        _request(),
        _experts(counterfactual={"alternative": "早疫病", "rejection_reason": "匹配度低"}),
    )
    assert compute_capability_scores(with_alternative, _case())["counterfactual_reasoning"] == 1.0
    without = _trace(_request(), _experts(counterfactual={}))
    assert compute_capability_scores(without, _case())["counterfactual_reasoning"] == 0.0


def test_uncertainty_quantification_score() -> None:
    insufficient_calibrated = _case(ground_truth="证据不足")
    trace_060 = _trace(_request(), _judge(0.6))
    assert compute_capability_scores(trace_060, insufficient_calibrated)["uncertainty_quantification"] == 1.0
    trace_080 = _trace(_request(), _judge(0.8))
    assert compute_capability_scores(trace_080, insufficient_calibrated)["uncertainty_quantification"] == 0.0
    disease_confident = _case(ground_truth="叶霉病")
    assert compute_capability_scores(trace_060, disease_confident)["uncertainty_quantification"] == 1.0
    trace_040 = _trace(_request(), _judge(0.4))
    assert compute_capability_scores(trace_040, disease_confident)["uncertainty_quantification"] == 0.0


def test_multi_step_planning_score() -> None:
    multi = _trace(_request(), _planner(True, steps=["步骤1", "步骤2", "步骤3"]))
    assert compute_capability_scores(multi, _case())["multi_step_planning"] == 1.0
    single = _trace(_request(), _planner(True, steps=["按裁决建议执行"]))
    assert compute_capability_scores(single, _case())["multi_step_planning"] == 0.0
    disabled = _trace(_request(), _planner(False))
    assert compute_capability_scores(disabled, _case())["multi_step_planning"] == 0.0


def test_sensor_cross_validation_score() -> None:
    anomalous = _trace(
        _request(),
        _sensor(True),
        _judge(0.6, sensor_readings={"air_humidity": 40.0}),
    )
    assert compute_capability_scores(anomalous, _case())["sensor_cross_validation"] == 1.0
    normal = _trace(
        _request(),
        _sensor(False),
        _judge(0.6, sensor_readings={"air_humidity": 65.0}),
    )
    assert compute_capability_scores(normal, _case())["sensor_cross_validation"] == 0.0
    sensor_tool = _trace(
        _request(),
        _sensor(False),
        _tool_router(["sensor_verify"]),
    )
    assert compute_capability_scores(sensor_tool, _case())["sensor_cross_validation"] == 1.0


# --------------------------- metrics integration ---------------------------


def test_compute_trace_metrics_records_capability_scores() -> None:
    trace = _trace(
        _request(),
        _memory(0.8),
        _experts(counterfactual={"alternative": "x"}),
        _judge(0.6),
        _planner(True, steps=["a", "b"]),
    )
    scores = compute_capability_scores(trace, _case(ground_truth="叶霉病"))
    metrics = compute_trace_metrics(
        trace,
        case_id="c",
        expected="叶霉病",
        capability_scores=scores,
    )
    assert metrics.capability_scores["knowledge_retrieval"] == 1.0
    assert metrics.capability_scores["multi_step_planning"] == 1.0
    assert 0.0 <= metrics.capability_scores["uncertainty_quantification"] <= 1.0


def test_aggregate_capability_scores() -> None:
    first = CaseMetrics(
        case_id="a",
        trace_id="t1",
        expected="叶霉病",
        decision="d",
        accuracy=1.0,
        confidence=0.7,
        runtime_seconds=0.1,
        planner_usage=1.0,
        tool_usage=1.0,
        tool_requests=1,
        memory_hits=2,
        debate_rounds=1,
        counterfactual_count=1,
        collective_omission_count=0,
        capability_scores={"knowledge_retrieval": 1.0, "multi_step_planning": 1.0},
    )
    second = CaseMetrics(
        case_id="b",
        trace_id="t2",
        expected="证据不足",
        decision="d",
        accuracy=1.0,
        confidence=0.6,
        runtime_seconds=0.1,
        planner_usage=1.0,
        tool_usage=1.0,
        tool_requests=1,
        memory_hits=0,
        debate_rounds=1,
        counterfactual_count=0,
        collective_omission_count=1,
        capability_scores={"knowledge_retrieval": 0.0, "multi_step_planning": 1.0},
    )
    aggregate = aggregate_capability_scores([first, second])
    assert aggregate["knowledge_retrieval"]["average"] == pytest.approx(0.5)
    assert aggregate["knowledge_retrieval"]["cases"] == 2
    assert aggregate["knowledge_retrieval"]["positive"] == 1
    assert aggregate["multi_step_planning"]["average"] == pytest.approx(1.0)
    assert aggregate["multi_step_planning"]["positive"] == 2
