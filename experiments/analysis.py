"""Statistical analysis engine (Phase 2.1E -> 2.2, Sprint 06).

Turns archived experiment results into publication-grade statistics: per-run
mean / std / 95% bootstrap CI, ablation effect sizes (Δ = baseline − ablated)
with bootstrap confidence intervals and p-values, multi-seed aggregation, and
a module×capability association matrix.

Design follows the sprint principle *effect size before p-value, reproduction
before aesthetics*. Every number is derived from the per-case ``metrics.csv``
rows archived by the frozen runner, so it traces back to the original Traces.
Multi-seed runs (identical module toggles, different seeds) are aggregated at
the seed level: the unit of replication is the seed when several are present,
otherwise the case. No frozen module is modified; this module only *reads*
archives and ``evals`` outputs.
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

#: Per-case core metric columns read from ``metrics.csv`` (capability columns
#: are discovered dynamically and prefixed with ``capability_``).
CORE_METRICS: tuple[str, ...] = (
    "accuracy",
    "confidence",
    "runtime_seconds",
    "planner_usage",
    "tool_usage",
    "memory_hits",
    "debate_rounds",
)

#: Core metrics also reported as effect sizes (capabilities are always included).
EFFECT_METRICS: tuple[str, ...] = ("accuracy", "confidence")

#: Trailing aggregate row written by ``evals.report`` that is not a real case.
_AGGREGATE_CASE_ID = "__aggregate__"

_CAPABILITY_PREFIX = "capability_"

#: Significance thresholds (two-sided bootstrap p-value).
_SIG_LEVELS: tuple[tuple[str, float], ...] = (
    ("***", 0.001),
    ("**", 0.01),
    ("*", 0.05),
)


@dataclass(frozen=True)
class MetricStats:
    """Point estimate, dispersion, and 95% bootstrap CI for one metric."""

    mean: float
    std: float
    ci_low: float
    ci_high: float
    n: int


@dataclass(frozen=True)
class RunAnalysis:
    """Aggregated statistics for one module configuration (possibly multi-seed)."""

    name: str
    toggles: dict[str, bool]
    n_seeds: int
    n_cases: int
    metrics: dict[str, MetricStats]
    capabilities: dict[str, MetricStats]
    is_baseline: bool


@dataclass(frozen=True)
class EffectSize:
    """Δ = baseline − ablated for one metric/capability, with inference."""

    ablated: str
    field: str
    delta: float
    ci_low: float
    ci_high: float
    p_value: float
    significant: bool


@dataclass(frozen=True)
class AnalysisResult:
    """Full statistical analysis of one archived experiment."""

    experiment_dir: str
    experiment_name: str
    baseline: str
    runs: tuple[RunAnalysis, ...]
    effect_sizes: tuple[EffectSize, ...]
    module_capability: dict[str, dict[str, float]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# numeric helpers
# ---------------------------------------------------------------------------


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def sample_std(values: list[float]) -> float:
    """Sample standard deviation (ddof=1); 0.0 for fewer than two values."""
    n = len(values)
    if n < 2:
        return 0.0
    mu = sum(values) / n
    var = sum((v - mu) ** 2 for v in values) / (n - 1)
    return var ** 0.5


def bootstrap_mean_ci(
    sample: list[float],
    *,
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Return ``(mean, ci_low, ci_high)`` for the mean of ``sample``.

    Uses the percentile bootstrap with ``n_resamples`` resamples. A degenerate
    sample (0 or 1 point) returns the point estimate with a zero-width CI.
    """
    n = len(sample)
    if n == 0:
        return 0.0, 0.0, 0.0
    point = sum(sample) / n
    if n == 1:
        return point, point, point
    rng = random.Random(seed)
    means = [
        sum(sample[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(n_resamples)
    ]
    means.sort()
    alpha = (1.0 - confidence) / 2.0
    lo = means[int(alpha * n_resamples)]
    hi = means[int((1.0 - alpha) * n_resamples)]
    return point, lo, hi


def _bootstrap_difference(
    baseline: list[float],
    ablated: list[float],
    *,
    n_resamples: int = 1000,
    seed: int = 0,
) -> list[float]:
    """Bootstrap distribution of ``mean(baseline) - mean(ablated)``."""
    nb, na = len(baseline), len(ablated)
    if nb == 0 or na == 0:
        return []
    rng = random.Random(seed)
    diffs: list[float] = []
    for _ in range(n_resamples):
        b = sum(baseline[rng.randrange(nb)] for _ in range(nb)) / nb
        a = sum(ablated[rng.randrange(na)] for _ in range(na)) / na
        diffs.append(b - a)
    diffs.sort()
    return diffs


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    k = round((pct / 100.0) * (len(sorted_vals) - 1))
    return sorted_vals[k]


def _significance(p_value: float) -> str:
    for label, threshold in _SIG_LEVELS:
        if p_value < threshold:
            return label
    return "ns"


# ---------------------------------------------------------------------------
# archive reading
# ---------------------------------------------------------------------------


def load_run_cases(run_dir: str | Path) -> list[dict[str, str]]:
    """Parse a run's ``metrics.csv`` into per-case dicts (skipping the aggregate row)."""
    path = Path(run_dir) / "metrics.csv"
    if not path.exists():
        return []
    cases: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("case_id") == _AGGREGATE_CASE_ID:
                continue
            cases.append(row)
    return cases


def _numeric_values(cases: list[dict[str, str]], key: str) -> list[float]:
    values: list[float] = []
    for case in cases:
        raw = case.get(key)
        if raw is None or raw == "":
            continue
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            continue
    return values


def _capability_columns(cases: list[dict[str, str]]) -> list[str]:
    keys: set[str] = set()
    for case in cases:
        for key in case:
            if key.startswith(_CAPABILITY_PREFIX):
                keys.add(key)
    return sorted(keys)


def _capability_name(column: str) -> str:
    return column.removeprefix(_CAPABILITY_PREFIX)


def _read_manifest(experiment_dir: str | Path) -> dict[str, Any]:
    path = Path(experiment_dir) / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"manifest.json not found in {experiment_dir}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return data


def _collect_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for run in manifest.get("runs", []) or []:
        if isinstance(run, dict):
            entries.append(run)
    ablation = manifest.get("ablation") or {}
    for combo in ablation.get("combos", []) or []:
        if isinstance(combo, dict):
            entries.append(combo)
    return entries


def _toggles_key(toggles: Any) -> tuple[tuple[str, bool], ...]:
    if not isinstance(toggles, dict):
        return ()
    return tuple(sorted((str(k), bool(v)) for k, v in toggles.items()))


def _combo_name(toggles: Any) -> str:
    """Derive a stable combo name from module toggles (e.g. ``no_memory``)."""
    if not isinstance(toggles, dict) or not toggles:
        return "all_on"
    off = sorted(k for k, v in toggles.items() if not v)
    return "all_on" if not off else "no_" + "_".join(off)


def _find_metrics_csv(experiment_dir: Path, entry: dict[str, Any]) -> Path | None:
    """Locate the metrics.csv for a manifest run/ablation entry."""
    candidates: list[Path] = []
    output_dir = entry.get("output_dir")
    name = entry.get("name")
    if output_dir:
        candidates.append(Path(output_dir) / "metrics.csv")
    if name:
        candidates.append(experiment_dir / "runs" / str(name) / "metrics.csv")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# core analysis
# ---------------------------------------------------------------------------


def _group_stats(
    per_run_cases: list[list[dict[str, str]]],
    *,
    n_resamples: int,
    seed: int,
) -> tuple[dict[str, MetricStats], dict[str, MetricStats], dict[str, list[float]]]:
    """Compute per-field stats for one group; return (metrics, capabilities, samples)."""
    all_cases = [case for run in per_run_cases for case in run]
    cap_columns = _capability_columns(all_cases)
    fields = list(CORE_METRICS) + cap_columns
    metrics: dict[str, MetricStats] = {}
    capabilities: dict[str, MetricStats] = {}
    samples: dict[str, list[float]] = {}
    for field_name in fields:
        per_run_means = [
            m for m in (_mean(_numeric_values(run, field_name)) for run in per_run_cases)
            if m is not None
        ]
        all_values = _numeric_values(all_cases, field_name)
        sample = per_run_means if len(per_run_means) >= 2 else all_values
        sample_key = field_name if field_name in CORE_METRICS else _capability_name(field_name)
        samples[sample_key] = sample
        point = sum(sample) / len(sample) if sample else 0.0
        std = sample_std(sample)
        _, ci_low, ci_high = bootstrap_mean_ci(
            sample, n_resamples=n_resamples, seed=seed
        )
        stats = MetricStats(mean=point, std=std, ci_low=ci_low, ci_high=ci_high, n=len(sample))
        if field_name in CORE_METRICS:
            metrics[field_name] = stats
        else:
            capabilities[_capability_name(field_name)] = stats
    return metrics, capabilities, samples


def analyze_experiment(
    experiment_dir: str | Path,
    *,
    n_resamples: int = 1000,
    seed: int = 0,
) -> AnalysisResult:
    """Analyze an archived experiment: per-run stats, effect sizes, associations."""
    exp = Path(experiment_dir)
    manifest = _read_manifest(exp)
    entries = _collect_entries(manifest)

    groups: dict[tuple[tuple[str, bool], ...], list[dict[str, Any]]] = {}
    for entry in entries:
        groups.setdefault(_toggles_key(entry.get("toggles")), []).append(entry)

    run_analyses: list[RunAnalysis] = []
    samples_by_combo: dict[str, dict[str, list[float]]] = {}
    cap_columns: set[str] = set()
    for members in groups.values():
        toggles = members[0].get("toggles") or {}
        combo = _combo_name(toggles)
        is_baseline = bool(toggles) and all(bool(v) for v in toggles.values())
        per_run_cases: list[list[dict[str, str]]] = []
        for member in members:
            csv_path = _find_metrics_csv(exp, member)
            per_run_cases.append(load_run_cases(csv_path.parent) if csv_path else [])
        metrics, capabilities, samples = _group_stats(
            per_run_cases, n_resamples=n_resamples, seed=seed
        )
        cap_columns.update(capabilities.keys())
        all_cases = [case for run in per_run_cases for case in run]
        run_analyses.append(
            RunAnalysis(
                name=combo,
                toggles=dict(toggles),
                n_seeds=len(members),
                n_cases=len(all_cases),
                metrics=metrics,
                capabilities=capabilities,
                is_baseline=is_baseline,
            )
        )
        samples_by_combo[combo] = samples

    baseline_ra = next((r for r in run_analyses if r.is_baseline), None)
    baseline = baseline_ra.name if baseline_ra else (run_analyses[0].name if run_analyses else "")
    baseline_samples = samples_by_combo.get(baseline, {})

    effect_fields = list(EFFECT_METRICS) + sorted(cap_columns)
    effect_sizes: list[EffectSize] = []
    for ra in run_analyses:
        if ra.name == baseline or not baseline_samples:
            continue
        ablated_samples = samples_by_combo.get(ra.name, {})
        for field_name in effect_fields:
            base_vals = baseline_samples.get(field_name, [])
            ablated_vals = ablated_samples.get(field_name, [])
            if not base_vals or not ablated_vals:
                continue
            delta = (sum(base_vals) / len(base_vals)) - (sum(ablated_vals) / len(ablated_vals))
            diffs = _bootstrap_difference(
                base_vals, ablated_vals, n_resamples=n_resamples, seed=seed
            )
            if not diffs:
                continue
            ci_low = _percentile(diffs, 2.5)
            ci_high = _percentile(diffs, 97.5)
            le = sum(1 for d in diffs if d <= 0)
            ge = sum(1 for d in diffs if d >= 0)
            p_value = min(1.0, 2.0 * min(le, ge) / len(diffs))
            effect_sizes.append(
                EffectSize(
                    ablated=ra.name,
                    field=_capability_name(field_name),
                    delta=delta,
                    ci_low=ci_low,
                    ci_high=ci_high,
                    p_value=p_value,
                    significant=p_value < 0.05,
                )
            )

    module_capability = _module_capability_matrix(
        run_analyses, samples_by_combo, baseline, sorted(cap_columns)
    )

    return AnalysisResult(
        experiment_dir=str(exp),
        experiment_name=str(manifest.get("experiment", "")),
        baseline=baseline,
        runs=tuple(run_analyses),
        effect_sizes=tuple(effect_sizes),
        module_capability=module_capability,
    )


def _module_capability_matrix(
    runs: list[RunAnalysis],
    samples_by_combo: dict[str, dict[str, list[float]]],
    baseline: str,
    cap_columns: list[str],
) -> dict[str, dict[str, float]]:
    """Average Δ per capability for each disabled module (capability×module link)."""
    baseline_samples = samples_by_combo.get(baseline, {})
    accumulated: dict[str, dict[str, list[float]]] = {}
    for ra in runs:
        if ra.name == baseline or not baseline_samples:
            continue
        off_modules = [k for k, v in ra.toggles.items() if not v]
        if not off_modules:
            continue
        ablated_samples = samples_by_combo.get(ra.name, {})
        for module in off_modules:
            for column in cap_columns:
                base_vals = baseline_samples.get(column, [])
                ablated_vals = ablated_samples.get(column, [])
                if not base_vals or not ablated_vals:
                    continue
                delta = (sum(base_vals) / len(base_vals)) - (
                    sum(ablated_vals) / len(ablated_vals)
                )
                accumulated.setdefault(module, {}).setdefault(column, []).append(delta)
    matrix: dict[str, dict[str, float]] = {}
    for module, caps in accumulated.items():
        matrix[module] = {
            _capability_name(cap): sum(vals) / len(vals) for cap, vals in caps.items()
        }
    return matrix


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------


def _fmt(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _fmt_stats(stats: MetricStats) -> str:
    return f"{_fmt(stats.mean)} ± {_fmt(stats.std)} [{_fmt(stats.ci_low)}, {_fmt(stats.ci_high)}]"


def result_to_json(result: AnalysisResult) -> dict[str, Any]:
    """Serialize an :class:`AnalysisResult` to a JSON-friendly mapping."""
    return {
        "experiment_dir": result.experiment_dir,
        "experiment_name": result.experiment_name,
        "baseline": result.baseline,
        "runs": [asdict(run) for run in result.runs],
        "effect_sizes": [asdict(es) for es in result.effect_sizes],
        "module_capability": result.module_capability,
    }


def format_analysis_markdown(result: AnalysisResult) -> str:
    """Render the analysis as a Markdown report (mean ± std [95% CI] tables)."""
    lines: list[str] = []
    lines.append(f"# Analysis: {result.experiment_name or result.experiment_dir}")
    lines.append("")
    lines.append(f"- Baseline: `{result.baseline}`")
    lines.append(f"- Runs analysed: {len(result.runs)}")
    lines.append(f"- Effect sizes: {len(result.effect_sizes)}")
    lines.append("")

    metric_cols = ("accuracy", "confidence", "planner_usage", "tool_usage", "memory_hits", "debate_rounds")
    lines.append("## Run Statistics (mean ± std [95% CI])")
    lines.append("")
    header = ["run", "seeds", "cases", *[c for c in metric_cols]]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for run in result.runs:
        cells = [run.name, str(run.n_seeds), str(run.n_cases)]
        cells.extend(_fmt_stats(run.metrics.get(c, MetricStats(0, 0, 0, 0, 0))) for c in metric_cols)
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    cap_keys: list[str] = sorted({cap for run in result.runs for cap in run.capabilities})
    if cap_keys:
        lines.append("## Capability Statistics (mean ± std [95% CI])")
        lines.append("")
        header = ["run", *cap_keys]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for run in result.runs:
            cells = [run.name]
            cells.extend(_fmt_stats(run.capabilities.get(c, MetricStats(0, 0, 0, 0, 0))) for c in cap_keys)
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    if result.effect_sizes:
        lines.append("## Effect Sizes (Δ = baseline − ablated)")
        lines.append("")
        lines.append("| ablated | field | Δ | 95% CI | p | sig |")
        lines.append("|---|---|---|---|---|---|")
        for es in result.effect_sizes:
            ci = f"[{_fmt(es.ci_low)}, {_fmt(es.ci_high)}]"
            lines.append(
                f"| {es.ablated} | {es.field} | {_fmt(es.delta)} | {ci} | "
                f"{es.p_value:.3f} | {_significance(es.p_value)} |"
            )
        lines.append("")

    if result.module_capability:
        lines.append("## Module × Capability Association (mean Δ)")
        lines.append("")
        modules = sorted(result.module_capability)
        caps = sorted({c for m in result.module_capability.values() for c in m})
        header = ["module", *caps]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for module in modules:
            cells = [module]
            cells.extend(_fmt(result.module_capability[module].get(c)) for c in caps)
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "AnalysisResult",
    "EffectSize",
    "MetricStats",
    "RunAnalysis",
    "analyze_experiment",
    "bootstrap_mean_ci",
    "format_analysis_markdown",
    "load_run_cases",
    "result_to_json",
    "sample_std",
]