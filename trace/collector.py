"""Trace collector (Phase 2.1E, Sprint 01).

Turns pipeline artifacts (request context, agent outputs, debate/critic state,
judge decision, planner plan, tool-router result) into immutable
:class:`~trace.types.TraceEvent` objects and aggregates them into a
:class:`~trace.types.Trace`.

The collector is the only trace module that depends on the domain data
contracts (``agents.types``, ``planner.types``, ``tool_router.types``); it only
*reads* them and never mutates them, so no existing API or cognitive behavior
changes. ``dataclasses.asdict`` is used where a whole object is wanted so each
event holds an independent deep snapshot.
"""

from __future__ import annotations

import dataclasses
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from agents.types import AgentOutput, DebateResult, DecisionOutput, RequestContext
from planner.types import ExecutionPlan
from tool_router.types import ToolRoutingResult

from .types import STAGE_ORDER, Trace, TraceEvent

#: Layer labels used by the agent fleet. Outputs are bucketed into trace stages
#: by ``AgentOutput.layer`` so perception / memory / experts stay separable
#: inside the single ``decision.traces`` list.
_LAYER_PERCEPTION = "感知层"
_LAYER_MEMORY = "记忆层"
_LAYER_EXPERTS = "专家层"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_trace_id() -> str:
    return uuid.uuid4().hex


def _serialize_request(context: RequestContext) -> dict[str, Any]:
    return {
        "query": context.query,
        "greenhouse_id": context.greenhouse_id,
        "crop": context.crop,
        "image_path": context.image_path,
        "intent": context.intent,
    }


def _serialize_agent_output(output: AgentOutput) -> dict[str, Any]:
    return dataclasses.asdict(output)


def _serialize_debate(debate: DebateResult) -> dict[str, Any]:
    return {
        "consensus": list(debate.consensus),
        "conflicts": list(debate.conflicts),
        "missing_evidence": list(debate.missing_evidence),
        "risk_level": debate.risk_level,
    }


def _serialize_critic(debate: DebateResult) -> dict[str, Any]:
    return dict(debate.critic)


def _serialize_decision(decision: DecisionOutput) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "summary": decision.summary,
        "decision": decision.decision,
        "confidence": decision.confidence,
        "risk_level": decision.risk_level,
        "judge_mode": decision.judge_mode,
        "need_human_review": decision.need_human_review,
        "reasoning_trace": decision.reasoning_trace,
        "judge_analysis": dict(decision.judge_analysis),
        "action_plan": list(decision.action_plan),
        "decision_id": decision.decision_id,
    }
    if decision.token_usage is not None:
        payload["token_usage"] = dict(decision.token_usage)
    return payload


def _serialize_plan(plan: ExecutionPlan | None) -> dict[str, Any]:
    if plan is None:
        return {"enabled": False}
    return {"enabled": True, **dataclasses.asdict(plan)}


def _serialize_tool_result(result: ToolRoutingResult | None) -> dict[str, Any]:
    if result is None:
        return {"enabled": False}
    return {
        "enabled": True,
        "requests": [dataclasses.asdict(request) for request in result.requests],
        "unresolved": list(result.unresolved),
    }


def _build_metrics(
    *,
    agent_outputs: list[AgentOutput],
    debate: DebateResult,
    decision: DecisionOutput,
    plan: ExecutionPlan | None,
    tool_result: ToolRoutingResult | None,
    total_events: int,
) -> dict[str, Any]:
    perception = sum(1 for o in agent_outputs if o.layer == _LAYER_PERCEPTION)
    memory = sum(1 for o in agent_outputs if o.layer == _LAYER_MEMORY)
    experts = sum(1 for o in agent_outputs if o.layer == _LAYER_EXPERTS)
    return {
        "agent_counts": {
            "perception": perception,
            "memory": memory,
            "experts": experts,
            "total": len(agent_outputs),
        },
        "debate": {
            "consensus": len(debate.consensus),
            "conflicts": len(debate.conflicts),
            "missing_evidence": len(debate.missing_evidence),
            "risk_level": debate.risk_level,
        },
        "critic": {"triggered": bool(debate.critic.get("triggered"))},
        "judge": {
            "confidence": decision.confidence,
            "risk_level": decision.risk_level,
            "need_human_review": decision.need_human_review,
            "judge_mode": decision.judge_mode,
        },
        "planner": {
            "enabled": plan is not None,
            "required_tools": len(plan.required_tools) if plan else 0,
        },
        "tool_router": {
            "enabled": tool_result is not None,
            "requests": len(tool_result.requests) if tool_result else 0,
            "unresolved": len(tool_result.unresolved) if tool_result else 0,
        },
        "total_events": total_events,
    }


