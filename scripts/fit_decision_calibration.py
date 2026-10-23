"""Fit the ADR-005 decision-confidence calibration from a real-Judge run.

Reads runner traces (which carry judge_analysis) plus metrics.csv correctness,
recomputes the structural score for every case, and writes
utils/decision_calibration_data.json as [(structural_score, correct)].

Always fit on one seed and evaluate on a different seed.
"""
from __future__ import annotations

import csv
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.confidence_calibration import combine_decision_score, compute_decision_signals


def load_run(run_dir: Path):
    samples = []
    for comp in sorted(run_dir.iterdir()):
        if not comp.is_dir() or not comp.name.startswith("config_"):
            continue
        metrics = {}
        for f in glob.glob(str(comp / "*" / "runner" / "metrics.csv")):
            for row in csv.DictReader(open(f, encoding="utf-8")):
                if row.get("case_id") == "__aggregate__":
                    continue
                metrics[row["trace_id"]] = row
        for tf in glob.glob(str(comp / "*" / "runner" / "traces" / "*.json")):
            trace = json.load(open(tf, encoding="utf-8"))
            tid = trace.get("trace_id")
            row = metrics.get(tid)
            if row is None:
                continue
            judges = trace.get("judge") or []
            judge = judges[0] if judges else {}
            analysis = judge.get("judge_analysis") or {}
            llm_like = {
                "final_confidence": judge.get("confidence"),
                "consistency_analysis": analysis.get("consistency_analysis") or {},
                "evidence_scores": analysis.get("evidence_scores") or {},
                "kg_contribution": analysis.get("kg_contribution"),
            }
            debate_raw = trace.get("debate") or {}
            if isinstance(debate_raw, list):
                debate_raw = debate_raw[0] if debate_raw and isinstance(debate_raw[0], dict) else {}

            _conf = debate_raw.get("conflicts")
            _conflicts = len(_conf) if isinstance(_conf, list) else int(_conf or 0)

            class _Debate:
                conflicts = _conflicts

            signals = compute_decision_signals(llm_like, analysis, _Debate())
            score = combine_decision_score(signals)
            correct = 1 if float(row.get("accuracy") or 0) >= 1.0 else 0
            samples.append({
                "component": comp.name,
                "case_id": row["case_id"],
                "score": score,
                "correct": correct,
                "self_report": signals["self_report"],
                "confidence": float(row.get("confidence") or 0),
            })
    return samples


def main(argv):
    run_dir = Path(argv[0]) if argv else ROOT / "logs/phase6_baseline_20261023/run_42"
    out = Path(argv[1]) if len(argv) > 1 else ROOT / "utils/decision_calibration_data.json"
    samples = load_run(run_dir)
    if not samples:
        print("no samples found in", run_dir)
        return 1
    payload = {
        "source_run": str(run_dir).replace("\\", "/"),
        "note": "fit on one seed, evaluate on another; see ADR-005",
        "samples": [[s["score"], s["correct"]] for s in samples],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    acc = sum(s["correct"] for s in samples) / len(samples)
    mean_score = sum(s["score"] for s in samples) / len(samples)
    mean_self = sum(s["self_report"] for s in samples) / len(samples)
    print(f"samples={len(samples)} accuracy={acc:.4f} mean_structural_score={mean_score:.4f} mean_self_report={mean_self:.4f}")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
