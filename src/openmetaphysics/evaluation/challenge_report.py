"""Phase 4 Challenge Evaluation report generator.

Aggregates the per-(arm, case) raw outputs written by
``scripts/run_challenge_evaluation.py`` into the Phase 4 metrics defined in
:mod:`openmetaphysics.evaluation.challenge_scorer`:

- Accuracy — per-case coverage fraction of ``expected_key_factors``
  (:func:`calc_factor_scores`), averaged over the arm.
- ECE — expected calibration error over (confidence, correctness) pairs,
  where a case counts as correct when all key factors are covered.
- Abstention rate — percentage of outputs that abstain
  (:func:`calc_abstention_rate`).
- Reasoning coherence — mean of :func:`calc_reasoning_coherence` (0-3).

Results are written as a Markdown comparison table to
``reports/phase4_evaluation_pilot.md`` (default), plus a per-group breakdown
over the four probe groups (ambiguity / conflicting / incomplete /
multi_step).

Decoupling contract: the report only reads the raw-output JSON files and the
scorer module; it never imports agent or runner code and never mutates
system state.

Usage from the repo root::

    python -m openmetaphysics.evaluation.challenge_report
    python -m openmetaphysics.evaluation.challenge_report --raw-dir data/evaluation/challenge_raw
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from openmetaphysics.evaluation.challenge_scorer import (
    DEFAULT_COHERENCE_MODEL,
    VALID_GROUPS,
    calc_abstention_rate,
    calc_confidence_calibration,
    calc_factor_scores,
)

DEFAULT_RAW_DIR = ROOT / "data" / "evaluation" / "challenge_raw"
DEFAULT_REPORT_PATH = ROOT / "reports" / "phase4_evaluation_pilot.md"


@dataclass(frozen=True)
class CaseResult:
    """One scored case within an arm."""

    arm: str
    arm_label: str
    case_id: str
    group: str
    decision: str
    confidence: float
    coverage: float
    coherence: int
    abstained: bool
    judge_mode: str


@dataclass(frozen=True)
class ArmAggregate:
    """Aggregated Phase 4 metrics for one arm."""

    arm: str
    label: str
    description: str
    n_cases: int
    accuracy: float
    ece: float
    abstention_rate: float
    coherence: float
    judge_modes: dict[str, int]
    by_group: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass(frozen=True)
class ArmSource:
    """One arm's manifest plus its per-case raw outputs."""

    arm: str
    manifest: dict[str, Any]
    cases: list[dict[str, Any]]


def load_raw_results(raw_dir: Path) -> dict[str, ArmSource]:
    """Load per-case raw outputs, keyed by arm name.

    Only directories carrying a ``run_manifest.json`` (written by
    ``scripts/run_challenge_evaluation.py``) are treated as arms; helper
    directories (``_flattened``, runner artifacts) are ignored. Inside an
    arm, top-level ``*.json`` files other than the manifest are case outputs.
    """
    results: dict[str, ArmSource] = {}
    if not raw_dir.exists():
        return results
    for arm_dir in sorted(path for path in raw_dir.iterdir() if path.is_dir()):
        manifest_path = arm_dir / "run_manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cases: list[dict[str, Any]] = []
        for path in sorted(arm_dir.glob("*.json")):
            if path.name == "run_manifest.json":
                continue
            cases.append(json.loads(path.read_text(encoding="utf-8")))
        if cases:
            results[arm_dir.name] = ArmSource(
                arm=arm_dir.name, manifest=manifest, cases=cases
            )
    return results


def score_case(raw: dict[str, Any], *, use_llm: bool) -> CaseResult:
    """Score one raw output against its expected key factors.

    Coverage fraction and the 0-3 coherence are derived from one single
    coverage judgment (:func:`calc_factor_scores`) so both metrics stay
    internally consistent even when the LLM judge falls back to rules.
    """
    factors = list(raw.get("expected_key_factors") or [])
    output = {
        "decision": raw.get("decision", ""),
        "reasoning_trace": raw.get("reasoning_trace", ""),
    }
    if factors:
        coverage, coherence = calc_factor_scores(
            output, factors, use_llm=use_llm
        )
    else:
        coverage, coherence = 0.0, 0
    return CaseResult(
        arm=raw.get("arm", ""),
        arm_label=raw.get("arm_label", ""),
        case_id=raw.get("case_id", ""),
        group=raw.get("group", ""),
        decision=str(raw.get("decision", "")),
        confidence=float(raw.get("confidence", 0.0)),
        coverage=coverage,
        coherence=coherence,
        abstained=bool(
            calc_abstention_rate([{"decision": raw.get("decision", "")}]) > 0
        ),
        judge_mode=str(raw.get("judge_mode", "rules")),
    )


