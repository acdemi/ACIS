"""Evaluation metrics derived from unified Traces (Phase 2.1E, Sprint 02).

All metrics are computed from the run's :class:`Trace` — the single source of
truth. Wall-clock runtime is measured by the runner and passed in, because the
Trace is snapshotted at the end of a run; expected labels come from the
dataset. This module is domain-free: it only reads ``trace.types`` payload
dicts and never imports agent, planner, or tool-router code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from trace.types import Trace

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
    confidence: float
    runtime_seconds: float
    planner_usage: float
    tool_usage: float
    tool_requests: int
    memory_hits: int
    debate_rounds: int
    counterfactual_count: int
    collective_omission_count: int


def compute_trace_metrics(
    trace: Trace,
    *,
    case_id: str = "",
    runtime_seconds: float = 0.0,
    expected: str | None = None,
    debate_on: bool = True,
) -> CaseMetrics:
    """Derive one case's metrics from its unified Trace."""
    judge = _judge_payload(trace)
    metrics = _metrics_payload(trace)
    planner = metrics.get("planner", {})
    tool_router = metrics.get("tool_router", {})
    tool_requests = int(tool_router.get("requests", 0))
    return CaseMetrics(
        case_id=case_id,
        trace_id=trace.trace_id,
        expected=expected,
        decision=str(judge.get("decision", "")),
        accuracy=_accuracy(expected, _pathology_claim(trace)),
        confidence=float(judge.get("confidence", 0.0)),
        runtime_seconds=max(0.0, runtime_seconds),
        planner_usage=1.0 if bool(planner.get("enabled")) else 0.0,
        tool_usage=1.0 if tool_requests > 0 else 0.0,
        tool_requests=tool_requests,
        memory_hits=_memory_hits(trace),
        debate_rounds=_debate_rounds(trace, debate_on),
        counterfactual_count=_counterfactual_count(trace),
        collective_omission_count=_collective_omission_count(trace),
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
        "accuracy": _mean(scored),
        "average_confidence": _mean([row.confidence for row in rows]),
        "average_runtime": _mean([row.runtime_seconds for row in rows]),
        "planner_usage": _mean([row.planner_usage for row in rows]),
        "tool_usage": _mean([row.tool_usage for row in rows]),
        "memory_hits": sum(row.memory_hits for row in rows),
        "debate_rounds": _mean([float(row.debate_rounds) for row in rows]),
        "counterfactual_count": sum(row.counterfactual_count for row in rows),
        "collective_omission_count": sum(
            row.collective_omission_count for row in rows
        ),
    }


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


def _pathology_claim(trace: Trace) -> str | None:
    for event in trace.events:
        if event.payload.get("agent") == "病理Agent":
            claim = event.payload.get("claim")
            if isinstance(claim, str):
                return claim
    return None


def _accuracy(expected: str | None, claim: str | None) -> float | None:
    if expected is None or claim is None:
        return None
    if expected == "证据不足":
        return 1.0 if "病理证据不足" in claim else 0.0
    return 1.0 if expected in claim else 0.0


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
