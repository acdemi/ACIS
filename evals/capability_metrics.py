"""Capability evaluation engine (Phase 2.1E, Sprint 04.5C).

Translates each capability's observable-evidence ``success_condition`` into
an executable, Trace-driven check. Every score is computed automatically
from the unified Trace (planner / memory / debate / critic / judge /
tool_router / perception events) plus the case's ground truth — no external
human judgment is involved.

Each scorer returns ``0.0`` or ``1.0``; the seven keys always present in the
resulting score dict match :data:`benchmarks.capabilities.ALL_CAPABILITIES`.
"""

from __future__ import annotations

from trace.types import Trace
from typing import Any

from benchmarks.capabilities import ALL_CAPABILITIES, Capability

#: Score dict keys, aligned with the capability enum.
CAPABILITY_SCORE_KEYS: tuple[str, ...] = tuple(
    capability.value for capability in ALL_CAPABILITIES
)

#: Confidence threshold below which an evidence-insufficient decision is
#: considered well-calibrated (uncertainty_quantification).
UNCERTAINTY_CONFIDENCE_MAX = 0.7

#: Confidence floor for a confident decision when evidence supports it.
CONFIDENT_CONFIDENCE_MIN = 0.5

#: Memory-layer confidence threshold for a retrieval hit (matches
#: ``evals.metrics.MEMORY_HIT_CONFIDENCE``).
MEMORY_HIT_CONFIDENCE = 0.5

#: Keywords indicating an active request for missing information.
INFO_REQUEST_KEYWORDS: tuple[str, ...] = (
    "询问",
    "补充",
    "获取",
    "收集",
    "检查",
    "确认",
    "采样",
    "取样",
    "送检",
    "复检",
    "观察",
    "记录",
    "信息",
)

_SENSOR_AGENT = "传感器Agent"
_PATHOLOGY_AGENT = "病理Agent"


def compute_capability_scores(trace: Trace, case: Any) -> dict[str, float]:
    """Compute 0-1 capability scores for one case from its Trace."""
    return {
        Capability.INFORMATION_GATHERING.value: _score_information_gathering(trace),
        Capability.KNOWLEDGE_RETRIEVAL.value: _score_knowledge_retrieval(trace),
        Capability.CONFLICT_RESOLUTION.value: _score_conflict_resolution(trace),
        Capability.COUNTERFACTUAL_REASONING.value: _score_counterfactual_reasoning(trace),
        Capability.UNCERTAINTY_QUANTIFICATION.value: _score_uncertainty_quantification(
            trace, case
        ),
        Capability.MULTI_STEP_PLANNING.value: _score_multi_step_planning(trace),
        Capability.SENSOR_CROSS_VALIDATION.value: _score_sensor_cross_validation(trace),
    }


def declared_capabilities(case: Any) -> tuple[str, ...]:
    """Capabilities explicitly declared by the case (metadata or case level)."""
    raw = getattr(case, "raw", None) if not isinstance(case, dict) else case
    raw = raw if isinstance(raw, dict) else {}
    metadata = raw.get("metadata")
    if isinstance(metadata, dict) and metadata.get("capabilities"):
        values = metadata["capabilities"]
    elif raw.get("capabilities"):
        values = raw["capabilities"]
    else:
        return ()
    return tuple(str(value) for value in values if value)


def declared_capability_satisfaction(
    scores: dict[str, float],
    declared: tuple[str, ...],
) -> dict[str, bool]:
    """Whether each declared capability scored above zero."""
    return {capability: scores.get(capability, 0.0) > 0.0 for capability in declared}


# ---------------------------------------------------------------------------
# per-capability scorers (Trace-driven)
# ---------------------------------------------------------------------------


def _score_information_gathering(trace: Trace) -> float:
    payload = _planner_payload(trace)
    if not payload.get("enabled"):
        return 0.0
    texts = [str(payload.get("goal", ""))]
    texts += [str(step) for step in payload.get("steps", [])]
    judge = _judge_payload(trace)
    texts += [str(item) for item in judge.get("action_plan", [])]
    return 1.0 if any(
        keyword in text for text in texts for keyword in INFO_REQUEST_KEYWORDS
    ) else 0.0


