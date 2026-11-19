"""Tool Router types (Sprint 01, Phase 9).

The Tool Router sits between the Planner (ExecutionPlan) and a future Executor.
It resolves each ``required_tools`` entry to a :class:`ToolDescriptor` and emits
a :class:`ToolRequest`. It never executes tools (RFC-005 Tool Protocol; the
execution-level boundary per ADR-003). Tool execution belongs to the MCP /
Executor layer in a later sprint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetryPolicy:
    """Retry configuration for a tool request."""

    max_attempts: int = 1
    backoff_seconds: float = 0.0

    def __post_init__(self) -> None:
        self.max_attempts = max(self.max_attempts, 1)
        if self.backoff_seconds < 0:
            self.backoff_seconds = 0.0


@dataclass
class ToolDescriptor:
    """Static description of a tool, held in the router registry."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)


@dataclass
class ToolRequest:
    """A request to execute a tool, produced by the router (not executed here).

    Fields follow the Sprint 01 spec: ``tool_name``, ``parameters``,
    ``priority``, ``timeout``, ``retry_policy``. RFC-005 additionally defines
    ``request_id`` / ``caller``; these are deferred to the Executor sprint.
    """

    tool_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    priority: str = "medium"
    timeout: float = 30.0
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)


@dataclass
class ToolRoutingResult:
    """Outcome of routing an ExecutionPlan: resolved requests + unresolved names."""

    requests: list[ToolRequest] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)