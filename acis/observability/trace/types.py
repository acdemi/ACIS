"""Unified Trace infrastructure (Phase 2.1E, Sprint 01).

A ``Trace`` is the single source of truth for one orchestrator run. Every
pipeline stage appends an immutable :class:`TraceEvent` to the trace's ordered
``events`` log; per-stage views (``request``, ``experts``, ``judge`` ...) are
derived from that log so there is exactly one source of data.

This module is deliberately free of domain imports so it can be reused and
unit-tested in isolation. Domain serialization lives in :mod:`trace.collector`.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Literal

#: Canonical, ordered set of traceable pipeline stages. ``perception`` is
#: included (in addition to the required stages) so that *every* pipeline
#: stage appends an event, satisfying the "every pipeline stage appends"
#: requirement; the required stages remain the trace's public surface.
TraceStage = Literal[
    "request",
    "perception",
    "memory",
    "experts",
    "debate",
    "critic",
    "judge",
    "planner",
    "tool_router",
    "metrics",
]

#: Stage names in canonical pipeline order.
STAGE_ORDER: tuple[str, ...] = (
    "request",
    "perception",
    "memory",
    "experts",
    "debate",
    "critic",
    "judge",
    "planner",
    "tool_router",
    "metrics",
)

#: Stages mandated by the Phase 2.1E spec (subset of :data:`STAGE_ORDER`).
REQUIRED_STAGES: tuple[str, ...] = (
    "request",
    "memory",
    "experts",
    "debate",
    "critic",
    "judge",
    "planner",
    "tool_router",
    "metrics",
)


@dataclass(frozen=True)
class TraceEvent:
    """An immutable record of a single pipeline-stage observation.

    ``frozen=True`` prevents reassignment of the fields after construction.
    The ``payload`` is deep-copied on construction so the event is an
    independent snapshot of the stage's output; later mutation of the source
    domain object cannot retroactively alter a recorded event.
    """

    stage: str
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.stage not in STAGE_ORDER:
            raise ValueError(
                f"Unknown trace stage: {self.stage!r}. "
                f"Expected one of {STAGE_ORDER}."
            )
        object.__setattr__(self, "payload", copy.deepcopy(self.payload))


@dataclass
class Trace:
    """The single source of truth for one orchestrator run.

    ``events`` is the canonical append-only, chronologically ordered log. The
    per-stage properties (``request`` ... ``metrics``) are read-only filtered
    views over ``events``; they are not duplicated storage, so the trace has
    exactly one source of data.
    """

    trace_id: str
    timestamp: str
    events: list[TraceEvent] = field(default_factory=list)

    def append(self, event: TraceEvent) -> TraceEvent:
        """Append an immutable event and return it."""
        self.events.append(event)
        return event

    def by_stage(self, stage: str) -> list[TraceEvent]:
        """All events recorded for ``stage``, in insertion order."""
        return [event for event in self.events if event.stage == stage]

    @property
    def stages_present(self) -> list[str]:
        """Stage names that have at least one event, in canonical order."""
        present = {event.stage for event in self.events}
        return [stage for stage in STAGE_ORDER if stage in present]

    @property
    def request(self) -> list[TraceEvent]:
        return self.by_stage("request")

    @property
    def perception(self) -> list[TraceEvent]:
        return self.by_stage("perception")

    @property
    def memory(self) -> list[TraceEvent]:
        return self.by_stage("memory")

    @property
    def experts(self) -> list[TraceEvent]:
        return self.by_stage("experts")

    @property
    def debate(self) -> list[TraceEvent]:
        return self.by_stage("debate")

    @property
    def critic(self) -> list[TraceEvent]:
        return self.by_stage("critic")

    @property
    def judge(self) -> list[TraceEvent]:
        return self.by_stage("judge")

    @property
    def planner(self) -> list[TraceEvent]:
        return self.by_stage("planner")

    @property
    def tool_router(self) -> list[TraceEvent]:
        return self.by_stage("tool_router")

    @property
    def metrics(self) -> list[TraceEvent]:
        return self.by_stage("metrics")
