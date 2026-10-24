"""Deterministic, offline delivery evaluation for the minimal MVP.

Runs the 12 fixed greenhouse fixtures through the real rules pipeline (no
external service, no LLM), and writes a machine-readable summary plus a short
Markdown report. Re-running the command should produce the same summary on the
same machine/hour (the weather/sensor layers are simulated and time-dependent;
the seed fixes the random part).

Usage (repo root)::

    python scripts/run_delivery_eval.py
    python scripts/run_delivery_eval.py --output-dir reports/delivery_eval
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Offline, in-process backends only: the result must not depend on Qdrant,
# Neo4j or an API key.
os.environ.setdefault("AGRI_AI_RAG_BACKEND", "memory")
os.environ.setdefault("AGRI_AI_KG_BACKEND", "memory")
os.environ.setdefault("AGRI_AI_PERSIST", "0")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ["AGRI_AI_DB_PATH"] = str(
    Path(tempfile.gettempdir()) / "acis_delivery_eval.db"
)

from evals.fixtures import FIXTURES  # noqa: E402
from orchestrator import AgentOrchestrator, build_context  # noqa: E402
from rule_engine import sensor_anomaly  # noqa: E402

SEED = 7


def _matches_expected(expected: str | None, pathology_claim: str) -> bool:
    if expected is None:
        return True
    if expected == "证据不足":
        return "病理证据不足" in pathology_claim
    return expected in pathology_claim


def run() -> dict:
    db_path = Path(os.environ["AGRI_AI_DB_PATH"])
    db_path.unlink(missing_ok=True)

    orchestrator = AgentOrchestrator(use_langgraph=True)
    cases: list[dict] = []
    for fixture in FIXTURES:
        context = build_context(fixture["query"])
        if fixture.get("sensor_override"):
            sensor_anomaly.ANOMALIES["gh-a"] = fixture["sensor_override"]
        try:
            random.seed(SEED)
            decision = orchestrator.run(fixture["query"])
        finally:
            sensor_anomaly.ANOMALIES.pop("gh-a", None)

        pathology = next(
            (trace for trace in decision.traces if trace.agent == "病理Agent"), None
        )
        pathology_claim = pathology.claim if pathology else ""
        cases.append(
            {
                "id": fixture["id"],
                "crop": context.crop,
                "intent": context.intent,
                "expected": fixture.get("disease"),
                "pathology_claim": pathology_claim,
                "matches_expected": _matches_expected(fixture.get("disease"), pathology_claim),
                "decision": decision.decision,
                "confidence": round(decision.confidence, 4),
                "risk_level": decision.risk_level,
                "judge_mode": decision.judge_mode,
                "need_human_review": decision.need_human_review,
                "critic_triggered": bool(decision.debate.critic.get("triggered")),
                # trace_id is intentionally excluded: it is random per run and
                # would make the summary non-reproducible. The stage list and
                # event count still prove the unified Trace was built.
                "trace_stages": (
                    orchestrator.last_trace.stages_present
                    if orchestrator.last_trace
                    else []
                ),
                "trace_event_count": (
                    len(orchestrator.last_trace.events)
                    if orchestrator.last_trace
                    else 0
                ),
            }
        )

    matched = sum(1 for case in cases if case["matches_expected"])
    criticisms = sum(1 for case in cases if case["critic_triggered"])
    summary = {
        "dataset": "evals.fixtures",
        "case_count": len(cases),
        "seed": SEED,
        "backends": {
            "rag": os.environ["AGRI_AI_RAG_BACKEND"],
            "kg": os.environ["AGRI_AI_KG_BACKEND"],
            "llm_judge": "disabled",
            "persist": os.environ["AGRI_AI_PERSIST"],
        },
        "aggregate": {
            "matched_expected": matched,
            "matched_rate": round(matched / len(cases), 4) if cases else 0.0,
            "critic_triggered": criticisms,
            "risk_counts": {
                level: sum(1 for case in cases if case["risk_level"] == level)
                for level in ("low", "medium", "high")
            },
            "mean_confidence": round(
                sum(case["confidence"] for case in cases) / len(cases), 4
            )
            if cases
            else 0.0,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "cases": cases,
    }
    return summary


def write_reports(summary: dict, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "summary.json"
    md_path = output_dir / "summary.md"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# ACIS 最小交付评测（离线规则链路）",
        "",
        f"- 数据集：`{summary['dataset']}`（{summary['case_count']} 例）",
        f"- 随机种子：{summary['seed']}",
        "- 后端：RAG=memory / KG=memory / LLM Judge=disabled / SQLite 持久化=off",
        "- 说明：天气与传感器为模拟数据，随机部分由种子固定；同一机器同一小时可复现。",
        "",
        "| 用例 | 期望 | 实际病理结论 | 判定 | 置信度 | 风险 | Critic |",
        "|---|---|---|---|---:|---|---|",
    ]
    for case in summary["cases"]:
        lines.append(
            "| {id} | {expected} | {claim} | {ok} | {conf:.0%} | {risk} | {critic} |".format(
                id=case["id"],
                expected=case["expected"] or "-",
                claim=case["pathology_claim"],
                ok="PASS" if case["matches_expected"] else "FAIL",
                conf=case["confidence"],
                risk=case["risk_level"],
                critic="on" if case["critic_triggered"] else "off",
            )
        )
    aggregate = summary["aggregate"]
    lines += [
        "",
        f"- 期望命中：{aggregate['matched_expected']}/{summary['case_count']}（{aggregate['matched_rate']:.0%}）",
        f"- Critic 触发：{aggregate['critic_triggered']} 例",
        f"- 平均置信度：{aggregate['mean_confidence']:.4f}",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="ACIS offline delivery evaluation")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "reports" / "delivery_eval"),
        help="report output directory (default: reports/delivery_eval)",
    )
    args = parser.parse_args()

    summary = run()
    json_path, md_path = write_reports(summary, Path(args.output_dir))
    aggregate = summary["aggregate"]
    print(f"delivery eval: {summary['case_count']} cases")
    print(f"  matched_expected={aggregate['matched_expected']}/{summary['case_count']}")
    print(f"  critic_triggered={aggregate['critic_triggered']}")
    print(f"  mean_confidence={aggregate['mean_confidence']}")
    print(f"  summary.json: {json_path}")
    print(f"  summary.md:   {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
