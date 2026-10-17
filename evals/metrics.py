"""Evaluation metrics derived from unified Traces (Phase 2.1E, Sprint 02).

All metrics are computed from the run's :class:`Trace` — the single source of
truth. Wall-clock runtime is measured by the runner and passed in, because the
Trace is snapshotted at the end of a run; expected labels come from the
dataset. This module is domain-free: it only reads ``trace.types`` payload
dicts and never imports agent, planner, or tool-router code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from trace.types import Trace
from typing import Any

from decision_semantics import decision_correctness

#: Memory-layer agent outputs at or above this confidence count as a
#: retrieval / replay "hit". The agents emit ~0.25-0.3 for misses and
#: >=0.5 for actual hits (RAG match, KG constraints, case replay).
MEMORY_HIT_CONFIDENCE = 0.5

_MULTI_ROUND_RE = re.compile(r"【多轮辩论·第(\d+)轮】")


@dataclass(frozen=True)
class CaseMetrics:
    """Metrics computed for a single evaluation case."""

    case_id: str
    trace_id: str
    expected: str | None
    decision: str
    accuracy: float | None
    confidence: float | None
    runtime_seconds: float
    planner_usage: float
    tool_usage: float
    tool_requests: int
    memory_hits: int
    debate_rounds: int
    counterfactual_count: int
    collective_omission_count: int
    capability_scores: dict[str, float] = field(default_factory=dict)
    judge_total_tokens: int = 0


def compute_trace_metrics(
    trace: Trace,
    *,
    case_id: str = "",
    runtime_seconds: float = 0.0,
    expected: str | None = None,
    debate_on: bool = True,
    capability_scores: dict[str, float] | None = None,
) -> CaseMetrics:
    """Derive one case's metrics from its unified Trace."""
    judge = _judge_payload(trace)
    judge_present = bool(judge)
    metrics = _metrics_payload(trace)
    planner = metrics.get("planner", {})
    tool_router = metrics.get("tool_router", {})
    tool_requests = int(tool_router.get("requests", 0))
    token_usage = judge.get("token_usage") or {}
    decision = str(judge.get("decision", "")) if judge_present else ""
    confidence_value = judge.get("confidence")
    try:
        confidence = (
            float(confidence_value)
            if judge_present and confidence_value is not None
            else None
        )
    except (TypeError, ValueError):
        confidence = None
    return CaseMetrics(
        case_id=case_id,
        trace_id=trace.trace_id,
        expected=expected,
        decision=decision,
        accuracy=_accuracy(expected, decision or None),
        confidence=confidence,
        runtime_seconds=max(0.0, runtime_seconds),
        planner_usage=1.0 if bool(planner.get("enabled")) else 0.0,
        tool_usage=1.0 if tool_requests > 0 else 0.0,
        tool_requests=tool_requests,
        memory_hits=_memory_hits(trace),
        debate_rounds=_debate_rounds(trace, debate_on),
        counterfactual_count=_counterfactual_count(trace),
        collective_omission_count=_collective_omission_count(trace),
        capability_scores=dict(capability_scores or {}),
        judge_total_tokens=int(token_usage.get("judge_total_tokens", 0)),
    )


def aggregate_metrics(rows: list[CaseMetrics]) -> dict[str, float | int | None]:
    """Aggregate per-case metrics for the report.

    Rates (accuracy, planner_usage, tool_usage) and averages (confidence,
    runtime, debate_rounds) are means; counts (memory_hits,
    counterfactual_count, collective_omission_count) are totals. Accuracy
    ignores cases without a ground truth.
    """
    scored = [row.accuracy for row in rows if row.accuracy is not None]
    return {
        "cases": len(rows),
        "scored_cases": len(scored),
        "label_accuracy": _mean(scored),
        "accuracy": _mean(scored),  # compatibility alias; prefer label_accuracy
        "average_confidence": _mean(
            [row.confidence for row in rows if row.confidence is not None]
        ),
        "average_runtime": _mean([row.runtime_seconds for row in rows]),
        "planner_usage": _mean([row.planner_usage for row in rows]),
        "tool_usage": _mean([row.tool_usage for row in rows]),
        "memory_hits": sum(row.memory_hits for row in rows),
        "debate_rounds": _mean([float(row.debate_rounds) for row in rows]),
        "counterfactual_count": sum(row.counterfactual_count for row in rows),
        "collective_omission_count": sum(
            row.collective_omission_count for row in rows
        ),
        "judge_total_tokens": sum(row.judge_total_tokens for row in rows),
    }


def aggregate_capability_scores(
    rows: list[CaseMetrics],
) -> dict[str, dict[str, float | int | None]]:
    """Aggregate per-case capability scores by capability.

    Returns ``{capability: {"average": mean, "cases": scored count,
    "positive": count with score > 0}}`` over every row carrying the key.
    """
    keys: set[str] = set()
    for row in rows:
        keys.update(row.capability_scores)
    result: dict[str, dict[str, float | int | None]] = {}
    for capability in sorted(keys):
        values = [
            row.capability_scores[capability]
            for row in rows
            if capability in row.capability_scores
        ]
        values_dict: dict[str, float | int | None] = {
            "average": _mean(values) if values else None,
            "cases": len(values),
            "positive": sum(1 for value in values if value > 0),
        }
        result[capability] = values_dict
    return result


# ---------------------------------------------------------------------------
# trace-derived helpers
# ---------------------------------------------------------------------------
def _judge_payload(trace: Trace) -> dict[str, Any]:
    events = trace.by_stage("judge")
    return events[0].payload if events else {}


def _metrics_payload(trace: Trace) -> dict[str, Any]:
    for event in trace.by_stage("metrics"):
        if "planner" in event.payload:
            return event.payload
    return {}


def _accuracy(expected: str | None, decision: str | None) -> float | None:
    if expected is None or decision is None:
        return None
    return 1.0 if decision_correctness(expected, decision) else 0.0


def _memory_hits(trace: Trace) -> int:
    return sum(
        1
        for event in trace.by_stage("memory")
        if float(event.payload.get("confidence", 0.0)) >= MEMORY_HIT_CONFIDENCE
    )


def _debate_rounds(trace: Trace, debate_on: bool) -> int:
    if not debate_on:
        return 0
    rounds = 1
    for event in trace.by_stage("debate"):
        for item in event.payload.get("consensus", []):
            match = _MULTI_ROUND_RE.search(str(item))
            if match:
                rounds = max(rounds, int(match.group(1)))
    return rounds


def _counterfactual_count(trace: Trace) -> int:
    count = 0
    for event in trace.events:
        payload = event.payload
        if payload.get("counterfactual") or payload.get(
            "counterfactual_observations"
        ):
            count += 1
    return count


def _collective_omission_count(trace: Trace) -> int:
    judge = _judge_payload(trace)
    omission = judge.get("judge_analysis", {}).get("collective_omission", {})
    return len(omission.get("ignored_candidates", []))


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None




