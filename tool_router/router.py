"""Tool Router - resolves an ExecutionPlan's required_tools into ToolRequests.

Sprint 01 (Phase 9): the Router inspects ``ExecutionPlan.required_tools``,
resolves each name to a :class:`ToolDescriptor` from its registry, and emits a
:class:`ToolRequest` per resolved tool. It NEVER executes tools; unknown names
are collected as ``unresolved`` for a future Executor / human to handle.

Loose coupling: the Router depends only on the ``ExecutionPlan`` contract (its
``required_tools`` and ``priority`` fields), not on the Planner or Orchestrator.
This keeps ``Planner -> Tool Router -> Executor`` decoupled (RFC-005 section 4).
"""
from __future__ import annotations

from typing import Any

from planner.types import ExecutionPlan
from tool_router.types import (
    RetryPolicy,
    ToolDescriptor,
    ToolRequest,
    ToolRoutingResult,
)

_DEFAULT_REGISTRY: dict[str, ToolDescriptor] = {
    "image_capture": ToolDescriptor(
        name="image_capture",
        description="采集叶片近景图像以补充视觉/病理交叉验证证据",
        parameters={"mode": "close_up", "count": 1},
        timeout_seconds=20.0,
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=1.0),
    ),
    "spray_workorder": ToolDescriptor(
        name="spray_workorder",
        description="生成施药工单（药剂、剂量、施用方式）",
        parameters={},
        timeout_seconds=15.0,
        retry_policy=RetryPolicy(max_attempts=1, backoff_seconds=0.0),
    ),
    "irrigation_control": ToolDescriptor(
        name="irrigation_control",
        description="控制灌溉设备执行水肥作业",
        parameters={"action": "schedule"},
        timeout_seconds=30.0,
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=2.0),
    ),
    "sensor_verify": ToolDescriptor(
        name="sensor_verify",
        description="复核传感器读数，确认环境异常",
        parameters={},
        timeout_seconds=10.0,
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=1.0),
    ),
    "human_review": ToolDescriptor(
        name="human_review",
        description="提请人工复核裁决与关键证据",
        parameters={},
        timeout_seconds=300.0,
        retry_policy=RetryPolicy(max_attempts=1, backoff_seconds=0.0),
    ),
}


class ToolRouter:
    """Resolve an ExecutionPlan into ToolRequests without executing them."""

    def __init__(self, registry: dict[str, ToolDescriptor] | None = None):
        self.registry: dict[str, ToolDescriptor] = dict(_DEFAULT_REGISTRY)
        if registry:
            self.registry.update(registry)

    def route(self, plan: ExecutionPlan) -> ToolRoutingResult:
        requests: list[ToolRequest] = []
        unresolved: list[str] = []
        for tool_name in plan.required_tools:
            descriptor = self.registry.get(tool_name)
            if descriptor is None:
                if tool_name not in unresolved:
                    unresolved.append(tool_name)
                continue
            requests.append(self._build_request(plan, descriptor))
        return ToolRoutingResult(requests=requests, unresolved=unresolved)

    @staticmethod
    def _build_request(plan: ExecutionPlan, descriptor: ToolDescriptor) -> ToolRequest:
        parameters: dict[str, Any] = dict(descriptor.parameters)
        parameters.setdefault("goal", plan.goal)
        return ToolRequest(
            tool_name=descriptor.name,
            parameters=parameters,
            priority=plan.priority,
            timeout=descriptor.timeout_seconds,
            retry_policy=RetryPolicy(
                max_attempts=descriptor.retry_policy.max_attempts,
                backoff_seconds=descriptor.retry_policy.backoff_seconds,
            ),
        )