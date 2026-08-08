"""Experiment catalog (Phase 2.1E, Sprint 05).

Indexes archived experiments under an output root so they can be listed,
filtered, and compared without re-running anything. Each experiment is
identified by its ``manifest.json``; the catalog never mutates archives.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExperimentRecord:
    """A catalogued experiment, backed by its manifest."""

    dir: Path
    manifest: dict[str, Any]
    name: str = ""
    started_at: str = ""


def load_record(exp_dir: str | Path) -> ExperimentRecord | None:
    """Load an experiment record from a directory containing ``manifest.json``."""
    path = Path(exp_dir) / "manifest.json"
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(manifest, dict):
        return None
    return ExperimentRecord(
        dir=Path(exp_dir),
        manifest=manifest,
        name=str(manifest.get("experiment", "")),
        started_at=str(manifest.get("started_at", "")),
    )


def list_experiments(output_root: str | Path) -> list[ExperimentRecord]:
    """List all catalogued experiments under ``output_root``, oldest first."""
    root = Path(output_root)
    if not root.exists():
        return []
    records: list[ExperimentRecord] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        record = load_record(child)
        if record is not None:
            records.append(record)
    records.sort(key=lambda record: record.started_at)
    return records


def _get_path(manifest: dict[str, Any], path: str) -> Any:
    cur: Any = manifest
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def filter_experiments(
    records: list[ExperimentRecord], filters: dict[str, str]
) -> list[ExperimentRecord]:
    """Filter records by ``key=value`` constraints (dot-paths into the manifest).

    Scalar fields match exactly (case-insensitive); list fields (e.g.
    ``metadata.tags``) match when the value is a member.
    """
    if not filters:
        return list(records)
    result: list[ExperimentRecord] = []
    for record in records:
        keep = True
        for key, value in filters.items():
            actual = _get_path(record.manifest, key)
            if isinstance(actual, list):
                if value not in [str(item) for item in actual]:
                    keep = False
                    break
            elif actual is None or str(actual).lower() != str(value).lower():
                keep = False
                break
        if keep:
            result.append(record)
    return result


def parse_filter_args(args: list[str]) -> dict[str, str]:
    """Parse ``KEY=VALUE`` CLI arguments into a filter mapping."""
    filters: dict[str, str] = {}
    for arg in args:
        if "=" not in arg:
            raise ValueError(f"filter must be KEY=VALUE, got {arg!r}")
        key, value = arg.split("=", 1)
        filters[key.strip()] = value.strip()
    return filters


def latest_experiment(output_root: str | Path) -> ExperimentRecord | None:
    """Return the most recent experiment (by ``started_at``), or ``None``."""
    records = list_experiments(output_root)
    return records[-1] if records else None


def _entries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return ``{entry_name: run_summary}`` for evaluation runs + ablation combos."""
    entries: dict[str, dict[str, Any]] = {}
    for run in manifest.get("runs", []) or []:
        if isinstance(run, dict):
            entries[str(run.get("name", "?"))] = run
    ablation = manifest.get("ablation") or {}
    for combo in ablation.get("combos", []) or []:
        if isinstance(combo, dict):
            entries[str(combo.get("name", "?"))] = combo
    return entries


def _capability_keys(entries: dict[str, dict[str, Any]]) -> list[str]:
    keys: set[str] = set()
    for entry in entries.values():
        caps = entry.get("capability_scores") or {}
        if isinstance(caps, dict):
            keys.update(caps.keys())
    return sorted(keys)


def _cap_average(entry: dict[str, Any], capability: str) -> str:
    caps = entry.get("capability_scores") or {}
    cap = caps.get(capability) if isinstance(caps, dict) else None
    if isinstance(cap, dict):
        return _fmt(cap.get("average"))
    return "-"


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


_METRIC_COLUMNS: tuple[str, ...] = (
    "cases",
    "accuracy",
    "average_confidence",
    "average_runtime",
)


def compare_experiments(a: ExperimentRecord, b: ExperimentRecord) -> str:
    """Render a Markdown comparison of two experiments with capability columns."""
    a_entries = _entries(a.manifest)
    b_entries = _entries(b.manifest)
    cap_keys = _capability_keys({**a_entries, **b_entries})
    lines: list[str] = []
    lines.append("# Experiment Comparison")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("| Field | A | B |")
    lines.append("|---|---|---|")
    lines.append(f"| directory | {a.dir.name} | {b.dir.name} |")
    lines.append(f"| experiment | {a.name} | {b.name} |")
    lines.append(
        f"| dataset | {_fmt(a.manifest.get('dataset'))} | {_fmt(b.manifest.get('dataset'))} |"
    )
    git_a = a.manifest.get("git") or {}
    git_b = b.manifest.get("git") or {}
    lines.append(
        f"| git | {_fmt(git_a.get('short'))} | {_fmt(git_b.get('short'))} |"
    )
    lines.append(
        f"| python | {_fmt(a.manifest.get('python'))} | {_fmt(b.manifest.get('python'))} |"
    )
    lines.append(f"| started_at | {a.started_at} | {b.started_at} |")
    lines.append("")
    lines.append("## Runs")
    lines.append("")
    for name in sorted(set(a_entries) | set(b_entries)):
        entry_a = a_entries.get(name, {})
        entry_b = b_entries.get(name, {})
        lines.append(f"### {name}")
        lines.append("")
        lines.append("| Metric | A | B |")
        lines.append("|---|---|---|")
        agg_a = entry_a.get("aggregate") or {}
        agg_b = entry_b.get("aggregate") or {}
        for metric in _METRIC_COLUMNS:
            lines.append(f"| {metric} | {_fmt(agg_a.get(metric))} | {_fmt(agg_b.get(metric))} |")
        for cap in cap_keys:
            lines.append(
                f"| {cap} | {_cap_average(entry_a, cap)} | {_cap_average(entry_b, cap)} |"
            )
        lines.append("")
    return "\n".join(lines)