class TraceCollector:
    """Builds a :class:`Trace` by recording one event per pipeline stage."""

    def __init__(
        self,
        trace_id: str | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock or _now_iso
        self._trace = Trace(
            trace_id=trace_id or _new_trace_id(),
            timestamp=self._clock(),
        )

    @property
    def trace(self) -> Trace:
        return self._trace

    def record(self, stage: str, payload: dict[str, Any] | None = None) -> TraceEvent:
        """Record an immutable event for ``stage`` and append it to the trace."""
        event = TraceEvent(stage=stage, timestamp=self._clock(), payload=payload or {})
        return self._trace.append(event)

    def record_request(self, context: RequestContext) -> TraceEvent:
        return self.record("request", _serialize_request(context))

    def record_agents(self, stage: str, outputs: list[AgentOutput]) -> list[TraceEvent]:
        """Record one event per agent output under ``stage``."""
        return [
            self.record(stage, _serialize_agent_output(output))
            for output in outputs
        ]

    def record_debate(self, debate: DebateResult) -> TraceEvent:
        return self.record("debate", _serialize_debate(debate))

    def record_critic(self, debate: DebateResult) -> TraceEvent:
        return self.record("critic", _serialize_critic(debate))

    def record_judge(self, decision: DecisionOutput) -> TraceEvent:
        return self.record("judge", _serialize_decision(decision))

    def record_planner(self, plan: ExecutionPlan | None) -> TraceEvent:
        return self.record("planner", _serialize_plan(plan))

    def record_tool_router(self, result: ToolRoutingResult | None) -> TraceEvent:
        return self.record("tool_router", _serialize_tool_result(result))

    def record_metrics(
        self,
        *,
        agent_outputs: list[AgentOutput],
        debate: DebateResult,
        decision: DecisionOutput,
        plan: ExecutionPlan | None,
        tool_result: ToolRoutingResult | None,
    ) -> TraceEvent:
        total_events = len(self._trace.events) + 1  # include this metrics event
        return self.record(
            "metrics",
            _build_metrics(
                agent_outputs=agent_outputs,
                debate=debate,
                decision=decision,
                plan=plan,
                tool_result=tool_result,
                total_events=total_events,
            ),
        )


def collect_pipeline_trace(
    *,
    context: RequestContext,
    agent_outputs: list[AgentOutput],
    debate: DebateResult,
    decision: DecisionOutput,
    plan: ExecutionPlan | None,
    tool_result: ToolRoutingResult | None,
    trace_id: str | None = None,
    clock: Callable[[], str] | None = None,
) -> Trace:
    """Build a complete :class:`Trace` from one orchestrator run's artifacts.

    Agent outputs are split into perception / memory / experts by their
    ``layer`` label and recorded under the corresponding stage. Planner and
    tool-router artifacts are optional so Planner ON and OFF both produce a
    valid trace.
    """
    collector = TraceCollector(trace_id=trace_id, clock=clock)
    collector.record_request(context)

    perception = [o for o in agent_outputs if o.layer == _LAYER_PERCEPTION]
    memory = [o for o in agent_outputs if o.layer == _LAYER_MEMORY]
    experts = [o for o in agent_outputs if o.layer == _LAYER_EXPERTS]
    collector.record_agents("perception", perception)
    collector.record_agents("memory", memory)
    collector.record_agents("experts", experts)

    collector.record_debate(debate)
    collector.record_critic(debate)
    collector.record_judge(decision)
    collector.record_planner(plan)
    collector.record_tool_router(tool_result)
    collector.record_metrics(
        agent_outputs=agent_outputs,
        debate=debate,
        decision=decision,
        plan=plan,
        tool_result=tool_result,
    )
    return collector.trace


__all__ = [
    "STAGE_ORDER",
    "Trace",
    "TraceCollector",
    "TraceEvent",
    "collect_pipeline_trace",
]
