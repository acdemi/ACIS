"""CSV and Markdown report generation (Phase 2.1E, Sprint 02).

Writes the per-case metrics table to ``metrics.csv`` (with a trailing
``__aggregate__`` row) and the aggregate summary to ``summary.md``.

Phase 2.1E, Sprint 04: adds ablation report generation — configuration
matrix, absolute metrics table, contribution matrix (Δ = baseline − combo),
key findings, normalized radar-chart data, and data-backed recommendations.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.capabilities import ALL_CAPABILITIES
from evals.config import EvalConfig
from evals.metrics import (
    CaseMetrics,
    aggregate_capability_scores,
    aggregate_metrics,
)

#: Per-capability score columns appended to the metrics CSV.
CAPABILITY_SCORE_COLUMNS: list[str] = [
    f"capability_{capability.value}" for capability in ALL_CAPABILITIES
]

CSV_FIELDS = [
    "case_id",
    "trace_id",
    "expected",
    "decision",
    "accuracy",
    "confidence",
    "runtime_seconds",
    "planner_usage",
    "tool_usage",
    "tool_requests",
    "memory_hits",
    "debate_rounds",
    "counterfactual_count",
    "collective_omission_count",
    *CAPABILITY_SCORE_COLUMNS,
]

AGGREGATE_CASE_ID = "__aggregate__"


def write_metrics_csv(
    rows: list[CaseMetrics],
    aggregate: dict[str, float | int | None],
    path: str | Path,
) -> None:
    """Write per-case metrics plus an aggregate row to ``path``."""
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(_row_dict(row))
        writer.writerow(_aggregate_row(aggregate))


def write_summary_markdown(
    aggregate: dict[str, float | int | None],
    config: EvalConfig,
    rows: list[CaseMetrics],
    path: str | Path,
    *,
    generated_at: str | None = None,
) -> None:
    """Write the aggregate summary and per-case table to ``path``."""
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# Evaluation Summary",
        "",
        f"- Generated: {timestamp}",
        f"- Dataset: `{config.dataset}` ({aggregate.get('cases', 0)} cases)",
        f"- Seed: {config.seed}",
        f"- LangGraph: {'on' if config.use_langgraph else 'off'}",
        "",
        "## Configuration",
        "",
        "| toggle | value |",
        "|---|---|",
        f"| planner | {'on' if config.planner_on else 'off'} |",
        f"| debate | {'on' if config.debate_on else 'off'} |",
        f"| memory | {'on' if config.memory_on else 'off'} |",
        f"| tool_router | {'on' if config.tool_router_on else 'off'} |",
        "",
        "## Metrics",
        "",
        "| metric | value |",
        "|---|---|",
        (
            "| accuracy | "
            f"{_fmt_rate(aggregate.get('accuracy'))} "
            f"({aggregate.get('scored_cases', 0)}/{aggregate.get('cases', 0)} scored) |"
        ),
        f"| average_confidence | {_fmt_rate(aggregate.get('average_confidence'))} |",
        f"| average_runtime (s) | {_fmt_seconds(aggregate.get('average_runtime'))} |",
        f"| planner_usage | {_fmt_rate(aggregate.get('planner_usage'))} |",
        f"| tool_usage | {_fmt_rate(aggregate.get('tool_usage'))} |",
        f"| memory_hits | {_fmt_count(aggregate.get('memory_hits'))} |",
        f"| debate_rounds | {_fmt_rate(aggregate.get('debate_rounds'))} |",
        (
            "| counterfactual_count | "
            f"{_fmt_count(aggregate.get('counterfactual_count'))} |"
        ),
        (
            "| collective_omission_count | "
            f"{_fmt_count(aggregate.get('collective_omission_count'))} |"
        ),
        "",
        "## Capability Performance",
        "",
        "| capability | average | cases | positive |",
        "|---|---|---|---|",
    ]
    capability_aggregate = aggregate_capability_scores(rows)
    for capability in sorted(capability_aggregate):
        values = capability_aggregate[capability]
        lines.append(
            f"| {capability} | {_fmt_rate(values['average'])} | "
            f"{values['cases']} | {values['positive']} |"
        )
    lines += [
        "",
        "## Per-case",
        "",
        (
            "| case_id | accuracy | confidence | runtime_s | planner | tool | "
            "memory_hits | rounds | counterfactual | omission | expected | decision |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(_case_table_row(row))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# row builders
# ---------------------------------------------------------------------------
def _row_dict(row: CaseMetrics) -> dict[str, Any]:
    values: dict[str, Any] = {
        "case_id": row.case_id,
        "trace_id": row.trace_id,
        "expected": row.expected if row.expected is not None else "",
        "decision": row.decision,
        "accuracy": _cell(row.accuracy),
        "confidence": round(row.confidence, 4),
        "runtime_seconds": round(row.runtime_seconds, 4),
        "planner_usage": round(row.planner_usage, 4),
        "tool_usage": round(row.tool_usage, 4),
        "tool_requests": row.tool_requests,
        "memory_hits": row.memory_hits,
        "debate_rounds": row.debate_rounds,
        "counterfactual_count": row.counterfactual_count,
        "collective_omission_count": row.collective_omission_count,
    }
    for column, capability in zip(CAPABILITY_SCORE_COLUMNS, ALL_CAPABILITIES):
        values[column] = _cell(row.capability_scores.get(capability.value))
    return values


def _aggregate_row(aggregate: dict[str, float | int | None]) -> dict[str, Any]:
    return {
        "case_id": AGGREGATE_CASE_ID,
        "trace_id": "",
        "expected": "",
        "decision": "",
        "accuracy": _cell(aggregate.get("accuracy")),
        "confidence": _cell(aggregate.get("average_confidence")),
        "runtime_seconds": _cell(aggregate.get("average_runtime")),
        "planner_usage": _cell(aggregate.get("planner_usage")),
        "tool_usage": _cell(aggregate.get("tool_usage")),
        "tool_requests": "",
        "memory_hits": aggregate.get("memory_hits") or 0,
        "debate_rounds": _cell(aggregate.get("debate_rounds")),
        "counterfactual_count": aggregate.get("counterfactual_count") or 0,
        "collective_omission_count": aggregate.get("collective_omission_count") or 0,
    }


def _case_table_row(row: CaseMetrics) -> str:
    return (
        f"| {row.case_id} | {_fmt_rate(row.accuracy)} | {row.confidence:.2f} | "
        f"{row.runtime_seconds:.3f} | {row.planner_usage:.2f} | {row.tool_usage:.2f} | "
        f"{row.memory_hits} | {row.debate_rounds} | {row.counterfactual_count} | "
        f"{row.collective_omission_count} | "
        f"{row.expected if row.expected is not None else '–'} | "
        f"{_truncate(row.decision)} |"
    )


# ---------------------------------------------------------------------------
# formatting helpers
# ---------------------------------------------------------------------------
def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return round(value, 6)
    return value


def _fmt_rate(value: Any) -> str:
    return "–" if value is None else f"{value:.2f}"


def _fmt_seconds(value: Any) -> str:
    return "–" if value is None else f"{value:.3f}"


def _fmt_count(value: Any) -> str:
    return "–" if value is None else str(int(value))


def _truncate(text: str, limit: int = 36) -> str:
    cleaned = text.strip().replace("\n", " ")
    return cleaned if len(cleaned) <= limit else cleaned[:limit] + "…"


# ---------------------------------------------------------------------------
# ablation report (Phase 2.1E, Sprint 04)
# ---------------------------------------------------------------------------

#: Metrics tracked in the ablation contribution matrix, in display order.
ABLATION_METRICS: tuple[str, ...] = (
    "accuracy",
    "disease_recall",
    "average_confidence",
    "memory_hits",
    "debate_rounds",
    "counterfactual_count",
    "collective_omission_count",
    "average_runtime",
    "planner_usage",
    "tool_usage",
)

_METRIC_LABELS: dict[str, str] = {
    "accuracy": "accuracy",
    "disease_recall": "disease_recall",
    "average_confidence": "average_confidence",
    "memory_hits": "memory_hits",
    "debate_rounds": "debate_rounds",
    "counterfactual_count": "counterfactual_count",
    "collective_omission_count": "collective_omission_count",
    "average_runtime": "average_runtime (s)",
    "planner_usage": "planner_usage",
    "tool_usage": "tool_usage",
}

#: Metrics included in the normalized radar-chart data table.
_RADAR_METRICS: tuple[str, ...] = (
    "accuracy",
    "average_confidence",
    "memory_hits",
    "debate_rounds",
    "counterfactual_count",
    "collective_omission_count",
    "planner_usage",
    "tool_usage",
)


@dataclass(frozen=True)
class AblationResult:
    """Aggregated outcome of one ablation combo run."""

    combo_name: str
    description: str
    toggles: dict[str, bool]
    aggregate: dict[str, float | int | None]
    rows: list[CaseMetrics]
    combo_dir: Path


def compute_ablation_metrics(rows: list[CaseMetrics]) -> dict[str, float | int | None]:
    """Aggregate metrics plus dataset-derived ``disease_recall``.

    ``disease_recall`` is the mean accuracy over cases carrying a concrete
    disease ground truth (not ``None`` and not ``证据不足``); it measures how
    well the pipeline recovers the expected diagnosis.
    """
    values: dict[str, float | int | None] = dict(aggregate_metrics(rows))
    disease = [
        row.accuracy
        for row in rows
        if row.expected is not None
        and row.expected != "证据不足"
        and row.accuracy is not None
    ]
    values["disease_recall"] = _mean(disease)
    return values


def contribution_deltas(
    baseline: dict[str, float | int | None],
    combo: dict[str, float | int | None],
) -> dict[str, float | int | None]:
    """Compute Δ = baseline − combo for every tracked metric (None-safe)."""
    deltas: dict[str, float | int | None] = {}
    for metric in ABLATION_METRICS:
        base = baseline.get(metric)
        value = combo.get(metric)
        deltas[metric] = (
            None if base is None or value is None else float(base) - float(value)
        )
    return deltas


def write_ablation_report(
    results: list[AblationResult],
    output_dir: Path,
    *,
    dataset: str,
    generated_at: str | None = None,
) -> Path:
    """Write ``REPORT.md`` with configuration, matrices, and findings."""
    if not results:
        raise ValueError("ablation report requires at least one combo result")
    baseline = next((r for r in results if r.combo_name == "all_on"), results[0])
    order = [baseline.combo_name] + [
        r.combo_name for r in results if r.combo_name != baseline.combo_name
    ]
    values = {r.combo_name: compute_ablation_metrics(r.rows) for r in results}

    timestamp = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines: list[str] = [
        "# ACIS Ablation Report",
        "",
        f"- Generated: {timestamp}",
        f"- Dataset: `{dataset}`",
        f"- Combos: {len(results)}（baseline: `{baseline.combo_name}`）",
        "",
        "## 配置矩阵",
        "",
        "| combo | description | planner | debate | critic | memory | tool_router | counterfactual |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for result in results:
        lines.append(_config_row(result))

    lines += _table_header("绝对指标", order)
    for metric in ABLATION_METRICS:
        cells = [_METRIC_LABELS[metric]] + [
            _fmt_metric(values[name].get(metric)) for name in order
        ]
        lines.append("| " + " | ".join(cells) + " |")

    baseline_values = values[baseline.combo_name]
    combo_names = [
        r.combo_name for r in results if r.combo_name != baseline.combo_name
    ]
    lines += _table_header("贡献度矩阵（Δ = baseline − combo）", combo_names)
    for metric in ABLATION_METRICS:
        cells = [_METRIC_LABELS[metric]]
        for name in combo_names:
            delta = contribution_deltas(baseline_values, values[name]).get(metric)
            cells.append(_fmt_delta(delta))
        lines.append("| " + " | ".join(cells) + " |")

    lines += ["", "## 关键发现", ""]
    for result in results:
        if result.combo_name == baseline.combo_name:
            continue
        deltas = contribution_deltas(baseline_values, values[result.combo_name])
        lines.append(f"### {result.combo_name}")
        lines.append("")
        lines.append(f"- {result.description}")
        lines.append(
            f"- accuracy：{_fmt_metric(baseline_values.get('accuracy'))} → "
            f"{_fmt_metric(values[result.combo_name].get('accuracy'))}"
            f"（Δ {_fmt_delta(deltas.get('accuracy'))}）"
        )
        lines.append(
            f"- average_confidence：{_fmt_metric(baseline_values.get('average_confidence'))} → "
            f"{_fmt_metric(values[result.combo_name].get('average_confidence'))}"
            f"（Δ {_fmt_delta(deltas.get('average_confidence'))}）"
        )
        notable = _notable_deltas(deltas)
        lines.append(f"- 其他显著变化：{notable if notable else '无'}")
        lines.append("")

    lines += ["## 雷达图数据（归一化 0–1）"]
    lines += _table_header(None, _RADAR_METRICS, first_column="combo")
    for name in order:
        cells = [name] + [
            _fmt_metric(_normalize(values[name].get(metric), values, metric))
            for metric in _RADAR_METRICS
        ]
        lines.append("| " + " | ".join(cells) + " |")

    lines += ["", "## 建议", ""]
    lines.extend(_recommendations(baseline.combo_name, values, combo_names))
    path = output_dir / "REPORT.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# ablation report helpers
# ---------------------------------------------------------------------------


def _config_row(result: AblationResult) -> str:
    return "| {name} | {desc} | {planner} | {debate} | {critic} | {memory} | {tool} | {cf} |".format(
        name=result.combo_name,
        desc=result.description,
        planner=_fmt_toggle(result.toggles.get("planner_on", True)),
        debate=_fmt_toggle(result.toggles.get("debate_on", True)),
        critic=_fmt_toggle(result.toggles.get("critic_on", True)),
        memory=_fmt_toggle(result.toggles.get("memory_on", True)),
        tool=_fmt_toggle(result.toggles.get("tool_router_on", True)),
        cf=_fmt_toggle(result.toggles.get("counterfactual_on", True)),
    )


def _table_header(
    title: str | None,
    columns: Sequence[str],
    *,
    first_column: str = "metric",
) -> list[str]:
    header = f"| {first_column} | " + " | ".join(columns) + " |"
    separator = "|" + "---|" * (len(columns) + 1)
    if title:
        return ["", f"## {title}", "", header, separator]
    return ["", header, separator]


def _fmt_toggle(value: bool) -> str:
    return "on" if value else "off"


def _fmt_metric(value: Any) -> str:
    if value is None:
        return "–"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{value:.3f}"
    return str(value)


def _fmt_delta(value: Any) -> str:
    if value is None:
        return "–"
    delta = float(value)
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.3f}"


def _notable_deltas(deltas: dict[str, float | int | None]) -> str:
    """Top two non-accuracy/confidence deltas, formatted as text."""
    skip = {"accuracy", "average_confidence"}
    ranked = sorted(
        (
            (metric, abs(float(value)))
            for metric, value in deltas.items()
            if metric not in skip and value is not None
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    return "；".join(f"{metric} Δ {_fmt_delta(deltas[metric])}" for metric, _ in ranked[:2])


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _normalize(
    value: Any,
    values: dict[str, dict[str, float | int | None]],
    metric: str,
) -> float:
    if value is None:
        return 0.0
    maximum = max(float(v.get(metric) or 0.0) for v in values.values())
    if maximum <= 0.0:
        return 0.0
    return float(value) / maximum


def _recommendations(
    baseline_name: str,
    values: dict[str, dict[str, float | int | None]],
    combo_names: list[str],
) -> list[str]:
    """Data-backed recommendations from accuracy contributions."""
    ranked = sorted(
        (
            (
                name,
                float(values[baseline_name].get("accuracy") or 0.0)
                - float(values[name].get("accuracy") or 0.0),
            )
            for name in combo_names
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    positive = [(name, delta) for name, delta in ranked if delta > 0.001]
    if not positive:
        return [
            (
                f"在当前数据集上，所有被消融模块对 accuracy 的边际贡献均为 0"
                f"（baseline `{baseline_name}` accuracy 与各组合一致）。"
                f"建议在 medium/hard 数据集上复跑以区分模块贡献。"
            )
        ]
    lines = []
    for name, delta in positive:
        module = name.replace("no_", "") or name
        lines.append(f"模块 {module}：关闭后 accuracy 下降 {delta:.3f}，边际贡献最大。")
    return lines