def aggregate_arm(
    source: ArmSource,
    *,
    use_llm: bool,
) -> ArmAggregate:
    """Aggregate the Phase 4 metrics for one arm."""
    arm = source.arm
    cases = source.cases
    manifest = source.manifest
    scored = [score_case(raw, use_llm=use_llm) for raw in cases]
    if not scored:
        return ArmAggregate(
            arm=arm,
            label=manifest.get("label", arm),
            description=str(manifest.get("description", "")),
            n_cases=0,
            accuracy=0.0,
            ece=0.0,
            abstention_rate=0.0,
            coherence=0.0,
            judge_modes={},
        )
    accuracy = sum(case.coverage for case in scored) / len(scored)
    ece = calc_confidence_calibration(
        [
            {
                "decision": case.decision,
                "confidence": case.confidence,
                "correct": case.coverage >= 1.0,
            }
            for case in scored
        ]
    )
    abstention = calc_abstention_rate(
        [{"decision": case.decision} for case in scored]
    )
    coherence = sum(case.coherence for case in scored) / len(scored)
    by_group: dict[str, dict[str, float]] = {}
    for group in VALID_GROUPS:
        grouped = [case for case in scored if case.group == group]
        if not grouped:
            continue
        by_group[group] = {
            "n": float(len(grouped)),
            "accuracy": sum(case.coverage for case in grouped) / len(grouped),
            "ece": calc_confidence_calibration(
                [
                    {
                        "decision": case.decision,
                        "confidence": case.confidence,
                        "correct": case.coverage >= 1.0,
                    }
                    for case in grouped
                ]
            ),
            "abstention": calc_abstention_rate(
                [{"decision": case.decision} for case in grouped]
            ),
            "coherence": sum(case.coherence for case in grouped) / len(grouped),
        }
    return ArmAggregate(
        arm=arm,
        label=scored[0].arm_label or manifest.get("label", arm),
        description=str(manifest.get("description", "")),
        n_cases=len(scored),
        accuracy=round(accuracy, 4),
        ece=round(ece, 4),
        abstention_rate=round(abstention, 2),
        coherence=round(coherence, 4),
        judge_modes=dict(Counter(case.judge_mode for case in scored)),
        by_group=by_group,
    )


def _coherence_judge_note(use_llm: bool) -> str:
    if not use_llm:
        return "rule engine (FACTOR_ALIASES, deterministic)"
    model = (
        os.environ.get("AGRI_AI_COHERENCE_MODEL")
        or os.environ.get("DEEPSEEK_MODEL")
        or DEFAULT_COHERENCE_MODEL
    )
    if os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return f"LLM ({model}) with per-case rule fallback"
    return f"rule engine (FACTOR_ALIASES, deterministic) — LLM ({model}) "
    "requested but DEEPSEEK_API_KEY is empty"


def render_markdown(
    aggregates: list[ArmAggregate],
    *,
    raw_dir: Path,
    use_llm: bool,
) -> str:
    """Render the pilot comparison report as Markdown."""
    lines: list[str] = [
        "# Phase 4 Evaluation Pilot — Architecture Impact on Challenge Tasks",
        "",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        f"> Raw outputs: `{raw_dir}`",
        f"> Coherence judge: {_coherence_judge_note(use_llm)}",
        "",
        "## Configurations",
        "",
        "| configuration | description |",
        "|---|---|",
    ]
    for agg in aggregates:
        lines.append(f"| {agg.label} (`{agg.arm}`) | {agg.description} |")
    lines += [
        "",
        "## Aggregate Results",
        "",
        (
            "| configuration | n | accuracy (factor coverage) | ECE ↓ | "
            "abstention rate | coherence (0-3) |"
        ),
        "|---|---|---|---|---|---|",
    ]
    for agg in aggregates:
        lines.append(
            f"| {agg.label} (`{agg.arm}`) | {agg.n_cases} | "
            f"{agg.accuracy:.4f} | {agg.ece:.4f} | "
            f"{agg.abstention_rate:.2f}% | {agg.coherence:.4f} |"
        )
    lines += [
        "",
        "## Per-Group Breakdown",
        "",
        (
            "| configuration | group | n | accuracy | ECE ↓ | abstention | "
            "coherence |"
        ),
        "|---|---|---|---|---|---|---|",
    ]
    for agg in aggregates:
        for group, metrics in agg.by_group.items():
            lines.append(
                f"| {agg.label} (`{agg.arm}`) | {group} | "
                f"{int(metrics['n'])} | {metrics['accuracy']:.4f} | "
                f"{metrics['ece']:.4f} | {metrics['abstention']:.2f}% | "
                f"{metrics['coherence']:.4f} |"
            )
    lines += [
        "",
        "## Judge Mode Distribution",
        "",
        "| configuration | judge_mode -> count |",
        "|---|---|",
    ]
    for agg in aggregates:
        modes = ", ".join(
            f"{mode}={count}" for mode, count in sorted(agg.judge_modes.items())
        )
        lines.append(f"| {agg.label} (`{agg.arm}`) | {modes} |")
    lines += [
        "",
        "## Interpretation Guide",
        "",
        (
            "- C1 在任一维度显著优于 C0 → 证据支持 ACIS 架构优势"
            "（补全 Phase 3 饱和结论）。"
        ),
        "- 仅 ECE / 弃权率有差异 → 强调决策质量收益而非准确率收益。",
        "- 全无差异 → 建议进入 Phase 6（架构重设计），不再增加工程复杂度。",
        (
            "- 注意：abstention rate 在 incomplete 组为期望行为"
            "（正确弃权），数值高并不等于性能差；需结合准确率解读。"
        ),
        "",
    ]
    return "\n".join(lines)


def build_report(
    raw_dir: Path = DEFAULT_RAW_DIR,
    output_path: Path = DEFAULT_REPORT_PATH,
    *,
    use_llm: bool = True,
) -> Path:
    """Aggregate all arms in ``raw_dir`` and write the Markdown report."""
    results = load_raw_results(raw_dir)
    if not results:
        raise ValueError(f"no raw challenge outputs found under {raw_dir}")
    aggregates = [
        aggregate_arm(source, use_llm=use_llm)
        for source in sorted(results.values(), key=lambda s: s.arm)
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_markdown(aggregates, raw_dir=raw_dir, use_llm=use_llm),
        encoding="utf-8",
    )
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 4 Challenge Evaluation report generator"
    )
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help=f"raw output root (default: {DEFAULT_RAW_DIR})",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_REPORT_PATH),
        help=f"markdown report path (default: {DEFAULT_REPORT_PATH})",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    use_llm = args.use_llm and not args.rules_only
    try:
        report = build_report(
            Path(args.raw_dir),
            Path(args.output),
            use_llm=use_llm,
        )
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    print(f"report written -> {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
