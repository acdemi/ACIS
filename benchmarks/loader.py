"""Benchmark dataset loader (Phase 2.1E, Sprint 03).

Resolves a source name to a JSON dataset file, validates it against
:mod:`benchmarks.schema`, and returns the case list as JSON-native dicts so
the runner's :func:`evals.config.load_dataset` can wrap them into
``EvalCase`` objects. The loader works with the existing runner by exposing
the module-style names the CLI accepts (``benchmarks.datasets.easy`` ...).

Phase 2.1E, Sprint 04.5: adds capability-suite loading — ``load_suite`` /
``load_all_suites`` / ``suite_dataset_path`` back ``--suite planning`` and
``--suite all`` on the runner and ablation CLIs. Suite cases additionally
carry a ``design_intent`` field validated by :mod:`benchmarks.taxonomy`.
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

#: Module-style names that are NOT difficulty tiers (validated without a
#: difficulty minimum). ``enriched`` is the Phase 2.1E Sprint 04.5 extension
#: set, validated via :mod:`benchmarks.metadata`.
NON_DIFFICULTY_DATASETS: tuple[str, ...] = ("enriched",)

#: Prefix recognized by the runner CLI (e.g. ``benchmarks.datasets.easy``).
MODULE_PREFIX = "benchmarks.datasets."

#: Capability suite ids (Phase 2.1E, Sprint 04.5).
CAPABILITY_SUITES: tuple[str, ...] = (
    "planning",
    "memory",
    "debate",
    "counterfactual",
    "adversarial",
)


def load_dataset(source: str) -> list[dict[str, Any]]:
    """Load and validate the dataset identified by ``source``.

    ``source`` may be a module-style name (``benchmarks.datasets.easy``), an
    absolute ``.json`` path, or a ``.json`` path relative to the current
    working directory. Returns the validated case list as plain dicts.
    """
    path, difficulty = resolve_dataset(source)
    data = json.loads(path.read_text(encoding="utf-8"))
    return validate_dataset(data, difficulty=difficulty)


def suite_dataset_path(suite_id: str) -> Path:
    """Map a capability suite id to its JSON dataset path."""
    if suite_id not in CAPABILITY_SUITES:
        raise BenchmarkValidationError(
            f"unknown capability suite {suite_id!r}; "
            f"expected one of {list(CAPABILITY_SUITES)}"
        )
    return DATASETS_DIR / f"{suite_id}.json"


def load_suite(suite_id: str) -> list[dict[str, Any]]:
    """Load and validate one capability suite (schema + taxonomy rules).

    In addition to the shared schema, suite cases must meet the suite's
    minimum count and declare a non-empty ``design_intent`` (validated by
    :func:`benchmarks.taxonomy.validate_suite_cases`).
    """
    path = suite_dataset_path(suite_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = validate_dataset(data)
    from benchmarks.taxonomy import validate_suite_cases  # local: avoid cycle

    validate_suite_cases(suite_id, cases)
    return cases


def load_all_suites() -> dict[str, list[dict[str, Any]]]:
    """Load every capability suite, keyed by suite id (definition order)."""
    return {suite_id: load_suite(suite_id) for suite_id in CAPABILITY_SUITES}


def resolve_dataset(source: str) -> tuple[Path, str | None]:
    """Map ``source`` to a dataset file plus its expected difficulty."""
    if source.startswith(MODULE_PREFIX):
        name = source[len(MODULE_PREFIX) :]
        if name in NON_DIFFICULTY_DATASETS:
            return DATASETS_DIR / f"{name}.json", None
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
    "CAPABILITY_SUITES",
    "DATASETS_DIR",
    "MODULE_PREFIX",
    "NON_DIFFICULTY_DATASETS",
    "load_all_suites",
    "load_dataset",
    "load_suite",
    "resolve_dataset",
    "suite_dataset_path",
]



