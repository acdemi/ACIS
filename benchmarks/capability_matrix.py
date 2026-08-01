"""Auto-generated benchmark documentation (Phase 2.1E, Sprint 04.5).

Reads every benchmark dataset (difficulty tiers, capability suites, and the
enriched challenge set) and regenerates ``CAPABILITY_MATRIX.md`` and
``COVERAGE.md`` under ``benchmarks/`` — all generated artifacts, never
hand-written. The module also computes the per-``challenge_type`` ablation
statistics required by the Evidence Review Gate.

Phase 2.1E, Sprint 04.5A (Capability Framework): scans every case for its
``capabilities`` annotation, infers recommended capabilities for unannotated
cases, and generates ``CAPABILITY_COVERAGE.md`` (per-capability case counts,
coverage density, under-covered flags) plus
``CAPABILITY_ANNOTATION_SUGGESTIONS.md`` for human review. Suggestions are
never written into dataset files.

Usage from the repo root::

    python -m benchmarks.capability_matrix
    python -m benchmarks.capability_matrix --ablation-dir results/ablation/enriched/<ts>
"""

from __future__ import annotations

import argparse
import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.capabilities import (
    ALL_CAPABILITIES,
    Capability,
    capability_from_reasoning_feature,
    parse_capabilities,
)
from benchmarks.loader import CAPABILITY_SUITES, DATASETS_DIR, load_dataset, load_suite
from benchmarks.metadata import (
    CHALLENGE_TYPES,
    challenge_counts,
    validate_enriched_case,
)
from benchmarks.taxonomy import (
    CAPABILITY_COLUMNS,
    SUITES,
    build_capability_matrix,
)

#: Datasets shown in the inventory, in display order.
DATASET_ORDER: tuple[str, ...] = (
    "easy",
    "medium",
    "hard",
    "planning",
    "memory",
    "debate",
    "counterfactual",
    "adversarial",
    "enriched",
)

#: Metrics included in the challenge-grouped ablation statistics.
GROUP_METRICS: tuple[str, ...] = (
    "accuracy",
    "disease_recall",
    "average_confidence",
    "memory_hits",
    "debate_rounds",
    "counterfactual_count",
)

#: Case count below which a capability is flagged as under-covered.
UNDER_COVERED_THRESHOLD = 2

_BASELINE_COMBO = "all_on"


def load_all_datasets() -> dict[str, list[dict[str, Any]]]:
    """Load every benchmark dataset, keyed by dataset name."""
    datasets: dict[str, list[dict[str, Any]]] = {}
    for name in DATASET_ORDER:
        if name in CAPABILITY_SUITES:
            datasets[name] = load_suite(name)
        else:
            datasets[name] = load_dataset(f"benchmarks.datasets.{name}")
    return datasets


def dataset_target(name: str) -> str:
    """Human-readable target description for a dataset."""
    if name in {"easy", "medium", "hard"}:
        return "difficulty tier（通用回归）"
    suite = next((s for s in SUITES if s.suite_id == name), None)
    if suite is not None:
        return f"capability: {suite.targeted_capability}"
    if name == "enriched":
        return "challenge: 五类认知挑战"
    return "—"


def metadata_complete_count(cases: Sequence[dict[str, Any]]) -> int:
    """Cases passing the full enrichment contract (metadata + case fields)."""
    count = 0
    for case in cases:
        try:
            validate_enriched_case(case)
            count += 1
        except ValueError:
            continue
    return count


