"""Delivery contract tests for the minimal MVP (greenhouse tomato diagnosis).

Scope: the core text path, the fallback/human-review boundary, the unified
Trace export, the API data contract and the vision adapter's result parsing.
These tests intentionally do not require any external service or real LLM.
"""

from __future__ import annotations

import json

import pytest

import storage.db as storage_db
from agents.judge_agent import JudgeResponseFormatError
from agents.types import AgentOutput, DebateResult, DecisionOutput, RequestContext
from agents.vision_agent import VisionAgent
from debate.critic import CriticEngine
from orchestrator import AgentOrchestrator, _decision_payload, build_context
from trace import STAGE_ORDER, export_trace_json, trace_to_dict

QUERY = "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Every test writes its audit rows to a throw-away SQLite file."""
    monkeypatch.setattr(storage_db, "_DB_PATH", tmp_path / "delivery_test.db")
    monkeypatch.setenv("AGRI_AI_PERSIST", "1")


def _assert_decision_contract(decision, trace) -> None:
    assert isinstance(decision.decision, str) and decision.decision.strip()
    assert 0.0 <= decision.confidence <= 1.0
    assert decision.risk_level in {"low", "medium", "high"}
    assert isinstance(decision.need_human_review, bool)
    assert decision.action_plan, "action_plan must not be empty"
    assert decision.traces, "agent traces must not be empty"
    assert decision.judge_mode in {"rules", "deepseek"}
    assert decision.reasoning_trace
    assert "kg" in decision.judge_analysis
    assert trace is not None
    missing = set(STAGE_ORDER) - set(trace.stages_present)
    assert not missing, f"missing trace stages: {sorted(missing)}"


def test_rules_flow_contract():
    orchestrator = AgentOrchestrator(use_langgraph=False)
    decision = orchestrator.run(QUERY)

    _assert_decision_contract(decision, orchestrator.last_trace)
    assert decision.judge_mode == "rules"
    assert decision.decision_id is not None

    payload = trace_to_dict(orchestrator.last_trace)
    assert payload["trace_id"] == orchestrator.last_trace.trace_id
    assert payload["events"], "trace events must be serialized"
    assert all(stage in payload for stage in STAGE_ORDER)

    json_payload = json.loads(export_trace_json(orchestrator.last_trace))
    assert json_payload["trace_id"] == payload["trace_id"]


def test_langgraph_flow_contract():
    orchestrator = AgentOrchestrator(use_langgraph=True)
    decision = orchestrator.run(QUERY)

    _assert_decision_contract(decision, orchestrator.last_trace)
    assert decision.judge_mode == "rules"
    assert "request" in orchestrator.last_trace.stages_present


def test_persistence_failure_is_non_fatal(monkeypatch, caplog):
    import storage.repository as repository

    def _boom(*args, **kwargs):
        raise RuntimeError("sqlite is read-only")

    monkeypatch.setattr(repository, "save_decision", _boom)
    orchestrator = AgentOrchestrator(use_langgraph=False)
    with caplog.at_level("WARNING"):
        decision = orchestrator.run(QUERY)

    assert decision.decision
    assert decision.decision_id is None
    assert any("persistence failed" in record.getMessage() for record in caplog.records)


def test_langgraph_failure_falls_back_to_rules():
    orchestrator = AgentOrchestrator(use_langgraph=True)
    assert orchestrator._compiled_graph is not None

    class _BoomGraph:
        def invoke(self, state):  # noqa: ANN001 - test double
            raise RuntimeError("graph exploded")

    orchestrator._compiled_graph = _BoomGraph()
    decision = orchestrator.run(QUERY)

    assert decision.judge_mode == "rules"
    assert decision.decision
    assert any("回退规则编排" in item for item in decision.debate.missing_evidence)


@pytest.mark.parametrize(
    ("exc", "expected_code"),
    [
        (RuntimeError("sdk exploded"), "provider_error"),
        (JudgeResponseFormatError("response format invalid"), "response_format_error"),
    ],
)
def test_llm_judge_failure_falls_back_with_reason(monkeypatch, exc, expected_code):
    from agents.judge_agent import JudgeAgent

    def _boom(*args, **kwargs):
        raise exc

    monkeypatch.setattr(JudgeAgent, "_run_llm_judge", _boom)
    orchestrator = AgentOrchestrator(use_langgraph=False, use_llm_judge=True)
    decision = orchestrator.run(QUERY)

    runtime = decision.judge_analysis["judge_runtime"]
    assert decision.judge_mode == "rules"
    assert runtime["outcome"] == "fallback"
    assert runtime["fallback_reason_code"] == expected_code
    assert runtime["retry_exhausted"] is False
    assert any("LLM Judge 不可用" in item for item in decision.debate.missing_evidence)


def test_decision_payload_exposes_trace_identity():
    orchestrator = AgentOrchestrator(use_langgraph=False)
    decision = orchestrator.run(QUERY)

    payload = _decision_payload(decision, orchestrator.last_trace)
    assert payload["decision"] == decision.decision
    assert payload["trace_id"] == orchestrator.last_trace.trace_id
    assert payload["trace_stages"] == orchestrator.last_trace.stages_present


