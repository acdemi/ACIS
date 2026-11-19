"""Compatibility launcher for the ACIS CLI.

``python orchestrator.py ...`` is kept for existing scripts and documentation.
New code should import :mod:`acis.core.orchestrator` or run ``python -m acis``.
"""

from __future__ import annotations

from acis.config import load_env

load_env()

from acis.core.orchestrator import (  # noqa: E402
    AgentOrchestrator,
    DecisionOutput,
    _decision_payload,  # noqa: F401 - compatibility re-export
    _print_safe,  # noqa: F401 - compatibility re-export
    build_context,
    format_decision,
    main,
    run_demo,
)

__all__ = [
    "AgentOrchestrator",
    "DecisionOutput",
    "build_context",
    "format_decision",
    "main",
    "run_demo",
]

if __name__ == "__main__":
    main()
