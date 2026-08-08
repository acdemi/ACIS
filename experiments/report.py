"""Publication-grade report generator (Phase 2.1E -> 2.2, Sprint 06).

Assembles a Markdown research report for an archived experiment from its
:class:`~experiments.analysis.AnalysisResult` and generated figures. Statistical
tables are emitted as LaTeX ``tabular`` blocks (copy-pasteable into a paper)
with bootstrap effect-size estimates, 95% confidence intervals, and
significance markers; figures are embedded by relative path.

Principle: *effect size before p-value, reproduction before aesthetics*. The
report always states Δ with its CI alongside any p-value. No frozen module is
modified; this module only reads the manifest and the analysis result.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments.analysis import AnalysisResult

#: Two-sided bootstrap p-value significance markers.
_SIG_MARKERS: tuple[tuple[float, str], ...] = (
    (0.001, "***"),
    (0.01, "**"),
    (0.05, "*"),
)


def _sig_marker(p_value: float) -> str:
    for threshold, marker in _SIG_MARKERS:
        if p_value < threshold:
            return marker
    return "ns"


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
        .replace("$", "\\$")
    )


def _fmt(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _read_manifest(experiment_dir: Path) -> dict[str, Any]:
    path = experiment_dir / "manifest.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _latex_run_table(result: AnalysisResult) -> str:
    """Per-run statistics as a LaTeX tabular (mean ± std [95% CI])."""
    metric_cols = ("accuracy", "confidence", "planner_usage", "tool_usage", "memory_hits")
    header = ["run", "seeds", "cases", *[c for c in metric_cols]]
    lines = [
        "\\begin{tabular}{l" + "c" * (len(header) - 1) + "}",
        "\\toprule",
        " & ".join(header) + " \\\\",
        "\\midrule",
    ]
    for run in result.runs:
        cells = [_latex_escape(run.name), str(run.n_seeds), str(run.n_cases)]
        for col in metric_cols:
            stats = run.metrics.get(col)
            if stats is None:
                cells.append("--")
            else:
                cells.append(
                    f"${_fmt(stats.mean)} \\pm {_fmt(stats.std)}$ "
                    f"$[{_fmt(stats.ci_low)}, {_fmt(stats.ci_high)}]$"
                )
        lines.append(" & ".join(cells) + " \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    return "\n".join(lines)


def _latex_effect_table(result: AnalysisResult) -> str:
    """Effect-size table as a LaTeX tabular with significance markers."""
    lines = [
        "\\begin{tabular}{llrrrl}",
        "\\toprule",
        "ablated & field & $\\Delta$ & CI low & CI high & sig \\\\",
        "\\midrule",
    ]
    for es in result.effect_sizes:
        marker = _sig_marker(es.p_value)
        lines.append(
            f"{_latex_escape(es.ablated)} & {_latex_escape(es.field)} & "
            f"{_fmt(es.delta)} & {_fmt(es.ci_low)} & {_fmt(es.ci_high)} & "
            f"{marker} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    return "\n".join(lines)


def _capability_markdown(result: AnalysisResult) -> list[str]:
    cap_keys = sorted({cap for run in result.runs for cap in run.capabilities})
    if not cap_keys:
        return []
    lines = [
        "## Capability Summary",
        "",
        "| run | " + " | ".join(cap_keys) + " |",
        "|" + "---|" * (len(cap_keys) + 1),
    ]
    for run in result.runs:
        cells = [run.name]
        for cap in cap_keys:
            stats = run.capabilities.get(cap)
            cells.append(_fmt(stats.mean) if stats else "-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def generate_report(
    experiment_dir: str | Path,
    result: AnalysisResult,
    figure_paths: list[Path],
) -> Path:
    """Write ``RESEARCH_REPORT.md`` into the experiment directory."""
    exp = Path(experiment_dir)
    manifest = _read_manifest(exp)
    git = manifest.get("git") or {}
    lines: list[str] = []

    lines.append(f"# Research Report: {result.experiment_name or exp.name}")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Experiment: `{result.experiment_name}`")
    lines.append(f"- Directory: `{exp}`")
    lines.append(f"- Dataset: `{manifest.get('dataset', '-')}`")
    lines.append(f"- Dataset SHA-256: `{manifest.get('dataset_sha256', '-')}`")
    lines.append(f"- Git: `{git.get('short', '-')}` ({git.get('branch', '-')})")
    lines.append(f"- Python: `{manifest.get('python', '-')}`")
    lines.append(f"- Baseline: `{result.baseline}`")
    lines.append(f"- Runs analysed: {len(result.runs)}")
    lines.append("")

    lines.append("## Run Statistics (LaTeX)")
    lines.append("")
    lines.append("Mean ± std with 95% bootstrap CI (1000 resamples). "
                 "Multi-seed runs aggregate at the seed level.")
    lines.append("")
    lines.append("```latex")
    lines.append(_latex_run_table(result))
    lines.append("```")
    lines.append("")

    cap_lines = _capability_markdown(result)
    lines.extend(cap_lines)

    lines.append("## Effect Sizes (LaTeX)")
    lines.append("")
    lines.append("$\\Delta = \\mathrm{baseline} - \\mathrm{ablated}$ with 95% bootstrap CI "
                 "and two-sided bootstrap p-value. Significance: "
                 "`*` p<0.05, `**` p<0.01, `***` p<0.001, `ns` not significant.")
    lines.append("")
    lines.append("```latex")
    lines.append(_latex_effect_table(result))
    lines.append("```")
    lines.append("")

    if result.module_capability:
        lines.append("## Module × Capability Association (mean Δ)")
        lines.append("")
        modules = sorted(result.module_capability)
        caps = sorted({c for m in result.module_capability.values() for c in m})
        header = ["module", *caps]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * len(header))
        for module in modules:
            cells = [module, *(_fmt(result.module_capability[module].get(c)) for c in caps)]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    if figure_paths:
        lines.append("## Figures")
        lines.append("")
        titles = {
            "ablation_capability_impact.png": "Figure 1: Ablation Capability Impact / 消融能力影响",
            "capability_radar.png": "Figure 2: Capability Radar / 能力雷达",
            "calibration_curve.png": "Figure 3: Calibration Curve / 校准曲线",
            "comparison_heatmap.png": "Figure 4: Comparison Heatmap / 对比热力图",
        }
        for fig in figure_paths:
            rel = fig.relative_to(exp) if fig.is_absolute() else fig
            name = Path(fig).name
            lines.append(f"### {titles.get(name, name)}")
            lines.append("")
            lines.append(f"![{name}]({rel.as_posix()})")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("> 设计原则：可信度优先于完整度，效应量优先于 p 值，复现优先于美观。")
    lines.append("> Design principle: credibility over completeness, effect size over p-value, reproduction over aesthetics.")

    report_path = exp / "RESEARCH_REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


__all__ = ["generate_report"]