def render_capability_matrix_doc(
    case_counts: dict[str, int],
    enriched_cases: Sequence[dict[str, Any]],
    *,
    generated_at: str | None = None,
) -> str:
    """Render the full capability matrix (suites + enriched challenges)."""
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    suite_rows = build_capability_matrix(
        SUITES,
        {suite.suite_id: case_counts.get(suite.suite_id, 0) for suite in SUITES},
    )
    lines = [
        "# Benchmark Capability Matrix",
        "",
        f"- Generated: {timestamp}",
        "",
        "## 能力套件矩阵",
        "",
        "| Suite | Case Count | Planner | Memory | Debate | Counterfactual | Adversarial |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in suite_rows:
        cells = [str(row["suite"]), str(row["case_count"])]
        cells += ["✓" if row[capability] else "" for capability in CAPABILITY_COLUMNS]
        lines.append("| " + " | ".join(cells) + " |")

    counts = challenge_counts(enriched_cases)
    lines += [
        "",
        "## 扩展挑战矩阵（enriched.json）",
        "",
        "| Challenge Type | Case Count | 主要 Reasoning Features |",
        "|---|---|---|",
    ]
    for challenge in CHALLENGE_TYPES:
        cases = [case for case in enriched_cases if _challenge(case) == challenge]
        features = sorted({feature for case in cases for feature in _features(case)})
        lines.append(
            f"| {challenge} | {counts.get(challenge, 0)} | "
            f"{', '.join(features) if features else '—'} |"
        )

    lines += [
        "",
        "## 数据集清单",
        "",
        "| Dataset | Cases | Target |",
        "|---|---|---|",
    ]
    for name in DATASET_ORDER:
        lines.append(f"| {name} | {case_counts.get(name, 0)} | {dataset_target(name)} |")
    lines.append("")
    lines.append(
        "每个 case 均携带 `design_intent`；enriched case 另带标准化的 "
        "`metadata`（challenge_type / expected_reasoning_features / difficulty / "
        "crop / disease / noise_level / modalities）。"
    )
    return "\n".join(lines) + "\n"


def render_coverage_doc(
    datasets: dict[str, list[dict[str, Any]]],
    *,
    generated_at: str | None = None,
) -> str:
    """Render the coverage report across all datasets."""
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    total_cases = sum(len(cases) for cases in datasets.values())
    enriched = datasets.get("enriched", [])
    lines = [
        "# Benchmark Coverage Report",
        "",
        f"- Generated: {timestamp}",
        f"- Datasets: {len(DATASET_ORDER)}",
        f"- Total cases: {total_cases}",
        "",
        "## Dataset Inventory",
        "",
        "| Dataset | Cases | Target | metadata complete |",
        "|---|---|---|---|",
    ]
    for name in DATASET_ORDER:
        cases = datasets.get(name, [])
        if name == "enriched":
            complete = f"{metadata_complete_count(cases)}/{len(cases)}"
        else:
            complete = "n/a（非 enriched）"
        lines.append(
            f"| {name} | {len(cases)} | {dataset_target(name)} | {complete} |"
        )

    lines += [
        "",
        "## Capability Suite Coverage",
        "",
        "| Module | Suite Cases | design_intent |",
        "|---|---|---|",
    ]
    for suite in SUITES:
        cases = datasets.get(suite.suite_id, [])
        intent = sum(
            1
            for case in cases
            if isinstance(case.get("design_intent"), str) and case["design_intent"].strip()
        )
        lines.append(f"| {suite.targeted_capability} | {len(cases)} | {intent} |")

    counts = challenge_counts(enriched)
    lines += [
        "",
        "## Enriched Challenge Coverage",
        "",
        "| Challenge Type | Cases | metadata complete | reasoning features covered |",
        "|---|---|---|---|",
    ]
    for challenge in CHALLENGE_TYPES:
        cases = [case for case in enriched if _challenge(case) == challenge]
        complete_count = metadata_complete_count(cases)
        features = sorted({feature for case in cases for feature in _features(case)})
        lines.append(
            f"| {challenge} | {counts.get(challenge, 0)} | {complete_count} | "
            f"{', '.join(features) if features else '—'} |"
        )

    suite_intent = sum(
        1
        for name in CAPABILITY_SUITES
        for case in datasets.get(name, [])
        if isinstance(case.get("design_intent"), str) and case["design_intent"].strip()
    )
    suite_total = sum(len(datasets.get(name, [])) for name in CAPABILITY_SUITES)
    lines += [
        "",
        "## Summary",
        "",
        f"- Capability suite cases with design_intent: {suite_intent}/{suite_total}",
        (
            f"- Enriched cases passing the full metadata contract: "
            f"{metadata_complete_count(enriched)}/{len(enriched)}"
        ),
        (
            "- 设计原则：真实性优先于难度 —— 每个 case 来源于真实农业场景，"
            "目标是区分模块能力而非让系统犯错。"
        ),
    ]
    return "\n".join(lines) + "\n"


def write_docs(output_dir: str | Path | None = None) -> tuple[Path, Path]:
    """Regenerate ``CAPABILITY_MATRIX.md`` and ``COVERAGE.md``."""
    base = Path(output_dir) if output_dir is not None else DATASETS_DIR.parent
    base.mkdir(parents=True, exist_ok=True)
    datasets = load_all_datasets()
    case_counts = {name: len(cases) for name, cases in datasets.items()}
    matrix_path = base / "CAPABILITY_MATRIX.md"
    coverage_path = base / "COVERAGE.md"
    matrix_path.write_text(
        render_capability_matrix_doc(case_counts, datasets.get("enriched", [])),
        encoding="utf-8",
    )
    coverage_path.write_text(render_coverage_doc(datasets), encoding="utf-8")
    return matrix_path, coverage_path


# ---------------------------------------------------------------------------
# capability coverage (Phase 2.1E, Sprint 04.5A)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapabilityCoverageRow:
    """Per-capability coverage counts across all datasets."""

    capability: Capability
    annotated: int
    inferred: int
    total: int

    @property
    def under_covered(self) -> bool:
        return self.total < UNDER_COVERED_THRESHOLD


def case_capabilities(case: dict[str, Any]) -> tuple[Capability, ...]:
    """Read an annotated ``capabilities`` list from a case (strict)."""
    metadata = case.get("metadata")
    if not isinstance(metadata, dict):
        return ()
    values = metadata.get("capabilities")
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError(f"case {case.get('id')!r}: capabilities must be a list")
    return parse_capabilities(values)


def infer_capabilities(case: dict[str, Any]) -> tuple[Capability, ...]:
    """Infer recommended capabilities from existing case signals.

    Combines ``expected_reasoning_features``, ``metadata.challenge_type``,
    ``design_intent`` keywords, ``ground_truth == 证据不足``, ``sensor_override``
    presence, and query keywords. Returns capabilities in declaration order.
    """
    candidates: set[Capability] = set()
    metadata = case.get("metadata")
    if isinstance(metadata, dict):
        features = metadata.get("expected_reasoning_features")
        if isinstance(features, list):
            for feature in features:
                mapped = capability_from_reasoning_feature(str(feature))
                if mapped is not None:
                    candidates.add(mapped)
        challenge = str(metadata.get("challenge_type", ""))
        if challenge == "missing_information":
            candidates.add(Capability.INFORMATION_GATHERING)
        elif challenge == "contradictory_evidence":
            candidates.add(Capability.CONFLICT_RESOLUTION)
        elif challenge == "multi_disease":
            candidates.add(Capability.COUNTERFACTUAL_REASONING)
        elif challenge == "rare_knowledge":
            candidates.add(Capability.KNOWLEDGE_RETRIEVAL)
        elif challenge == "sensor_conflict":
            candidates.add(Capability.SENSOR_CROSS_VALIDATION)
            candidates.add(Capability.CONFLICT_RESOLUTION)
        design_intent = metadata.get("design_intent")
        if isinstance(design_intent, str):
            candidates.update(_capabilities_from_keywords(design_intent))

    # Suite datasets store design_intent at case level (not in metadata).
    case_intent = case.get("design_intent")
    if isinstance(case_intent, str):
        candidates.update(_capabilities_from_keywords(case_intent))

    if case.get("sensor_override") is not None:
        candidates.add(Capability.SENSOR_CROSS_VALIDATION)
    if case.get("ground_truth") == "证据不足":
        candidates.add(Capability.UNCERTAINTY_QUANTIFICATION)
    query = str(case.get("query", ""))
    candidates.update(_capabilities_from_keywords(query))
    return tuple(capability for capability in ALL_CAPABILITIES if capability in candidates)


def _capabilities_from_keywords(text: str) -> set[Capability]:
    """Keyword heuristics over design_intent / query text."""
    matched: set[Capability] = set()
    if any(
        keyword in text
        for keyword in ("planner", "计划", "安排", "作业", "制定", "方案", "规划", "步骤", "浇", "灌")
    ):
        matched.add(Capability.MULTI_STEP_PLANNING)
    if any(keyword in text for keyword in ("memory", "检索", "查询", "资料", "经验", "案例", "知识")):
        matched.add(Capability.KNOWLEDGE_RETRIEVAL)
    if any(keyword in text for keyword in ("debate", "冲突", "矛盾", "辩论", "裁决", "优先怀疑")):
        matched.add(Capability.CONFLICT_RESOLUTION)
    if any(
        keyword in text
        for keyword in ("counterfactual", "反事实", "排除", "替代", "鉴别", "哪个病")
    ):
        matched.add(Capability.COUNTERFACTUAL_REASONING)
    if any(keyword in text for keyword in ("缺素", "生理性", "无法确认", "证据不足")):
        matched.add(Capability.UNCERTAINTY_QUANTIFICATION)
    if any(keyword in text for keyword in ("sensor", "传感器", "异常")):
        matched.add(Capability.SENSOR_CROSS_VALIDATION)
    if any(keyword in text for keyword in ("信息", "补充", "还需要")):
        matched.add(Capability.INFORMATION_GATHERING)
    return matched


def scan_case_capabilities(
    case: dict[str, Any],
) -> tuple[tuple[Capability, ...], tuple[Capability, ...]]:
    """Return ``(annotated, inferred)`` capabilities for one case."""
    annotated = case_capabilities(case)
    inferred = () if annotated else infer_capabilities(case)
    return annotated, inferred


def build_capability_coverage(
    datasets: dict[str, list[dict[str, Any]]],
) -> dict[Capability, CapabilityCoverageRow]:
    """Count per-capability annotated / inferred / effective coverage."""
    counts = {capability: [0, 0, 0] for capability in ALL_CAPABILITIES}
    for cases in datasets.values():
        for case in cases:
            annotated, inferred = scan_case_capabilities(case)
            effective = annotated or inferred
            for capability in ALL_CAPABILITIES:
                if capability in annotated:
                    counts[capability][0] += 1
                if capability in inferred:
                    counts[capability][1] += 1
                if capability in effective:
                    counts[capability][2] += 1
    return {
        capability: CapabilityCoverageRow(
            capability=capability,
            annotated=counts[capability][0],
            inferred=counts[capability][1],
            total=counts[capability][2],
        )
        for capability in ALL_CAPABILITIES
    }


def render_capability_coverage(
    datasets: dict[str, list[dict[str, Any]]],
    *,
    generated_at: str | None = None,
) -> str:
    """Render ``CAPABILITY_COVERAGE.md`` (per-capability coverage matrix)."""
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    rows = build_capability_coverage(datasets)
    total_cases = sum(len(cases) for cases in datasets.values())
    annotated_cases = sum(1 for cases in datasets.values() for case in cases if case_capabilities(case))
    lines = [
        "# Benchmark Capability Coverage",
        "",
        f"- Generated: {timestamp}",
        f"- Datasets: {len(DATASET_ORDER)}",
        f"- Total cases: {total_cases}",
        f"- Capability-annotated cases: {annotated_cases} "
        f"（其余 {total_cases - annotated_cases} 个为待标注，见 "
        "CAPABILITY_ANNOTATION_SUGGESTIONS.md）",
        "",
        "## 能力覆盖矩阵",
        "",
        "| Capability | 中文说明 | 已标注 | 待标注(推断) | 覆盖案例 | 覆盖密度 | 缺口 |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows.values():
        density = row.total / total_cases * 100.0 if total_cases else 0.0
        flag = "⚠ 覆盖不足" if row.under_covered else ""
        lines.append(
            f"| {row.capability.value} | {row.capability.description_zh} | "
            f"{row.annotated} | {row.inferred} | {row.total} | "
            f"{density:.1f}% | {flag} |"
        )
    covered = sum(1 for row in rows.values() if row.total > 0)
    solid = sum(1 for row in rows.values() if not row.under_covered)
    lines += [
        "",
        "## Summary",
        "",
        f"- 有案例覆盖的能力数：{covered}/{len(ALL_CAPABILITIES)}",
        f"- 覆盖案例 ≥ {UNDER_COVERED_THRESHOLD} 的能力数：{solid}/{len(ALL_CAPABILITIES)}",
        "- 覆盖密度 = 该能力覆盖案例数 / 全部案例数。",
        "- 已标注 = case 的 metadata.capabilities 显式声明；待标注(推断) = "
        "自动推断的推荐标注，需人工审查。",
    ]
    return "\n".join(lines) + "\n"


def build_annotation_suggestions(
    datasets: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Recommended capability annotations for unannotated cases."""
    suggestions: list[dict[str, Any]] = []
    for dataset_name in DATASET_ORDER:
        for case in datasets.get(dataset_name, []):
            annotated, inferred = scan_case_capabilities(case)
            if annotated:
                continue
            basis_parts: list[str] = []
            metadata = case.get("metadata")
            if isinstance(metadata, dict):
                if metadata.get("challenge_type"):
                    basis_parts.append(f"challenge={metadata['challenge_type']}")
                if metadata.get("expected_reasoning_features"):
                    basis_parts.append(
                        f"features={','.join(map(str, metadata['expected_reasoning_features']))}"
                    )
                if metadata.get("design_intent"):
                    basis_parts.append(f"design_intent={metadata['design_intent']}")
            if not basis_parts:
                basis_parts.append("query 关键词推断")
            suggestions.append(
                {
                    "dataset": dataset_name,
                    "case_id": str(case.get("id", "")),
                    "capabilities": [capability.value for capability in inferred],
                    "basis": "；".join(basis_parts),
                }
            )
    return suggestions


def render_annotation_suggestions(
    suggestions: Sequence[dict[str, Any]],
    *,
    generated_at: str | None = None,
) -> str:
    """Render ``CAPABILITY_ANNOTATION_SUGGESTIONS.md`` for human review."""
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    lines = [
        "# Benchmark Capability Annotation Suggestions",
        "",
        f"- Generated: {timestamp}",
        f"- Pending cases: {len(suggestions)}",
        "",
        "以下为自动推断的能力标注建议，供人工审查。**不会自动写入任何数据集文件**；"
        "审查通过后可在 case 的 `metadata.capabilities` 中显式声明。",
        "",
        "| Dataset | Case ID | 推荐 capabilities | 推断依据 |",
        "|---|---|---|---|",
    ]
    for suggestion in suggestions:
        lines.append(
            f"| {suggestion['dataset']} | {suggestion['case_id']} | "
            f"{', '.join(suggestion['capabilities']) if suggestion['capabilities'] else '—'} | "
            f"{suggestion['basis']} |"
        )
    return "\n".join(lines) + "\n"


def write_capability_docs(output_dir: str | Path | None = None) -> tuple[Path, Path]:
    """Write ``CAPABILITY_COVERAGE.md`` and ``CAPABILITY_ANNOTATION_SUGGESTIONS.md``."""
    base = Path(output_dir) if output_dir is not None else DATASETS_DIR.parent
    base.mkdir(parents=True, exist_ok=True)
    datasets = load_all_datasets()
    coverage_path = base / "CAPABILITY_COVERAGE.md"
    suggestions_path = base / "CAPABILITY_ANNOTATION_SUGGESTIONS.md"
    coverage_path.write_text(
        render_capability_coverage(datasets),
        encoding="utf-8",
    )
    suggestions_path.write_text(
        render_annotation_suggestions(build_annotation_suggestions(datasets)),
        encoding="utf-8",
    )
    return coverage_path, suggestions_path


# ---------------------------------------------------------------------------
# per-challenge-type ablation statistics (Evidence Review Gate)
# ---------------------------------------------------------------------------


def _challenge(case: dict[str, Any]) -> str:
    metadata = case.get("metadata")
    if isinstance(metadata, dict):
        return str(metadata.get("challenge_type", ""))
    return ""


def _features(case: dict[str, Any]) -> list[str]:
    metadata = case.get("metadata")
    if isinstance(metadata, dict) and isinstance(
        metadata.get("expected_reasoning_features"), list
    ):
        return [str(feature) for feature in metadata["expected_reasoning_features"]]
    return []


def _group_values(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate one combo's metric rows into grouped scalar values."""
    accuracy = [
        float(row["accuracy"])
        for row in rows
        if row.get("accuracy") not in (None, "")
    ]
    disease = [
        float(row["accuracy"])
        for row in rows
        if row.get("accuracy") not in (None, "")
        and row.get("expected", "") != "证据不足"
    ]
    confidence = [
        float(row["confidence"])
        for row in rows
        if row.get("confidence") not in (None, "")
    ]
    rounds = [
        float(row["debate_rounds"])
        for row in rows
        if row.get("debate_rounds") not in (None, "")
    ]
    return {
        "accuracy": _mean(accuracy),
        "disease_recall": _mean(disease),
        "average_confidence": _mean(confidence),
        "memory_hits": float(sum(int(row.get("memory_hits") or 0) for row in rows)),
        "debate_rounds": _mean(rounds),
        "counterfactual_count": float(
            sum(int(row.get("counterfactual_count") or 0) for row in rows)
        ),
    }


def challenge_ablation_stats(run_dir: Path) -> dict[str, dict[str, dict[str, float]]]:
    """Group per-combo metrics by ``challenge_type``.

    Returns ``{challenge: {combo: {metric: value}}}`` read from the ablation
    run's per-combo ``metrics.csv`` files joined with ``enriched.json``.
    """
    enriched = load_dataset(str(DATASETS_DIR / "enriched.json"))
    challenge_by_case: dict[str, str] = {
        case["id"]: _challenge(case) for case in enriched
    }
    grouped: dict[str, dict[str, dict[str, float]]] = {
        challenge: {} for challenge in CHALLENGE_TYPES
    }
    for combo_dir in sorted(run_dir.iterdir()):
        if not combo_dir.is_dir():
            continue
        csv_path = combo_dir / "metrics.csv"
        if not csv_path.is_file():
            continue
        rows_by_case: dict[str, dict[str, Any]] = {}
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                rows_by_case[row["case_id"]] = row
        for challenge in CHALLENGE_TYPES:
            challenge_rows = [
                row
                for case_id, row in rows_by_case.items()
                if challenge_by_case.get(case_id) == challenge
            ]
            if challenge_rows:
                grouped[challenge][combo_dir.name] = _group_values(challenge_rows)
    return grouped


def render_challenge_stats_section(
    grouped: dict[str, dict[str, dict[str, float]]],
) -> str:
    """Render per-challenge Δ tables (Δ = baseline − combo)."""
    lines = ["", "## 按 challenge_type 分组的模块贡献统计", ""]
    for challenge in CHALLENGE_TYPES:
        combos = grouped.get(challenge, {})
        baseline = combos.get(_BASELINE_COMBO)
        others = [name for name in combos if name != _BASELINE_COMBO]
        lines.append(f"### {challenge}")
        lines.append("")
        lines.append("| combo | " + " | ".join(GROUP_METRICS) + " |")
        lines.append("|" + "---|" * (len(GROUP_METRICS) + 1))
        if baseline is None:
            lines.append(
                "| _（无数据） | "
                + " | ".join(["—"] * len(GROUP_METRICS))
                + " |"
            )
            lines.append("")
            continue
        for name in others:
            combo_values = combos.get(name, {})
            cells = [name]
            for metric in GROUP_METRICS:
                delta = baseline.get(metric, 0.0) - combo_values.get(metric, 0.0)
                cells.append(_fmt_delta(delta))
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines) + "\n"


def write_challenge_ablation_stats(run_dir: str | Path) -> Path:
    """Append challenge-grouped statistics to the ablation run's REPORT.md."""
    run_dir_path = Path(run_dir)
    report_path = run_dir_path / "REPORT.md"
    grouped = challenge_ablation_stats(run_dir_path)
    section = render_challenge_stats_section(grouped)
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(section)
    return report_path


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _fmt_delta(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate benchmark docs / capability coverage / challenge "
        "ablation stats (Phase 2.1E, Sprint 04.5A)"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="override docs directory (default: benchmarks/)",
    )
    parser.add_argument(
        "--ablation-dir",
        default=None,
        help="append per-challenge-type stats to an ablation run's REPORT.md",
    )
    args = parser.parse_args()
    matrix_path, coverage_path = write_docs(args.output_dir)
    capability_coverage_path, suggestions_path = write_capability_docs(args.output_dir)
    print(f"capability matrix:        {matrix_path}")
    print(f"coverage report:          {coverage_path}")
    print(f"capability coverage:      {capability_coverage_path}")
    print(f"annotation suggestions:   {suggestions_path}")
    if args.ablation_dir:
        report_path = write_challenge_ablation_stats(args.ablation_dir)
        print(f"challenge stats appended to: {report_path}")


if __name__ == "__main__":
    main()

