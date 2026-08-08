"""Agent base types shared across all agent modules.

Refactored from orchestrator.py to avoid circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentOutput:
    layer: str
    agent: str
    claim: str
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    # ACIS 2.0: counterfactual reasoning - alternative diagnosis an expert
    # considered but rejected. Format: {alternative, rejection_reason}.
    counterfactual: dict[str, Any] = field(default_factory=dict)

    # ACIS cognitive upgrade: hypothetical observations that would change
    # this expert conclusion. Optional list[str], defaults to empty list.
    # Each entry is a free-form statement, e.g. if leaf lesions had concentric
    # rings, Alternaria would become the preferred diagnosis. Intended for
    # later Judge robustness analysis.
    counterfactual_observations: list[str] = field(default_factory=list)


@dataclass
class RequestContext:
    query: str
    greenhouse_id: str
    crop: str
    image_path: str | None = None
    intent: str = "diagnose"


@dataclass
class DebateResult:
    consensus: list[str]
    conflicts: list[str]
    missing_evidence: list[str]
    risk_level: str
    critic: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionOutput:
    summary: str
    decision: str
    confidence: float
    risk_level: str
    action_plan: list[str]
    debate: DebateResult
    traces: list[AgentOutput]
    judge_mode: str = "rules"
    need_human_review: bool = False
    reasoning_trace: str = ""
    judge_analysis: dict[str, Any] = field(default_factory=dict)
    decision_id: int | None = None
    #: Optional additive observability — token usage from the LLM judge call.
    #: Present only when the DeepSeek response exposes ``usage``; None otherwise.
    token_usage: dict[str, int] | None = None
