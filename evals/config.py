"""Evaluation Runner configuration (Phase 2.1E, Sprint 02).

Configuration and dataset loading for the ACIS Evaluation Runner. The runner
honors four subsystem toggles (planner, debate, memory, tool_router) and
records them in the experiment report so runs are reproducible.

Phase 2.1E, Sprint 03: dataset loading also accepts benchmark module-style
names (``benchmarks.datasets.easy`` ...) backed by JSON files, and the
configuration carries the ``save_traces`` flag used by the runner's
``--save-traces`` CLI option (default off).
"""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_DATASET = "evals.fixtures"
DEFAULT_OUTPUT_DIR = "results"

#: Module-style names served by the benchmark framework (see benchmarks/).
BENCHMARK_PREFIX = "benchmarks.datasets."


@dataclass(frozen=True)
class EvalConfig:
    """Reproducible experiment configuration."""

    dataset: str = DEFAULT_DATASET
    planner_on: bool = True
    debate_on: bool = True
    memory_on: bool = True
    tool_router_on: bool = True
    output_dir: str = DEFAULT_OUTPUT_DIR
    use_langgraph: bool = True
    seed: int = 7
    max_cases: int | None = None
    persist: bool = False
    save_traces: bool = False


@dataclass(frozen=True)
class EvalCase:
    """A single labeled benchmark case."""

    id: str
    query: str
    ground_truth: str | None = None
    sensor_override: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def load_dataset(source: str | None = None) -> list[EvalCase]:
    """Load a dataset from a JSON file or a Python module path.

    JSON datasets are either a list of case dicts or an object with a
    ``cases`` list. Benchmark module-style names (``benchmarks.datasets.*``)
    are resolved to schema-validated JSON by :mod:`benchmarks.loader`.
    Other module datasets must expose ``FIXTURES``, ``CASES``, or ``DATASET``.
    Every case requires ``id`` and ``query``.
    """
    src = source or DEFAULT_DATASET
    if src.endswith(".json"):
        raw = json.loads(Path(src).read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else raw.get("cases", [])
    elif src.startswith(BENCHMARK_PREFIX):
        loader = importlib.import_module("benchmarks.loader")
        items = loader.load_dataset(src)
    else:
        module = importlib.import_module(src)
        items = (
            getattr(module, "FIXTURES", None)
            or getattr(module, "CASES", None)
            or getattr(module, "DATASET", None)
        )
        if items is None:
            raise ValueError(
                f"dataset module {src!r} must expose FIXTURES, CASES, or DATASET"
            )
    return [_to_case(item) for item in items]


def _to_case(item: Any) -> EvalCase:
    if not isinstance(item, dict) or "id" not in item or "query" not in item:
        raise ValueError("every dataset case must be a dict with 'id' and 'query'")
    return EvalCase(
        id=str(item["id"]),
        query=str(item["query"]),
        ground_truth=item.get("ground_truth"),
        sensor_override=item.get("sensor_override"),
        raw=dict(item),
    )
