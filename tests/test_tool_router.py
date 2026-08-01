"""Unit tests for the Tool Router (Sprint 01, Phase 9).

Covers ToolRouter.route resolution, ToolRequest fields, RetryPolicy clamping,
and registry override. The Router never executes tools; tests assert it only
builds requests and does not mutate the input plan.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from planner.types import ExecutionPlan  # noqa: E402
from tool_router import (  # noqa: E402
    RetryPolicy,
    ToolDescriptor,
    ToolRequest,
    ToolRouter,
    ToolRoutingResult,
)


def _plan(required_tools, priority="medium"):
    return ExecutionPlan(
        goal="执行 Judge 裁决：番茄叶霉病",
        steps=["清除病叶", "降低湿度"],
        required_tools=required_tools,
        priority=priority,
        estimated_risk="medium",
        estimated_cost="medium",
    )


def test_route_resolves_known_tools():
    result = ToolRouter().route(_plan(["image_capture", "spray_workorder"]))
    assert isinstance(result, ToolRoutingResult)
    assert len(result.requests) == 2
    assert result.unresolved == []
    assert [r.tool_name for r in result.requests] == ["image_capture", "spray_workorder"]


def test_route_collects_unresolved_tools():
    result = ToolRouter().route(_plan(["image_capture", "unknown_tool"]))
    assert len(result.requests) == 1
    assert result.unresolved == ["unknown_tool"]


def test_route_empty_required_tools():
    result = ToolRouter().route(_plan([]))
    assert result.requests == []
    assert result.unresolved == []


def test_tool_request_has_required_fields():
    result = ToolRouter().route(_plan(["sensor_verify"], priority="high"))
    req = result.requests[0]
    assert isinstance(req, ToolRequest)
    assert req.tool_name == "sensor_verify"
    assert isinstance(req.parameters, dict)
    assert req.priority == "high"
    assert req.timeout == 10.0
    assert isinstance(req.retry_policy, RetryPolicy)
    assert req.retry_policy.max_attempts == 3


def test_priority_propagates_from_plan():
    for priority in ("low", "medium", "high"):
        result = ToolRouter().route(_plan(["human_review"], priority=priority))
        assert result.requests[0].priority == priority


def test_parameters_include_goal_and_descriptor_defaults():
    result = ToolRouter().route(_plan(["image_capture"]))
    params = result.requests[0].parameters
    assert params["goal"] == "执行 Judge 裁决：番茄叶霉病"
    assert params["mode"] == "close_up"
    assert params["count"] == 1


def test_custom_registry_overrides_descriptor():
    custom = {
        "image_capture": ToolDescriptor(
            name="image_capture",
            description="custom",
            parameters={"mode": "macro"},
            timeout_seconds=5.0,
            retry_policy=RetryPolicy(max_attempts=5, backoff_seconds=0.5),
        )
    }
    result = ToolRouter(registry=custom).route(_plan(["image_capture"]))
    req = result.requests[0]
    assert req.timeout == 5.0
    assert req.retry_policy.max_attempts == 5
    assert req.parameters["mode"] == "macro"


def test_retry_policy_clamps_invalid_values():
    policy = RetryPolicy(max_attempts=0, backoff_seconds=-1.0)
    assert policy.max_attempts == 1
    assert policy.backoff_seconds == 0.0


def test_route_does_not_mutate_plan():
    plan = _plan(["image_capture", "spray_workorder"])
    original = list(plan.required_tools)
    ToolRouter().route(plan)
    assert plan.required_tools == original


def test_all_planner_tool_names_resolvable():
    planner_tools = [
        "human_review",
        "image_capture",
        "spray_workorder",
        "irrigation_control",
        "sensor_verify",
    ]
    result = ToolRouter().route(_plan(planner_tools))
    assert result.unresolved == []
    assert len(result.requests) == 5