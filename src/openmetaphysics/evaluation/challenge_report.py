"""Phase 4 Challenge Evaluation report generator.

Aggregates the per-(arm, case) raw outputs written by
``scripts/run_challenge_evaluation.py`` into the Phase 4 metrics defined in
:mod:`openmetaphysics.evaluation.challenge_scorer`:

- Label accuracy — final Judge decision vs the case ``ground_truth``.
- Factor coverage — fraction of ``expected_key_factors`` explicit in the
  final user-visible decision, reasoning, and structured action plan.
- Factor coverage level — the historical 0-3 quantization of coverage; this is
  not a logical-consistency metric.
- Label ECE and factor ECE — confidence calibration against label correctness
  and full-factor coverage respectively.
- Abstention behaviour — overall rate plus correct-abstention and
  false-abstention conditional rates.
- Judge fallback rate — execution reliability, reported independently from
  model quality.

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

from decision_semantics import decision_correctness, is_abstention
from openmetaphysics.evaluation.challenge_scorer import (
    DEFAULT_COHERENCE_MODEL,
    VALID_GROUPS,
    calc_confidence_calibration,
    calc_factor_scores,
)

DEFAULT_RAW_DIR = ROOT / "data" / "evaluation" / "challenge_raw"
DEFAULT_REPORT_PATH = ROOT / "reports" / "phase4_evaluation_pilot.md"


@dataclass(frozen=True)
class CaseResult:
    """One scored case within an arm.

    Label correctness and factor coverage are deliberately separate fields.
    ``None`` means the corresponding metric could not be computed from valid
    input; it does not mean zero performance.
    """

    arm: str
    arm_label: str
    case_id: str
    group: str
    ground_truth: str | None
    decision: str
    confidence: float | None
    label_correct: bool | None
    factor_coverage: float | None
    factor_coverage_level: int | None
    abstained: bool | None
    expected_abstention: bool | None
    judge_mode: str | None
    fallback_state: bool | None
    fallback_reason: str | None


@dataclass(frozen=True)
class ArmAggregate:
    """Aggregated Phase 4 metrics for one arm."""

    arm: str
    label: str
    description: str
    n_cases: int
    label_scored: int
    factor_scored: int
    label_accuracy: float | None
    factor_coverage: float | None
    factor_coverage_level: float | None
    label_ece: float | None
    factor_ece: float | None
    abstention_rate: float | None
    correct_abstention_rate: float | None
    false_abstention_rate: float | None
    judge_fallback_rate: float | None
    judge_fallback_known: int
    judge_fallback_unknown: int
    judge_modes: dict[str, int]
    fallback_reasons: dict[str, int]
    by_group: dict[str, dict[str, float | int | None]] = field(default_factory=dict)


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


def _fallback_state(
    raw: dict[str, Any],
    *,
    llm_requested: bool | None,
) -> tuple[bool | None, str | None]:
    """Classify Judge fallback without mapping unknown legacy data to success."""
    runtime = raw.get("judge_runtime") or {}
    outcome = runtime.get("outcome")
    reason = runtime.get("fallback_reason_code")
    if outcome == "fallback":
        return True, reason or "unknown"
    if outcome in {"success", "rules"}:
        return False, None
    mode = raw.get("judge_mode")
    if llm_requested is True:
        if mode == "rules":
            return True, "legacy_inferred_rules_fallback"
        if mode == "deepseek":
            return False, None
    if llm_requested is False and mode == "rules":
        return False, None
    return None, None


def score_case(
    raw: dict[str, Any],
    *,
    use_llm: bool,
    llm_requested: bool | None = None,
) -> CaseResult:
    """Score one raw output under the Phase 4 metric contract."""
    factors = list(raw.get("expected_key_factors") or [])
    decision = str(raw.get("decision") or "")
    reasoning_present = bool(
        decision.strip()
        or str(raw.get("reasoning_trace") or "").strip()
        or str(raw.get("summary") or "").strip()
        or any(
            isinstance(item, str) and item.strip()
            for item in (raw.get("action_plan") or [])
        )
    )
    output = {
        "decision": decision,
        "reasoning_trace": raw.get("reasoning_trace", ""),
        "summary": raw.get("summary", ""),
        "action_plan": raw.get("action_plan", []),
    }
    if factors and reasoning_present:
        factor_coverage, factor_level = calc_factor_scores(
            output, factors, use_llm=use_llm
        )
    else:
        factor_coverage, factor_level = None, None

    ground_truth = raw.get("ground_truth")
    label_correct = (
        decision_correctness(str(ground_truth), decision)
        if ground_truth is not None and decision
        else None
    )
    expected_abstention = (
        str(ground_truth) in {"证据不足", "ABSTAIN"}
        if ground_truth is not None
        else None
    )
    abstained = is_abstention(decision) if decision else None
    confidence_value = raw.get("confidence")
    try:
        confidence = float(confidence_value) if confidence_value is not None else None
    except (TypeError, ValueError):
        confidence = None
    fallback_state, fallback_reason = _fallback_state(
        raw, llm_requested=llm_requested
    )
    return CaseResult(
        arm=raw.get("arm", ""),
        arm_label=raw.get("arm_label", ""),
        case_id=raw.get("case_id", ""),
        group=raw.get("group", ""),
        ground_truth=str(ground_truth) if ground_truth is not None else None,
        decision=decision,
        confidence=confidence,
        label_correct=label_correct,
        factor_coverage=factor_coverage,
        factor_coverage_level=factor_level,
        abstained=abstained,
        expected_abstention=expected_abstention,
        judge_mode=str(raw["judge_mode"]) if raw.get("judge_mode") else None,
        fallback_state=fallback_state,
        fallback_reason=fallback_reason,
    )


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _conditional_rate(rows: list[bool]) -> float | None:
    return round(100.0 * sum(1 for value in rows if value) / len(rows), 2) if rows else None


def _calibration(
    cases: list[CaseResult],
    *,
    domain: str,
) -> float | None:
    pairs: list[dict[str, Any]] = []
    for case in cases:
        if case.confidence is None:
            continue
        if domain == "label" and case.label_correct is not None:
            correct = case.label_correct
        elif domain == "factor" and case.factor_coverage is not None:
            correct = case.factor_coverage >= 1.0
        else:
            continue
        pairs.append(
            {"decision": case.decision, "confidence": case.confidence, "correct": correct}
        )
    return calc_confidence_calibration(pairs) if pairs else None


def _aggregate_group(cases: list[CaseResult]) -> dict[str, float | int | None]:
    label_values = [case.label_correct for case in cases if case.label_correct is not None]
    factor_values = [
        case.factor_coverage for case in cases if case.factor_coverage is not None
    ]
    level_values = [
        case.factor_coverage_level
        for case in cases
        if case.factor_coverage_level is not None
    ]
    abstention_values = [case.abstained for case in cases if case.abstained is not None]
    expected_abstain = [
        case.abstained
        for case in cases
        if case.expected_abstention is True and case.abstained is not None
    ]
    expected_diagnosis = [
        case.abstained
        for case in cases
        if case.expected_abstention is False and case.abstained is not None
    ]
    return {
        "n": len(cases),
        "label_scored": len(label_values),
        "factor_scored": len(factor_values),
        "label_accuracy": _mean([1.0 if value else 0.0 for value in label_values]),
        "factor_coverage": _mean([float(value) for value in factor_values]),
        "factor_coverage_level": _mean([float(value) for value in level_values]),
        "label_ece": _calibration(cases, domain="label"),
        "factor_ece": _calibration(cases, domain="factor"),
        "abstention_rate": _conditional_rate(
            [bool(value) for value in abstention_values]
        ),
        "correct_abstention_rate": _conditional_rate(
            [bool(value) for value in expected_abstain]
        ),
        "false_abstention_rate": _conditional_rate(
            [bool(value) for value in expected_diagnosis]
        ),
    }


def aggregate_arm(
    source: ArmSource,
    *,
    use_llm: bool,
) -> ArmAggregate:
    """Aggregate the Phase 4 metrics for one arm."""
    arm = source.arm
    cases = source.cases
    manifest = source.manifest
    llm_requested = manifest.get("use_llm_judge")
    llm_requested = bool(llm_requested) if llm_requested is not None else None
    scored = [
        score_case(raw, use_llm=use_llm, llm_requested=llm_requested)
        for raw in cases
    ]
    aggregate = _aggregate_group(scored)
    fallback_known = [case.fallback_state for case in scored if case.fallback_state is not None]
    fallback_rate = _conditional_rate([bool(value) for value in fallback_known])
    reasons: dict[str, int] = {}
    for case in scored:
        if case.fallback_state and case.fallback_reason:
            reasons[case.fallback_reason] = reasons.get(case.fallback_reason, 0) + 1
    by_group: dict[str, dict[str, float | int | None]] = {}
    for group in VALID_GROUPS:
        grouped = [case for case in scored if case.group == group]
        if grouped:
            by_group[group] = _aggregate_group(grouped)
    return ArmAggregate(
        arm=arm,
        label=scored[0].arm_label if scored else manifest.get("label", arm),
        description=str(manifest.get("description", "")),
        n_cases=len(scored),
        label_scored=int(aggregate["label_scored"] or 0),
        factor_scored=int(aggregate["factor_scored"] or 0),
        label_accuracy=aggregate["label_accuracy"],
        factor_coverage=aggregate["factor_coverage"],
        factor_coverage_level=aggregate["factor_coverage_level"],
        label_ece=aggregate["label_ece"],
        factor_ece=aggregate["factor_ece"],
        abstention_rate=aggregate["abstention_rate"],
        correct_abstention_rate=aggregate["correct_abstention_rate"],
        false_abstention_rate=aggregate["false_abstention_rate"],
        judge_fallback_rate=fallback_rate,
        judge_fallback_known=len(fallback_known),
        judge_fallback_unknown=len(scored) - len(fallback_known),
        judge_modes=dict(Counter(case.judge_mode for case in scored if case.judge_mode)),
        fallback_reasons=reasons,
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


def _fmt(value: float | None, digits: int = 4) -> str:
    return "–" if value is None else f"{float(value):.{digits}f}"


def _fmt_pct(value: float | None) -> str:
    return "–" if value is None else f"{value:.2f}%"


def render_markdown(
    aggregates: list[ArmAggregate],
    *,
    raw_dir: Path,
    use_llm: bool,
) -> str:
    """Render separate label, factor, calibration, abstention, reliability tables."""
    lines: list[str] = [
        "# Phase 4 Evaluation Pilot — Architecture Impact on Challenge Tasks",
        "",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        f"> Raw outputs: `{raw_dir}`",
        f"> Factor scorer: {_coherence_judge_note(use_llm)}",
        (
            "> Factor coverage is scored over final user-visible decision fields: "
            "`decision`, `reasoning_trace`, and structured `action_plan`."
        ),
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
        "## Aggregate Metrics",
        "",
        "| configuration | n | label scored | label accuracy | factor scored | factor coverage | factor level (0-3) |",
        "|---|---|---|---|---|---|---|",
    ]
    for agg in aggregates:
        lines.append(
            f"| {agg.label} (`{agg.arm}`) | {agg.n_cases} | "
            f"{agg.label_scored} | {_fmt(agg.label_accuracy)} | "
            f"{agg.factor_scored} | {_fmt(agg.factor_coverage)} | "
            f"{_fmt(agg.factor_coverage_level, 2)} |"
        )

    lines += [
        "",
        "## Calibration and Abstention",
        "",
        "| configuration | label ECE ↓ | factor ECE ↓ | abstention rate | correct abstention rate | false abstention rate |",
        "|---|---|---|---|---|---|",
    ]
    for agg in aggregates:
        lines.append(
            f"| {agg.label} (`{agg.arm}`) | {_fmt(agg.label_ece)} | "
            f"{_fmt(agg.factor_ece)} | {_fmt_pct(agg.abstention_rate)} | "
            f"{_fmt_pct(agg.correct_abstention_rate)} | "
            f"{_fmt_pct(agg.false_abstention_rate)} |"
        )

    lines += [
        "",
        "## Per-Group Breakdown",
        "",
        "| configuration | group | n | label accuracy | factor coverage | factor level | abstention |",
        "|---|---|---|---|---|---|---|",
    ]
    for agg in aggregates:
        for group, metrics in agg.by_group.items():
            lines.append(
                f"| {agg.label} (`{agg.arm}`) | {group} | "
                f"{int(metrics['n'] or 0)} | {_fmt(metrics['label_accuracy'])} | "
                f"{_fmt(metrics['factor_coverage'])} | "
                f"{_fmt(metrics['factor_coverage_level'], 2)} | "
                f"{_fmt_pct(metrics['abstention_rate'])} |"
            )

    lines += [
        "",
        "## Judge Execution Reliability",
        "",
        "| configuration | judge_mode distribution | fallback rate | known | unknown | fallback reasons |",
        "|---|---|---|---|---|---|",
    ]
    for agg in aggregates:
        modes = ", ".join(
            f"{mode}={count}" for mode, count in sorted(agg.judge_modes.items())
        ) or "–"
        reasons = ", ".join(
            f"{reason}={count}" for reason, count in sorted(agg.fallback_reasons.items())
        ) or "–"
        lines.append(
            f"| {agg.label} (`{agg.arm}`) | {modes} | "
            f"{_fmt_pct(agg.judge_fallback_rate)} | {agg.judge_fallback_known} | "
            f"{agg.judge_fallback_unknown} | {reasons} |"
        )

    lines += [
        "",
        "## Interpretation Contract",
        "",
        "- **Label accuracy** answers whether the final decision matches the case ground truth.",
        "- **Factor coverage** answers how many expected diagnostic/action factors are explicit in the final user-visible output.",
        "- **Factor level (0-3)** is a quantized version of factor coverage, not a separate logical-consistency measurement.",
        "- **Label ECE** calibrates confidence against final-label correctness.",
        "- **Factor ECE** calibrates confidence against full expected-factor coverage.",
        "- **Abstention rate** is descriptive; correct and false abstention rates depend on the expected label.",
        "- **Judge fallback rate** measures execution reliability and must be reported separately from model quality.",
        "- Rules fallback decisions remain valid rule-path decisions but must not be attributed to a successful LLM Judge.",
        "- Internal expert trace evidence is not included in factor coverage under this contract; that would be a separate full-trace metric.",
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
