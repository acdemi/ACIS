"""Publication figure generation (Phase 2.1E -> 2.2, Sprint 06).

Renders four standard research figures as PNGs into an experiment's
``figures/`` directory, driven by an :class:`~experiments.analysis.AnalysisResult`:

1. Ablation Capability Impact - grouped bars of Δ per capability per ablation.
2. Capability Radar - 7-axis radar comparing baseline vs ablated configs.
3. Calibration Curve - binned confidence vs observed accuracy.
4. Experiment Comparison Heatmap - runs × capabilities mean-score matrix.

Titles, axis labels, and legends are bilingual (中 / EN). matplotlib is the
only new dependency introduced this sprint; the Agg backend is forced so no
display is required. No frozen module is modified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from experiments.analysis import AnalysisResult, load_run_cases

#: Canonical capability order (matches benchmarks.capabilities.ALL_CAPABILITIES).
CANONICAL_CAPS: tuple[str, ...] = (
    "information_gathering",
    "knowledge_retrieval",
    "conflict_resolution",
    "counterfactual_reasoning",
    "uncertainty_quantification",
    "multi_step_planning",
    "sensor_cross_validation",
)

#: Bilingual short labels for each capability.
_CAP_LABELS: dict[str, str] = {
    "information_gathering": "信息收集 / Info Gathering",
    "knowledge_retrieval": "知识检索 / Knowledge Retrieval",
    "conflict_resolution": "冲突消解 / Conflict Resolution",
    "counterfactual_reasoning": "反事实推理 / Counterfactual",
    "uncertainty_quantification": "不确定性量化 / Uncertainty",
    "multi_step_planning": "多步规划 / Multi-step Planning",
    "sensor_cross_validation": "传感器交叉验证 / Sensor Validation",
}

_FIGURE_NAMES: tuple[str, ...] = (
    "ablation_capability_impact.png",
    "capability_radar.png",
    "calibration_curve.png",
    "comparison_heatmap.png",
)


def _configure_font() -> None:
    """Pick a CJK-capable font when available; never raise."""
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def _cap_label(cap: str) -> str:
    return _CAP_LABELS.get(cap, cap)


def _run_capability_means(run: Any) -> dict[str, float]:
    return {
        cap: float(stats.mean)
        for cap, stats in run.capabilities.items()
    }


def _fig_ablation_impact(result: AnalysisResult, out: Path) -> Path:
    """Grouped bar chart of Δ capability per ablated combo (baseline − ablated)."""
    cap_effects: dict[str, dict[str, float]] = {}
    for es in result.effect_sizes:
        if es.field in {"accuracy", "confidence"}:
            continue
        cap_effects.setdefault(es.ablated, {})[es.field] = float(es.delta)
    if not cap_effects:
        return _write_empty(out, "消融能力影响 Ablation Capability Impact\n(no ablation effect sizes)")
    ablated = sorted(cap_effects)
    caps = sorted({c for vals in cap_effects.values() for c in vals})
    x = np.arange(len(caps))
    width = 0.8 / max(len(ablated), 1)
    fig, ax = plt.subplots(figsize=(max(8, len(caps) * 1.4), 5))
    for i, combo in enumerate(ablated):
        deltas = [cap_effects[combo].get(c, 0.0) for c in caps]
        ax.bar(x + i * width - 0.4 + width / 2, deltas, width, label=combo)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([_cap_label(c) for c in caps], rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Δ 能力分数 / Δ Capability Score")
    ax.set_title("消融能力影响 Ablation Capability Impact")
    ax.legend(title="ablated", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def _fig_capability_radar(result: AnalysisResult, out: Path) -> Path:
    """7-axis radar comparing each run's mean capability profile."""
    caps = [c for c in CANONICAL_CAPS if any(c in r.capabilities for r in result.runs)]
    if not caps:
        return _write_empty(out, "能力雷达 Capability Radar\n(no capability scores)")
    angles = np.linspace(0, 2 * np.pi, len(caps), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})
    for run in result.runs:
        means = _run_capability_means(run)
        values = [max(0.0, min(1.0, means.get(c, 0.0))) for c in caps]
        values += values[:1]
        style = "-" if run.is_baseline else "--"
        width = 2.2 if run.is_baseline else 1.4
        ax.plot(angles, values, style, linewidth=width, label=run.name)
        ax.fill(angles, values, alpha=0.06)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([_cap_label(c) for c in caps], fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_title("能力雷达 Capability Radar", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def _baseline_cases(experiment_dir: Path, result: AnalysisResult) -> list[dict[str, str]]:
    """Load per-case rows for the baseline run (first seed) for calibration."""
    manifest_path = experiment_dir / "manifest.json"
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []
    for run in manifest.get("runs", []) or []:
        if isinstance(run, dict):
            entries.append(run)
    ablation = manifest.get("ablation") or {}
    for combo in ablation.get("combos", []) or []:
        if isinstance(combo, dict):
            entries.append(combo)
    for entry in entries:
        toggles = entry.get("toggles") or {}
        is_baseline = bool(toggles) and all(bool(v) for v in toggles.values())
        if is_baseline or entry.get("name") == result.baseline:
            output_dir = entry.get("output_dir")
            if output_dir:
                cases = load_run_cases(output_dir)
                if cases:
                    return cases
    # fall back to first entry with cases
    for entry in entries:
        output_dir = entry.get("output_dir")
        if output_dir:
            cases = load_run_cases(output_dir)
            if cases:
                return cases
    return []


def _fig_calibration_curve(experiment_dir: Path, result: AnalysisResult, out: Path) -> Path:
    """Binned confidence vs observed accuracy calibration curve."""
    cases = _baseline_cases(experiment_dir, result)
    pairs: list[tuple[float, float]] = []
    for case in cases:
        conf = case.get("confidence")
        acc = case.get("accuracy")
        if conf in (None, "") or acc in (None, ""):
            continue
        try:
            pairs.append((float(conf), float(acc)))
        except (TypeError, ValueError):
            continue
    if not pairs:
        return _write_empty(out, "校准曲线 Calibration Curve\n(no confidence/accuracy data)")
    bins = np.linspace(0, 1, 6)
    centers, observed = [], []
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        in_bin = [a for c, a in pairs if (c >= lo and (c < hi or i == len(bins) - 2))]
        if in_bin:
            centers.append((lo + hi) / 2)
            observed.append(sum(in_bin) / len(in_bin))
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="理想 / Perfect")
    ax.plot(centers, observed, "o-", color="tab:blue", label="观测 / Observed")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("预测置信度 / Predicted Confidence")
    ax.set_ylabel("观测准确率 / Observed Accuracy")
    ax.set_title("置信度校准曲线 Calibration Curve")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def _fig_comparison_heatmap(result: AnalysisResult, out: Path) -> Path:
    """Runs × capabilities heatmap of mean capability scores."""
    caps = [c for c in CANONICAL_CAPS if any(c in r.capabilities for r in result.runs)]
    if not caps or not result.runs:
        return _write_empty(out, "实验对比热力图 Comparison Heatmap\n(no capability scores)")
    matrix = np.array(
        [[stats.mean if (stats := r.capabilities.get(c)) else 0.0 for c in caps] for r in result.runs]
    )
    fig, ax = plt.subplots(figsize=(max(7, len(caps) * 1.1), max(3, len(result.runs) * 0.6 + 1)))
    im = ax.imshow(matrix, vmin=0, vmax=1, aspect="auto", cmap="RdYlGn")
    ax.set_xticks(range(len(caps)))
    ax.set_xticklabels([_cap_label(c) for c in caps], rotation=30, ha="right", fontsize=8)
    ax.set_yticks(range(len(result.runs)))
    ax.set_yticklabels([r.name for r in result.runs], fontsize=9)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="分数 / Score")
    ax.set_title("实验对比热力图 Experiment Comparison Heatmap")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def _write_empty(out: Path, message: str) -> Path:
    """Write a placeholder PNG when there is no data for a figure."""
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def generate_figures(experiment_dir: str | Path, result: AnalysisResult) -> list[Path]:
    """Generate all four standard figures; return their paths in canonical order."""
    _configure_font()
    figs_dir = Path(experiment_dir) / "figures"
    figs_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    paths.append(_fig_ablation_impact(result, figs_dir / _FIGURE_NAMES[0]))
    paths.append(_fig_capability_radar(result, figs_dir / _FIGURE_NAMES[1]))
    paths.append(_fig_calibration_curve(Path(experiment_dir), result, figs_dir / _FIGURE_NAMES[2]))
    paths.append(_fig_comparison_heatmap(result, figs_dir / _FIGURE_NAMES[3]))
    return paths


__all__ = [
    "CANONICAL_CAPS",
    "generate_figures",
]