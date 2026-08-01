"""Unit tests for the capability framework (Phase 2.1E, Sprint 04.5A).

Covers the stable capability enum, metadata validation (missing
``capabilities`` must be rejected for new cases), coverage matrix
generation, and annotation suggestions for legacy unannotated cases.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.capabilities import (
    ALL_CAPABILITIES,
    Capability,
    capability_from_reasoning_feature,
    parse_capabilities,
)
from benchmarks.capability_matrix import (
    CapabilityCoverageRow,
    build_annotation_suggestions,
    build_capability_coverage,
    load_all_datasets,
    render_annotation_suggestions,
    render_capability_coverage,
    scan_case_capabilities,
    write_capability_docs,
)
from benchmarks.loader import DATASETS_DIR
from benchmarks.metadata import (
    BenchmarkMetadataError,
    validate_enriched_case,
    validate_metadata,
)

_METADATA = {
    "challenge_type": "rare_knowledge",
    "expected_reasoning_features": ["knowledge_retrieval"],
    "difficulty": 3,
    "crop": "tomato",
    "disease": None,
    "noise_level": "medium",
    "modalities": ["text"],
    "design_intent": "rare_knowledge: 验证知识边界",
}


def _metadata_with_capabilities(*capabilities: str) -> dict:
    return {**_METADATA, "capabilities": list(capabilities)}


# ------------------------------ capability enum ----------------------------


def test_capability_enum_has_seven_stable_members() -> None:
    assert len(ALL_CAPABILITIES) == 7
    values = [capability.value for capability in ALL_CAPABILITIES]
    assert len(values) == len(set(values))
    for capability in ALL_CAPABILITIES:
        assert capability.value == capability.name.lower()


def test_each_capability_has_description_and_triggers() -> None:
    for capability in ALL_CAPABILITIES:
        assert capability.description_zh.strip()
        assert isinstance(capability.trigger_scenarios, tuple)
        assert len(capability.trigger_scenarios) >= 1
        assert all(scenario.strip() for scenario in capability.trigger_scenarios)


def test_parse_capabilities_valid_and_dedupe() -> None:
    parsed = parse_capabilities(["knowledge_retrieval", "conflict_resolution"])
    assert parsed == (
        Capability.KNOWLEDGE_RETRIEVAL,
        Capability.CONFLICT_RESOLUTION,
    )
    assert parse_capabilities(["knowledge_retrieval", "knowledge_retrieval"]) == (
        Capability.KNOWLEDGE_RETRIEVAL,
    )


def test_parse_capabilities_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unknown capability"):
        parse_capabilities(["not_a_capability"])


def test_feature_to_capability_mapping() -> None:
    assert (
        capability_from_reasoning_feature("information_request")
        == Capability.INFORMATION_GATHERING
    )
    assert capability_from_reasoning_feature("unknown_feature") is None


# ---------------------------- metadata validation --------------------------


def test_validate_metadata_requires_capabilities() -> None:
    with pytest.raises(BenchmarkMetadataError, match="capabilities"):
        validate_metadata(dict(_METADATA))
    with pytest.raises(BenchmarkMetadataError, match="capabilities"):
        validate_metadata(_metadata_with_capabilities())
    with pytest.raises(BenchmarkMetadataError, match="unknown capability"):
        validate_metadata(_metadata_with_capabilities("nope"))


def test_validate_metadata_accepts_capabilities() -> None:
    metadata = validate_metadata(
        _metadata_with_capabilities("knowledge_retrieval", "uncertainty_quantification")
    )
    assert metadata.capabilities == (
        Capability.KNOWLEDGE_RETRIEVAL,
        Capability.UNCERTAINTY_QUANTIFICATION,
    )


def test_validate_metadata_lenient_for_legacy_scan() -> None:
    metadata = validate_metadata(dict(_METADATA), require_capabilities=False)
    assert metadata.capabilities == ()


def test_legacy_enriched_cases_remain_valid() -> None:
    from benchmarks.loader import load_dataset

    for case in load_dataset("benchmarks.datasets.enriched"):
        validate_enriched_case(case)  # must not raise (pending annotation)


# --------------------------- coverage matrix -------------------------------


def test_coverage_rows_cover_all_capabilities() -> None:
    rows = build_capability_coverage(load_all_datasets())
    assert set(rows) == set(ALL_CAPABILITIES)
    covered = [capability for capability in rows if rows[capability].total > 0]
    assert len(covered) >= 5  # acceptance: at least 5 capabilities covered


def test_coverage_under_covered_flag() -> None:
    low = CapabilityCoverageRow(
        capability=Capability.INFORMATION_GATHERING,
        annotated=0,
        inferred=1,
        total=1,
    )
    ok = CapabilityCoverageRow(
        capability=Capability.KNOWLEDGE_RETRIEVAL,
        annotated=1,
        inferred=1,
        total=2,
    )
    assert low.under_covered is True
    assert ok.under_covered is False


def test_render_capability_coverage() -> None:
    text = render_capability_coverage(
        load_all_datasets(),
        generated_at="2026-01-01T00:00:00+00:00",
    )
    assert "# Benchmark Capability Coverage" in text
    assert "## 能力覆盖矩阵" in text
    assert "覆盖密度" in text
    for capability in ALL_CAPABILITIES:
        assert capability.value in text
    assert "## Summary" in text


# --------------------------- annotation suggestions ------------------------


def test_annotation_suggestions_cover_unannotated_cases() -> None:
    datasets = load_all_datasets()
    suggestions = build_annotation_suggestions(datasets)
    assert suggestions
    by_case = {
        suggestion["case_id"]: suggestion["capabilities"] for suggestion in suggestions
    }
    assert "information_gathering" in by_case["mi_tomato_growth_slow"]
    assert "multi_step_planning" in by_case["tomato_leaf_mold_action_plan"]


def test_annotation_suggestions_do_not_modify_datasets() -> None:
    enriched_path = DATASETS_DIR / "enriched.json"
    before = enriched_path.read_text(encoding="utf-8")
    build_annotation_suggestions(load_all_datasets())
    after = enriched_path.read_text(encoding="utf-8")
    assert after == before
    assert "capabilities" not in after  # still pending annotation


def test_render_annotation_suggestions() -> None:
    suggestions = [
        {
            "dataset": "enriched",
            "case_id": "mi_x",
            "capabilities": ["information_gathering"],
            "basis": "challenge=missing_information",
        }
    ]
    text = render_annotation_suggestions(
        suggestions,
        generated_at="2026-01-01T00:00:00+00:00",
    )
    assert "# Benchmark Capability Annotation Suggestions" in text
    assert "| enriched | mi_x |" in text
    assert "information_gathering" in text


def test_scan_case_capabilities_annotated_vs_inferred() -> None:
    annotated_case = {
        "id": "x",
        "query": "q",
        "metadata": _metadata_with_capabilities("knowledge_retrieval"),
    }
    annotated, inferred = scan_case_capabilities(annotated_case)
    assert annotated == (Capability.KNOWLEDGE_RETRIEVAL,)
    assert inferred == ()


def test_write_capability_docs(tmp_path: Path) -> None:
    coverage_path, suggestions_path = write_capability_docs(tmp_path)
    assert coverage_path.is_file()
    assert suggestions_path.is_file()
    assert "information_gathering" in coverage_path.read_text(encoding="utf-8")
    assert "# Benchmark Capability Annotation Suggestions" in suggestions_path.read_text(
        encoding="utf-8"
    )

