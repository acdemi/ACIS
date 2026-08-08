"""Tests for the statistical analysis engine (Phase 2.1E -> 2.2, Sprint 06).

Builds synthetic experiment archives (metrics.csv + manifest.json) so the
analysis can be exercised without running the orchestrator.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from experiments.analysis import (
    analyze_experiment,
    bootstrap_mean_ci,
    format_analysis_markdown,
    load_run_cases,
    result_to_json,
    sample_std,
)

CAPS: tuple[str, ...] = (
    "information_gathering",
    "knowledge_retrieval",
    "conflict_resolution",
    "counterfactual_reasoning",
    "uncertainty_quantification",
    "multi_step_planning",
    "sensor_cross_validation",
)
CAP_COLS: list[str] = [f"capability_{c}" for c in CAPS]

_FIELDS: list[str] = [
    "case_id",
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
    *CAP_COLS,
]


def _case(cid: str, acc: float, conf: float, caps: list[float]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "case_id": cid,
        "accuracy": acc,
        "confidence": conf,
        "runtime_seconds": 0.1,
        "planner_usage": 1.0,
        "tool_usage": 1.0,
        "tool_requests": 1,
        "memory_hits": 2,
        "debate_rounds": 1,
        "counterfactual_count": 3,
        "collective_omission_count": 0,
    }
    for col, value in zip(CAP_COLS, caps):
        row[col] = value
    return row


def _write_run(run_dir: Path, rows: list[dict[str, Any]]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return run_dir


def _make_experiment(
    tmp_path: Path, runs: list[tuple[str, dict[str, bool], list[dict[str, Any]]]]
) -> Path:
    exp = tmp_path / "exp"
    exp.mkdir()
    manifest_runs: list[dict[str, Any]] = []
    for name, toggles, rows in runs:
        run_dir = _write_run(exp / "runs" / name, rows)
        manifest_runs.append(
            {"name": name, "toggles": toggles, "output_dir": str(run_dir), "cases": len(rows)}
        )
    manifest = {
        "experiment": "test_exp",
        "dataset": "benchmarks.datasets.enriched",
        "runs": manifest_runs,
        "ablation": {"enabled": False, "combos": []},
    }
    (exp / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return exp


_ALL_ON = {
    "planner": True,
    "debate": True,
    "memory": True,
    "tool_router": True,
    "counterfactual": True,
    "critic": True,
}
_NO_MEMORY = {**_ALL_ON, "memory": False}


def _baseline_caps(kr: float = 1.0) -> list[float]:
    caps = [1.0] * 7
    caps[1] = kr  # knowledge_retrieval
    return caps


def _ablated_caps(kr: float = 0.0) -> list[float]:
    caps = [1.0] * 7
    caps[1] = kr
    return caps


# ---------------------------------------------------------------------------
# numeric primitives
# ---------------------------------------------------------------------------


def test_bootstrap_mean_ci_contains_point() -> None:
    sample = [0.1, 0.2, 0.3, 0.4, 0.5]
    mean, lo, hi = bootstrap_mean_ci(sample, n_resamples=500, seed=1)
    assert mean == 0.3
    assert lo <= mean <= hi


def test_bootstrap_mean_ci_degenerate() -> None:
    assert bootstrap_mean_ci([]) == (0.0, 0.0, 0.0)
    mean, lo, hi = bootstrap_mean_ci([0.42])
    assert (mean, lo, hi) == (0.42, 0.42, 0.42)


def test_sample_std() -> None:
    assert sample_std([]) == 0.0
    assert sample_std([5.0]) == 0.0
    assert sample_std([1.0, 1.0, 1.0]) == 0.0
    # sample std (ddof=1) of [0,2] -> sqrt(2)
    assert abs(sample_std([0.0, 2.0]) - 2.0 ** 0.5) < 1e-9


# ---------------------------------------------------------------------------
# archive reading
# ---------------------------------------------------------------------------


def test_load_run_cases_skips_aggregate_row(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_run(run_dir, [_case("c1", 1.0, 0.5, _baseline_caps())])
    # append a synthetic aggregate row that must be ignored
    with (run_dir / "metrics.csv").open("a", encoding="utf-8") as handle:
        agg = {f: "" for f in _FIELDS}
        agg["case_id"] = "__aggregate__"
        csv.DictWriter(handle, fieldnames=_FIELDS).writerow(agg)
    cases = load_run_cases(run_dir)
    assert len(cases) == 1
    assert cases[0]["case_id"] == "c1"


# ---------------------------------------------------------------------------
# analyze_experiment
# ---------------------------------------------------------------------------


def test_analyze_single_seed_baseline_vs_ablated(tmp_path: Path) -> None:
    exp = _make_experiment(
        tmp_path,
        [
            ("all_on", _ALL_ON, [_case(f"b{i}", 1.0, 0.6, _baseline_caps(1.0)) for i in range(4)]),
            ("no_memory", _NO_MEMORY, [_case(f"m{i}", 1.0, 0.6, _ablated_caps(0.0)) for i in range(4)]),
        ],
    )
    result = analyze_experiment(exp, n_resamples=300, seed=0)
    assert result.baseline == "all_on"
    assert len(result.runs) == 2
    by_name = {r.name: r for r in result.runs}
    assert by_name["all_on"].is_baseline
    assert by_name["no_memory"].n_seeds == 1
    assert by_name["no_memory"].n_cases == 4
    # knowledge_retrieval effect size: baseline 1.0 - ablated 0.0 = 1.0
    kr_effects = [e for e in result.effect_sizes if e.field == "knowledge_retrieval"]
    assert kr_effects, "expected a knowledge_retrieval effect size"
    assert kr_effects[0].ablated == "no_memory"
    assert abs(kr_effects[0].delta - 1.0) < 1e-9
    assert kr_effects[0].significant


def test_analyze_multi_seed_aggregation(tmp_path: Path) -> None:
    runs = []
    for seed in (1, 2):
        runs.append((f"all_on__s{seed}", _ALL_ON, [_case(f"b{seed}{i}", 1.0, 0.6, _baseline_caps(1.0)) for i in range(3)]))
        runs.append((f"no_memory__s{seed}", _NO_MEMORY, [_case(f"m{seed}{i}", 1.0, 0.6, _ablated_caps(0.0)) for i in range(3)]))
    exp = _make_experiment(tmp_path, runs)
    result = analyze_experiment(exp, n_resamples=300, seed=0)
    by_name = {r.name: r for r in result.runs}
    assert by_name["all_on"].n_seeds == 2
    assert by_name["no_memory"].n_seeds == 2
    assert by_name["all_on"].n_cases == 6
    # multi-seed stats use per-run means -> n == number of seeds
    assert by_name["all_on"].metrics["accuracy"].n == 2
    kr = [e for e in result.effect_sizes if e.field == "knowledge_retrieval"]
    assert kr and abs(kr[0].delta - 1.0) < 1e-9


def test_module_capability_matrix(tmp_path: Path) -> None:
    exp = _make_experiment(
        tmp_path,
        [
            ("all_on", _ALL_ON, [_case(f"b{i}", 1.0, 0.6, _baseline_caps(1.0)) for i in range(3)]),
            ("no_memory", _NO_MEMORY, [_case(f"m{i}", 1.0, 0.6, _ablated_caps(0.0)) for i in range(3)]),
        ],
    )
    result = analyze_experiment(exp, n_resamples=200, seed=0)
    assert "memory" in result.module_capability
    assert abs(result.module_capability["memory"]["knowledge_retrieval"] - 1.0) < 1e-9


def test_format_and_serialize(tmp_path: Path) -> None:
    exp = _make_experiment(
        tmp_path,
        [
            ("all_on", _ALL_ON, [_case("b", 1.0, 0.6, _baseline_caps())]),
            ("no_memory", _NO_MEMORY, [_case("m", 1.0, 0.6, _ablated_caps())]),
        ],
    )
    result = analyze_experiment(exp, n_resamples=100, seed=0)
    md = format_analysis_markdown(result)
    assert "Effect Sizes" in md
    assert "knowledge_retrieval" in md
    # JSON round-trips
    payload = result_to_json(result)
    assert json.loads(json.dumps(payload))["baseline"] == "all_on"