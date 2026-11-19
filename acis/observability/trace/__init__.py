"""Unified Trace infrastructure (Phase 2.1E, Sprint 01).

Public API:

- :class:`Trace`, :class:`TraceEvent`, :data:`STAGE_ORDER` - immutable types.
- :class:`TraceCollector`, :func:`collect_pipeline_trace` - build a trace.
- :func:`trace_to_dict`, :func:`export_trace_json` - serialize a trace.
"""

from __future__ import annotations

from .collector import TraceCollector, collect_pipeline_trace
from .exporter import export_trace_json, trace_to_dict
from .types import REQUIRED_STAGES, STAGE_ORDER, Trace, TraceEvent, TraceStage

__all__ = [
    "REQUIRED_STAGES",
    "STAGE_ORDER",
    "Trace",
    "TraceCollector",
    "TraceEvent",
    "TraceStage",
    "collect_pipeline_trace",
    "export_trace_json",
    "trace_to_dict",
]