def _score_knowledge_retrieval(trace: Trace) -> float:
    return 1.0 if _memory_hits(trace) >= 1 else 0.0


def _score_conflict_resolution(trace: Trace) -> float:
    debate = trace.by_stage("debate")
    critic = _critic_payload(trace)
    if not debate:
        return 0.0
    return 1.0 if bool(critic.get("triggered")) else 0.0


def _score_counterfactual_reasoning(trace: Trace) -> float:
    return 1.0 if _counterfactual_count(trace) >= 1 else 0.0


def _score_uncertainty_quantification(trace: Trace, case: Any) -> float:
    confidence = float(_judge_payload(trace).get("confidence", 0.0))
    if _evidence_insufficient(case, trace):
        return 1.0 if confidence <= UNCERTAINTY_CONFIDENCE_MAX else 0.0
    return 1.0 if confidence >= CONFIDENT_CONFIDENCE_MIN else 0.0


def _score_multi_step_planning(trace: Trace) -> float:
    payload = _planner_payload(trace)
    if not payload.get("enabled"):
        return 0.0
    return 1.0 if len(payload.get("steps", [])) >= 2 else 0.0


def _score_sensor_cross_validation(trace: Trace) -> float:
    anomaly = any(
        "异常" in str(payload.get("claim", ""))
        for payload in _sensor_agent_payloads(trace)
    )
    judge = _judge_payload(trace)
    sensor_used = bool(judge.get("judge_analysis", {}).get("sensor_readings"))
    tools = [
        str(request.get("tool_name", ""))
        for request in _tool_requests(trace)
    ]
    return 1.0 if (anomaly and sensor_used) or "sensor_verify" in tools else 0.0


# ---------------------------------------------------------------------------
# Trace helpers
# ---------------------------------------------------------------------------


def _planner_payload(trace: Trace) -> dict[str, Any]:
    events = trace.by_stage("planner")
    return events[0].payload if events else {}


def _judge_payload(trace: Trace) -> dict[str, Any]:
    events = trace.by_stage("judge")
    return events[0].payload if events else {}


def _critic_payload(trace: Trace) -> dict[str, Any]:
    events = trace.by_stage("critic")
    return events[0].payload if events else {}


def _memory_hits(trace: Trace) -> int:
    return sum(
        1
        for event in trace.by_stage("memory")
        if float(event.payload.get("confidence", 0.0)) >= MEMORY_HIT_CONFIDENCE
    )


def _counterfactual_count(trace: Trace) -> int:
    return sum(
        1
        for event in trace.events
        if event.payload.get("counterfactual")
        or event.payload.get("counterfactual_observations")
    )


def _sensor_agent_payloads(trace: Trace) -> list[dict[str, Any]]:
    return [
        event.payload
        for event in trace.by_stage("perception")
        if event.payload.get("agent") == _SENSOR_AGENT
    ]


def _tool_requests(trace: Trace) -> list[dict[str, Any]]:
    payload = trace.by_stage("tool_router")
    if not payload:
        return []
    requests = payload[0].payload.get("requests", [])
    return requests if isinstance(requests, list) else []


def _evidence_insufficient(case: Any, trace: Trace) -> bool:
    ground_truth = getattr(case, "ground_truth", None)
    if ground_truth == "证据不足":
        return True
    for event in trace.events:
        if event.payload.get("agent") == _PATHOLOGY_AGENT:
            claim = str(event.payload.get("claim", ""))
            if "病理证据不足" in claim:
                return True
    return False


__all__ = [
    "CAPABILITY_SCORE_KEYS",
    "CONFIDENT_CONFIDENCE_MIN",
    "INFO_REQUEST_KEYWORDS",
    "MEMORY_HIT_CONFIDENCE",
    "UNCERTAINTY_CONFIDENCE_MAX",
    "compute_capability_scores",
    "declared_capabilities",
    "declared_capability_satisfaction",
]