def test_vision_agent_parses_diagnosis_block(tmp_path, monkeypatch):
    import agents.vision as vision_module

    image_path = tmp_path / "tomato_leaf.jpg"
    image_path.write_bytes(b"not-a-real-image")
    monkeypatch.setattr(
        vision_module,
        "diagnose_image",
        lambda path: {
            "image_path": path,
            "diagnosis": {"primary": "番茄叶霉病", "confidence": 0.87, "top3": []},
            "note": "mock",
        },
    )
    context = RequestContext(
        query=QUERY, greenhouse_id="gh-a", crop="tomato", intent="diagnose",
        image_path=str(image_path),
    )
    output = VisionAgent().run(context)

    assert "番茄叶霉病" in output.claim
    assert output.confidence == 0.87
    assert "diagnosis" in output.evidence


def test_vision_agent_reports_visual_error(monkeypatch):
    import agents.vision as vision_module

    monkeypatch.setattr(vision_module, "diagnose_image", lambda path: {"error": "模型不可用"})
    context = RequestContext(
        query=QUERY, greenhouse_id="gh-a", crop="tomato", intent="diagnose",
        image_path="missing.jpg",
    )
    output = VisionAgent().run(context)
    # A missing path is handled before model invocation; the contract stays explicit.
    assert "无法执行视觉识别" in output.claim
    assert output.confidence == 0.0


def test_critic_rule_validation_contract():
    outputs = [
        AgentOutput(
            layer="感知层", agent="传感器Agent", claim="传感器读数整体正常", confidence=0.65,
            evidence={"reading": {"readings": {"air_humidity": 90.0}}},
        ),
        AgentOutput(
            layer="专家层", agent="病理Agent", claim="病理判断首选：番茄叶霉病", confidence=0.85,
        ),
        AgentOutput(
            layer="专家层", agent="气象Agent", claim="气象条件支持灌溉", confidence=0.72,
        ),
        AgentOutput(
            layer="专家层", agent="栽培Agent", claim="已生成栽培管理建议", confidence=0.68,
            warnings=["棚内湿度偏高，注意通风"],
        ),
    ]
    debate = DebateResult(
        consensus=[], conflicts=["灌溉与病害风险冲突"], missing_evidence=[], risk_level="medium"
    )
    refined, resolved = CriticEngine(use_llm=False).run(build_context(QUERY), outputs, debate)

    assert resolved.critic["triggered"] is True
    assert resolved.critic["mode"] == "rules"
    assert resolved.critic["down_weighted"], "critic must down-weight the weaker expert"
    meteorology = next(item for item in refined if item.agent == "气象Agent")
    assert meteorology.confidence < 0.72


def test_storage_roundtrip_contract():
    from storage.repository import get_decision, save_decision, set_feedback

    decision = DecisionOutput(
        summary="test",
        decision="病理判断首选：番茄叶霉病",
        confidence=0.7,
        risk_level="medium",
        action_plan=["a"],
        debate=DebateResult(consensus=[], conflicts=[], missing_evidence=[], risk_level="medium"),
        traces=[AgentOutput(layer="专家层", agent="病理Agent", claim="x", confidence=0.7)],
        judge_mode="rules",
        reasoning_trace="trace",
        judge_analysis={"kg": {"backend": "memory"}},
    )
    context = RequestContext(query=QUERY, greenhouse_id="gh-a", crop="tomato")
    decision_id = save_decision(decision, context, QUERY)
    assert decision_id > 0

    stored = get_decision(decision_id)
    assert stored["decision"] == decision.decision
    assert stored["judge_analysis"]["kg"]["backend"] == "memory"

    updated = set_feedback(decision_id, "correct", "ok")
    assert updated["feedback"] == "correct"


def test_api_diagnose_contract(monkeypatch):
    from fastapi.testclient import TestClient

    import gateway.app as gateway_module

    fake_decision = DecisionOutput(
        summary="fake",
        decision="病理判断首选：番茄叶霉病",
        confidence=0.7,
        risk_level="medium",
        action_plan=["a"],
        debate=DebateResult(consensus=[], conflicts=[], missing_evidence=[], risk_level="medium"),
        traces=[AgentOutput(layer="专家层", agent="病理Agent", claim="x", confidence=0.7)],
        judge_mode="rules",
        reasoning_trace="trace",
        judge_analysis={"kg": {"backend": "memory"}},
        decision_id=1,
    )

    class _FakeOrchestrator:
        last_trace = None

        def __init__(self, **kwargs):
            pass

        def run(self, query, image_path=None):
            return fake_decision

    monkeypatch.setattr(gateway_module, "AgentOrchestrator", _FakeOrchestrator)
    client = TestClient(gateway_module.app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert isinstance(health.json()["judge_configured"], bool)

    response = client.post("/diagnose", json={"query": QUERY})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == fake_decision.decision
    assert body["judge_mode"] == "rules"
    assert body["decision_id"] == 1
