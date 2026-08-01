"""CSV and Markdown report generation (Phase 2.1E, Sprint 02).

Writes the per-case metrics table to ``metrics.csv`` (with a trailing
``__aggregate__`` row) and the aggregate summary to ``summary.md``.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.config import EvalConfig
from evals.metrics import CaseMetrics

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
    return {
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
