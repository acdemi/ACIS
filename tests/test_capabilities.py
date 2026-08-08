"""Unit tests for the capability framework (Phase 2.1E, Sprint 04.5A).

Covers the stable capability enum, metadata validation (missing
``capabilities`` must be rejected for new cases), coverage matrix
generation, and annotation suggestions for legacy unannotated cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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
    return {
        **_METADATA,
        "capabilities": list(capabilities),
        "observable_evidence": [
            {
                "capability": capability,
                "expected_behavior": f"evidence for {capability}",
                "success_condition": f"condition for {capability}",
            }
            for capability in capabilities
        ],
    }


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
    assert len(metadata.observable_evidence) == 2


def test_validate_metadata_requires_observable_evidence() -> None:
    metadata = {**_METADATA, "capabilities": ["knowledge_retrieval"]}
    with pytest.raises(BenchmarkMetadataError, match="observable_evidence"):
        validate_metadata(metadata)


def test_validate_metadata_rejects_evidence_not_in_capabilities() -> None:
    metadata = {
        **_METADATA,
        "capabilities": ["knowledge_retrieval"],
        "observable_evidence": [
            {
                "capability": "knowledge_retrieval",
                "expected_behavior": "b",
                "success_condition": "c",
            },
            {
                "capability": "conflict_resolution",
                "expected_behavior": "b",
                "success_condition": "c",
            },
        ],
    }
    with pytest.raises(BenchmarkMetadataError, match="capabilities 中未包含"):
        validate_metadata(metadata)


def test_validate_observable_evidence_format() -> None:
    from benchmarks.metadata import validate_observable_evidence

    evidence = validate_observable_evidence(
        {
            "capability": "knowledge_retrieval",
            "expected_behavior": "检索证据",
            "success_condition": "命中一致",
        }
    )
    assert evidence.capability == Capability.KNOWLEDGE_RETRIEVAL
    with pytest.raises(BenchmarkMetadataError):
        validate_observable_evidence(
            {"capability": "knowledge_retrieval", "expected_behavior": "b"}
        )
    with pytest.raises(BenchmarkMetadataError):
        validate_observable_evidence({"capability": "nope", "expected_behavior": "b", "success_condition": "c"})


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
    # Sprint 04.5B: explicit annotations — information_gathering >= 6
    assert rows[Capability.INFORMATION_GATHERING].annotated >= 6


def test_annotated_cases_are_consistent() -> None:
    from benchmarks.capability_matrix import build_consistency_rows

    rows = build_consistency_rows(load_all_datasets())
    annotated = [row for row in rows if row["status"] != "unannotated"]
    inconsistent = [row for row in annotated if row["status"] == "inconsistent"]
    assert annotated  # every capability-focused case is annotated
    assert inconsistent == []  # acceptance: 100% consistency


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
    # Annotated cases are excluded from suggestions...
    assert "mi_tomato_growth_slow" not in by_case
    # ...while unannotated difficulty cases remain listed for review.
    assert "tomato_leaf_mold" in by_case


def test_annotation_suggestions_do_not_modify_datasets() -> None:
    enriched_path = DATASETS_DIR / "enriched.json"
    before = enriched_path.read_text(encoding="utf-8")
    build_annotation_suggestions(load_all_datasets())
    after = enriched_path.read_text(encoding="utf-8")
    assert after == before


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



# --------------------- consistency check (Sprint 04.5B) ---------------------


def test_check_case_consistency_consistent() -> None:
    from benchmarks.capability_matrix import check_case_consistency

    case = {
        "id": "x",
        "query": "q",
        "capabilities": ["knowledge_retrieval"],
        "observable_evidence": [
            {
                "capability": "knowledge_retrieval",
                "expected_behavior": "检索证据",
                "success_condition": "命中一致",
            }
        ],
        "design_intent": "knowledge_retrieval: 验证检索",
    }
    check = check_case_consistency(case)
    assert check["status"] == "consistent"
    assert check["issues"] == []


def test_check_case_consistency_unannotated() -> None:
    from benchmarks.capability_matrix import check_case_consistency

    check = check_case_consistency({"id": "x", "query": "q"})
    assert check["status"] == "unannotated"


def test_check_case_consistency_inconsistent_missing_evidence() -> None:
    from benchmarks.capability_matrix import check_case_consistency

    case = {
        "id": "x",
        "query": "q",
        "capabilities": ["knowledge_retrieval"],
        "design_intent": "knowledge_retrieval: 验证检索",
    }
    check = check_case_consistency(case)
    assert check["status"] == "inconsistent"
    assert any("observable_evidence" in issue for issue in check["issues"])


def test_check_case_consistency_inconsistent_intent() -> None:
    from benchmarks.capability_matrix import check_case_consistency

    case = {
        "id": "x",
        "query": "q",
        "capabilities": ["knowledge_retrieval"],
        "observable_evidence": [
            {
                "capability": "knowledge_retrieval",
                "expected_behavior": "检索证据",
                "success_condition": "命中一致",
            }
        ],
        "design_intent": "与能力无关的描述",
    }
    check = check_case_consistency(case)
    assert check["status"] == "inconsistent"
    assert any("design_intent" in issue for issue in check["issues"])


def test_render_consistency_report(tmp_path: Path) -> None:
    from benchmarks.capability_matrix import (
        build_consistency_rows,
        render_consistency_report,
        write_consistency_report,
    )

    rows = build_consistency_rows(load_all_datasets())
    text = render_consistency_report(rows, generated_at="2026-01-01T00:00:00+00:00")
    assert "# Benchmark Capability Consistency Report" in text
    assert "Annotated cases:" in text
    assert "Inconsistent: 0" in text
    assert "一致性检验" in text
    report_path = write_consistency_report(tmp_path)
    assert report_path.is_file()


# --------------------- capability ablation stats ---------------------------


def test_capability_ablation_stats_groups_by_capability(tmp_path: Path) -> None:
    import csv

    from benchmarks.capability_matrix import (
        capability_ablation_stats,
        write_capability_ablation_stats,
    )

    run_dir = tmp_path / "run"
    all_on = run_dir / "all_on"
    no_memory = run_dir / "no_memory"
    all_on.mkdir(parents=True)
    no_memory.mkdir(parents=True)
    (run_dir / "REPORT.md").write_text("# Ablation Report\n", encoding="utf-8")
    fields = [
        "case_id",
        "expected",
        "accuracy",
        "confidence",
        "memory_hits",
        "debate_rounds",
        "counterfactual_count",
    ]

    def write_rows(path: Path, rows: list[dict]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fields})

    rows = [
        {"case_id": "mi_tomato_growth_slow", "expected": "证据不足", "accuracy": 1.0, "confidence": 0.6, "memory_hits": 2, "debate_rounds": 1, "counterfactual_count": 5},
        {"case_id": "ce_tomato_mold_dry", "expected": "叶霉病", "accuracy": 1.0, "confidence": 0.7, "memory_hits": 2, "debate_rounds": 2, "counterfactual_count": 8},
    ]
    write_rows(all_on / "metrics.csv", rows)
    no_memory_rows = [
        {**row, "memory_hits": 0} for row in rows
    ]
    write_rows(no_memory / "metrics.csv", no_memory_rows)

    grouped = capability_ablation_stats(run_dir)
    assert grouped[Capability.INFORMATION_GATHERING]["all_on"]["memory_hits"] == pytest.approx(2.0)
    assert grouped[Capability.CONFLICT_RESOLUTION]["no_memory"]["memory_hits"] == pytest.approx(0.0)

    report_path = write_capability_ablation_stats(run_dir)
    text = report_path.read_text(encoding="utf-8")
    assert "## 按 capability 分组的模块贡献统计" in text
    assert "### information_gathering" in text
    assert "### conflict_resolution" in text

