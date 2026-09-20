"""Phase 4.2-R3 stress test — 30 consecutive real-agent judge calls.

Runs the exact experiment call chain (``scripts/run_phase4_2_real_agent.py``
-> ``evals.runner.run_evaluation``) 30 times back-to-back with fixed inputs
(case 1 / C1 / seed 42) to probe gateway stability under burst load.

Observational only: no agent logic, no timeout/retry/temperature changes.
The ``agents.judge_agent`` logger is captured per call so any
``Judge exception`` details (type / cause / base_url) are recorded into the
report.

Usage from the repo root (with gateway env injected)::

    python scripts/stress_test_judge.py --calls 30
"""

from __future__ import annotations

import argparse
import logging
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.run_challenge_evaluation import load_challenge_set
from scripts.run_phase4_2_real_agent import config_specs, run_real_agent

DEFAULT_OUTPUT = ROOT / "reports" / "phase4_2_r3_stress_test.md"
DEFAULT_LOG_DIR = ROOT / "logs" / "phase4_2_r3_stress"


class _CaptureHandler(logging.Handler):
    """In-memory capture of the judge-agent logger output per call."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(self.format(record))

    def reset(self) -> None:
        self.messages = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_stress(
    *,
    calls: int,
    case_index: int,
    config: str,
    seed: int,
    output: Path,
    log_dir: Path,
) -> int:
    """Execute ``calls`` consecutive real-agent runs and write the report."""
    handler = _CaptureHandler()
    handler.setFormatter(
        logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    )
    judge_logger = logging.getLogger("agents.judge_agent")
    judge_logger.addHandler(handler)

    cases = load_challenge_set()
    if case_index < 1 or case_index > len(cases):
        raise ValueError(f"case index {case_index} out of range (1-{len(cases)})")
    selected = [dict(cases[case_index - 1], case_id=case_index)]
    spec = config_specs([config])[0]

    print(
        f"[stress] {calls} calls | case={selected[0]['id']} config={spec.label} "
        f"seed={seed} | endpoint: {_endpoint_note()}"
    )
    rows: list[dict[str, Any]] = []
    started = _now_iso()
    for index in range(1, calls + 1):
        call_start = time.perf_counter()
        handler.reset()
        try:
            records = run_real_agent(
                spec,
                selected,
                log_dir / f"call_{index:02d}",
                seed=seed,
                max_cases=1,
            )
            record = records[0]
            mode = str(record.get("judge_mode", "?"))
            success = mode == "deepseek"
            detail = {
                "decision": record.get("decision", ""),
                "confidence": record.get("confidence", 0.0),
            }
        except Exception as exc:  # noqa: BLE001  record any run-level failure
            mode = f"ERROR:{type(exc).__name__}"
            success = False
            detail = {"error": str(exc)}
        elapsed = time.perf_counter() - call_start
        judge_log_lines = list(handler.messages)
        rows.append(
            {
                "id": index,
                "timestamp": _now_iso(),
                "success": success,
                "mode": mode,
                "elapsed_seconds": round(elapsed, 2),
                **detail,
                "judge_log": judge_log_lines,
            }
        )
        print(
            f"Run {index:02d}: {mode} ({elapsed:.2f}s)"
            + ("" if success else f" | log: {judge_log_lines}")
        )

    finished = _now_iso()
    success_count = sum(1 for row in rows if row["success"])
    rate = 100.0 * success_count / len(rows)
    elapsed_values = [row["elapsed_seconds"] for row in rows]
    passed = rate >= 95.0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_markdown(
            rows=rows,
            started=started,
            finished=finished,
            success_count=success_count,
            rate=rate,
            elapsed_values=elapsed_values,
            case_id=selected[0]["id"],
            config=spec.label,
            seed=seed,
            passed=passed,
        ),
        encoding="utf-8",
    )
    print(f"[stress] success {success_count}/{calls} ({rate:.1f}%)")
    print(f"[stress] {'PASS (>=95%)' if passed else 'FAIL (<95%)'} -> {output}")
    return 0 if passed else 1


def _endpoint_note() -> str:
    import os

    return (
        f"base_url={os.environ.get('DEEPSEEK_BASE_URL', '(unset)')} "
        f"model={os.environ.get('DEEPSEEK_MODEL', '(unset)')}"
    )


def render_markdown(
    *,
    rows: list[dict[str, Any]],
    started: str,
    finished: str,
    success_count: int,
    rate: float,
    elapsed_values: list[float],
    case_id: str,
    config: str,
    seed: int,
    passed: bool,
) -> str:
    """Render the stress-test report (data only)."""
    lines: list[str] = [
        "# Phase 4.2-R3 Stress Test Report",
        "",
        f"> Started: {started} | Finished: {finished}",
        f"> Case: {case_id} | Config: {config} | Seed: {seed}",
        f"> Endpoint: {_endpoint_note()}",
        "",
        (
            f"**Verdict: {'PASS' if passed else 'FAIL'}** — success "
            f"{success_count}/{len(rows)} ({rate:.1f}%)"
        ),
        "",
        "## Per-call results",
        "",
        "| # | timestamp | judge_mode | elapsed (s) | decision | judge log |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        log_text = "; ".join(row["judge_log"])[:120].replace("|", "/")
        decision = str(row.get("decision", row.get("error", "")))[:30]
        lines.append(
            f"| {row['id']} | {row['timestamp'][11:19]} | {row['mode']} | "
            f"{row['elapsed_seconds']} | {decision} | {log_text} |"
        )
    lines += [
        "",
        "## Summary",
        "",
        f"- Success rate: {success_count}/{len(rows)} ({rate:.1f}%)",
        (
            f"- Elapsed distribution (s): min={min(elapsed_values):.2f} "
            f"mean={statistics.fmean(elapsed_values):.2f} "
            f"max={max(elapsed_values):.2f}"
        ),
        "",
    ]
    failures = [row for row in rows if not row["success"]]
    if failures:
        lines += [
            "## Failures (judge-agent logger evidence)",
            "",
            "| # | mode | judge log |",
            "|---|---|---|",
        ]
        for row in failures:
            log_text = "; ".join(row["judge_log"]).replace("|", "/")
            lines.append(f"| {row['id']} | {row['mode']} | {log_text} |")
    else:
        lines += ["## Failures", "", "_None._", ""]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 4.2-R3 stress test (30 consecutive judge calls)"
    )
    parser.add_argument("--calls", type=int, default=30)
    parser.add_argument("--case", type=int, default=1)
    parser.add_argument("--config", choices=("C0", "C1", "C2"), default="C1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_stress(
        calls=args.calls,
        case_index=args.case,
        config=args.config,
        seed=args.seed,
        output=Path(args.output),
        log_dir=Path(args.log_dir),
    )


if __name__ == "__main__":
    raise SystemExit(main())
