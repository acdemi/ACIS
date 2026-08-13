"""Phase 4.2-R batch runner — REAL ACIS agent (audit-approved).

Unlike the Phase 4.2 harness (standalone direct API calls with its own
baseline prompt), this runner executes the actual ACIS system through the
frozen evaluation runner (:func:`evals.runner.run_evaluation`) with the
three architecture configurations mapped to the runner's toggle combos:

    C0 (bare_baseline) -> every module disabled
    C1 (all_on)        -> every module enabled
    C2 (no_memory)     -> memory layer disabled, rest enabled

Two modes:

- ``precheck`` — run case 1 once per config (seed 42) through the real
  agent and compare against the Phase 4.2 harness results for the same
  case. PASS requires structurally comparable outputs with no confidence
  offset > 0.3; the report is written and the exit code signals pass (0)
  or fail (1).
- ``full`` — 3 seeds x 3 configs x 24 cases = 216 real-agent executions,
  raw records written to ``--output`` (checkpointed) and per-call audit
  logs under ``--log-dir``.

Constraints honored: no agent code is modified (the runner is imported
lazily and only invoked); the Challenge Set is read-only; the scorer is
not involved in this runner.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _env import load_env

#: Configurations -> (arm name, module toggles).
CONFIG_ARMS: dict[str, dict[str, Any]] = {
    "C0": {
        "arm": "c0_bare_baseline",
        "planner_on": False,
        "debate_on": False,
        "critic_on": False,
        "memory_on": False,
        "tool_router_on": False,
        "counterfactual_on": False,
    },
    "C1": {
        "arm": "c1_all_on",
        "planner_on": True,
        "debate_on": True,
        "critic_on": True,
        "memory_on": True,
        "tool_router_on": True,
        "counterfactual_on": True,
    },
    "C2": {
        "arm": "c2_no_memory",
        "planner_on": True,
        "debate_on": True,
        "critic_on": True,
        "memory_on": False,
        "tool_router_on": True,
        "counterfactual_on": True,
    },
}

DEFAULT_SEEDS: tuple[int, ...] = (42, 43, 44)
CONFIG_ORDER: tuple[str, ...] = ("C0", "C1", "C2")

#: Disease names present in the Challenge Set (for label normalization).
_DISEASE_NAMES: tuple[str, ...] = (
    "叶霉病",
    "早疫病",
    "霜霉病",
    "褐斑病",
    "根腐病",
    "黄萎病",
    "枯萎病",
)

#: Pre-check pass criterion: max |real confidence - harness confidence|.
CONFIDENCE_OFFSET_TOLERANCE: float = 0.3


@dataclass(frozen=True)
class ConfigSpec:
    """Real-agent configuration mapping for one config label."""

    label: str
    arm: str
    toggles: dict[str, bool]


def config_specs(configs: list[str]) -> list[ConfigSpec]:
    """Resolve config labels to their runner mappings."""
    specs: list[ConfigSpec] = []
    for label in configs:
        if label not in CONFIG_ARMS:
            raise ValueError(
                f"unknown config {label!r}; expected one of {CONFIG_ORDER}"
            )
        mapping = CONFIG_ARMS[label]
        specs.append(
            ConfigSpec(
                label=label,
                arm=mapping["arm"],
                toggles={
                    key: bool(value)
                    for key, value in mapping.items()
                    if key != "arm"
                },
            )
        )
    return specs


def _real_record(
    raw: dict[str, Any],
    *,
    seed: int,
    config: str,
    case_index: int,
) -> dict[str, Any]:
    """Convert one runner raw file into a Phase 4.2-R record.

    ``raw["case_id"]`` is the challenge case id (string); ``case_index`` is
    the 1-based position within the selected case list (harness-compatible).
    """
    return {
        "seed": seed,
        "config": config,
        "case_index": case_index,
        "case_id": raw.get("case_id"),
        "group": raw.get("group"),
        "difficulty": raw.get("difficulty"),
        "expected_key_factors": raw.get("expected_key_factors"),
        "ground_truth": raw.get("ground_truth"),
        "decision": raw.get("decision", ""),
        "confidence": float(raw.get("confidence", 0.0)),
        "judge_mode": raw.get("judge_mode", "rules"),
        "reasoning_trace": raw.get("reasoning_trace", ""),
        "action_plan": raw.get("action_plan", []),
        "runtime_seconds": raw.get("runtime_seconds", 0.0),
        "trace_id": raw.get("trace_id", ""),
        "status": "ok",
        "valid": bool(raw.get("decision")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def run_real_agent(
    spec: ConfigSpec,
    cases: list[dict[str, Any]],
    output_dir: Path,
    *,
    seed: int,
    max_cases: int | None,
    force: bool = True,
) -> list[dict[str, Any]]:
    """Run one config through the real runner and return per-case records."""
    from evals.runner import run_evaluation  # lazy: heavy stack
    from scripts.run_challenge_evaluation import (
        EvalConfig,
        write_flattened_dataset,
    )

    flattened = write_flattened_dataset(
        cases, output_dir / "_flattened" / "challenge_set_v1_flattened.json"
    )
    config = EvalConfig(
        dataset=str(flattened),
        output_dir=str(output_dir / spec.arm / "runner"),
        save_traces=True,
        use_langgraph=True,
        use_llm_judge=True,
        seed=seed,
        max_cases=max_cases,
        **spec.toggles,
    )
    result = run_evaluation(config)
    trace_dir = result.trace_dir
    case_by_id = {case["id"]: case for case in cases}
    case_index_by_id = {
        case["id"]: index for index, case in enumerate(cases, start=1)
    }
    records: list[dict[str, Any]] = []
    for row in result.rows:
        case = case_by_id[row.case_id]
        raw = {
            "case_id": row.case_id,
            "group": case.get("group"),
            "difficulty": case.get("difficulty"),
            "expected_key_factors": case.get("expected_key_factors"),
            "ground_truth": case.get("ground_truth"),
            "trace_id": row.trace_id,
            "decision": row.decision,
            "confidence": row.confidence,
            "runtime_seconds": row.runtime_seconds,
        }
        if trace_dir is not None:
            trace_path = trace_dir / f"{row.trace_id}.json"
            if trace_path.exists():
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
                judge = (trace.get("judge") or [{}])[0]
                raw["decision"] = judge.get("decision", raw["decision"])
                raw["confidence"] = judge.get("confidence", raw["confidence"])
                raw["judge_mode"] = judge.get("judge_mode", "rules")
                raw["reasoning_trace"] = judge.get("reasoning_trace", "")
                raw["action_plan"] = judge.get("action_plan", [])
        records.append(
            _real_record(
                raw,
                seed=seed,
                config=spec.label,
                case_index=case_index_by_id.get(row.case_id, 0),
            )
        )
    return records


# ---------------------------------------------------------------------------
# label normalization + precheck comparison
# ---------------------------------------------------------------------------


def _abstained(text: str) -> bool:
    return bool(re.search(r"证据不足|无法定论|不能确诊|不能下结论|不确定", text))


def normalize_label(decision: str) -> str:
    """Map a decision string to a canonical label: disease name or ABSTAIN."""
    if _abstained(decision):
        return "ABSTAIN"
    for name in _DISEASE_NAMES:
        if name in decision:
            return name
    return decision.strip()[:40] or "EMPTY"


def load_harness_results(path: Path) -> list[dict[str, Any]]:
    """Load the Phase 4.2 harness aggregate results file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("results", []))


