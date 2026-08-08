"""Experiment manager (Phase 2.1E, Sprint 05).

Orchestrates an experiment end-to-end: parse the definition, execute each run
(and the optional ablation arm) through the runner adapter, archive an
immutable result bundle (config, environment snapshot, manifest), and emit a
summary ``REPORT.md``. Also exposes the catalog CLI (``run`` / ``list`` /
``compare`` / ``latest``).

Entry point::

    python -m experiments.manager run experiments/definitions/baseline.yaml
    python -m experiments.manager list --filter dataset=benchmarks.datasets.enriched
    python -m experiments.manager compare <exp1> <exp2>
    python -m experiments.manager latest

The manager never modifies frozen modules; execution flows solely through
:class:`~experiments.runner_adapter.RunnerAdapter`, which is the
dependency-injection seam used by the test suite.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiments.analysis import (
    analyze_experiment,
    format_analysis_markdown,
    result_to_json,
)
from experiments.archive import (
    AblationSummary,
    RunSummary,
    build_manifest,
    write_config_copy,
    write_environment,
    write_manifest,
)
from experiments.catalog import (
    compare_experiments,
    filter_experiments,
    latest_experiment,
    list_experiments,
    load_record,
    parse_filter_args,
)
from experiments.fingerprint import augment_manifest, verify_experiment
from experiments.runner_adapter import DefaultRunnerAdapter, RunnerAdapter
from experiments.schema import TOGGLE_FIELDS, ExperimentDefinition, load_definition


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


def _experiment_dir(definition: ExperimentDefinition, output_root: str) -> Path:
    return Path(output_root) / f"{_safe_name(definition.name)}__{_utc_stamp()}"


def _run_toggles(run_spec: Any) -> dict[str, bool]:
    return {field: bool(getattr(run_spec, field)) for field in TOGGLE_FIELDS}


def _expand_seeds(run_spec: Any) -> list[Any]:
    """Expand a multi-seed run into one spec per seed (``{name}__seed{seed}``).

    A run with no ``seeds`` is returned unchanged (single-seed behavior).
    """
    if not run_spec.seeds:
        return [run_spec]
    from dataclasses import replace

    return [
        replace(run_spec, seed=seed, name=f"{run_spec.name}__seed{seed}")
        for seed in run_spec.seeds
    ]


def _capability_averages(rows: list[Any]) -> dict[str, Any]:
    if not rows:
        return {}
    from evals.metrics import aggregate_capability_scores

    return aggregate_capability_scores(rows)


def _summarize_run(run_spec: Any, dataset: str, output_dir: Path, result: Any) -> RunSummary:
    return RunSummary(
        name=run_spec.name,
        dataset=dataset,
        output_dir=str(output_dir),
        toggles=_run_toggles(run_spec),
        cases=len(result.rows),
        aggregate=dict(result.aggregate),
        capability_scores=_capability_averages(result.rows),
    )


def _summarize_ablation(dataset: str, result: Any) -> AblationSummary:
    combos: list[RunSummary] = []
    for combo_result in result.combo_results:
        combos.append(
            RunSummary(
                name=combo_result.combo_name,
                dataset=dataset,
                output_dir=str(combo_result.combo_dir),
                toggles=dict(combo_result.toggles),
                cases=len(combo_result.rows),
                aggregate=dict(combo_result.aggregate),
                capability_scores=_capability_averages(combo_result.rows),
            )
        )
    return AblationSummary(
        enabled=True,
        run_dir=str(result.run_dir),
        report_path=str(result.report_path),
        combos=tuple(combos),
    )


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _cap_avg(capability_scores: dict[str, Any], key: str) -> str:
    cap = capability_scores.get(key) if isinstance(capability_scores, dict) else None
    if isinstance(cap, dict):
        return _fmt(cap.get("average"))
    return "-"


def _collect_cap_keys(
    runs: list[RunSummary], ablation: AblationSummary
) -> list[str]:
    keys: set[str] = set()
    for summary in [*runs, *ablation.combos]:
        caps = summary.capability_scores
        if isinstance(caps, dict):
            keys.update(caps.keys())
    return sorted(keys)


_RUN_METRIC_COLUMNS: tuple[str, ...] = (
    "cases",
    "accuracy",
    "average_confidence",
    "average_runtime",
    "planner_usage",
    "tool_usage",
    "memory_hits",
    "debate_rounds",
)


def _row_metrics_line(name: str, summary: RunSummary) -> str:
    agg = summary.aggregate
    cells = [name, str(summary.cases)]
    cells.extend(_fmt(agg.get(col)) for col in _RUN_METRIC_COLUMNS[1:])
    return "| " + " | ".join(cells) + " |"


def write_report(
    exp_dir: Path,
    definition: ExperimentDefinition,
    manifest: dict[str, Any],
    runs: list[RunSummary],
    ablation: AblationSummary,
) -> Path:
    """Render the experiment-level ``REPORT.md``."""
    git = manifest.get("git") or {}
    meta = definition.metadata
    lines: list[str] = []
    lines.append(f"# Experiment Report: {definition.name}")
    lines.append("")
    lines.append(f"- Description: {definition.description or '-'}")
    lines.append(f"- Dataset: {definition.dataset}")
    lines.append(f"- Capability eval: {definition.capability_eval}")
    lines.append(f"- Git: {git.get('short') or '-'} ({git.get('branch') or '-'})")
    lines.append(f"- Python: {manifest.get('python', '-')}")
    lines.append(f"- Platform: {manifest.get('platform', '-')}")
    lines.append(f"- Started: {manifest.get('started_at', '-')}")
    lines.append(f"- Ended: {manifest.get('ended_at', '-')}")
    lines.append(f"- Duration: {_fmt(manifest.get('duration_seconds'))}s")
    if meta.author or meta.version or meta.tags or meta.paper:
        lines.append(
            f"- Metadata: author={meta.author or '-'} "
            f"version={meta.version or '-'} "
            f"tags={','.join(meta.tags) or '-'} "
            f"paper={meta.paper or '-'}"
        )
    lines.append("")
    if runs:
        lines.append("## Run Metrics")
        lines.append("")
        header = ["run", *_RUN_METRIC_COLUMNS]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for summary in runs:
            lines.append(_row_metrics_line(summary.name, summary))
        lines.append("")
    if definition.capability_eval and (runs or ablation.combos):
        cap_keys = _collect_cap_keys(runs, ablation)
        if cap_keys:
            lines.append("## Capability Summary")
            lines.append("")
            header = ["run", *cap_keys]
            lines.append("| " + " | ".join(header) + " |")
            lines.append("|" + "|".join(["---"] * len(header)) + "|")
            for summary in runs:
                row = [summary.name, *(_cap_avg(summary.capability_scores, k) for k in cap_keys)]
                lines.append("| " + " | ".join(row) + " |")
            for combo in ablation.combos:
                row = [combo.name, *(_cap_avg(combo.capability_scores, k) for k in cap_keys)]
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")
    if ablation.enabled:
        lines.append("## Ablation")
        lines.append("")
        lines.append(f"- Run dir: `{ablation.run_dir}`")
        lines.append(f"- Report: `{ablation.report_path}`")
        lines.append(f"- Combos: {len(ablation.combos)}")
        lines.append("")
    report_path = exp_dir / "REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def run(
    definition_path: str | Path,
    *,
    adapter: RunnerAdapter | None = None,
    output_root: str | None = None,
) -> Path:
    """Execute an experiment definition and archive the results.

    Returns the experiment directory. ``adapter`` defaults to the real runner;
    tests inject a fake to avoid orchestrator execution.
    """
    definition = load_definition(definition_path)
    runner = adapter or DefaultRunnerAdapter()
    root = output_root or definition.output_root
    exp_dir = _experiment_dir(definition, root)
    exp_dir.mkdir(parents=True, exist_ok=True)

    started_at = _utc_now_iso()
    start_perf = time.perf_counter()

    write_config_copy(exp_dir, definition)
    write_environment(exp_dir)

    run_summaries: list[RunSummary] = []
    for run_spec in definition.runs:
        specs = _expand_seeds(run_spec)
        for spec in specs:
            dataset = spec.dataset or definition.dataset
            run_dir = exp_dir / "runs" / spec.name
            run_dir.mkdir(parents=True, exist_ok=True)
            result = runner.run_evaluation(
                spec, dataset=dataset, output_dir=str(run_dir)
            )
            run_summaries.append(_summarize_run(spec, dataset, run_dir, result))

    ablation_summary = AblationSummary()
    if definition.ablation.enabled:
        dataset = definition.ablation.dataset or definition.dataset
        abl_dir = exp_dir / "ablation"
        abl_dir.mkdir(parents=True, exist_ok=True)
        ablation_result = runner.run_ablation(
            definition.ablation, dataset=dataset, output_dir=str(abl_dir)
        )
        ablation_summary = _summarize_ablation(dataset, ablation_result)

    ended_at = _utc_now_iso()
    duration = time.perf_counter() - start_perf

    manifest = build_manifest(
        definition,
        dataset=definition.dataset,
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=duration,
        runs=run_summaries,
        ablation=ablation_summary,
    )
    manifest = augment_manifest(manifest, definition.dataset)
    write_manifest(exp_dir, manifest)
    report_path = write_report(exp_dir, definition, manifest, run_summaries, ablation_summary)

    print(f"experiment complete: {definition.name}")
    print(f"  dir: {exp_dir}")
    print(f"  runs: {len(run_summaries)}")
    if ablation_summary.enabled:
        print(f"  ablation combos: {len(ablation_summary.combos)}")
    print(f"  manifest: {exp_dir / 'manifest.json'}")
    print(f"  report: {report_path}")
    return exp_dir


def _resolve_experiment_dir(output_root: str, name: str) -> Path:
    path = Path(name)
    if path.exists():
        return path
    return Path(output_root) / name


def cmd_list(output_root: str, filter_args: list[str]) -> int:
    records = list_experiments(output_root)
    filters = parse_filter_args(filter_args)
    records = filter_experiments(records, filters)
    if not records:
        print("no experiments found")
        return 0
    print(f"{len(records)} experiment(s):")
    for record in records:
        git = (record.manifest.get("git") or {}).get("short", "")
        print(
            f"  {record.dir.name}  name={record.name}  "
            f"dataset={record.manifest.get('dataset')}  git={git}  "
            f"started={record.started_at}"
        )
    return 0


def cmd_compare(output_root: str, exp1: str, exp2: str) -> int:
    dir_a = _resolve_experiment_dir(output_root, exp1)
    dir_b = _resolve_experiment_dir(output_root, exp2)
    record_a = load_record(dir_a)
    record_b = load_record(dir_b)
    if record_a is None:
        print(f"experiment not found: {exp1}", file=sys.stderr)
        return 1
    if record_b is None:
        print(f"experiment not found: {exp2}", file=sys.stderr)
        return 1
    print(compare_experiments(record_a, record_b))
    return 0


def cmd_latest(output_root: str) -> int:
    record = latest_experiment(output_root)
    if record is None:
        print("no experiments found")
        return 0
    git = (record.manifest.get("git") or {}).get("short", "")
    print(f"latest: {record.dir.name}")
    print(f"  name: {record.name}")
    print(f"  dataset: {record.manifest.get('dataset')}")
    print(f"  git: {git}")
    print(f"  started: {record.started_at}")
    print(f"  dir: {record.dir}")
    return 0


def _resolve_experiment(output_root: str, name: str) -> Path | None:
    """Resolve an experiment by path, archive dir name, or experiment name (latest)."""
    direct = Path(name)
    if direct.exists() and (direct / "manifest.json").exists():
        return direct
    under_root = Path(output_root) / name
    if under_root.exists() and (under_root / "manifest.json").exists():
        return under_root
    records = list_experiments(output_root)
    matches = [record for record in records if record.name == name]
    if matches:
        return matches[-1].dir
    return None


def cmd_analyze(output_root: str, name: str, n_resamples: int, seed: int) -> int:
    exp_dir = _resolve_experiment(output_root, name)
    if exp_dir is None:
        print(f"experiment not found: {name}", file=sys.stderr)
        return 1
    result = analyze_experiment(exp_dir, n_resamples=n_resamples, seed=seed)
    print(format_analysis_markdown(result))
    json_path = exp_dir / "analysis.json"
    json_path.write_text(
        json.dumps(result_to_json(result), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nanalysis json: {json_path}", file=sys.stderr)
    return 0


def cmd_figure(output_root: str, name: str, n_resamples: int, seed: int) -> int:
    from experiments.figures import generate_figures

    exp_dir = _resolve_experiment(output_root, name)
    if exp_dir is None:
        print(f"experiment not found: {name}", file=sys.stderr)
        return 1
    result = analyze_experiment(exp_dir, n_resamples=n_resamples, seed=seed)
    paths = generate_figures(exp_dir, result)
    for path in paths:
        print(f"figure: {path}")
    return 0


def cmd_report(output_root: str, name: str, n_resamples: int, seed: int) -> int:
    from experiments.figures import generate_figures
    from experiments.report import generate_report

    exp_dir = _resolve_experiment(output_root, name)
    if exp_dir is None:
        print(f"experiment not found: {name}", file=sys.stderr)
        return 1
    result = analyze_experiment(exp_dir, n_resamples=n_resamples, seed=seed)
    paths = generate_figures(exp_dir, result)
    report_path = generate_report(exp_dir, result, paths)
    print(f"report: {report_path}")
    print(f"figures: {len(paths)}")
    return 0


def cmd_verify(output_root: str, name: str) -> int:
    exp_dir = _resolve_experiment(output_root, name)
    if exp_dir is None:
        print(f"experiment not found: {name}", file=sys.stderr)
        return 1
    result = verify_experiment(exp_dir)
    status = "PASS" if result.verified else "FAIL"
    print(f"verify {status}: {exp_dir.name}")
    print(f"  dataset:  {result.dataset_source}")
    print(f"  stored:   {result.stored_sha256}")
    print(f"  computed: {result.computed_sha256}")
    print(f"  reason:   {result.reason}")
    return 0 if result.verified else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="experiments.manager",
        description="ACIS Experiment Manager (Phase 2.1E, Sprint 05)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run an experiment definition")
    run_parser.add_argument("definition", help="path to a YAML/JSON experiment definition")
    run_parser.add_argument("--output-root", default=None, help="override output_root")

    list_parser = sub.add_parser("list", help="list archived experiments")
    list_parser.add_argument("--output-root", default="results/experiments")
    list_parser.add_argument(
        "--filter", nargs="*", default=[], help="KEY=VALUE filters (dot-paths)"
    )

    compare_parser = sub.add_parser("compare", help="compare two experiments")
    compare_parser.add_argument("--output-root", default="results/experiments")
    compare_parser.add_argument("exp1", help="experiment directory name or path")
    compare_parser.add_argument("exp2", help="experiment directory name or path")

    latest_parser = sub.add_parser("latest", help="show the most recent experiment")
    latest_parser.add_argument("--output-root", default="results/experiments")

    analyze_parser = sub.add_parser("analyze", help="statistical analysis of an experiment")
    analyze_parser.add_argument("--output-root", default="results/experiments")
    analyze_parser.add_argument("experiment", help="experiment name or directory")
    analyze_parser.add_argument("--n-resamples", type=int, default=1000)
    analyze_parser.add_argument("--seed", type=int, default=0)

    figure_parser = sub.add_parser("figure", help="generate publication figures")
    figure_parser.add_argument("--output-root", default="results/experiments")
    figure_parser.add_argument("experiment", help="experiment name or directory")
    figure_parser.add_argument("--n-resamples", type=int, default=1000)
    figure_parser.add_argument("--seed", type=int, default=0)

    report_parser = sub.add_parser("report", help="generate full research report")
    report_parser.add_argument("--output-root", default="results/experiments")
    report_parser.add_argument("experiment", help="experiment name or directory")
    report_parser.add_argument("--n-resamples", type=int, default=1000)
    report_parser.add_argument("--seed", type=int, default=0)

    verify_parser = sub.add_parser("verify", help="verify dataset fingerprint")
    verify_parser.add_argument("--output-root", default="results/experiments")
    verify_parser.add_argument("experiment", help="experiment name or directory")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        run(args.definition, output_root=args.output_root)
        return 0
    if args.command == "list":
        return cmd_list(args.output_root, args.filter)
    if args.command == "compare":
        return cmd_compare(args.output_root, args.exp1, args.exp2)
    if args.command == "latest":
        return cmd_latest(args.output_root)
    if args.command == "analyze":
        return cmd_analyze(args.output_root, args.experiment, args.n_resamples, args.seed)
    if args.command == "figure":
        return cmd_figure(args.output_root, args.experiment, args.n_resamples, args.seed)
    if args.command == "report":
        return cmd_report(args.output_root, args.experiment, args.n_resamples, args.seed)
    if args.command == "verify":
        return cmd_verify(args.output_root, args.experiment)
    return 1


if __name__ == "__main__":
    sys.exit(main())