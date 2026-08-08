"""Unit tests for the ablation framework (Phase 2.1E, Sprint 04).

Covers combo generation, toggle-to-config passing, contribution matrix
math, the ablation Markdown report, and end-to-end ablation runs over the
fast fixture dataset (all combos, small case count).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.ablation import (
    ABLATION_COMBOS,
    REQUIRED_COMBOS,
    combo_config,
    combo_names,
    get_combo,
    run_ablation,
)
from evals.config import AblationConfig, EvalConfig
from evals.metrics import CaseMetrics
from evals.report import (
    AblationResult,
    compute_ablation_metrics,
    contribution_deltas,
    write_ablation_report,
)


def _row(
    case_id: str,
    accuracy: float | None,
    confidence: float,
    *,
    memory_hits: int = 0,
    debate_rounds: int = 1,
    counterfactual_count: int = 0,
    collective_omission_count: int = 0,
    expected: str | None = "叶霉病",
) -> CaseMetrics:
    return CaseMetrics(
        case_id=case_id,
        trace_id=f"trace-{case_id}",
        expected=expected,
        decision="d",
        accuracy=accuracy,
        confidence=confidence,
        runtime_seconds=0.01,
        planner_usage=1.0,
        tool_usage=1.0,
        tool_requests=1,
        memory_hits=memory_hits,
        debate_rounds=debate_rounds,
        counterfactual_count=counterfactual_count,
        collective_omission_count=collective_omission_count,
    )


def _full_toggles(**overrides: bool) -> dict[str, bool]:
    toggles = {
        "planner_on": True,
        "debate_on": True,
        "critic_on": True,
        "memory_on": True,
        "tool_router_on": True,
        "counterfactual_on": True,
    }
    toggles.update(overrides)
    return toggles


# ------------------------------ combo generation ---------------------------


def test_required_combos_are_defined() -> None:
    names = combo_names()
    for required in REQUIRED_COMBOS:
        assert required in names
    assert len(ABLATION_COMBOS) >= 5


def test_combo_names_are_unique() -> None:
    names = combo_names()
    assert len(names) == len(set(names))


def test_required_combo_toggle_semantics() -> None:
    assert get_combo("all_on").toggles() == _full_toggles()
    assert get_combo("no_planner").planner_on is False
    assert get_combo("no_debate").debate_on is False
    assert get_combo("no_debate").critic_on is True  # 保留 Critic
    assert get_combo("no_memory").memory_on is False
    assert get_combo("no_counterfactual").counterfactual_on is False
    assert get_combo("no_tool_router").tool_router_on is False
    assert get_combo("no_critic").critic_on is False


def test_unknown_combo_is_rejected() -> None:
    with pytest.raises(ValueError):
        get_combo("no_such_combo")


# ----------------------------- config passing ------------------------------


def test_ablation_config_defaults() -> None:
    config = AblationConfig()
    assert config.dataset == "evals.fixtures"
    assert config.output_dir == "results/ablation"
    assert config.combos == ()
    assert config.max_cases is None
    assert config.use_langgraph is True


def test_combo_config_maps_toggles() -> None:
    for combo in ABLATION_COMBOS:
        config = combo_config(
            combo,
            dataset="evals.fixtures",
            output_dir="out",
            seed=7,
            max_cases=2,
            use_langgraph=False,
        )
        assert isinstance(config, EvalConfig)
        assert config.dataset == "evals.fixtures"
        assert config.output_dir == "out"
        assert config.seed == 7
        assert config.max_cases == 2
        assert config.use_langgraph is False
        assert config.planner_on == combo.planner_on
        assert config.debate_on == combo.debate_on
        assert config.critic_on == combo.critic_on
        assert config.memory_on == combo.memory_on
        assert config.tool_router_on == combo.tool_router_on
        assert config.counterfactual_on == combo.counterfactual_on


# ---------------------------- matrix math/report ---------------------------


def test_contribution_deltas_math() -> None:
    baseline: dict[str, float | int | None] = {
        "accuracy": 1.0,
        "average_confidence": 0.8,
        "memory_hits": 20,
    }
    combo: dict[str, float | int | None] = {
        "accuracy": 0.75,
        "average_confidence": 0.6,
        "memory_hits": 0,
    }
    deltas = contribution_deltas(baseline, combo)
    assert deltas["accuracy"] == pytest.approx(0.25)
    assert deltas["average_confidence"] == pytest.approx(0.2)
    assert deltas["memory_hits"] == pytest.approx(20)
    assert deltas["debate_rounds"] is None  # missing in both → None


def test_compute_ablation_metrics_disease_recall() -> None:
    rows = [
        _row("a", 1.0, 0.8),
        _row("b", 0.0, 0.6),
        _row("c", None, 0.5, expected=None),
        _row("d", 1.0, 0.5, expected="证据不足"),
    ]
    values = compute_ablation_metrics(rows)
    assert values["disease_recall"] == pytest.approx(0.5)
    assert values["accuracy"] == pytest.approx(2 / 3)


def test_write_ablation_report_contains_matrix(tmp_path: Path) -> None:
    baseline = AblationResult(
        combo_name="all_on",
        description="基线",
        toggles=_full_toggles(),
        aggregate={},
        rows=[_row("a", 1.0, 0.8, memory_hits=2), _row("b", 1.0, 0.8, memory_hits=2)],
        combo_dir=tmp_path / "all_on",
    )
    no_memory = AblationResult(
        combo_name="no_memory",
        description="关闭记忆",
        toggles=_full_toggles(memory_on=False),
        aggregate={},
        rows=[_row("a", 0.5, 0.6), _row("b", 0.5, 0.6)],
        combo_dir=tmp_path / "no_memory",
    )
    report_path = write_ablation_report(
        [baseline, no_memory],
        tmp_path,
        dataset="synthetic",
        generated_at="2026-01-01T00:00:00+00:00",
    )
    text = report_path.read_text(encoding="utf-8")
    assert report_path.name == "REPORT.md"
    assert "## 配置矩阵" in text
    assert "## 贡献度矩阵（Δ = baseline − combo）" in text
    assert "| no_memory |" in text
    assert "+0.500" in text  # accuracy Δ = 1.0 − 0.5
    assert "+0.200" in text  # confidence Δ = 0.8 − 0.6


# ---------------------------- end-to-end runs ------------------------------


def test_run_ablation_all_combos(tmp_path: Path) -> None:
    config = AblationConfig(
        dataset="evals.fixtures",
        output_dir=str(tmp_path),
        max_cases=2,
        use_langgraph=False,
    )
    result = run_ablation(config)
    names = [r.combo_name for r in result.combo_results]
    assert names == list(combo_names())
    assert result.report_path.is_file()
    report = result.report_path.read_text(encoding="utf-8")
    assert "贡献度矩阵" in report

    by_name = {r.combo_name: r for r in result.combo_results}
    for combo in ABLATION_COMBOS:
        combo_dir = by_name[combo.name].combo_dir
        assert (combo_dir / "metrics.csv").is_file()
        assert by_name[combo.name].aggregate["accuracy"] is not None

    assert by_name["no_memory"].aggregate["memory_hits"] == 0
    assert by_name["no_debate"].aggregate["debate_rounds"] == 0
    assert by_name["no_counterfactual"].aggregate["counterfactual_count"] == 0
    assert by_name["no_planner"].aggregate["planner_usage"] == 0.0


def test_run_ablation_selected_combos(tmp_path: Path) -> None:
    config = AblationConfig(
        dataset="evals.fixtures",
        output_dir=str(tmp_path),
        combos=("all_on", "no_planner"),
        max_cases=1,
        use_langgraph=False,
    )
    result = run_ablation(config)
    assert [r.combo_name for r in result.combo_results] == ["all_on", "no_planner"]
    run_dir = result.run_dir
    assert (run_dir / "all_on" / "metrics.csv").is_file()
    assert (run_dir / "no_planner" / "metrics.csv").is_file()
    assert not (run_dir / "no_memory").exists()


