from __future__ import annotations

import random

import pytest

from acis.agents.rag_memory_agent import RagMemoryAgent
from acis.core.types import RequestContext
from acis.core.orchestrator import AgentOrchestrator, build_context
from acis.knowledge.storage.repository import get_decision
from acis.ui.demo_cases import DEMO_CASES


MAIZE_QUERY, WHEAT_QUERY, INSUFFICIENT_QUERY = (case["query"] for case in DEMO_CASES)
TEST_API_KEY = "acis-test-key-0123456789abcdef0123456789"


@pytest.fixture
def isolated_database(monkeypatch: pytest.MonkeyPatch, tmp_path):
    import acis.knowledge.storage.db as database

    monkeypatch.setattr(database, "_DB_PATH", tmp_path / "delivery.sqlite3")
    monkeypatch.setenv("AGRI_AI_KG_BACKEND", "memory")
    monkeypatch.setenv("AGRI_AI_RAG_BACKEND", "memory")
    monkeypatch.setenv("AGRI_AI_PERSIST", "1")


@pytest.mark.parametrize(
    ("query", "expected", "crop"),
    [
        (MAIZE_QUERY, "玉米大斑病", "maize"),
        (WHEAT_QUERY, "小麦条锈病", "wheat"),
    ],
)
def test_cereal_diagnoses_include_evidence_report_and_persisted_trace(
    query: str,
    expected: str,
    crop: str,
    isolated_database,
):
    random.seed(7)
    orchestrator = AgentOrchestrator(use_langgraph=False)
    decision = orchestrator.run(query)

    assert expected in decision.decision
    assert decision.report["crop"]["code"] == crop
    assert decision.report["candidates"][0]["name"] == expected
    assert decision.report["knowledge_sources"]["rag"]
    assert decision.report["request_id"] == orchestrator.last_trace.trace_id
    assert all(output.execution["duration_ms"] is not None for output in decision.traces)

    stored = get_decision(decision.decision_id)
    assert stored["trace_id"] == orchestrator.last_trace.trace_id
    assert stored["trace_json"]["events"]
    assert stored["report_json"]["diagnosis"] == decision.decision


def test_insufficient_symptoms_abstain_and_request_more_information(isolated_database):
    random.seed(7)
    decision = AgentOrchestrator(use_langgraph=False).run(INSUFFICIENT_QUERY)

    assert "证据不足" in decision.decision
    assert decision.need_human_review
    assert decision.report["follow_up_questions"]
    assert not decision.report["candidates"]
    assert all("喷施" not in recommendation for recommendation in decision.action_plan)


def test_cereal_context_and_empty_input_validation():
    assert build_context(MAIZE_QUERY).crop == "maize"
    assert build_context(WHEAT_QUERY).crop == "wheat"
    with pytest.raises(ValueError, match="query"):
        build_context("   ")


def test_rag_distinguishes_backend_failure_from_no_matching_knowledge(monkeypatch):
    import acis.agents.rag_memory_agent as rag_agent_module

    context = RequestContext(
        query="玉米叶斑病",
        greenhouse_id="gh-a",
        crop="maize",
    )
    monkeypatch.setattr(
        rag_agent_module,
        "retrieve_with_backend",
        lambda *_args, **_kwargs: {
            "backend": "memory",
            "retrieval_status": "failed",
            "matches": [],
            "error": "Qdrant connection timeout",
        },
    )
    failed = RagMemoryAgent().run(context)
    assert failed.execution["status"] == "failed"
    assert failed.evidence["retrieval_status"] == "failed"
    assert failed.evidence["match_status"] == "no_results"
    assert "Qdrant connection timeout" in failed.evidence["error"]

    monkeypatch.setattr(
        rag_agent_module,
        "retrieve_with_backend",
        lambda *_args, **_kwargs: {"backend": "memory", "matches": []},
    )
    empty = RagMemoryAgent().run(context)
    assert empty.execution["status"] == "no_results"
    assert empty.evidence["retrieval_status"] == "no_results"
    assert empty.evidence["match_status"] == "no_results"


def test_agent_exception_is_recorded_as_failed_not_success(monkeypatch, isolated_database):
    def fail(_context):
        raise RuntimeError("sensor unavailable")

    orchestrator = AgentOrchestrator(use_langgraph=False)
    monkeypatch.setattr(orchestrator.sensor_agent, "run", fail)
    decision = orchestrator.run(MAIZE_QUERY)

    sensor = next(output for output in decision.traces if output.agent == "传感器Agent")
    assert sensor.execution["status"] == "failed"
    assert sensor.execution["error_type"] == "RuntimeError"
    assert "诊断执行失败" in sensor.claim


def test_memory_retriever_marks_empty_result_as_no_results(monkeypatch):
    import acis.knowledge.rag.retriever as retriever

    monkeypatch.setattr(retriever, "_get_backend", lambda: "memory")
    monkeypatch.setattr(retriever, "_memory_hits", lambda *_args, **_kwargs: [])

    result = retriever.retrieve_with_backend("未知作物的未见症状", "unknown")

    assert result["backend"] == "memory"
    assert result["retrieval_status"] == "no_results"
    assert result["matches"] == []
    assert "error" not in result


