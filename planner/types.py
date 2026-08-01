"""ExecutionPlan dataclass for the Planner MVP (Sprint 01).

Sprint 01 positions the Planner after the Judge (decision-level action planning
per ADR-003), a pragmatic MVP subset of RFC-008. The Planner never executes
tools; ``required_tools`` only declares which MCP tools would be needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExecutionPlan:
    """High-level execution plan derived from a Judge DecisionOutput."""

    goal: str
    steps: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    priority: str = "medium"
    estimated_risk: str = "medium"
    estimated_cost: str = "medium"