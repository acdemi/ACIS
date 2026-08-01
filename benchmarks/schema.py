"""Benchmark dataset schema and validation (Phase 2.1E, Sprint 03).

Defines the contract every benchmark dataset must satisfy so it can be
consumed by :class:`evals.config.EvalCase`: every case carries a unique
``id`` and a non-empty ``query``, with optional ``ground_truth`` and
``sensor_override`` fields. Extra metadata fields (``crop``, ``intent``,
``disease``, ``expect_critic`` ...) are preserved untouched for traceability
and future scoring.

This module is domain-free: it only validates JSON-native dicts and never
imports agent, planner, or evals code.
"""

from __future__ import annotations

from typing import Any

#: Difficulty labels supported by the benchmark framework.
DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard")

#: Minimum number of cases per difficulty (CURRENT_SPRINT deliverable 2).
MIN_CASES_BY_DIFFICULTY: dict[str, int] = {
    "easy": 10,
    "medium": 10,
    "hard": 5,
}

#: Fields every case must carry.
REQUIRED_CASE_FIELDS: tuple[str, ...] = ("id", "query")


class BenchmarkValidationError(ValueError):
    """Raised when a benchmark dataset violates the schema contract."""


def validate_dataset(
    data: Any,
    *,
    difficulty: str | None = None,
) -> list[dict[str, Any]]:
    """Validate a parsed benchmark dataset and return the case list.

    Accepts either a bare JSON array of case dicts or an object with a
    ``cases`` list (optionally carrying ``name`` and ``difficulty``
    metadata). When ``difficulty`` is given (module-style source) the
    dataset-level ``difficulty`` field, if present, must match it, and the
    case count must meet the minimum for that difficulty.
    """
    if isinstance(data, list):
        cases, meta_difficulty = data, None
    elif isinstance(data, dict) and isinstance(data.get("cases"), list):
        cases = data["cases"]
        meta_difficulty = data.get("difficulty")
    else:
        raise BenchmarkValidationError(
            "dataset must be a JSON array of cases or an object with a "
            "'cases' list"
        )

    if meta_difficulty is not None and meta_difficulty not in DIFFICULTIES:
        raise BenchmarkValidationError(
            f"unknown difficulty {meta_difficulty!r}; "
            f"expected one of {list(DIFFICULTIES)}"
        )
    if difficulty is not None and difficulty not in DIFFICULTIES:
        raise BenchmarkValidationError(
            f"unknown difficulty {difficulty!r}; "
            f"expected one of {list(DIFFICULTIES)}"
        )
    if (
        difficulty is not None
        and meta_difficulty is not None
        and meta_difficulty != difficulty
    ):
        raise BenchmarkValidationError(
            f"difficulty mismatch: file says {meta_difficulty!r}, "
            f"expected {difficulty!r}"
        )

    effective = difficulty or meta_difficulty
    minimum = MIN_CASES_BY_DIFFICULTY.get(effective, 0) if effective else 0
    if len(cases) < minimum:
        raise BenchmarkValidationError(
            f"dataset {effective!r} needs at least {minimum} cases, "
            f"got {len(cases)}"
        )

    validated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        validated.append(_validate_case(case, index, seen_ids))
    return validated


def _validate_case(
    case: Any,
    index: int,
    seen_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(case, dict):
        raise BenchmarkValidationError(f"case {index} must be an object")
    for field in REQUIRED_CASE_FIELDS:
        if field not in case:
            raise BenchmarkValidationError(
                f"case {index} is missing required field {field!r}"
            )
    if not isinstance(case["id"], str) or not case["id"].strip():
        raise BenchmarkValidationError(f"case {index} has a non-empty id")
    if not isinstance(case["query"], str) or not case["query"].strip():
        raise BenchmarkValidationError(f"case {index} has a non-empty query")
    if case["id"] in seen_ids:
        raise BenchmarkValidationError(f"duplicate case id {case['id']!r}")
    seen_ids.add(case["id"])

    ground_truth = case.get("ground_truth")
    if ground_truth is not None and not isinstance(ground_truth, str):
        raise BenchmarkValidationError(
            f"case {case['id']!r}: ground_truth must be a string or null"
        )
    override = case.get("sensor_override")
    if override is not None:
        _validate_sensor_override(case["id"], override)
    return dict(case)


def _validate_sensor_override(case_id: str, override: Any) -> None:
    if not isinstance(override, dict) or not all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in override.values()
    ):
        raise BenchmarkValidationError(
            f"case {case_id!r}: sensor_override must be a dict of numeric "
            "offset values"
        )


__all__ = [
    "DIFFICULTIES",
    "MIN_CASES_BY_DIFFICULTY",
    "REQUIRED_CASE_FIELDS",
    "BenchmarkValidationError",
    "validate_dataset",
]