def test_vision_mock_and_inference_failure_are_not_reported_as_real_success(
    monkeypatch, tmp_path
):
    import acis.agents.vision as vision_module
    from acis.agents.vision_agent import VisionAgent

    image_path = tmp_path / "leaf.jpg"
    image_path.write_bytes(b"image")
    context = RequestContext(
        query=MAIZE_QUERY,
        greenhouse_id="gh-a",
        crop="maize",
        image_path=str(image_path),
    )
    monkeypatch.setattr(
        vision_module,
        "diagnose_image",
        lambda _path: {
            "diagnosis": {"primary": "mock label", "confidence": 0.8},
            "note": "使用模拟数据",
        },
    )
    mocked = VisionAgent().run(context)
    assert mocked.execution["status"] == "degraded"
    assert mocked.execution["mode"] == "mock"

    monkeypatch.setattr(
        vision_module,
        "diagnose_image",
        lambda _path: {"error": "inference failed", "fallback": "mock"},
    )
    failed = VisionAgent().run(context)
    assert failed.execution["status"] == "failed"
    assert failed.execution["mode"] == "transformers"


def test_langgraph_failure_is_visible_as_rules_fallback_in_trace(isolated_database):
    class FailingGraph:
        def invoke(self, _state):
            raise RuntimeError("graph unavailable")

    random.seed(7)
    orchestrator = AgentOrchestrator(use_langgraph=False)
    orchestrator._compiled_graph = FailingGraph()

    decision = orchestrator.run(MAIZE_QUERY)

    runtime = decision.judge_analysis["orchestration_runtime"]
    assert decision.status == "degraded"
    assert runtime["mode"] == "rules_fallback"
    judge_trace = next(
        event for event in orchestrator.last_trace.events if event.stage == "judge"
    )
    assert judge_trace.payload["judge_analysis"]["orchestration_runtime"] == runtime


def test_api_returns_real_diagnosis_report_and_trace(monkeypatch, isolated_database):
    from fastapi.testclient import TestClient
    import acis.api.app as gateway_module

    class RulesOrchestrator(AgentOrchestrator):
        def __init__(self, **kwargs):
            super().__init__(use_langgraph=False, **kwargs)

    monkeypatch.setattr(gateway_module, "AgentOrchestrator", RulesOrchestrator)
    monkeypatch.setenv("ACIS_API_KEY", TEST_API_KEY)
    random.seed(7)
    response = TestClient(gateway_module.app).post(
        "/diagnose",
        json={"query": MAIZE_QUERY},
        headers={"X-API-Key": TEST_API_KEY},
    )

    assert response.status_code == 200
    body = response.json()
    assert "玉米大斑病" in body["decision"]
    assert body["report"]["crop"]["code"] == "maize"
    assert body["report"]["knowledge_sources"]["rag"]
    assert body["trace_id"] == body["report"]["request_id"]
    assert any(event["stage"] == "memory" for event in body["trace"]["events"])


def test_builtin_case_patterns_are_not_claimed_as_confirmed_history(isolated_database):
    context = RequestContext(
        query="番茄叶片黄斑，背面有霉层",
        greenhouse_id="gh-a",
        crop="tomato",
    )
    output = AgentOrchestrator(use_langgraph=False).case_memory_agent.run(context)

    assert "内置示例模式" in output.claim
    assert output.evidence["source"] == "builtin_pattern"
    assert output.execution["mode"] == "builtin_pattern"


def test_critic_missing_credentials_records_rules_fallback(monkeypatch):
    from acis.reasoning.debate.critic import CriticEngine
    from acis.core.types import DebateResult

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    context = RequestContext(
        query="存在相互冲突的诊断证据",
        greenhouse_id="gh-a",
        crop="unknown",
    )
    debate = DebateResult(
        consensus=[],
        conflicts=["候选诊断结论冲突"],
        missing_evidence=[],
        risk_level="medium",
    )

    _outputs, resolved = CriticEngine(use_llm=True).run(context, [], debate)

    assert resolved.critic["mode"] == "rules"
    assert resolved.critic["requested_mode"] == "llm"
    assert resolved.critic["outcome"] == "fallback"
    assert resolved.critic["fallback_reason_code"] == "missing_credentials"


def test_api_key_protects_diagnosis_and_audit_routes(monkeypatch, isolated_database):
    from fastapi.testclient import TestClient
    import acis.api.app as gateway_module

    monkeypatch.delenv("ACIS_API_KEY", raising=False)
    client = TestClient(gateway_module.app)
    assert client.get("/health").status_code == 503
    assert client.post("/diagnose", json={"query": MAIZE_QUERY}).status_code == 503

    monkeypatch.setenv("ACIS_API_KEY", "short")
    assert client.get("/health").status_code == 503
    assert client.post(
        "/diagnose",
        json={"query": MAIZE_QUERY},
        headers={"X-API-Key": "short"},
    ).status_code == 503

    monkeypatch.setenv("ACIS_API_KEY", TEST_API_KEY)
    assert client.get("/health").status_code == 200
    assert client.post("/diagnose", json={"query": MAIZE_QUERY}).status_code == 401
    assert client.post(
        "/diagnose",
        json={"query": MAIZE_QUERY},
        headers={"X-API-Key": "wrong-key"},
    ).status_code == 401
    assert client.get("/decisions").status_code == 401

    headers = {"X-API-Key": TEST_API_KEY}
    response = client.post("/diagnose", json={"query": MAIZE_QUERY}, headers=headers)
    assert response.status_code == 200
    assert "玉米大斑病" in response.json()["decision"]
    assert client.get("/decisions", headers=headers).status_code == 200


