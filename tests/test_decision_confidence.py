"""Tests for ADR-005 decision confidence, abstention policy and memory gate."""
from __future__ import annotations

import math

import pytest

from agents.judge_agent import JudgeAgent
from agents.types import AgentOutput
from decision_semantics import is_abstention
from utils.confidence_calibration import (
    DecisionCalibrator,
    combine_decision_score,
    compute_decision_signals,
    parse_signed_delta,
)


def test_parse_signed_delta_handles_common_forms():
    assert parse_signed_delta("+0.15") == pytest.approx(0.15)
    assert parse_signed_delta("-0.10") == pytest.approx(-0.10)
    assert parse_signed_delta("15%") == pytest.approx(0.15)
    assert parse_signed_delta(None) == 0.0
    assert parse_signed_delta("garbage") == 0.0
    assert parse_signed_delta(9.0) == pytest.approx(0.2)  # bounded


def test_signals_extract_kg_support_and_omission():
    llm = {
        "final_confidence": 0.6,
        "consistency_analysis": {
            "agent_diagnoses": [
                {"kg_match": "完全匹配"},
                {"kg_match": "部分匹配"},
                {"kg_match": "冲突"},
                {"kg_match": "完全匹配"},
            ],
            "critical_conflicts": ["a"],
        },
        "evidence_scores": {"甲": 8, "乙": 6},
        "kg_contribution": "+0.10",
    }
    analysis = {"collective_omission": {"omitted_diseases": ["x", "y"]}, "critic": {"escalate": True}}
    signals = compute_decision_signals(llm, analysis, None)
    assert signals["self_report"] == pytest.approx(0.6)
    assert signals["kg_support"] == pytest.approx((2 + 0.5) / 4)
    assert signals["evidence_strength"] == pytest.approx(0.7)
    assert signals["omission_count"] == 2
    assert signals["critic_escalate"] is True
    assert signals["kg_contribution"] == pytest.approx(0.10)
    assert signals["conflict_count"] >= 1


def test_decision_score_is_bounded_and_penalises_conflict():
    clean = {"self_report": 0.5, "evidence_strength": 0.5, "kg_support": 0.5}
    conflicted = dict(clean, conflict_count=3, omission_count=2, critic_escalate=True)
    assert combine_decision_score(clean) > combine_decision_score(conflicted)
    for signals in (clean, conflicted, {"self_report": 5.0}, {}):
        score = combine_decision_score(signals)
        assert 0.05 <= score <= 0.95


def test_self_consistency_enters_the_structural_score():
    base = {"self_report": 0.4, "evidence_strength": 0.4, "kg_support": 0.4}
    without = combine_decision_score(base)
    low_agreement = combine_decision_score(dict(base, self_consistency=0.0))
    high_agreement = combine_decision_score(dict(base, self_consistency=1.0))
    assert high_agreement > low_agreement
    # different weighting regime once the signal exists
    assert without != high_agreement


def test_calibrator_identity_without_data():
    calibrator = DecisionCalibrator(data_path="/nonexistent/path.json")
    assert calibrator.status()["model"] == "identity"
    assert calibrator.calibrate(0.42) == pytest.approx(0.42)


def test_memory_gate_drops_low_confidence_and_no_match(monkeypatch):
    monkeypatch.delenv("AGRI_AI_MEMORY_GATE", raising=False)
    monkeypatch.delenv("AGRI_AI_MEMORY_GATE_MIN_CONF", raising=False)
    outputs = [
        AgentOutput(layer="专家层", agent="病理Agent", claim="番茄早疫病", confidence=0.8),
        AgentOutput(layer="记忆层", agent="RAG", claim="症状最匹配：番茄叶霉病", confidence=0.39),
        AgentOutput(layer="记忆层", agent="历史病例库", claim="历史案例库暂无强匹配案例", confidence=0.9),
        AgentOutput(layer="记忆层", agent="知识图谱", claim="已提取作物最佳环境约束", confidence=0.7),
    ]
    kept, stats = JudgeAgent._gate_memory_outputs(outputs)
    agents = [o.agent for o in kept]
    assert "RAG" not in agents
    assert "历史病例库" not in agents
    assert "知识图谱" in agents
    assert "病理Agent" in agents
    assert len(stats["dropped"]) == 2


def test_memory_gate_can_be_disabled(monkeypatch):
    monkeypatch.setenv("AGRI_AI_MEMORY_GATE", "0")
    outputs = [AgentOutput(layer="记忆层", agent="RAG", claim="x", confidence=0.1)]
    kept, stats = JudgeAgent._gate_memory_outputs(outputs)
    assert len(kept) == 1
    assert stats["enabled"] is False


def test_abstention_policy_keeps_abstention_when_evidence_is_thin():
    agent = JudgeAgent(use_llm=False)
    signals = {"kg_support": 0.1, "evidence_strength": 0.2, "conflict_count": 0}
    decision, detail = agent._apply_abstention_policy("证据不足，建议采样", signals, [])
    assert is_abstention(decision)
    assert detail["overridden"] is False


def test_abstention_policy_overrides_false_abstention():
    agent = JudgeAgent(use_llm=False)
    outputs = [
        AgentOutput(layer="专家层", agent="病理Agent", claim="番茄早疫病", confidence=0.8),
        AgentOutput(layer="专家层", agent="环境Agent", claim="番茄早疫病", confidence=0.7),
    ]
    signals = {"kg_support": 0.9, "evidence_strength": 0.8, "conflict_count": 0}
    decision, detail = agent._apply_abstention_policy("无法定论", signals, outputs)
    assert not is_abstention(decision)
    assert detail["overridden"] is True


def test_abstention_policy_respects_conflicts():
    agent = JudgeAgent(use_llm=False)
    outputs = [AgentOutput(layer="专家层", agent="病理Agent", claim="番茄早疫病", confidence=0.8)]
    signals = {"kg_support": 0.9, "evidence_strength": 0.9, "conflict_count": 2}
    decision, detail = agent._apply_abstention_policy("证据不足", signals, outputs)
    assert is_abstention(decision)
    assert detail["overridden"] is False
