"""Validation tests for the Phase 4 Challenge Set (benchmarks/challenge_set_v1.json).

Verifies the file exists, every probe group carries at least 5 cases, every
case carries the required fields (id, group, difficulty, input,
expected_key_factors) with legal values, group labels are drawn from
:data:`openmetaphysics.evaluation.challenge_scorer.VALID_GROUPS`, and the set
is fully isolated from the Phase 3 built-in datasets (no shared ids, no
loader-name collisions).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.loader import DATASETS_DIR, load_all_suites, load_dataset
from openmetaphysics.evaluation.challenge_scorer import VALID_GROUPS

CHALLENGE_PATH = Path(__file__).resolve().parent.parent / "benchmarks" / (
    "challenge_set_v1.json"
)
MIN_CASES_PER_GROUP = 5
REQUIRED_CASE_FIELDS = ("id", "group", "difficulty", "input", "expected_key_factors")


@pytest.fixture(scope="module")
def challenge_set() -> dict:
    if not CHALLENGE_PATH.exists():
        pytest.fail(f"challenge set missing at {CHALLENGE_PATH}")
    return json.loads(CHALLENGE_PATH.read_text(encoding="utf-8"))


def _all_cases(challenge_set: dict) -> list[dict]:
    return [
        case
        for spec in challenge_set["groups"].values()
        for case in spec["cases"]
    ]


def test_challenge_set_file_exists() -> None:
    assert CHALLENGE_PATH.exists()
    assert CHALLENGE_PATH.stat().st_size > 0


def test_challenge_set_groups_match_valid_labels(challenge_set: dict) -> None:
    assert set(challenge_set["groups"]) == set(VALID_GROUPS)


def test_each_group_has_minimum_cases(challenge_set: dict) -> None:
    for group in VALID_GROUPS:
        cases = challenge_set["groups"][group]["cases"]
        assert isinstance(cases, list)
        assert len(cases) >= MIN_CASES_PER_GROUP, (
            f"group {group!r} has {len(cases)} cases, "
            f"expected >= {MIN_CASES_PER_GROUP}"
        )


def test_total_cases_at_least_20(challenge_set: dict) -> None:
    assert len(_all_cases(challenge_set)) >= 20


def test_every_case_has_required_fields(challenge_set: dict) -> None:
    for case in _all_cases(challenge_set):
        for field in REQUIRED_CASE_FIELDS:
            assert field in case, f"case {case.get('id')!r} missing {field!r}"


def test_case_ids_unique(challenge_set: dict) -> None:
    ids = [case["id"] for case in _all_cases(challenge_set)]
    assert len(ids) == len(set(ids))


def test_case_group_matches_parent_group(challenge_set: dict) -> None:
    for group, spec in challenge_set["groups"].items():
        for case in spec["cases"]:
            assert case["group"] == group, (
                f"case {case['id']!r} declares group {case['group']!r}, "
                f"nested under {group!r}"
            )


def test_group_labels_are_legal(challenge_set: dict) -> None:
    for case in _all_cases(challenge_set):
        assert case["group"] in VALID_GROUPS, (
            f"case {case['id']!r} has illegal group {case['group']!r}"
        )


def test_difficulty_within_range(challenge_set: dict) -> None:
    for case in _all_cases(challenge_set):
        assert case["difficulty"] in (1, 2, 3), (
            f"case {case['id']!r} has difficulty {case['difficulty']!r}"
        )


def test_input_and_expected_key_factors_non_empty(challenge_set: dict) -> None:
    for case in _all_cases(challenge_set):
        assert isinstance(case["input"], str) and case["input"].strip(), (
            f"case {case['id']!r} has empty input"
        )
        factors = case["expected_key_factors"]
        assert isinstance(factors, list) and factors, (
            f"case {case['id']!r} has empty expected_key_factors"
        )
        assert all(
            isinstance(f, str) and f.strip() for f in factors
        ), f"case {case['id']!r} has a non-string key factor"


def test_ground_truth_present(challenge_set: dict) -> None:
    for case in _all_cases(challenge_set):
        gt = case.get("ground_truth")
        assert isinstance(gt, str) and gt.strip(), (
            f"case {case['id']!r} must carry a ground_truth string"
        )


# ---------------------------------------------------------------------------
# isolation from the Phase 3 built-in datasets
# ---------------------------------------------------------------------------


def _builtin_ids() -> set[str]:
    ids: set[str] = set()
    for name in ("easy", "medium", "hard", "enriched"):
        ids.update(case["id"] for case in load_dataset(f"benchmarks.datasets.{name}"))
    for cases in load_all_suites().values():
        ids.update(case["id"] for case in cases)
    return ids


def test_challenge_ids_do_not_collide_with_builtin_ids(challenge_set: dict) -> None:
    builtin = _builtin_ids()
    overlap = {case["id"] for case in _all_cases(challenge_set)} & builtin
    assert not overlap, f"challenge ids collide with Phase 3 ids: {overlap}"


def test_builtin_datasets_untouched_by_challenge_set() -> None:
    """The challenge set must not alter the Phase 3 dataset inventory."""
    counts = {}
    for name in ("easy", "medium", "hard", "enriched"):
        counts[name] = len(load_dataset(f"benchmarks.datasets.{name}"))
    for suite_id, cases in load_all_suites().items():
        counts[suite_id] = len(cases)
    assert counts == {
        "easy": 12,
        "medium": 10,
        "hard": 6,
        "enriched": 18,
        "planning": 4,
        "memory": 4,
        "debate": 4,
        "counterfactual": 3,
        "adversarial": 3,
    }
    assert sum(counts.values()) == 64


def test_challenge_set_not_served_by_builtin_loader() -> None:
    """challenge_set_v1.json lives outside datasets/ and must not be reachable
    through the built-in loader names."""
    assert CHALLENGE_PATH.parent != DATASETS_DIR
    names = sorted(path.stem for path in DATASETS_DIR.glob("*.json"))
    assert "challenge_set_v1" not in names
