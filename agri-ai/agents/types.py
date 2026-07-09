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
