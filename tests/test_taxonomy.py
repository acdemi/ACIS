"""Unit tests for the benchmark taxonomy (Phase 2.1E, Sprint 04.5).

Covers the capability suite definitions, suite dataset loading and
validation (including the mandatory ``design_intent``), the capability
matrix, and the coverage report.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.loader import (
    CAPABILITY_SUITES,
    DATASETS_DIR,
    load_all_suites,
    load_suite,
    suite_dataset_path,
)
from benchmarks.schema import BenchmarkValidationError
from benchmarks.taxonomy import (
    CAPABILITY_COLUMNS,
    SUITE_MIN_CASES,
    SUITES,
    build_capability_matrix,
    get_suite,
    render_capability_matrix,
    render_coverage_report,
    validate_suite_cases,
    write_capability_matrix,
    write_coverage_report,
)

# ------------------------------ suite taxonomy -----------------------------


def test_suites_cover_all_capabilities() -> None:
    assert len(SUITES) == 5
    assert {suite.suite_id for suite in SUITES} == set(CAPABILITY_SUITES)
    assert {suite.targeted_capability for suite in SUITES} == set(CAPABILITY_COLUMNS)
    assert len({suite.suite_id for suite in SUITES}) == len(SUITES)


def test_each_suite_has_minimum_case_target() -> None:
    for suite in SUITES:
        assert suite.min_cases == SUITE_MIN_CASES[suite.suite_id]
        assert (DATASETS_DIR / suite.dataset_name).is_file()


def test_get_suite_lookup() -> None:
    assert get_suite("planning").targeted_capability == "planner"
    with pytest.raises(ValueError):
        get_suite("nope")


# ---------------------------- suite dataset loading -------------------------


@pytest.mark.parametrize("suite_id", CAPABILITY_SUITES)
def test_suite_dataset_meets_minimum_and_validates(suite_id: str) -> None:
    cases = load_suite(suite_id)
    assert len(cases) >= SUITE_MIN_CASES[suite_id]
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert all(case["query"].strip() for case in cases)


@pytest.mark.parametrize("suite_id", CAPABILITY_SUITES)
def test_every_suite_case_has_design_intent(suite_id: str) -> None:
    for case in load_suite(suite_id):
        intent = case.get("design_intent")
        assert isinstance(intent, str) and intent.strip()


def test_load_all_suites_returns_every_suite() -> None:
    cases_by_suite = load_all_suites()
    assert set(cases_by_suite) == set(CAPABILITY_SUITES)
    for suite_id in CAPABILITY_SUITES:
        assert len(cases_by_suite[suite_id]) >= SUITE_MIN_CASES[suite_id]


def test_suite_dataset_path_mapping() -> None:
    assert suite_dataset_path("planning") == DATASETS_DIR / "planning.json"
    with pytest.raises(BenchmarkValidationError):
        suite_dataset_path("nope")


def test_validate_suite_cases_rejects_missing_design_intent() -> None:
    cases = [{"id": "a", "query": "q"}, {"id": "b", "query": "q2"}, {"id": "c", "query": "q3"}]
    with pytest.raises(ValueError, match="design_intent"):
        validate_suite_cases("planning", cases)


def test_validate_suite_cases_rejects_short_suite() -> None:
    cases = [
        {"id": "a", "query": "q", "design_intent": "x"},
        {"id": "b", "query": "q", "design_intent": "x"},
    ]
    with pytest.raises(ValueError, match="at least"):
        validate_suite_cases("planning", cases)


# --------------------------- matrix and coverage ----------------------------


def test_capability_matrix_rows() -> None:
    counts = {"planning": 4, "memory": 4, "debate": 4, "counterfactual": 3, "adversarial": 3}
    rows = build_capability_matrix(SUITES, counts)
    assert len(rows) == 5
    by_suite = {row["suite"]: row for row in rows}
    for suite in SUITES:
        row = by_suite[suite.suite_id]
        assert row["case_count"] == counts[suite.suite_id]
        for capability in CAPABILITY_COLUMNS:
            assert row[capability] is (capability == suite.targeted_capability)


def test_render_capability_matrix() -> None:
    counts = {suite_id: SUITE_MIN_CASES[suite_id] for suite_id in CAPABILITY_SUITES}
    text = render_capability_matrix(
        SUITES,
        counts,
        generated_at="2026-01-01T00:00:00+00:00",
    )
    assert "# Benchmark Capability Matrix" in text
    assert "| Suite | Case Count | Planner | Memory | Debate | Counterfactual | Adversarial |" in text
    assert "| planning | 3 | ✓ |  |  |  |  |" in text
    assert "| memory | 3 |  | ✓ |  |  |  |" in text
    assert "| debate | 2 |  |  | ✓ |  |  |" in text
    assert "| counterfactual | 2 |  |  |  | ✓ |  |" in text
    assert "| adversarial | 2 |  |  |  |  | ✓ |" in text
    assert "design_intent" in text


def test_render_coverage_report() -> None:
    cases = {
        "planning": [{"id": "a", "query": "q", "design_intent": "planner: 任务分解"}],
        "memory": [{"id": "b", "query": "q", "design_intent": "memory: 检索"}],
        "debate": [{"id": "c", "query": "q", "design_intent": "debate: 冲突"}],
        "counterfactual": [
            {"id": "d", "query": "q", "design_intent": "counterfactual: 排除"}
        ],
        "adversarial": [
            {"id": "e", "query": "q", "design_intent": "adversarial: 边界"}
        ],
    }
    text = render_coverage_report(
        SUITES,
        cases,
        generated_at="2026-01-01T00:00:00+00:00",
    )
    assert "# Benchmark Coverage Report" in text
    assert "## Per-module Coverage" in text
    assert "| planner | 1 | 1 | 100% |" in text
    assert "| memory | 1 | 1 | 100% |" in text
    assert "| debate | 1 | 1 | 100% |" in text
    assert "| counterfactual | 1 | 1 | 100% |" in text
    assert "| adversarial | 1 | 1 | 100% |" in text


def test_write_taxonomy_docs(tmp_path: Path) -> None:
    matrix_path = write_capability_matrix(tmp_path / "CAPABILITY_MATRIX.md")
    coverage_path = write_coverage_report(tmp_path / "COVERAGE.md")
    assert matrix_path.is_file()
    assert coverage_path.is_file()
    matrix_text = matrix_path.read_text(encoding="utf-8")
    coverage_text = coverage_path.read_text(encoding="utf-8")
    for suite_id in CAPABILITY_SUITES:
        assert f"| {suite_id} |" in matrix_text
        assert f"| {suite_id} |" in coverage_text
    assert "5" in coverage_text  # suites count