def test_api_rejects_unbounded_server_image_paths(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import acis.api.app as gateway_module

    monkeypatch.setenv("ACIS_API_KEY", TEST_API_KEY)
    image_path = tmp_path / "outside.png"
    image_path.write_bytes(b"image")
    response = TestClient(gateway_module.app).post(
        "/diagnose",
        json={"query": MAIZE_QUERY, "image_path": str(image_path)},
        headers={"X-API-Key": TEST_API_KEY},
    )

    assert response.status_code == 422
    assert "image_path" in response.json()["detail"]


def test_api_accepts_staged_image_within_size_limit(monkeypatch, tmp_path):
    from io import BytesIO
    import acis.api.app as gateway_module
    from PIL import Image

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    image_path = upload_dir / "leaf.png"
    encoded = BytesIO()
    Image.new("RGB", (2, 2), color="green").save(encoded, format="PNG")
    image_path.write_bytes(encoded.getvalue())
    monkeypatch.setenv("ACIS_IMAGE_UPLOAD_DIR", str(upload_dir))

    assert gateway_module._validate_image_path(str(image_path)) == str(image_path.resolve())


def test_api_rejects_image_content_that_does_not_match_extension(monkeypatch, tmp_path):
    from io import BytesIO
    from fastapi import HTTPException
    import acis.api.app as gateway_module
    from PIL import Image

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    image_path = upload_dir / "not-really-jpeg.jpg"
    encoded = BytesIO()
    Image.new("RGB", (2, 2), color="green").save(encoded, format="PNG")
    image_path.write_bytes(encoded.getvalue())
    monkeypatch.setenv("ACIS_IMAGE_UPLOAD_DIR", str(upload_dir))

    with pytest.raises(HTTPException) as error:
        gateway_module._validate_image_path(str(image_path))
    assert error.value.status_code == 422


def test_api_rejects_staged_image_over_size_limit(monkeypatch, tmp_path):
    from fastapi import HTTPException
    import acis.api.app as gateway_module

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    image_path = upload_dir / "large.png"
    with image_path.open("wb") as image_file:
        image_file.truncate(gateway_module.MAX_IMAGE_BYTES + 1)
    monkeypatch.setenv("ACIS_IMAGE_UPLOAD_DIR", str(upload_dir))

    with pytest.raises(HTTPException) as error:
        gateway_module._validate_image_path(str(image_path))
    assert error.value.status_code == 413


def test_api_rejects_blank_and_oversized_queries(monkeypatch):
    from fastapi.testclient import TestClient
    import acis.api.app as gateway_module

    monkeypatch.setenv("ACIS_API_KEY", TEST_API_KEY)
    headers = {"X-API-Key": TEST_API_KEY}
    client = TestClient(gateway_module.app)
    assert client.post("/diagnose", json={"query": ""}, headers=headers).status_code == 422
    assert client.post(
        "/diagnose", json={"query": "症状" * 2001}, headers=headers
    ).status_code == 422


def test_api_validates_audit_query_and_feedback_parameters(monkeypatch):
    from fastapi.testclient import TestClient
    import acis.api.app as gateway_module

    monkeypatch.setenv("ACIS_API_KEY", TEST_API_KEY)
    client = TestClient(gateway_module.app)
    headers = {"X-API-Key": TEST_API_KEY}

    assert client.get("/decisions?limit=0", headers=headers).status_code == 422
    assert client.get("/decisions?limit=201", headers=headers).status_code == 422
    assert client.get("/decisions/0", headers=headers).status_code == 422
    assert client.post(
        "/decisions/0/feedback",
        json={"feedback": "correct"},
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/decisions/0/outcome",
        json={"outcome": "有效"},
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/decisions/1/feedback",
        json={"feedback": "unrecognized"},
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/decisions/1/feedback",
        json={"feedback": "correct", "note": "x" * 2001},
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/decisions/1/outcome",
        json={"outcome": "unknown"},
        headers=headers,
    ).status_code == 422


def test_neo4j_driver_is_not_created_without_explicit_password(monkeypatch):
    import acis.knowledge.kg.adapter as kg_adapter

    monkeypatch.setenv("NEO4J_PASSWORD", "")
    monkeypatch.setattr(kg_adapter, "_driver", None)

    assert kg_adapter._get_driver() is None


def test_neo4j_importer_requires_explicit_password(monkeypatch):
    from scripts import import_agrikg

    monkeypatch.setattr(import_agrikg, "NEO4J_PASSWORD", "")

    with pytest.raises(RuntimeError, match="NEO4J_PASSWORD"):
        import_agrikg.get_driver()
