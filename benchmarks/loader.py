"""Benchmark dataset loader (Phase 2.1E, Sprint 03).

Resolves a source name to a JSON dataset file, validates it against
:mod:`benchmarks.schema`, and returns the case list as JSON-native dicts so
the runner's :func:`evals.config.load_dataset` can wrap them into
``EvalCase`` objects. The loader works with the existing runner by exposing
the module-style names the CLI accepts (``benchmarks.datasets.easy`` ...).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmarks.schema import BenchmarkValidationError, validate_dataset

#: Directory holding the built-in JSON datasets.
DATASETS_DIR = Path(__file__).resolve().parent / "datasets"

#: Names served as ``benchmarks.datasets.<name>`` module-style sources.
BUILTIN_DATASETS: tuple[str, ...] = ("easy", "medium", "hard")

#: Prefix recognized by the runner CLI (e.g. ``benchmarks.datasets.easy``).
MODULE_PREFIX = "benchmarks.datasets."


def load_dataset(source: str) -> list[dict[str, Any]]:
    """Load and validate the dataset identified by ``source``.

    ``source`` may be a module-style name (``benchmarks.datasets.easy``), an
    absolute ``.json`` path, or a ``.json`` path relative to the current
    working directory. Returns the validated case list as plain dicts.
    """
    path, difficulty = resolve_dataset(source)
    data = json.loads(path.read_text(encoding="utf-8"))
    return validate_dataset(data, difficulty=difficulty)


def resolve_dataset(source: str) -> tuple[Path, str | None]:
    """Map ``source`` to a dataset file plus its expected difficulty."""
    if source.startswith(MODULE_PREFIX):
        name = source[len(MODULE_PREFIX) :]
        if not name or name not in BUILTIN_DATASETS:
            raise BenchmarkValidationError(
                f"unknown benchmark dataset {source!r}; "
                f"expected one of {[MODULE_PREFIX + n for n in BUILTIN_DATASETS]}"
            )
        return DATASETS_DIR / f"{name}.json", name
    if source.endswith(".json"):
        path = Path(source)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path, None
    raise BenchmarkValidationError(
        f"dataset source {source!r} must be a .json path or a "
        f"{MODULE_PREFIX}<name> module-style name"
    )


__all__ = [
    "BUILTIN_DATASETS",
    "DATASETS_DIR",
    "MODULE_PREFIX",
    "load_dataset",
    "resolve_dataset",
]
