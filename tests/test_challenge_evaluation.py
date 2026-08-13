"""Isolation tests for the Phase 4 evaluation pilot tooling.

Verifies the two evaluation scripts stay decoupled from agent internals and
that the raw-output pipeline actually generates per-(arm, case) files:

- ``test_challenge_evaluation_imports`` — both scripts import cleanly, their
  source never imports ``agents``, and the three arms carry the expected
  toggles.
- ``test_challenge_output_saved`` — runs the run-script pipeline against a
  fake ``evals.runner.run_evaluation`` and asserts one raw output file per
  case is written under the raw root.
- report generation tests — feeds fabricated raw outputs into the report
  generator and asserts the Markdown comparison table is produced.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.config import EvalCase, EvalConfig
from evals.metrics import CaseMetrics
from evals.runner import EvaluationResult
from openmetaphysics.evaluation import challenge_report
from scripts import run_challenge_evaluation as run_script

SCRIPT_SOURCES = (
    Path(run_script.__file__).resolve().read_text(encoding="utf-8"),
    Path(challenge_report.__file__).resolve().read_text(encoding="utf-8"),
)


# ---------------------------------------------------------------------------
# decoupling / imports
# ---------------------------------------------------------------------------


def test_challenge_evaluation_imports() -> None:
    """Both scripts import without touching agent internals."""
    assert callable(run_script.run_arm)
    assert callable(run_script.main)
    assert callable(challenge_report.build_report)
    assert callable(challenge_report.main)


def test_scripts_do_not_import_agents() -> None:
    """Evaluation scripts must not depend on agent internal state."""
    for source in SCRIPT_SOURCES:
        assert "from agents " not in source
        assert "from agents." not in source
        assert "import agents" not in source


def test_pilot_arms_defined_with_expected_toggles() -> None:
    assert set(run_script.CHALLENGE_ARMS) == {
        "c0_bare_baseline",
        "c1_all_on",
        "c2_no_memory",
    }
    c0 = run_script.CHALLENGE_ARMS["c0_bare_baseline"]
    assert not any(
        (c0.planner_on, c0.debate_on, c0.critic_on, c0.memory_on,
         c0.tool_router_on, c0.counterfactual_on)
    )
    c1 = run_script.CHALLENGE_ARMS["c1_all_on"]
    assert all(
        (c1.planner_on, c1.debate_on, c1.critic_on, c1.memory_on,
         c1.tool_router_on, c1.counterfactual_on)
    )
    c2 = run_script.CHALLENGE_ARMS["c2_no_memory"]
    assert c2.memory_on is False
    assert all(
        (c2.planner_on, c2.debate_on, c2.critic_on,
         c2.tool_router_on, c2.counterfactual_on)
    )


def test_flatten_challenge_set_produces_24_cases() -> None:
    data = json.loads(run_script.CHALLENGE_PATH.read_text(encoding="utf-8"))
    cases = run_script.flatten_challenge_set(data)
    assert len(cases) == 24
    assert len({case["id"] for case in cases}) == 24
    for case in cases:
        assert case["query"].strip()
        assert case["expected_key_factors"]
    assert all(case["group"] in {
        "ambiguity", "conflicting", "incomplete", "multi_step"
    } for case in cases)


# ---------------------------------------------------------------------------
# raw output generation
# ---------------------------------------------------------------------------


def _fake_trace_dict(trace_id: str, decision: str, confidence: float) -> dict:
    return {
        "trace_id": trace_id,
        "judge": [
            {
                "decision": decision,
                "confidence": confidence,
                "judge_mode": "rules",
                "reasoning_trace": "trace of " + decision,
                "action_plan": [],
            }
        ],
    }


def _fake_evaluation_result(
    tmp_path: Path,
    rows: list[tuple[str, str, str, float]],
) -> EvaluationResult:
    """Build a runner result whose trace files already exist on disk."""
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    for case_id, trace_id, decision, confidence in rows:
        (trace_dir / f"{trace_id}.json").write_text(
            json.dumps(
                _fake_trace_dict(trace_id, decision, confidence),
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    cases = [
        EvalCase(id=case_id, query="q", ground_truth="证据不足")
        for case_id, _, _, _ in rows
    ]
    metrics_rows = [
        CaseMetrics(
            case_id=case_id,
            trace_id=trace_id,
            expected="证据不足",
            decision=decision,
            accuracy=None,
            confidence=confidence,
            runtime_seconds=0.5,
            planner_usage=1.0,
            tool_usage=1.0,
            tool_requests=1,
            memory_hits=0,
            debate_rounds=1,
            counterfactual_count=0,
            collective_omission_count=0,
        )
        for case_id, trace_id, decision, confidence in rows
    ]
    return EvaluationResult(
        config=EvalConfig(dataset="fake"),
        cases=cases,
        rows=metrics_rows,
        aggregate={"cases": len(rows)},
        csv_path=tmp_path / "metrics.csv",
        summary_path=tmp_path / "summary.md",
        trace_dir=trace_dir,
    )


def _patch_fake_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    first_ids: list[str],
) -> list[dict[str, Any]]:
    """Replace ``evals.runner.run_evaluation`` with a fake; return its calls."""
    calls: list[dict[str, Any]] = []

    def fake_run_evaluation(config: EvalConfig) -> EvaluationResult:
        rows = []
        for index, case_id in enumerate(first_ids):
            rows.append(
                (case_id, f"trace-{index}", f"决策{index}", 0.5 + index * 0.1)
            )
        result = _fake_evaluation_result(tmp_path, rows)
        calls.append({"config": config, "result": result})
        return result

    monkeypatch.setattr("evals.runner.run_evaluation", fake_run_evaluation)
    return calls


def test_challenge_output_saved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The run pipeline writes one raw output file per (arm, case)."""
    cases = run_script.load_challenge_set()
    first_two = [case["id"] for case in cases[:2]]
    calls = _patch_fake_runner(monkeypatch, tmp_path, first_two)

    code = run_script.main(
        ["--output-dir", str(tmp_path), "--max-cases", "2"]
    )
    assert code == 0

    for arm in ("c0_bare_baseline", "c1_all_on", "c2_no_memory"):
        arm_dir = tmp_path / arm
        assert (arm_dir / "run_manifest.json").exists()
        for case_id in first_two:
            raw_path = arm_dir / f"{case_id}.json"
            assert raw_path.exists(), f"missing raw output {raw_path}"
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            assert raw["case_id"] == case_id
            assert raw["arm"] == arm
            assert raw["expected_key_factors"]
            assert "decision" in raw
            assert "confidence" in raw
            assert "trace" in raw

    # the fake runner was invoked once per arm with llm-judge enabled
    assert len(calls) == 3
    for call in calls:
        assert call["config"].use_llm_judge is True
        assert call["config"].save_traces is True