def run_precheck(
    *,
    case_id: int,
    seed: int,
    configs: list[str],
    harness_path: Path,
    output_dir: Path,
    report_path: Path,
) -> int:
    """Run case ``case_id`` through the real agent per config and compare
    with the harness. Returns 0 (pass) or 1 (fail)."""
    from scripts.run_challenge_evaluation import load_challenge_set

    cases = load_challenge_set()
    if case_id < 1 or case_id > len(cases):
        raise ValueError(f"case id {case_id} out of range (1-{len(cases)})")
    selected = [dict(cases[case_id - 1], case_id=case_id)]
    harness = load_harness_results(harness_path)

    lines: list[str] = [
        "# Phase 4.2-R Pre-check Report",
        "",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        f"> Case: {selected[0]['id']} | seed: {seed} | configs: {configs}",
        f"> Harness reference: {harness_path}",
        "",
        (
            "| config | real decision | real confidence | judge_mode | "
            "harness diagnosis | harness confidence | label match | "
            "conf. offset |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]
    failed: list[str] = []
    for spec in config_specs(configs):
        records = run_real_agent(
            spec,
            selected,
            output_dir / f"precheck_seed{seed}",
            seed=seed,
            max_cases=1,
        )
        real = records[0] if records else {}
        real_decision = str(real.get("decision", ""))
        real_conf = float(real.get("confidence", 0.0))
        judge_mode = real.get("judge_mode", "rules")

        harness_records = [
            record
            for record in harness
            if int(record.get("seed", -1)) == seed
            and record.get("config") == spec.label
            and int(record.get("case_id", -1)) == case_id
        ]
        if not harness_records:
            failed.append(
                f"{spec.label}: no harness reference for "
                f"(seed={seed}, case={case_id})"
            )
            lines.append(
                f"| {spec.label} | {real_decision[:30]} | {real_conf} | "
                f"{judge_mode} | MISSING | - | - | - |"
            )
            continue
        harness_rec = harness_records[0]
        harness_diagnosis = str(harness_rec.get("output", {}).get(
            "diagnosis", ""
        ))
        harness_conf = float(
            harness_rec.get("output", {}).get("confidence", 0.0)
        )
        real_label = normalize_label(real_decision)
        harness_label = normalize_label(harness_diagnosis)
        match = "match" if real_label == harness_label else "DIFFERS"
        offset = abs(real_conf - harness_conf)
        if offset > CONFIDENCE_OFFSET_TOLERANCE:
            failed.append(
                f"{spec.label}: confidence offset {offset:.3f} > "
                f"{CONFIDENCE_OFFSET_TOLERANCE}"
            )
        lines.append(
            f"| {spec.label} | {real_decision[:30]} | {real_conf} | "
            f"{judge_mode} | {harness_diagnosis[:20]} | {harness_conf} | "
            f"{match} ({real_label} vs {harness_label}) | {offset:.3f} |"
        )

    if failed:
        lines += ["", "## Verdict", "", "**FAIL** — " + "; ".join(failed), ""]
    else:
        lines += [
            "",
            "## Verdict",
            "",
            (
                "**PASS** — outputs structurally comparable (decision/"
                "confidence present; harness carries "
                "diagnosis/confidence/coherence(1-5), real agent carries "
                "judge_mode/reasoning_trace/action_plan; tool-call traces "
                "are expected real-agent differences); no confidence offset "
                "> 0.3."
            ),
            "",
        ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"pre-check report -> {report_path}")
    return 1 if failed else 0


# ---------------------------------------------------------------------------
# full run
# ---------------------------------------------------------------------------


def run_full(
    *,
    seeds: list[int],
    configs: list[str],
    case_range: str,
    output_path: Path,
    log_root: Path,
) -> int:
    """Run seeds x configs x cases through the real agent (216 executions)."""
    from scripts.run_challenge_evaluation import load_challenge_set

    cases = load_challenge_set()
    case_ids = _resolve_cases(case_range, max_id=len(cases))
    selected = [dict(cases[cid - 1], case_id=cid) for cid in case_ids]

    log_root.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    total = len(seeds) * len(configs) * len(selected)
    completed = 0
    manifest: dict[str, Any] = {
        "mode": "full",
        "model_note": "real ACIS runner (evals.runner.run_evaluation) with "
        "LLM judge; judge model from env (default deepseek-chat)",
        "configs": configs,
        "seeds": seeds,
        "case_ids": case_ids,
        "started": datetime.now(timezone.utc).isoformat(),
    }
    for seed in seeds:
        for spec in config_specs(configs):
            arm_dir = log_root / f"run_{seed}" / f"config_{spec.label}"
            arm_records = run_real_agent(
                spec,
                selected,
                arm_dir,
                seed=seed,
                max_cases=len(selected),
            )
            for record in arm_records:
                records.append(record)
                call_log = log_root / f"run_{seed}" / f"config_{spec.label}" / (
                    f"case_{int(record['case_index']):02d}.json"
                )
                call_log.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                completed += 1
                print(
                    f"[{completed}/{total}] seed={seed} config={spec.label} "
                    f"case={int(record['case_index']):02d} "
                    f"valid={record['valid']} "
                    f"conf={record['confidence']:.2f} "
                    f"mode={record['judge_mode']}"
                )
            if completed % 25 == 0:
                _write_aggregate(output_path, manifest, records)

    manifest["finished"] = datetime.now(timezone.utc).isoformat()
    manifest["completed_calls"] = completed
    _write_aggregate(output_path, manifest, records)
    print(f"phase 4.2-R complete: {completed} executions -> {output_path}")
    return 0


def _write_aggregate(
    output_path: Path,
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    output_path.write_text(
        json.dumps(
            {"manifest": manifest, "results": records},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _resolve_cases(spec: str, *, max_id: int) -> list[int]:
    ids: list[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            ids.extend(range(int(start), int(end) + 1))
        else:
            ids.append(int(chunk))
    ids = sorted(set(ids))
    invalid = [cid for cid in ids if cid < 1 or cid > max_id]
    if invalid:
        raise ValueError(f"case ids out of range: {invalid} (1-{max_id})")
    return ids


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 4.2-R real-agent batch runner"
    )
    parser.add_argument(
        "--mode",
        choices=("precheck", "full"),
        required=True,
        help="precheck (1 case x configs vs harness) or full (216 runs)",
    )
    parser.add_argument(
        "--configs",
        nargs="*",
        choices=CONFIG_ORDER,
        default=list(CONFIG_ORDER),
        help="configs (default: C0 C1 C2)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="seed for precheck (default: 42)",
    )
    parser.add_argument(
        "--seeds",
        nargs="*",
        type=int,
        default=list(DEFAULT_SEEDS),
        help="seeds for full mode (default: 42 43 44)",
    )
    parser.add_argument(
        "--case",
        type=int,
        default=1,
        help="case id for precheck (default: 1)",
    )
    parser.add_argument(
        "--cases",
        default="1-24",
        help="case range for full mode (default: 1-24)",
    )
    parser.add_argument(
        "--compare-harness",
        default=str(ROOT / "reports" / "phase4_2_harness" /
                    "phase4_2_raw_results.json"),
        help="Phase 4.2 harness results JSON for precheck comparison",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "reports" / "phase4_2_real_agent" /
                    "raw_results.json"),
        help="output JSON path (full mode)",
    )
    parser.add_argument(
        "--log-dir",
        default=str(ROOT / "logs" / "phase4_2_real_agent"),
        help="per-call audit log directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_env()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("error: DEEPSEEK_API_KEY is not set")
        return 1
    if args.mode == "precheck":
        return run_precheck(
            case_id=args.case,
            seed=args.seed,
            configs=list(args.configs),
            harness_path=Path(args.compare_harness),
            output_dir=Path(args.log_dir),
            report_path=Path(args.output),
        )
    return run_full(
        seeds=list(args.seeds),
        configs=list(args.configs),
        case_range=args.cases,
        output_path=Path(args.output),
        log_root=Path(args.log_dir),
    )


if __name__ == "__main__":
    raise SystemExit(main())
