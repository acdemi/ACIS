"""Unit tests for the enriched benchmark (Phase 2.1E, Sprint 04.5).

Covers the enriched dataset contract (≥15 cases, ≥3 per challenge type,
complete standardized metadata), the metadata validator, loader
integration, auto-generated docs, and per-challenge-type ablation
statistics used by the Evidence Review Gate.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.capability_matrix import (
    challenge_ablation_stats,
    load_all_datasets,
    render_capability_matrix_doc,
    render_coverage_doc,
    write_challenge_ablation_stats,
    write_docs,
)
from benchmarks.loader import DATASETS_DIR, load_dataset
from benchmarks.metadata import (
    CHALLENGE_TYPES,
    BenchmarkMetadataError,
    challenge_counts,
    validate_enriched_case,
    validate_metadata,
)
from evals.config import load_dataset as load_runner_dataset

ENRICHED_PATH = DATASETS_DIR / "enriched.json"


def _enriched_cases() -> list[dict]:
    return load_dataset("benchmarks.datasets.enriched")


def _metadata(**overrides: object) -> dict:
    metadata = {
        "challenge_type": "missing_information",
        "expected_reasoning_features": ["information_request"],
        "capabilities": ["information_gathering"],
        "observable_evidence": [
            {
                "capability": "information_gathering",
                "expected_behavior": "主动请求缺失信息",
                "success_condition": "输出中包含信息补充请求",
            }
        ],
        "difficulty": 2,
        "crop": "tomato",
        "disease": None,
        "noise_level": "low",
        "modalities": ["text"],
        "design_intent": "missing_information: 验证信息补全",
    }
    metadata.update(overrides)
    return metadata


# ---------------------------- dataset contract -----------------------------


def test_enriched_has_enough_cases_and_distribution() -> None:
    cases = _enriched_cases()
    assert len(cases) >= 15
    counts = challenge_counts(cases)
    for challenge in CHALLENGE_TYPES:
        assert counts[challenge] >= 3


def test_every_enriched_case_has_complete_metadata() -> None:
    for case in _enriched_cases():
        validated = validate_enriched_case(case)
        metadata = validated["metadata"]
        assert metadata["challenge_type"] in CHALLENGE_TYPES
        assert metadata["expected_reasoning_features"]
        assert isinstance(metadata["difficulty"], int) and 1 <= metadata["difficulty"] <= 5
        assert metadata["crop"].strip()
        assert metadata["noise_level"] in {"low", "medium", "high"}
        assert metadata["modalities"]
        assert metadata["design_intent"].strip()


def test_every_enriched_case_has_expected_fields() -> None:
    for case in _enriched_cases():
        low, high = case["expected_confidence_range"]
        assert 0.0 <= low <= high <= 1.0
        assert isinstance(case["expected_tools"], list)
        assert case["ground_truth"].strip()
        override = case.get("sensor_override")
        if override is not None:
            assert all(
                isinstance(value, (int, float)) and not isinstance(value, bool)
                for value in override.values()
            )


def test_enriched_loads_through_runner_dataset_path() -> None:
    cases = load_runner_dataset("benchmarks.datasets.enriched")
    assert len(cases) >= 15
    assert all(case.ground_truth for case in cases)
    first = cases[0]
    assert first.raw["metadata"]["challenge_type"] in CHALLENGE_TYPES


# ------------------------------ metadata rules -----------------------------


def test_validate_metadata_accepts_full_metadata() -> None:
    metadata = validate_metadata(_metadata())
    assert metadata.challenge_type == "missing_information"
    assert metadata.expected_reasoning_features == ("information_request",)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("challenge_type", "unknown_challenge"),
        ("difficulty", 0),
        ("difficulty", 6),
        ("difficulty", 2.5),
        ("noise_level", "extreme"),
        ("expected_reasoning_features", []),
        ("expected_reasoning_features", ["not_a_feature"]),
        ("design_intent", "  "),
        ("modalities", []),
    ],
)
def test_validate_metadata_rejects_bad_values(field: str, bad_value: object) -> None:
    with pytest.raises(BenchmarkMetadataError):
        validate_metadata(_metadata(**{field: bad_value}))


def test_validate_enriched_case_rejects_bad_confidence_range() -> None:
    case = {
        "id": "x",
        "query": "q",
        "ground_truth": "叶霉病",
        "expected_confidence_range": [0.9, 0.5],
        "expected_tools": [],
        "metadata": _metadata(),
    }
    with pytest.raises(BenchmarkMetadataError):
        validate_enriched_case(case)


# --------------------------- auto-generated docs ---------------------------


def test_render_capability_matrix_doc_includes_enriched() -> None:
    cases = _enriched_cases()
    counts = {name: len(load_dataset(f"benchmarks.datasets.{name}")) for name in ("easy", "medium", "hard", "enriched")}
    text = render_capability_matrix_doc(
        counts,
        cases,
        generated_at="2026-01-01T00:00:00+00:00",
    )
    assert "# Benchmark Capability Matrix" in text
    assert "## 扩展挑战矩阵（enriched.json）" in text
    for challenge in CHALLENGE_TYPES:
        assert f"| {challenge} |" in text
    assert "| enriched | 18 |" in text


def test_render_coverage_doc_covers_all_datasets() -> None:
    datasets = load_all_datasets()
    text = render_coverage_doc(datasets, generated_at="2026-01-01T00:00:00+00:00")
    assert "## Dataset Inventory" in text
    assert "## Enriched Challenge Coverage" in text
    assert "| enriched | 18 |" in text
    assert "| easy |" in text


def test_write_docs_generates_matrix_and_coverage(tmp_path: Path) -> None:
    matrix_path, coverage_path = write_docs(tmp_path)
    assert matrix_path.is_file()
    assert coverage_path.is_file()
    assert "enriched" in matrix_path.read_text(encoding="utf-8")
    assert "enriched" in coverage_path.read_text(encoding="utf-8")


# --------------------- challenge-grouped ablation stats --------------------


def _write_metrics_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "case_id",
        "expected",
        "accuracy",
        "confidence",
        "memory_hits",
        "debate_rounds",
        "counterfactual_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def test_challenge_ablation_stats_groups_by_challenge(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    all_on = run_dir / "all_on"
    no_memory = run_dir / "no_memory"
    all_on.mkdir(parents=True)
    no_memory.mkdir(parents=True)
    (run_dir / "REPORT.md").write_text("# Ablation Report\n", encoding="utf-8")

    _write_metrics_csv(
        all_on / "metrics.csv",
        [
            {"case_id": "mi_tomato_growth_slow", "expected": "证据不足", "accuracy": 1.0, "confidence": 0.6, "memory_hits": 2, "debate_rounds": 1, "counterfactual_count": 5},
            {"case_id": "ce_tomato_mold_dry", "expected": "叶霉病", "accuracy": 1.0, "confidence": 0.7, "memory_hits": 2, "debate_rounds": 2, "counterfactual_count": 8},
        ],
    )
    _write_metrics_csv(
        no_memory / "metrics.csv",
        [
            {"case_id": "mi_tomato_growth_slow", "expected": "证据不足", "accuracy": 1.0, "confidence": 0.6, "memory_hits": 0, "debate_rounds": 1, "counterfactual_count": 5},
            {"case_id": "ce_tomato_mold_dry", "expected": "叶霉病", "accuracy": 1.0, "confidence": 0.7, "memory_hits": 0, "debate_rounds": 2, "counterfactual_count": 8},
        ],
    )

    grouped = challenge_ablation_stats(run_dir)
    missing = grouped["missing_information"]
    assert missing["all_on"]["accuracy"] == pytest.approx(1.0)
    assert missing["all_on"]["memory_hits"] == pytest.approx(2.0)
    assert missing["no_memory"]["memory_hits"] == pytest.approx(0.0)
    contradictory = grouped["contradictory_evidence"]
    assert contradictory["all_on"]["disease_recall"] == pytest.approx(1.0)

    report_path = write_challenge_ablation_stats(run_dir)
    text = report_path.read_text(encoding="utf-8")
    assert "## 按 challenge_type 分组的模块贡献统计" in text
    assert "### missing_information" in text
    assert "### contradictory_evidence" in text
    assert "| no_memory |" in text
    assert "+2.000" in text  # memory_hits Δ for missing_information




