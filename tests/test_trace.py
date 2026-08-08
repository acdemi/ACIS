"""Unit tests for the unified Trace infrastructure (Phase 2.1E, Sprint 01).

Covers trace collection (every stage appends an immutable TraceEvent; Planner
ON and OFF both produce a valid trace) and JSON export (required top-level
keys, valid round-trip, JSON-native payloads, snapshot independence).
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from agents.types import AgentOutput, DebateResult, DecisionOutput, RequestContext  # noqa: E402
from planner.types import ExecutionPlan  # noqa: E402
from tool_router import ToolRequest, ToolRoutingResult  # noqa: E402
from trace import (  # noqa: E402
    REQUIRED_STAGES,
    STAGE_ORDER,
    Trace,
    TraceCollector,
    TraceEvent,
    collect_pipeline_trace,
    export_trace_json,
    trace_to_dict,
)

FIXED_TIME = "2026-01-01T00:00:00+00:00"


def _ctx() -> RequestContext:
    return RequestContext(
        query="番茄叶片出现黄斑",
        greenhouse_id="gh-a",
        crop="tomato",
        image_path=None,
        intent="diagnose",
    )


def _agent(
    layer: str, agent: str, claim: str = "claim", confidence: float = 0.7
) -> AgentOutput:
    return AgentOutput(
        layer=layer,
        agent=agent,
        claim=claim,
        confidence=confidence,
        evidence={"key": "value"},
        warnings=["w"],
    )


def _debate() -> DebateResult:
    return DebateResult(
        consensus=["共识1"],
        conflicts=["冲突1"],
        missing_evidence=["缺图"],
        risk_level="medium",
        critic={"triggered": True, "resolution": "已降权", "down_weighted": []},
    )


def _decision(traces: list[AgentOutput]) -> DecisionOutput:
    return DecisionOutput(
        summary="s",
        decision="病理判断首选：番茄灰霉病",
        confidence=0.72,
        risk_level="medium",
        action_plan=["清除病叶"],
        debate=_debate(),
        traces=traces,
        judge_mode="rules",
        need_human_review=False,
        reasoning_trace="rt",
        judge_analysis={"kg": {"diseases": ["番茄灰霉病"]}},
        decision_id=42,
    )


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        goal="g",
        steps=["s1"],
        required_tools=["spray_workorder", "image_capture"],
        priority="medium",
        estimated_risk="medium",
        estimated_cost="medium",
    )


def _tool_result() -> ToolRoutingResult:
    return ToolRoutingResult(
        requests=[
            ToolRequest(
                tool_name="spray_workorder",
                parameters={"goal": "g"},
                priority="medium",
                timeout=15.0,
            )
        ],
        unresolved=["image_capture"],
    )


def _outputs() -> list[AgentOutput]:
    return [
        _agent("感知层", "视觉Agent"),
        _agent("感知层", "传感器Agent"),
        _agent("感知层", "天气Agent"),
        _agent("记忆层", "RAGAgent"),
        _agent("记忆层", "KGAgent"),
        _agent("专家层", "病理Agent"),
        _agent("专家层", "气象Agent"),
    ]


_SENTINEL = object()


def _full_trace(plan=_SENTINEL, tool_result=_SENTINEL):
    outputs = _outputs()
    return collect_pipeline_trace(
        context=_ctx(),
        agent_outputs=outputs,
        debate=_debate(),
        decision=_decision(outputs),
        plan=_plan() if plan is _SENTINEL else plan,
        tool_result=_tool_result() if tool_result is _SENTINEL else tool_result,
        clock=lambda: FIXED_TIME,
    )


# ----------------------------- TraceEvent -----------------------------


def test_trace_event_is_immutable():
    event = TraceEvent(stage="judge", timestamp=FIXED_TIME, payload={"a": 1})
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.stage = "critic"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.timestamp = "x"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.payload = {}  # type: ignore[misc]


def test_trace_event_rejects_unknown_stage():
    with pytest.raises(ValueError):
        TraceEvent(stage="unknown_stage", timestamp=FIXED_TIME, payload={})


def test_trace_event_payload_is_deep_copied_snapshot():
    evidence = {"nested": [1, 2, 3]}
    event = TraceEvent(stage="judge", timestamp=FIXED_TIME, payload=evidence)
    evidence["nested"].append(999)
    assert event.payload["nested"] == [1, 2, 3]


# --------------------------- TraceCollector ---------------------------


def test_collector_records_in_insertion_order():
    collector = TraceCollector(trace_id="t1", clock=lambda: FIXED_TIME)
    collector.record_request(_ctx())
    collector.record_debate(_debate())
    collector.record_judge(_decision([]))
    stages = [event.stage for event in collector.trace.events]
    assert stages == ["request", "debate", "judge"]
    assert collector.trace.trace_id == "t1"
    assert collector.trace.timestamp == FIXED_TIME


def test_collector_generates_trace_id_when_none():
    collector = TraceCollector(clock=lambda: FIXED_TIME)
    assert collector.trace.trace_id
    assert len(collector.trace.trace_id) > 0


def test_trace_per_stage_views_filter_events():
    trace = _full_trace()
    assert len(trace.request) == 1
    assert len(trace.perception) == 3
    assert len(trace.memory) == 2
    assert len(trace.experts) == 2
    assert len(trace.debate) == 1
    assert len(trace.critic) == 1
    assert len(trace.judge) == 1
    assert len(trace.planner) == 1
    assert len(trace.tool_router) == 1
    assert len(trace.metrics) == 1


# ---------------------- collect_pipeline_trace ------------------------


def test_pipeline_trace_has_all_required_stages_in_order():
    trace = _full_trace()
    assert isinstance(trace, Trace)
    present = [event.stage for event in trace.events]
    for stage in REQUIRED_STAGES:
        assert stage in present, stage
    indexes = [STAGE_ORDER.index(stage) for stage in present]
    assert indexes == sorted(indexes)


def test_pipeline_trace_event_count_and_metrics():
    outputs = _outputs()
    trace = collect_pipeline_trace(
        context=_ctx(),
        agent_outputs=outputs,
        debate=_debate(),
        decision=_decision(outputs),
        plan=_plan(),
        tool_result=_tool_result(),
        clock=lambda: FIXED_TIME,
    )
    # request(1) + agents(7) + debate/critic/judge/planner/tool_router/metrics(6)
    assert len(trace.events) == 1 + len(outputs) + 6
    metrics = trace.metrics[0].payload
    counts = metrics["agent_counts"]
    assert counts == {"perception": 3, "memory": 2, "experts": 2, "total": 7}
    assert metrics["planner"] == {"enabled": True, "required_tools": 2}
    assert metrics["tool_router"] == {"enabled": True, "requests": 1, "unresolved": 1}
    assert metrics["total_events"] == len(trace.events)


def test_pipeline_trace_planner_on_records_plan_and_tools():
    trace = _full_trace()
    planner_payload = trace.planner[0].payload
    assert planner_payload["enabled"] is True
    assert planner_payload["goal"] == "g"
    assert "spray_workorder" in planner_payload["required_tools"]
    tr_payload = trace.tool_router[0].payload
    assert tr_payload["enabled"] is True
    assert tr_payload["requests"][0]["tool_name"] == "spray_workorder"
    assert tr_payload["unresolved"] == ["image_capture"]


def test_pipeline_trace_planner_off_still_valid():
    trace = _full_trace(plan=None, tool_result=None)
    assert trace.planner[0].payload["enabled"] is False
    assert trace.tool_router[0].payload["enabled"] is False
    metrics = trace.metrics[0].payload
    assert metrics["planner"] == {"enabled": False, "required_tools": 0}
    assert metrics["tool_router"] == {"enabled": False, "requests": 0, "unresolved": 0}
    present = {event.stage for event in trace.events}
    for stage in REQUIRED_STAGES:
        assert stage in present, stage


def test_pipeline_trace_request_payload_captures_context():
    trace = _full_trace()
    request_payload = trace.request[0].payload
    assert request_payload["query"] == "番茄叶片出现黄斑"
    assert request_payload["greenhouse_id"] == "gh-a"
    assert request_payload["intent"] == "diagnose"


def test_recorded_events_are_independent_of_source_mutation():
    outputs = _outputs()
    decision = _decision(outputs)
    trace = collect_pipeline_trace(
        context=_ctx(),
        agent_outputs=outputs,
        debate=decision.debate,
        decision=decision,
        plan=_plan(),
        tool_result=_tool_result(),
        clock=lambda: FIXED_TIME,
    )
    outputs[0].claim = "MUTATED"
    decision.debate.conflicts.append("新冲突")
    assert trace.perception[0].payload["claim"] == "claim"
    assert trace.debate[0].payload["conflicts"] == ["冲突1"]


# ------------------------------ export --------------------------------


def test_trace_to_dict_has_required_top_level_keys():
    trace = _full_trace()
    data = trace_to_dict(trace)
    expected = {"trace_id", "timestamp", "events", *REQUIRED_STAGES, "perception"}
    for key in expected:
        assert key in data, key


def test_export_trace_json_round_trips():
    trace = _full_trace()
    data = json.loads(export_trace_json(trace))
    assert data["trace_id"] == trace.trace_id
    assert len(data["events"]) == len(trace.events)
    assert data["events"][0]["stage"] == "request"
    assert data["judge"][0]["decision"] == "病理判断首选：番茄灰霉病"
    assert data["metrics"][0]["agent_counts"]["total"] == 7


def test_export_trace_json_payload_is_json_native():
    trace = _full_trace()
    data = json.loads(export_trace_json(trace))
    assert data["experts"][0]["agent"] == "病理Agent"
    assert "retry_policy" in data["tool_router"][0]["requests"][0]
    assert data["tool_router"][0]["requests"][0]["retry_policy"]["max_attempts"] >= 1


def test_export_trace_json_with_ensure_ascii():
    trace = _full_trace()
    text = export_trace_json(trace, ensure_ascii=True)
    assert "\\u" in text or "番茄" not in text
    data = json.loads(text)
    assert data["request"][0]["query"] == "番茄叶片出现黄斑"
