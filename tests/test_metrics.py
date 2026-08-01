"""Unit tests for the Evaluation Runner metrics (Phase 2.1E, Sprint 02).

Covers metrics generation from unified Traces (accuracy, confidence, runtime,
planner/tool usage, memory hits, debate rounds, counterfactual and collective
omission counts), aggregation, CSV + Markdown report writing, and dataset
loading.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.config import EvalConfig, load_dataset  # noqa: E402
from evals.metrics import (  # noqa: E402
    MEMORY_HIT_CONFIDENCE,
    CaseMetrics,
    aggregate_metrics,
    compute_trace_metrics,
)
from evals.report import (  # noqa: E402
    AGGREGATE_CASE_ID,
    CSV_FIELDS,
    write_metrics_csv,
    write_summary_markdown,
)
from trace import Trace, TraceEvent  # noqa: E402

FIXED_TIME = "2026-01-01T00:00:00+00:00"


def _agent_payload(
    agent: str,
    confidence: float,
    claim: str = "claim",
    *,
    counterfactual: dict | None = None,
    counterfactual_observations: list[str] | None = None,
) -> dict:
    layer = "记忆层" if agent in {"RAG", "KG", "历史案例Agent"} else "专家层"
    return {
        "layer": layer,
        "agent": agent,
        "claim": claim,
        "confidence": confidence,
        "evidence": {},
        "warnings": [],
        "recommendations": [],
        "counterfactual": counterfactual or {},
        "counterfactual_observations": counterfactual_observations or [],
    }


def _event(stage: str, payload: dict) -> TraceEvent:
    return TraceEvent(stage=stage, timestamp=FIXED_TIME, payload=payload)


def _base_trace() -> Trace:
    trace = Trace(trace_id="trace-1", timestamp=FIXED_TIME)
    trace.append(_event("request", {"query": "温室A番茄叶片黄斑"}))
    trace.append(_event("perception", _agent_payload("视觉Agent", 0.9)))
    trace.append(_event("memory", _agent_payload("RAG", 0.72, "症状最匹配：叶霉病")))
    trace.append(_event("memory", _agent_payload("KG", 0.3)))
    trace.append(
        _event(
            "experts",
            _agent_payload("病理Agent", 0.7, "病理判断首选：番茄叶霉病"),
        )
    )
    trace.append(
        _event(
            "debate",
            {
                "consensus": ["共识1"],
                "conflicts": [],
                "missing_evidence": [],
                "risk_level": "medium",
            },
        )
    )
    trace.append(_event("critic", {"triggered": False}))
    trace.append(
        _event(
            "judge",
            {
                "decision": "病理判断首选：番茄叶霉病",
                "confidence": 0.72,
                "judge_analysis": {
                    "collective_omission": {
                        "ignored_candidates": ["霜霉病"],
                        "omission_score": 0.25,
                        "omission_level": "warn",
                    }
                },
            },
        )
    )
    trace.append(
        _event(
            "planner",
            {"enabled": True, "goal": "g", "required_tools": ["spray_workorder"]},
        )
    )
    trace.append(
        _event(
            "tool_router",
            {
                "enabled": True,
                "requests": [{"tool_name": "spray_workorder"}],
                "unresolved": [],
            },
        )
    )
    trace.append(
        _event(
            "metrics",
            {
                "planner": {"enabled": True, "required_tools": 1},
                "tool_router": {"enabled": True, "requests": 1, "unresolved": 0},
                "total_events": 11,
            },
        )
    )
    return trace


# ------------------------------ metrics -----------------------------------
def test_metrics_has_all_required_fields():
    row = compute_trace_metrics(
        _base_trace(),
        case_id="case-1",
        runtime_seconds=1.25,
        expected="叶霉病",
    )
    assert isinstance(row, CaseMetrics)
    assert row.accuracy == 1.0
    assert row.confidence == 0.72
    assert row.runtime_seconds == 1.25
    assert row.planner_usage == 1.0
    assert row.tool_usage == 1.0
    assert row.tool_requests == 1
    assert row.memory_hits == 1  # only RAG at 0.72 >= 0.5
    assert row.debate_rounds == 1
    assert row.counterfactual_count == 0
    assert row.collective_omission_count == 1


def test_accuracy_match_and_miss():
    trace = _base_trace()
    assert compute_trace_metrics(trace, expected="叶霉病").accuracy == 1.0
    assert compute_trace_metrics(trace, expected="早疫病").accuracy == 0.0


def test_accuracy_insufficient_evidence_special_case():
    trace = _base_trace()
    trace.events[4] = _event(
        "experts",
        _agent_payload("病理Agent", 0.4, "病理证据不足，需补充图像"),
    )
    assert compute_trace_metrics(trace, expected="证据不足").accuracy == 1.0
    assert compute_trace_metrics(trace, expected="叶霉病").accuracy == 0.0


def test_accuracy_none_without_ground_truth():
    assert compute_trace_metrics(_base_trace(), expected=None).accuracy is None


def test_planner_and_tool_usage_disabled():
    trace = _base_trace()
    trace.events[10] = _event(
        "metrics",
        {
            "planner": {"enabled": False, "required_tools": 0},
            "tool_router": {"enabled": False, "requests": 0, "unresolved": 0},
            "total_events": 11,
        },
    )
    row = compute_trace_metrics(trace)
    assert row.planner_usage == 0.0
    assert row.tool_usage == 0.0
    assert row.tool_requests == 0


def test_memory_hits_threshold_boundary():
    trace = _base_trace()
    trace.events = [
        _event("memory", _agent_payload("RAG", 0.72)),
        _event("memory", _agent_payload("KG", 0.3)),
        _event("memory", _agent_payload("历史案例Agent", MEMORY_HIT_CONFIDENCE)),
    ]
    assert compute_trace_metrics(trace).memory_hits == 2


def test_debate_rounds_off_is_zero():
    row = compute_trace_metrics(_base_trace(), debate_on=False)
    assert row.debate_rounds == 0


def test_debate_rounds_from_multi_round_marker():
    trace = _base_trace()
    trace.events[5] = _event(
        "debate",
        {
            "consensus": ["【多轮辩论·第2轮】已携带前1轮辩论上下文"],
            "conflicts": [],
            "missing_evidence": [],
            "risk_level": "medium",
        },
    )
    assert compute_trace_metrics(trace).debate_rounds == 2


def test_counterfactual_count_counts_events_with_content():
    trace = _base_trace()
    trace.events.append(
        _event(
            "experts",
            _agent_payload(
                "病理Agent",
                0.7,
                "首选",
                counterfactual={"alternative": "早疫病"},
            ),
        )
    )
    trace.events.append(
        _event(
            "experts",
            _agent_payload(
                "气象Agent",
                0.6,
                "灌溉",
                counterfactual_observations=["若湿度上升"],
            ),
        )
    )
    trace.events.append(_event("experts", _agent_payload("栽培Agent", 0.6)))
    assert compute_trace_metrics(trace).counterfactual_count == 2


def test_collective_omission_count_and_missing_default():
    row = compute_trace_metrics(_base_trace())
    assert row.collective_omission_count == 1

    trace = _base_trace()
    trace.events[7] = _event("judge", {"decision": "d", "confidence": 0.5})
    assert compute_trace_metrics(trace).collective_omission_count == 0


def test_runtime_is_clamped_non_negative():
    row = compute_trace_metrics(_base_trace(), runtime_seconds=-0.5)
    assert row.runtime_seconds == 0.0


def test_aggregate_metrics_means_and_sums():
    first = compute_trace_metrics(
        _base_trace(),
        case_id="a",
        runtime_seconds=1.0,
        expected="叶霉病",
    )
    second = compute_trace_metrics(
        _base_trace(),
        case_id="b",
        runtime_seconds=3.0,
        expected="早疫病",  # miss
    )
    unlabeled = compute_trace_metrics(
        _base_trace(),
        case_id="c",
        runtime_seconds=2.0,
        expected=None,
    )
    aggregate = aggregate_metrics([first, second, unlabeled])
    assert aggregate["cases"] == 3
    assert aggregate["scored_cases"] == 2
    assert aggregate["accuracy"] == pytest.approx(0.5)
    assert aggregate["average_confidence"] == pytest.approx(0.72)
    assert aggregate["average_runtime"] == pytest.approx(2.0)
    assert aggregate["planner_usage"] == pytest.approx(1.0)
    assert aggregate["tool_usage"] == pytest.approx(1.0)
    assert aggregate["memory_hits"] == 3
    assert aggregate["debate_rounds"] == pytest.approx(1.0)
    assert aggregate["counterfactual_count"] == 0
    assert aggregate["collective_omission_count"] == 3


# ------------------------------- reports ----------------------------------
def test_write_metrics_csv_round_trips(tmp_path: Path):
    rows = [
        compute_trace_metrics(
            _base_trace(),
            case_id="a",
            runtime_seconds=1.0,
            expected="叶霉病",
        ),
        compute_trace_metrics(
            _base_trace(),
            case_id="b",
            runtime_seconds=2.0,
            expected=None,
        ),
    ]
    aggregate = aggregate_metrics(rows)
    path = tmp_path / "metrics.csv"
    write_metrics_csv(rows, aggregate, path)

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = list(csv.DictReader(handle))
    assert list(reader[0].keys()) == CSV_FIELDS
    assert len(reader) == 3  # 2 cases + aggregate
    assert reader[0]["case_id"] == "a"
    assert reader[0]["accuracy"] == "1.0"
    assert reader[1]["expected"] == ""
    assert reader[2]["case_id"] == AGGREGATE_CASE_ID
    assert reader[2]["memory_hits"] == "2"


def test_write_summary_markdown(tmp_path: Path):
    rows = [compute_trace_metrics(_base_trace(), case_id="a", expected="叶霉病")]
    aggregate = aggregate_metrics(rows)
    path = tmp_path / "summary.md"
    write_summary_markdown(
        aggregate,
        EvalConfig(dataset="evals.fixtures"),
        rows,
        path,
        generated_at="2026-01-01T00:00:00+00:00",
    )
    text = path.read_text(encoding="utf-8")
    assert "# Evaluation Summary" in text
    assert "## Configuration" in text
    assert "## Metrics" in text
    assert "| accuracy |" in text
    assert "| planner | on |" in text
    assert "| debate | on |" in text
    assert "| memory | on |" in text
    assert "| tool_router | on |" in text
    assert "| a | 1.00 |" in text
    assert "Generated: 2026-01-01T00:00:00+00:00" in text


# -------------------------------- config ----------------------------------
def test_config_defaults():
    config = EvalConfig()
    assert config.dataset == "evals.fixtures"
    assert config.planner_on is True
    assert config.debate_on is True
    assert config.memory_on is True
    assert config.tool_router_on is True
    assert config.output_dir == "results"


def test_load_dataset_builtin_fixtures():
    cases = load_dataset("evals.fixtures")
    assert len(cases) == 12
    first = cases[0]
    assert first.id == "tomato_leaf_mold"
    assert first.query
    assert first.ground_truth == "叶霉病"


def test_load_dataset_json(tmp_path: Path):
    dataset = {
        "cases": [
            {"id": "x", "query": "q1", "ground_truth": "叶霉病"},
            {"id": "y", "query": "q2"},
        ]
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    cases = load_dataset(str(path))
    assert [case.id for case in cases] == ["x", "y"]
    assert cases[1].ground_truth is None


def test_load_dataset_rejects_bad_case(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps([{"id": "x"}], ensure_ascii=False),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_dataset(str(path))
