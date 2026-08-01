"""Unit tests for the benchmark dataset framework (Phase 2.1E, Sprint 03).

Covers dataset schema validation, the benchmark loader (module-style names
and ``.json`` paths), the built-in easy/medium/hard datasets, and the
``evals.config`` integration that wraps benchmark cases into ``EvalCase``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.loader import (
    BUILTIN_DATASETS,
    DATASETS_DIR,
    MODULE_PREFIX,
    resolve_dataset,
)
from benchmarks.loader import (
    load_dataset as load_benchmark_dataset,
)
from benchmarks.schema import (
    MIN_CASES_BY_DIFFICULTY,
    BenchmarkValidationError,
    validate_dataset,
)
from evals.config import EvalCase, EvalConfig, load_dataset


def _cases(count: int, prefix: str = "case") -> list[dict]:
    return [
        {"id": f"{prefix}_{index}", "query": f"query {index}"}
        for index in range(count)
    ]


# ------------------------------ built-in datasets --------------------------


@pytest.mark.parametrize("name", BUILTIN_DATASETS)
def test_builtin_dataset_meets_minimum_count(name: str) -> None:
    cases = load_benchmark_dataset(f"{MODULE_PREFIX}{name}")
    assert len(cases) >= MIN_CASES_BY_DIFFICULTY[name]


@pytest.mark.parametrize("name", BUILTIN_DATASETS)
def test_builtin_dataset_schema_valid(name: str) -> None:
    cases = load_benchmark_dataset(f"{MODULE_PREFIX}{name}")
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert all(case["id"].strip() for case in cases)
    assert all(case["query"].strip() for case in cases)
    assert all(
        case["ground_truth"] is None or isinstance(case["ground_truth"], str)
        for case in cases
    )


def test_loader_resolves_module_style_names() -> None:
    path, difficulty = resolve_dataset("benchmarks.datasets.easy")
    assert path == DATASETS_DIR / "easy.json"
    assert difficulty == "easy"


def test_loader_rejects_unknown_dataset_name() -> None:
    with pytest.raises(BenchmarkValidationError):
        load_benchmark_dataset("benchmarks.datasets.nope")


def test_loader_rejects_unrecognized_source() -> None:
    with pytest.raises(BenchmarkValidationError):
        load_benchmark_dataset("random.module.path")


def test_loader_loads_json_path(tmp_path: Path) -> None:
    path = tmp_path / "dataset.json"
    path.write_text(
        json.dumps([{"id": "a", "query": "q"}], ensure_ascii=False),
        encoding="utf-8",
    )
    cases = load_benchmark_dataset(str(path))
    assert [case["id"] for case in cases] == ["a"]


# --------------------------- evals.config integration ----------------------


def test_config_loads_benchmark_dataset_as_evalcases() -> None:
    cases = load_dataset("benchmarks.datasets.easy")
    assert len(cases) >= MIN_CASES_BY_DIFFICULTY["easy"]
    assert all(isinstance(case, EvalCase) for case in cases)
    first = cases[0]
    assert first.id == "tomato_leaf_mold"
    assert first.ground_truth == "叶霉病"
    assert first.sensor_override is None
    assert first.raw["crop"] == "tomato"


def test_config_loads_medium_and_hard_datasets() -> None:
    medium = load_dataset("benchmarks.datasets.medium")
    hard = load_dataset("benchmarks.datasets.hard")
    assert len(medium) >= MIN_CASES_BY_DIFFICULTY["medium"]
    assert len(hard) >= MIN_CASES_BY_DIFFICULTY["hard"]
    assert any(case.sensor_override for case in hard)


def test_config_save_traces_defaults_off() -> None:
    assert EvalConfig().save_traces is False
    assert EvalConfig(save_traces=True).save_traces is True


# ------------------------------ schema validation --------------------------


def test_schema_accepts_bare_list() -> None:
    cases = validate_dataset(_cases(10))
    assert len(cases) == 10


def test_schema_accepts_metadata_object() -> None:
    data = {"name": "x", "difficulty": "medium", "cases": _cases(10)}
    cases = validate_dataset(data)
    assert len(cases) == 10


def test_schema_enforces_minimum_case_counts() -> None:
    assert len(validate_dataset(_cases(10), difficulty="easy")) == 10
    assert len(validate_dataset(_cases(10), difficulty="medium")) == 10
    assert len(validate_dataset(_cases(5), difficulty="hard")) == 5
    with pytest.raises(BenchmarkValidationError):
        validate_dataset(_cases(9), difficulty="easy")
    with pytest.raises(BenchmarkValidationError):
        validate_dataset(_cases(4), difficulty="hard")


def test_schema_rejects_missing_required_fields() -> None:
    with pytest.raises(BenchmarkValidationError):
        validate_dataset([{"query": "q"}])
    with pytest.raises(BenchmarkValidationError):
        validate_dataset([{"id": "a"}])


def test_schema_rejects_empty_id_or_query() -> None:
    with pytest.raises(BenchmarkValidationError):
        validate_dataset([{"id": "  ", "query": "q"}])
    with pytest.raises(BenchmarkValidationError):
        validate_dataset([{"id": "a", "query": ""}])


def test_schema_rejects_duplicate_ids() -> None:
    with pytest.raises(BenchmarkValidationError):
        validate_dataset([{"id": "a", "query": "q1"}, {"id": "a", "query": "q2"}])


def test_schema_rejects_non_object_case() -> None:
    with pytest.raises(BenchmarkValidationError):
        validate_dataset([42])


def test_schema_rejects_unknown_difficulty() -> None:
    with pytest.raises(BenchmarkValidationError):
        validate_dataset({"difficulty": "nightmare", "cases": _cases(10)})


def test_schema_rejects_difficulty_mismatch() -> None:
    data = {"difficulty": "hard", "cases": _cases(6)}
    with pytest.raises(BenchmarkValidationError):
        validate_dataset(data, difficulty="easy")


def test_schema_validates_sensor_override() -> None:
    good = _cases(1)
    good[0]["sensor_override"] = {"humidity_offset": -25.0, "temp_offset": 6}
    assert validate_dataset(good)[0]["sensor_override"] == {
        "humidity_offset": -25.0,
        "temp_offset": 6,
    }
    for bad in ({"humidity_offset": "high"}, {"humidity_offset": None}, [1.0]):
        case = {"id": "x", "query": "q", "sensor_override": bad}
        with pytest.raises(BenchmarkValidationError):
            validate_dataset([case])


def test_schema_preserves_extra_metadata() -> None:
    case = {
        "id": "a",
        "query": "q",
        "ground_truth": "叶霉病",
        "crop": "tomato",
        "intent": "diagnose",
        "expect_critic": True,
    }
    validated = validate_dataset([case])[0]
    assert validated["crop"] == "tomato"
    assert validated["intent"] == "diagnose"
    assert validated["expect_critic"] is True