def test_challenge_output_saved_rules_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--rules-only disables the LLM judge and LangGraph path."""
    cases = run_script.load_challenge_set()
    first_two = [case["id"] for case in cases[:2]]
    calls = _patch_fake_runner(monkeypatch, tmp_path, first_two)

    code = run_script.main(
        ["--output-dir", str(tmp_path), "--max-cases", "2", "--rules-only"]
    )
    assert code == 0
    assert len(calls) == 3
    for call in calls:
        assert call["config"].use_llm_judge is False
        assert call["config"].use_langgraph is False


def test_challenge_run_skips_completed_arm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Arms with complete raw outputs are skipped unless --force."""
    cases = run_script.load_challenge_set()
    first_two = [case["id"] for case in cases[:2]]
    calls = _patch_fake_runner(monkeypatch, tmp_path, first_two)

    assert run_script.main(["--output-dir", str(tmp_path), "--max-cases", "2"]) == 0
    calls.clear()
    # second run: arms already complete -> no runner invocation
    assert run_script.main(["--output-dir", str(tmp_path), "--max-cases", "2"]) == 0
    assert calls == []
    # --force reruns
    assert run_script.main(
        ["--output-dir", str(tmp_path), "--max-cases", "2", "--force"]
    ) == 0
    assert len(calls) == 3


# ---------------------------------------------------------------------------
# report generation
# ---------------------------------------------------------------------------


def _write_fake_raw(arm_dir: Path, raw: dict[str, Any]) -> None:
    arm_dir.mkdir(parents=True, exist_ok=True)
    (arm_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "arm": arm_dir.name,
                "label": "Fake",
                "description": "fake arm",
                "seed": 42,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (arm_dir / f"{raw['case_id']}.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _fake_raw_case(
    case_id: str,
    group: str,
    factors: list[str],
    decision: str,
    confidence: float,
    judge_mode: str = "rules",
) -> dict[str, Any]:
    return {
        "arm": "c1_all_on",
        "arm_label": "C1 (Full)",
        "case_id": case_id,
        "group": group,
        "difficulty": 2,
        "input": "input text",
        "expected_key_factors": factors,
        "ground_truth": "证据不足",
        "crop": "tomato",
        "intent": "diagnose",
        "trace_id": "t1",
        "decision": decision,
        "confidence": confidence,
        "judge_mode": judge_mode,
        "reasoning_trace": "证据不足，需要补充病斑形状信息；叶背霉层待确认。",
        "action_plan": [],
        "runtime_seconds": 1.0,
        "trace": {},
    }


def test_report_generates_markdown_table(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    _write_fake_raw(
        raw_dir / "c1_all_on",
        _fake_raw_case(
            "inc_tomato_vague_spot",
            "incomplete",
            ["evidence_insufficient", "info_request", "differential"],
            "病理证据不足，不能确认具体病害",
            0.55,
        ),
    )
    _write_fake_raw(
        raw_dir / "c0_bare_baseline",
        _fake_raw_case(
            "inc_tomato_vague_spot",
            "incomplete",
            ["evidence_insufficient", "info_request", "differential"],
            "病理判断首选：番茄早疫病",
            0.8,
        ),
    )
    output = tmp_path / "report.md"
    build = challenge_report.build_report(raw_dir, output, use_llm=False)
    assert build == output
    text = output.read_text(encoding="utf-8")
    assert "Aggregate Results" in text
    assert "c1_all_on" in text
    assert "c0_bare_baseline" in text
    assert "accuracy" in text
    assert "Per-Group Breakdown" in text
    assert "incomplete" in text


def test_report_cli_main(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    raw_dir = tmp_path / "raw"
    _write_fake_raw(
        raw_dir / "c2_no_memory",
        _fake_raw_case(
            "amb_cotton_edge_vas",
            "ambiguity",
            ["edge_yellowing", "vascular_browning", "half_leaf_yellowing",
             "differential"],
            "病理判断首选：棉花黄萎病",
            0.7,
            judge_mode="deepseek",
        ),
    )
    output = tmp_path / "cli_report.md"
    code = challenge_report.main(
        ["--raw-dir", str(raw_dir), "--output", str(output), "--rules-only"]
    )
    assert code == 0
    assert output.exists()
    captured = capsys.readouterr().out
    assert "report written" in captured
    text = output.read_text(encoding="utf-8")
    assert "c2_no_memory" in text
    assert "fake arm" in text  # description read from the arm manifest


def test_report_no_raw_outputs_errors(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        challenge_report.build_report(
            tmp_path / "missing", tmp_path / "r.md", use_llm=False
        )
