"""Run the deterministic, offline diagnosis-fixture regression evaluation.

The fixture suite is an engineering regression set, not expert-confirmed field
data. The report therefore separates diagnosis and Top-3 checks from metrics
that need reviewed labels, relevant-source annotations, or a calibrated model.

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
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from time import perf_counter
from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEED = 7
EVIDENCE_INSUFFICIENT = "证据不足"
OFFLINE_ENVIRONMENT = {
    "AGRI_AI_RAG_BACKEND": "memory",
    "AGRI_AI_KG_BACKEND": "memory",
    "AGRI_AI_PERSIST": "0",
    "ACIS_ENABLE_PLANNER": "0",
    "AGRI_AI_EXTRA_EXPERTS": "1",
    "AGRI_AI_MULTI_ROUND_DEBATE": "1",
    "AGRI_AI_MEMORY_GATE": "1",
    "AGRI_AI_MEMORY_GATE_MIN_CONF": "0.45",
    "AGRI_AI_ABSTAIN_MIN_SUFFICIENCY": "0.55",
    "AGRI_AI_KG_DRAFTS_LOAD": "0",
    "AGRI_AI_RAG_TOP_K": "3",
    "AGRI_AI_CALIBRATION": "1",
    "AGRI_AI_CALIB_ALPHA": "0.5",
    "AGRI_AI_JUDGE_SELF_CONSISTENCY_K": "3",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
}
SIMULATION_TIME = datetime(2026, 6, 15, 10, 0, 0)
CROP_LABELS = {
    "tomato": "番茄",
    "maize": "玉米",
    "wheat": "小麦",
    "sugar_beet": "甜菜",
    "cotton": "棉花",
    "cucumber": "黄瓜",
}
FINAL_DIAGNOSIS_PREFIXES = (
    "病理判断首选：",
    "病理判断首选:",
    "诊断结论：",
    "诊断结论:",
    "最终诊断：",
    "最终诊断:",
)


@contextmanager
def _offline_environment(db_path: Path) -> Iterator[None]:
    values = {**OFFLINE_ENVIRONMENT, "AGRI_AI_DB_PATH": str(db_path)}
    previous = {name: os.environ.get(name) for name in values}
    try:
        os.environ.update(values)
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _load_runtime():
    from acis.evaluation.evals.fixtures import FIXTURES
    import acis.agents.weather as weather_module
    from acis.core.orchestrator import AgentOrchestrator, build_context
    from acis.reasoning.rule_engine import sensor_anomaly
    import acis.knowledge.storage.db as database

    return (
        FIXTURES,
        AgentOrchestrator,
        build_context,
        sensor_anomaly,
        database,
        weather_module,
    )


@contextmanager
def _fixed_simulation_clock(sensor_anomaly, weather_module) -> Iterator[None]:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return cls(2026, 6, 15, 10, 0, 0)
            return cls(2026, 6, 15, 10, 0, 0, tzinfo=tz)

    clock_modules = (sensor_anomaly, weather_module)
    previous_datetimes = [module.datetime for module in clock_modules]
    previous_weather = dict(weather_module._WEATHER_STATE)
    weather_module._WEATHER_STATE.clear()
    weather_module._WEATHER_STATE.update(
        {
            "condition": "多云转晴",
            "season": "夏季",
            "region": "华北平原",
            "base_temp": 32.0,
            "base_humidity": 55.0,
        }
    )
    try:
        for module in clock_modules:
            module.datetime = FixedDateTime
        yield
    finally:
        for module, previous_datetime in zip(clock_modules, previous_datetimes):
            module.datetime = previous_datetime
        weather_module._WEATHER_STATE.clear()
        weather_module._WEATHER_STATE.update(previous_weather)


def _extract_final_diagnosis(decision: str) -> str | None:
    for prefix in FINAL_DIAGNOSIS_PREFIXES:
        if decision.startswith(prefix):
            label = decision[len(prefix) :].strip()
            return label.split("，", 1)[0].split(",", 1)[0].strip() or None
    return None


def _normalize_label(label: str, crop: str) -> str:
    normalized = label.strip()
    crop_label = CROP_LABELS.get(crop, "")
    if crop_label and normalized.startswith(crop_label):
        normalized = normalized[len(crop_label) :]
    return normalized


def _score_diagnosis(
    *,
    expected: str | None,
    intent: str,
    decision: str,
    candidate_names: list[str],
    crop: str,
) -> dict[str, bool | None]:
    if expected is None or intent != "diagnose":
        return {
            "scored": False,
            "matches_expected": None,
            "top3_scored": False,
            "top3_matches_expected": None,
        }

    if expected == EVIDENCE_INSUFFICIENT:
        matches_expected = any(
            marker in decision
            for marker in ("证据不足", "暂不能确认", "无法确认", "暂不进行病害定性")
        ) and _extract_final_diagnosis(decision) is None
        top3_scored = False
        top3_matches_expected = None
    else:
        normalized_expected = _normalize_label(expected, crop)
        final_label = _extract_final_diagnosis(decision)
        matches_expected = (
            final_label is not None
            and _normalize_label(final_label, crop) == normalized_expected
        )
        top3_scored = True
        top3_matches_expected = (
            any(
                _normalize_label(candidate, crop) == normalized_expected
                for candidate in candidate_names[:3]
            )
        )

    return {
        "scored": True,
        "matches_expected": matches_expected,
        "top3_scored": top3_scored,
        "top3_matches_expected": top3_matches_expected,
    }


def _candidate_names(decision) -> list[str]:
    report = getattr(decision, "report", None) or {}
    candidates = report.get("candidates", []) if isinstance(report, dict) else []
    names = []
    for candidate in candidates:
        name = candidate.get("name") if isinstance(candidate, dict) else candidate
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return names


def _rate(correct: int, scored: int) -> float | None:
    return round(correct / scored, 4) if scored else None


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1")

    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index
    return round(
        ordered[lower_index]
        + fraction * (ordered[upper_index] - ordered[lower_index]),
        12,
    )


def run() -> dict:
    initial_random_state = random.getstate()
    try:
        with tempfile.TemporaryDirectory(prefix="acis-delivery-eval-") as temp_dir:
            isolated_db = Path(temp_dir) / "audit.sqlite3"
            with _offline_environment(isolated_db):
                (
                    fixtures,
                    orchestrator_type,
                    build_context,
                    sensor_anomaly,
                    database,
                    weather_module,
                ) = _load_runtime()
                original_db_path = database._DB_PATH
                database._DB_PATH = isolated_db
                try:
                    with _fixed_simulation_clock(sensor_anomaly, weather_module):
                        orchestrator = orchestrator_type(
                            use_langgraph=True,
                            use_llm_judge=False,
                            use_llm_critic=False,
                        )
                        cases: list[dict] = []
                        for fixture in fixtures:
                            context = build_context(fixture["query"])
                            anomaly_map = sensor_anomaly.ANOMALIES
                            had_previous_anomaly = "gh-a" in anomaly_map
                            previous_anomaly = anomaly_map.get("gh-a")
                            anomaly_map.pop("gh-a", None)
                            if fixture.get("sensor_override"):
                                anomaly_map["gh-a"] = fixture["sensor_override"]
                            try:
                                random.seed(SEED)
                                started = perf_counter()
                                decision = orchestrator.run(fixture["query"])
                                duration_ms = (perf_counter() - started) * 1000
                            finally:
                                if had_previous_anomaly:
                                    anomaly_map["gh-a"] = previous_anomaly
                                else:
                                    anomaly_map.pop("gh-a", None)

                            pathology = next(
                                (
                                    trace
                                    for trace in decision.traces
                                    if trace.agent == "病理Agent"
                                ),
                                None,
                            )
                            candidates = _candidate_names(decision)
                            reference_intent = fixture.get("intent", "diagnose")
                            score = _score_diagnosis(
                                expected=fixture.get("disease"),
                                intent=reference_intent,
                                decision=decision.decision,
                                candidate_names=candidates,
                                crop=context.crop,
                            )
                            trace = orchestrator.last_trace
                            cases.append(
                                {
                                    "id": fixture["id"],
                                    "crop": context.crop,
                                    "intent": context.intent,
                                    "expected_intent": reference_intent,
                                    "intent_matches_expected": context.intent
                                    == reference_intent,
                                    "expected": fixture.get("disease"),
                                    "pathology_claim": pathology.claim if pathology else None,
                                    "predicted_diagnosis_label": _extract_final_diagnosis(
                                        decision.decision
                                    ),
                                    "decision": decision.decision,
                                    "candidate_names": candidates,
                                    **score,
                                    "confidence": round(decision.confidence, 4),
                                    "risk_level": decision.risk_level,
                                    "judge_mode": decision.judge_mode,
                                    "need_human_review": decision.need_human_review,
                                    "critic_triggered": bool(
                                        decision.debate.critic.get("triggered")
                                    ),
                                    "duration_ms": round(duration_ms, 3),
                                    "agent_execution": [
                                        {
                                            "agent": output.agent,
                                            "status": (output.execution or {}).get(
                                                "status", "unknown"
                                            ),
                                            "mode": (output.execution or {}).get(
                                                "mode", "unknown"
                                            ),
                                        }
                                        for output in decision.traces
                                    ],
                                    "trace_stages": trace.stages_present if trace else [],
                                    "trace_event_count": len(trace.events) if trace else 0,
                                }
                            )
                finally:
                    database._DB_PATH = original_db_path
    finally:
        random.setstate(initial_random_state)

    diagnosis_cases = [case for case in cases if case["scored"]]
    top3_cases = [case for case in cases if case["top3_scored"]]
    diagnosis_correct = sum(case["matches_expected"] is True for case in diagnosis_cases)
    top3_correct = sum(case["top3_matches_expected"] is True for case in top3_cases)
    intent_correct = sum(case["intent_matches_expected"] for case in cases)
    duration_values = [case["duration_ms"] for case in cases]
    summary = {
        "dataset": "evals.fixtures",
        "dataset_scope": "engineering regression fixtures; not expert-confirmed field data",
        "case_count": len(cases),
        "seed": SEED,
        "simulation_time": SIMULATION_TIME.isoformat(),
        "backends": {
            "rag": "memory",
            "kg": "memory",
            "llm_judge": "disabled",
            "llm_critic": "disabled",
            "persist": "0",
        },
        "aggregate": {
            "diagnosis_accuracy": {
                "correct": diagnosis_correct,
                "scored": len(diagnosis_cases),
                "rate": _rate(diagnosis_correct, len(diagnosis_cases)),
            },
            "top3_accuracy": {
                "correct": top3_correct,
                "scored": len(top3_cases),
                "rate": _rate(top3_correct, len(top3_cases)),
            },
            "intent_accuracy": {
                "correct": intent_correct,
                "scored": len(cases),
                "rate": _rate(intent_correct, len(cases)),
            },
            "unscored_cases": len(cases) - len(diagnosis_cases),
            "critic_triggered": sum(case["critic_triggered"] for case in cases),
            "risk_counts": {
                level: sum(1 for case in cases if case["risk_level"] == level)
                for level in ("low", "medium", "high")
            },
            "mean_confidence": round(
                sum(case["confidence"] for case in cases) / len(cases), 4
            )
            if cases
            else None,
            "mean_latency_ms": round(sum(duration_values) / len(duration_values), 3)
            if duration_values
            else None,
            "p50_latency_ms": round(_percentile(duration_values, 0.5), 3)
            if duration_values
            else None,
            "p95_latency_ms": round(_percentile(duration_values, 0.95), 3)
            if duration_values
            else None,
            "not_measured": {
                "macro_f1": "fixture set does not provide expert-reviewed multi-class labels",
                "factor_coverage": "no reference factors are annotated for these fixtures",
                "abstention_quality": "no expert-reviewed insufficient-evidence diagnosis set",
                "confidence_calibration": "no held-out expert-reviewed calibration set",
                "retrieval_recall_at_k": "no gold relevant-source identifiers",
                "agent_fallback_rate": "no suite-wide normalized fallback denominator",
                "token_cost": "LLM is disabled and provider pricing metadata is unavailable",
            },
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

    aggregate = summary["aggregate"]
    diagnosis = aggregate["diagnosis_accuracy"]
    top3 = aggregate["top3_accuracy"]
    lines = [
        "# ACIS 离线农业诊断回归评测",
        "",
        f"- 数据集：`{summary['dataset']}`（{summary['case_count']} 例）",
        "- 运行模式：RAG=memory / KG=memory / LLM Judge=disabled / LLM Critic=disabled / SQLite 持久化=off",
        f"- 固定模拟时钟：`{summary['simulation_time']}`；运行延迟仍按实际执行耗时测量。",
        "- 结果边界：这些是工程回归夹具，不是人工确认标签或真实田间诊断质量评测。",
        "- 计分：按夹具的参考意图选择 Diagnosis Accuracy 分母；另报系统实际意图准确率。病名只做裁剪前缀规范化后的精确匹配。",
        "",
        "| 用例 | 参考/实际意图 | 参考标签 | 最终决策 | Diagnosis | Top-3 | 耗时(ms) | Trace 事件 |",
        "|---|---|---|---|---|---|---:|---:|",
    ]
    for case in summary["cases"]:
        if not case["scored"]:
            diagnosis_status = "不计分"
        else:
            diagnosis_status = "PASS" if case["matches_expected"] else "FAIL"
        if not case["top3_scored"]:
            top3_status = "不计分"
        else:
            top3_status = "PASS" if case["top3_matches_expected"] else "FAIL"
        lines.append(
            "| {id} | {expected_intent}/{intent} | {expected} | {decision} | {diagnosis} | {top3} | {latency:.3f} | {events} |".format(
                id=case["id"],
                intent=case["intent"],
                expected_intent=case["expected_intent"],
                expected=case["expected"] or "-",
                decision=case["decision"],
                diagnosis=diagnosis_status,
                top3=top3_status,
                latency=case["duration_ms"],
                events=case["trace_event_count"],
            )
        )
    lines += [
        "",
        f"- Diagnosis Accuracy：{diagnosis['correct']}/{diagnosis['scored']}（{diagnosis['rate'] if diagnosis['rate'] is not None else '未测量'}）",
        f"- Top-3 Accuracy：{top3['correct']}/{top3['scored']}（{top3['rate'] if top3['rate'] is not None else '未测量'}；以系统候选列表和单标签夹具计算）",
        f"- 意图分类准确率：{aggregate['intent_accuracy']['correct']}/{aggregate['intent_accuracy']['scored']}（{aggregate['intent_accuracy']['rate']}；独立于诊断准确率）",
        f"- 执行延迟：平均 {aggregate['mean_latency_ms']} ms / P50 {aggregate['p50_latency_ms']} ms / P95 {aggregate['p95_latency_ms']} ms（本地离线流水线，不代表生产延迟）",
        f"- 平均置信度：{aggregate['mean_confidence']}（仅描述性统计，不是校准指标）",
        f"- Critic 触发：{aggregate['critic_triggered']} 例；这不是 Agent Fallback Rate。",
        "",
        "## 未测量指标",
        "",
    ]
    lines.extend(
        f"- {name}：未测量（{reason}）。"
        for name, reason in aggregate["not_measured"].items()
    )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ACIS offline delivery evaluation")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "reports" / "delivery_eval"),
        help="report output directory (default: reports/delivery_eval)",
    )
    args = parser.parse_args(argv)

    summary = run()
    json_path, md_path = write_reports(summary, Path(args.output_dir))
    diagnosis = summary["aggregate"]["diagnosis_accuracy"]
    top3 = summary["aggregate"]["top3_accuracy"]
    print(f"delivery eval: {summary['case_count']} cases")
    print(f"  diagnosis_accuracy={diagnosis['correct']}/{diagnosis['scored']} ({diagnosis['rate']})")
    print(f"  top3_accuracy={top3['correct']}/{top3['scored']} ({top3['rate']})")
    print(f"  mean_latency_ms={summary['aggregate']['mean_latency_ms']}")
    print(f"  p50_latency_ms={summary['aggregate']['p50_latency_ms']}")
    print(f"  p95_latency_ms={summary['aggregate']['p95_latency_ms']}")
    print(f"  summary.json: {json_path}")
    print(f"  summary.md:   {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
