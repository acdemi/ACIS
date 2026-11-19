"""Trace exporter (Phase 2.1E, Sprint 01).

Serializes a :class:`~trace.types.Trace` to a plain dict / JSON string. The
output mirrors the Trace's public surface: ``trace_id``, ``timestamp``, one
key per stage (each a list of payload dicts), and the full ordered ``events``
log. Only depends on :mod:`trace.types`, so it stays free of domain imports.
"""

from __future__ import annotations

import json
from typing import Any

from .types import STAGE_ORDER, Trace


def trace_to_dict(trace: Trace) -> dict[str, Any]:
    """Return a JSON-safe dict view of ``trace``.

    Each stage key maps to the list of payload dicts recorded for that stage,
    in insertion order. ``events`` is the full chronological log of
    ``{stage, timestamp, payload}`` records.
    """
    data: dict[str, Any] = {
        "trace_id": trace.trace_id,
        "timestamp": trace.timestamp,
    }
    for stage in STAGE_ORDER:
        data[stage] = [event.payload for event in trace.by_stage(stage)]
    data["events"] = [
        {"stage": event.stage, "timestamp": event.timestamp, "payload": event.payload}
        for event in trace.events
    ]
    return data


def export_trace_json(
    trace: Trace,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> str:
    """Serialize ``trace`` to a JSON string.

    ``default=str`` is a defensive fallback so an unexpected non-JSON-native
    value in a payload is stringified rather than crashing the export.
    """
    return json.dumps(
        trace_to_dict(trace),
        ensure_ascii=ensure_ascii,
        indent=indent,
        default=str,
    )


__all__ = ["export_trace_json", "trace_to_dict"]
