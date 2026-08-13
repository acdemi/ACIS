"""Phase 4.2 validation report generator (data summary only, no analysis).

Reads ``reports/phase4_2_raw_results.json`` (written by
``scripts/run_phase4_2.py``) and produces a neutral, descriptive summary:

- call counts per (config x seed) and overall validity / error rates;
- per config: diagnosis value distribution, ABSTAIN count, mean confidence
  (min/max), mean coherence, format-validity rate, mean latency;
- seed pass-through acceptance counts (``seed_accepted``).

Explicitly NOT a stability/ranking analysis: the report only aggregates the
raw measurements for the Evidence Review.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 4) if values else None


def render_summary(data: dict[str, Any]) -> str:
    """Render the data summary as Markdown (no analysis)."""
    manifest = data.get("manifest", {})
    results: list[dict[str, Any]] = data.get("results", [])
    lines: list[str] = [
        "# Phase 4.2 Validation Report (data summary only)",
        "",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        (
            f"> Model: {manifest.get('model')} | temperature: "
            f"{manifest.get('temperature')} | base_url: "
            f"{manifest.get('base_url')}"
        ),
        f"> Challenge set: {manifest.get('challenge_set')}",
        (
            f"> Configs: {manifest.get('configs')} | seeds: "
            f"{manifest.get('seeds')} | cases: {manifest.get('case_ids')}"
        ),
        f"> Total calls: {manifest.get('completed_calls', len(results))}",
        "",
        "## 1. Call counts and validity",
        "",
        "| seed | config | calls | valid | invalid | errors |",
        "|---|---|---|---|---|---|",
    ]
    by_seed_config: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for record in results:
        key = (int(record["seed"]), str(record["config"]))
        by_seed_config.setdefault(key, []).append(record)
    for seed in manifest.get("seeds", []):
        for config in manifest.get("configs", []):
            records = by_seed_config.get((int(seed), str(config)), [])
            valid = sum(1 for r in records if r.get("valid"))
            invalid = sum(1 for r in records if r.get("status") == "ok" and not r.get("valid"))
            errors = sum(1 for r in records if r.get("status") != "ok")
            lines.append(
                f"| {seed} | {config} | {len(records)} | {valid} | "
                f"{invalid} | {errors} |"
            )
    lines += [
        "",
        "## 2. Per-config summary",
        "",
        (
            "| config | calls | ABSTAIN | diagnosis values | mean confidence "
            "(min-max) | mean coherence | validity rate | mean latency (s) |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]
    for config in manifest.get("configs", []):
        records = [r for r in results if r["config"] == config]
        if not records:
            continue
        valid_records = [r for r in records if r.get("valid")]
        diagnosis_counter: Counter[str] = Counter()
        for record in valid_records:
            diagnosis = record["output"].get("diagnosis", "")
            diagnosis_counter[diagnosis if isinstance(diagnosis, str) else str(diagnosis)] += 1
        confidences = [
            float(record["output"].get("confidence", 0.0))
            for record in valid_records
        ]
        coherences = [
            float(record["output"].get("coherence", 0))
            for record in valid_records
            if record["output"].get("coherence") is not None
        ]
        latencies = [
            float(record.get("latency_seconds", 0.0)) for record in records
        ]
        top_diagnoses = ", ".join(
            f"{name}={count}" for name, count in diagnosis_counter.most_common(6)
        ) or "-"
        validity = (
            round(100.0 * len(valid_records) / len(records), 2)
            if records
            else 0.0
        )
        mean_conf = _mean(confidences)
        conf_range = (
            f"({min(confidences)}-{max(confidences)})" if confidences else "-"
        )
        lines.append(
            f"| {config} | {len(records)} | {diagnosis_counter.get('ABSTAIN', 0)} "
            f"| {top_diagnoses} | {mean_conf} {conf_range} | "
            f"{_mean(coherences)} | {validity}% | {_mean(latencies)} |"
        )
    lines += [
        "",
        "## 3. Seed pass-through (audit)",
        "",
        "| seed | calls | seed_accepted | seed_rejected |",
        "|---|---|---|---|",
    ]
    for seed in manifest.get("seeds", []):
        records = [r for r in results if int(r["seed"]) == int(seed)]
        accepted = sum(1 for r in records if r.get("seed_accepted"))
        rejected = sum(1 for r in records if not r.get("seed_accepted"))
        lines.append(
            f"| {seed} | {len(records)} | {accepted} | {rejected} |"
        )
    lines += [
        "",
        "## 4. Malformed outputs (validation only, not corrected)",
        "",
    ]
    malformed = [r for r in results if r.get("parse_error")]
    if malformed:
        lines += ["| seed | config | case | error |", "|---|---|---|---|"]
        for record in malformed[:30]:
            lines.append(
                f"| {record['seed']} | {record['config']} | "
                f"{record['case_id']} | {record.get('parse_error')} |"
            )
    else:
        lines.append("_None._")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 4.2 validation report (data summary only)"
    )
    parser.add_argument(
        "--input",
        default=str(ROOT / "reports" / "phase4_2_raw_results.json"),
        help="raw results JSON path",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "reports" / "phase4_validation_report.md"),
        help="markdown report path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"error: no raw results at {input_path}")
        return 1
    data = json.loads(input_path.read_text(encoding="utf-8"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_summary(data), encoding="utf-8")
    print(f"validation report written -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
