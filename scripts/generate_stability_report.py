"""Phase 4.2-R stability report generator (data only, no interpretation).

Reads the Phase 4.2-R real-agent raw results and the Phase 4.1 pilot
reference JSON, then reports:

- per-configuration Mean ± Std across seeds for Accuracy / ECE /
  Abstention rate / Coherence (Phase 4 metrics);
- the empirically observed Full Ranking and Pairwise Dominance per metric
  per seed — NOT compared against any preset order;
- per-metric consistency of the Phase 4.2-R empirical ranking with the
  Phase 4.1 pilot's actual observed ranking (match / flip, recorded only).

The pilot reference is used as an observation record, not as an
expectation: rank flips are valid scientific observations.

Usage from the repo root::

    python scripts/generate_stability_report.py \\
        --input reports/phase4_2_real_agent/raw_results.json \\
        --pilot-reference phase4_1_pilot_results.json \\
        --output reports/phase4_2_real_agent/stability_report.md
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from openmetaphysics.evaluation.challenge_scorer import (
    calc_abstention_rate,
    calc_confidence_calibration,
    calc_factor_scores,
)

#: Config labels in a fixed display order.
CONFIG_ORDER: tuple[str, ...] = ("C0", "C1", "C2")

#: Config label -> pilot reference arm name.
CONFIG_ARM_MAP: dict[str, str] = {
    "C0": "c0_bare_baseline",
    "C1": "c1_all_on",
    "C2": "c2_no_memory",
}

#: Metrics aggregated (lower is better for ECE; the report records raw
#: orders and the direction note for the others without judgment).
METRICS: tuple[str, ...] = (
    "accuracy",
    "ece",
    "abstention_rate",
    "coherence",
)

#: Metric direction as recorded in the Phase 4.1 pilot reference
#: (asc = smaller value ranks first, desc = larger value ranks first).
METRIC_DIRECTION: dict[str, str] = {
    "accuracy": "desc",
    "ece": "asc",
    "abstention_rate": "desc",
    "coherence": "desc",
}


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _std(values: list[float]) -> float:
    return statistics.pstdev(values) if values else 0.0


def _case_metrics(record: dict[str, Any], *, use_llm: bool) -> dict[str, Any]:
    """Phase 4 metrics for one record (factor-coverage based)."""
    factors = list(record.get("expected_key_factors") or [])
    output = {
        "decision": record.get("decision", ""),
        "reasoning_trace": record.get("reasoning_trace", ""),
    }
    if factors:
        coverage, coherence = calc_factor_scores(
            output, factors, use_llm=use_llm
        )
    else:
        coverage, coherence = 0.0, 0
    return {
        "decision": record.get("decision", ""),
        "coverage": coverage,
        "coherence": float(coherence),
        "correct": coverage >= 1.0,
        "confidence": float(record.get("confidence", 0.0)),
        "abstained": bool(
            calc_abstention_rate([{"decision": record.get("decision", "")}])
            > 0
        ),
    }


def scored_index(
    results: list[dict[str, Any]], *, use_llm: bool
) -> dict[tuple[int, str, int], dict[str, Any]]:
    """Score every record exactly once; key = (seed, config, case_index).

    One LLM coverage judgment per record; all aggregations below reuse the
    cache so the number of API calls stays equal to the record count.
    """
    index: dict[tuple[int, str, int], dict[str, Any]] = {}
    for record in results:
        key = (
            int(record["seed"]),
            str(record["config"]),
            int(record.get("case_index", 0)),
        )
        index[key] = _case_metrics(record, use_llm=use_llm)
    return index


def aggregate_scored(
    scored: list[dict[str, Any]],
) -> dict[str, float]:
    """Aggregate one group's per-case metrics into the four Phase 4
    metrics."""
    if not scored:
        return {
            "accuracy": 0.0,
            "ece": 0.0,
            "abstention_rate": 0.0,
            "coherence": 0.0,
        }
    accuracy = _mean([row["coverage"] for row in scored])
    ece = calc_confidence_calibration(
        [
            {
                "decision": row["decision"],
                "confidence": row["confidence"],
                "correct": row["correct"],
            }
            for row in scored
        ]
    )
    abstention = calc_abstention_rate(
        [{"decision": row["decision"]} for row in scored]
    )
    coherence = _mean([row["coherence"] for row in scored])
    return {
        "accuracy": round(accuracy, 4),
        "ece": round(ece, 4),
        "abstention_rate": round(abstention, 2),
        "coherence": round(coherence, 4),
    }


def _record_key(record: dict[str, Any]) -> tuple[int, str, int]:
    """Cache key for one record: (seed, config, case_index)."""
    return (
        int(record["seed"]),
        str(record["config"]),
        int(record.get("case_index", 0)),
    )


def group_records(
    results: list[dict[str, Any]],
) -> dict[tuple[int, str], list[dict[str, Any]]]:
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for record in results:
        key = (int(record["seed"]), str(record["config"]))
        grouped.setdefault(key, []).append(record)
    return grouped


def _rank(
    values: dict[str, float], *, metric: str
) -> list[str]:
    """Order configs by one metric (direction from the reference notes)."""
    ascending = METRIC_DIRECTION.get(metric, "desc") == "asc"
    return sorted(
        values,
        key=lambda config: (values[config], config),
        reverse=not ascending,
    )


def load_pilot_reference(path: Path) -> dict[str, Any]:
    """Load the Phase 4.1 pilot reference JSON."""
    if not path.exists():
        raise ValueError(f"pilot reference missing at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def render_report(
    *,
    results: list[dict[str, Any]],
    manifest: dict[str, Any],
    pilot: dict[str, Any],
    use_llm: bool,
    comparison_mode: str = "pilot_reference",
    group_by: str = "none",
) -> str:
    """Render the stability report (data only).

    ``comparison_mode`` controls the Phase 4.1 pilot section:
    ``pilot_reference`` adds a match/flip judgment column; ``within_agent_only``
    records the pilot orderings as informational reference without judgment.

    ``group_by="difficulty_category"`` adds a per-difficulty (1/2/3)
    Mean ± Std breakdown across seeds.
    """
    grouped = group_records(results)
    index = scored_index(results, use_llm=use_llm)
    seeds = sorted({key[0] for key in grouped})
    pilot_configs = pilot.get("configs", {})
    pilot_rankings = pilot.get("observed_rankings", {})

    lines: list[str] = [
        "# Phase 4.2-R Stability Report (data only)",
        "",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        (
            f"> Source: {manifest.get('started', '')} | configs: "
            f"{manifest.get('configs')} | seeds: {manifest.get('seeds')}"
        ),
        (
            f"> Coherence judge: "
            f"{'LLM with per-case rule fallback' if use_llm else 'rule engine'}"
        ),
        (
            f"> Pilot reference: recorded Phase 4.1 observations "
            f"(source: {pilot.get('source', 'n/a')})"
        ),
        "",
        "## 1. Mean ± Std across seeds (per configuration)",
        "",
        "| config | metric | mean | std |",
        "|---|---|---|---|",
    ]
    per_config_values: dict[str, dict[str, list[float]]] = {}
    for config in CONFIG_ORDER:
        per_config_values[config] = {
            metric: [] for metric in METRICS
        }
        for seed in seeds:
            records = grouped.get((seed, config), [])
            if not records:
                continue
            aggregate = aggregate_scored(
                [index[_record_key(record)] for record in records]
            )
            for metric in METRICS:
                per_config_values[config][metric].append(aggregate[metric])
    for config in CONFIG_ORDER:
        for metric in METRICS:
            values = per_config_values[config][metric]
            lines.append(
                f"| {config} | {metric} | {_mean(values):.4f} | "
                f"{_std(values):.4f} |"
            )

    if group_by == "difficulty_category":
        lines += [
            "",
            "## 1b. Per-difficulty breakdown (Mean ± Std across seeds)",
            "",
            "| config | difficulty | metric | mean | std |",
            "|---|---|---|---|---|",
        ]
        for config in CONFIG_ORDER:
            for difficulty in (1, 2, 3):
                per_metric_values: dict[str, list[float]] = {
                    metric: [] for metric in METRICS
                }
                for seed in seeds:
                    records = [
                        record
                        for record in grouped.get((seed, config), [])
                        if int(record.get("difficulty", -1)) == difficulty
                    ]
                    if not records:
                        continue
                    aggregate = aggregate_scored(
                        [index[_record_key(record)] for record in records]
                    )
                    for metric in METRICS:
                        per_metric_values[metric].append(
                            aggregate[metric]
                        )
                for metric in METRICS:
                    values = per_metric_values[metric]
                    if not values:
                        continue
                    lines.append(
                        f"| {config} | {difficulty} | {metric} | "
                        f"{_mean(values):.4f} | {_std(values):.4f} |"
                    )

    lines += [
        "",
        "## 2. Empirically observed Full Ranking & Pairwise Dominance",
        "",
        (
            "Metric directions as recorded: accuracy/abstention/coherence "
            "descending, ECE ascending (reference note only, no judgment)."
        ),
        "",
        "| seed | metric | ranking |",
        "|---|---|---|",
    ]
    ranking_per_seed: dict[str, list[list[str]]] = {
        metric: [] for metric in METRICS
    }
    for seed in seeds:
        for metric in METRICS:
            seed_values: dict[str, float] = {}
            for config in CONFIG_ORDER:
                records = grouped.get((seed, config), [])
                if not records:
                    continue
                aggregate = aggregate_scored(
                    [index[_record_key(record)] for record in records]
                )
                seed_values[config] = aggregate[metric]
            ranking = _rank(seed_values, metric=metric)
            ranking_per_seed[metric].append(ranking)
            lines.append(
                f"| run_{seed} | {metric} | {' > '.join(ranking)} |"
            )

    lines += [
        "",
        (
            "Pairwise dominance (number of seeds where the left config wins "
            "per metric):"
        ),
        "",
        "| metric | pair | dominance |",
        "|---|---|---|",
    ]
    pairwise: dict[tuple[str, str, str], int] = {}
    for metric in METRICS:
        for left in CONFIG_ORDER:
            for right in CONFIG_ORDER:
                if left >= right:
                    continue
                wins = 0
                for ranking in ranking_per_seed[metric]:
                    if ranking.index(left) < ranking.index(right):
                        wins += 1
                pairwise[(metric, left, right)] = wins
                lines.append(
                    f"| {metric} | {left} vs {right} | "
                    f"{left} ahead in {wins}/{len(seeds)} seeds |"
                )

    # empirical majority ranking per metric
    if comparison_mode == "within_agent_only":
        lines += [
            "",
            "## 3. Phase 4.1 pilot reference (recorded, informational)",
            "",
            (
                "Comparison mode: within_agent_only — rankings above are "
                "empirically observed within Phase 4.2-R; the pilot "
                "orderings are listed as reference data without match/flip "
                "judgment."
            ),
            "",
            "| metric | pilot observed ranking |",
            "|---|---|",
        ]
        for metric in METRICS:
            pilot_ranking = pilot_rankings.get(metric, [])
            lines.append(
                f"| {metric} | {' > '.join(pilot_ranking) or '-'} |"
            )
    else:
        lines += [
            "",
            "## 3. Phase 4.1 pilot reference comparison (recorded, not judged)",
            "",
            (
                "| metric | pilot observed ranking | Phase 4.2-R majority "
                "ranking | match / flip |"
            ),
            "|---|---|---|---|",
        ]
        for metric in METRICS:
            pilot_ranking = pilot_rankings.get(metric, [])
            majority: list[tuple[int, str]] = []
            for config in CONFIG_ORDER:
                rank_sum = sum(
                    ranking.index(config)
                    for ranking in ranking_per_seed[metric]
                )
                majority.append((rank_sum, config))
            majority_ranking = [
                config for _, config in sorted(majority)
            ]
            match = (
                "match"
                if list(pilot_ranking) == majority_ranking
                else "FLIP"
            )
            lines.append(
                f"| {metric} | {' > '.join(pilot_ranking) or '-'} | "
                f"{' > '.join(majority_ranking)} | {match} |"
            )

    lines += [
        "",
        "## 4. Pilot reference values (Phase 4.1, recorded)",
        "",
        "| config | accuracy | ECE | abstention rate | coherence |",
        "|---|---|---|---|---|",
    ]
    for config in CONFIG_ORDER:
        values = pilot_configs.get(CONFIG_ARM_MAP[config], {})
        lines.append(
            f"| {config} | {values.get('accuracy', '-')} | "
            f"{values.get('ece', '-')} | "
            f"{values.get('abstention_rate', '-')} | "
            f"{values.get('coherence', '-')} |"
        )
    lines += [
        "",
        (
            "_This report records measurements and observed orderings only; "
            "no stability judgment is attached._"
        ),
        "",
    ]
    return "\n".join(lines)


def build_report(
    *,
    input_path: Path,
    pilot_path: Path,
    output_path: Path,
    use_llm: bool,
    comparison_mode: str = "pilot_reference",
    group_by: str = "none",
) -> Path:
    """Load results, aggregate, and write the stability report."""
    data = json.loads(input_path.read_text(encoding="utf-8"))
    results = data.get("results", [])
    manifest = data.get("manifest", {})
    pilot = load_pilot_reference(pilot_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_report(
            results=results,
            manifest=manifest,
            pilot=pilot,
            use_llm=use_llm,
            comparison_mode=comparison_mode,
            group_by=group_by,
        ),
        encoding="utf-8",
    )
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 4.2-R stability report (data only)"
    )
    parser.add_argument(
        "--input",
        default=str(ROOT / "reports" / "phase4_2_real_agent" /
                    "raw_results.json"),
        help="Phase 4.2-R raw results JSON",
    )
    parser.add_argument(
        "--pilot-reference",
        default="phase4_1_pilot_results.json",
        help="Phase 4.1 pilot reference JSON (recorded observations)",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "reports" / "phase4_2_real_agent" /
                    "stability_report.md"),
        help="markdown report path",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        default=True,
        help="judge factor coverage with the LLM when the API key is set "
        "(default; falls back to rules per case)",
    )
    parser.add_argument(
        "--rules-only",
        action="store_true",
        help="force the deterministic rule engine for factor coverage",
    )
    parser.add_argument(
        "--comparison-mode",
        choices=("pilot_reference", "within_agent_only"),
        default="pilot_reference",
        help="pilot_reference adds a match/flip judgment column; "
        "within_agent_only records pilot orderings without judgment",
    )
    parser.add_argument(
        "--group-by",
        choices=("none", "difficulty_category"),
        default="none",
        help="add a per-difficulty (1/2/3) Mean ± Std breakdown "
        "(difficulty_category) or not (none)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    use_llm = args.use_llm and not args.rules_only
    try:
        report = build_report(
            input_path=Path(args.input),
            pilot_path=Path(args.pilot_reference),
            output_path=Path(args.output),
            use_llm=use_llm,
            comparison_mode=args.comparison_mode,
            group_by=args.group_by,
        )
    except (ValueError, OSError) as exc:
        print(f"error: {exc}")
        return 1
    print(f"stability report written -> {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
