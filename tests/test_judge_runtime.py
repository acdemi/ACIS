"""Regression tests for Judge runtime configuration and observability."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import ClassVar

import pytest

from agents.types import AgentOutput, DebateResult, RequestContext
from utils.judge_runtime import (
    classify_failure,
    redact_error_detail,
    resolve_judge_config,
)


def test_judge_configuration_precedence() -> None:
    config = resolve_judge_config(
        {
            "AGRI_AI_JUDGE_API_KEY": "judge-key",
            "DEEPSEEK_API_KEY": "fallback-key",
            "AGRI_AI_JUDGE_BASE_URL": "https://judge.example/v1",
            "DEEPSEEK_BASE_URL": "https://fallback.example/v1",
            "AGRI_AI_JUDGE_MODEL": "judge-model",
            "DEEPSEEK_MODEL": "fallback-model",
            "AGRI_AI_JUDGE_PROVIDER": "custom-provider",
            "AGRI_AI_JUDGE_TIMEOUT_SECONDS": "12.5",
            "AGRI_AI_JUDGE_MAX_RETRIES": "1",
        }
    )
    assert config.api_key == "judge-key"
    assert config.base_url == "https://judge.example/v1"
    assert config.model == "judge-model"
    assert config.provider == "custom-provider"
    assert config.timeout_seconds == 12.5
    assert config.max_retries == 1
    assert config.sources == {
        "api_key": "AGRI_AI_JUDGE_API_KEY",
        "base_url": "AGRI_AI_JUDGE_BASE_URL",
        "model": "AGRI_AI_JUDGE_MODEL",
        "provider": "AGRI_AI_JUDGE_PROVIDER",
        "timeout_seconds": "AGRI_AI_JUDGE_TIMEOUT_SECONDS",
        "max_retries": "AGRI_AI_JUDGE_MAX_RETRIES",
    }


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Message(content)


class _Response:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(content)]
        self.usage = type("Usage", (), {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        })()


class _Completions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Response(self.content)


class _FakeClient:
    last_init: ClassVar[dict] = {}
    last_completions: ClassVar[_Completions | None] = None

    def __init__(self, **kwargs) -> None:
        type(self).last_init = dict(kwargs)
        self.chat = type("Chat", (), {})()
        self.chat.completions = _Completions(
            '{"final_diagnosis":"叶霉病","final_confidence":0.76,'
            '"risk_level":"medium","summary":"需要复核",'
            '"action_plan":["降低湿度"],"reasoning_trace":"证据一致"}'
        )
        type(self).last_completions = self.chat.completions


def _run(
    monkeypatch: pytest.MonkeyPatch,
    use_llm: bool = True,
    client_type: type = _FakeClient,
):
    import openai

    monkeypatch.setattr(openai, "OpenAI", client_type)
    import agents.judge_agent as judge_module

    monkeypatch.setattr(
        judge_module,
        "query_kg",
        lambda crop, query: {"diseases": [], "rules": [], "backend": "memory"},
    )
    agent = judge_module.JudgeAgent(use_llm=use_llm)
    context = RequestContext(query="叶背霉层", greenhouse_id="A", crop="番茄")
    outputs = [
        AgentOutput(
            layer="专家层",
            agent="病理Agent",
            claim="叶霉病",
            confidence=0.7,
        )
    ]
    debate = DebateResult([], [], [], "medium", {})
    return agent.run(context, outputs, debate)


def test_judge_success_records_safe_runtime_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGRI_AI_JUDGE_API_KEY", "super-secret-key-must-not-leak")
    monkeypatch.setenv("AGRI_AI_JUDGE_BASE_URL", "https://judge.example/v1?token=secret")
    monkeypatch.setenv("AGRI_AI_JUDGE_MODEL", "judge-pro")
    monkeypatch.setenv("AGRI_AI_JUDGE_PROVIDER", "test-provider")
    monkeypatch.setenv("AGRI_AI_JUDGE_TIMEOUT_SECONDS", "9")
    monkeypatch.setenv("AGRI_AI_JUDGE_MAX_RETRIES", "1")

    decision = _run(monkeypatch)

    assert decision.judge_mode == "deepseek"
    assert decision.decision == "叶霉病"
    assert decision.judge_analysis["confidence_design"]["self_report"] == 0.76
    assert 0.05 <= decision.confidence <= 0.95
    runtime = decision.judge_analysis["judge_runtime"]
    assert runtime["outcome"] == "success"
    assert runtime["provider"] == "test-provider"
    assert runtime["endpoint_id"] == "https://judge.example/v1"
    assert runtime["model"] == "judge-pro"
    assert runtime["sdk_max_retries"] == 1
    assert _FakeClient.last_init["timeout"] == 9.0
    assert _FakeClient.last_init["max_retries"] == 1
    serialized = json.dumps(asdict(decision), ensure_ascii=False)
    assert "super-secret-key-must-not-leak" not in serialized
    assert "token=secret" not in serialized
    assert "Authorization" not in serialized


class _FailNetworkClient(_FakeClient):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.chat.completions.create = self._fail

    def _fail(self, **kwargs):
        raise ConnectionError("Connection error.")


def test_connection_failure_falls_back_with_explicit_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGRI_AI_JUDGE_API_KEY", "connection-secret")
    monkeypatch.setenv("AGRI_AI_JUDGE_BASE_URL", "https://offline.example/v1")
    monkeypatch.setenv("AGRI_AI_JUDGE_MODEL", "offline-model")

    decision = _run(monkeypatch, client_type=_FailNetworkClient)

    assert decision.judge_mode == "rules"
    runtime = decision.judge_analysis["judge_runtime"]
    assert runtime["outcome"] == "fallback"
    assert runtime["fallback_reason_code"] == "connection_error"
    assert runtime["endpoint_id"] == "https://offline.example/v1"
    assert runtime["retry_exhausted"] is True
    assert any("connection_error" in item for item in decision.debate.missing_evidence)


def test_missing_credentials_fallbacks_without_creating_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openai

    monkeypatch.delenv("AGRI_AI_JUDGE_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def fail_if_called(**kwargs):
        raise AssertionError("OpenAI client must not be created without credentials")

    monkeypatch.setattr(openai, "OpenAI", fail_if_called)
    decision = _run(monkeypatch)

    assert decision.judge_mode == "rules"
    runtime = decision.judge_analysis["judge_runtime"]
    assert runtime["fallback_reason_code"] == "missing_credentials"
    assert runtime["outcome"] == "fallback"


class _MalformedClient(_FakeClient):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.chat.completions = _Completions("not-json")


def test_malformed_response_falls_back_as_response_format_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGRI_AI_JUDGE_API_KEY", "format-secret")
    decision = _run(monkeypatch, client_type=_MalformedClient)
    runtime = decision.judge_analysis["judge_runtime"]
    assert decision.judge_mode == "rules"
    assert runtime["fallback_reason_code"] == "response_format_error"


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (type("AuthenticationError", (Exception,), {"status_code": 401})("x"), "authentication_error"),
        (type("BillingError", (Exception,), {"status_code": 402})("x"), "billing_error"),
        (type("RateLimitError", (Exception,), {"status_code": 429})("x"), "rate_limit"),
        (TimeoutError("timed out"), "timeout"),
        (ConnectionError("Connection error."), "connection_error"),
        (ValueError("bad json"), "provider_error"),
    ],
)
def test_failure_taxonomy(exception: Exception, expected: str) -> None:
    assert classify_failure(exception) == expected


def test_fallback_detail_redacts_masked_key_suffix() -> None:
    detail = redact_error_detail(
        "Authentication Fails, Your api key: ****1562 is invalid",
        api_key="super-secret",
    )
    assert "****1562" not in detail
    assert "1562" not in detail


def test_judge_structured_success_through_real_openai_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx
    import openai

    monkeypatch.setenv("AGRI_AI_JUDGE_API_KEY", "sdk-secret")
    monkeypatch.setenv("AGRI_AI_JUDGE_BASE_URL", "https://judge.test/v1")
    monkeypatch.setenv("AGRI_AI_JUDGE_MODEL", "sdk-model")
    seen_headers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers.get("authorization", ""))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1,
                "model": "sdk-model",
                "choices": [{
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": (
                            '{"final_diagnosis":"番茄叶霉病",'
                            '"final_confidence":0.81,'
                            '"risk_level":"medium",'
                            '"summary":"结构化成功",'
                            '"action_plan":["通风"],'
                            '"reasoning_trace":"叶背霉层"}'
                        ),
                    },
                }],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 10,
                    "total_tokens": 30,
                },
            },
        )

    real_openai = openai.OpenAI

    def sdk_factory(**kwargs):
        kwargs["http_client"] = httpx.Client(transport=httpx.MockTransport(handler))
        return real_openai(**kwargs)

    decision = _run(monkeypatch, client_type=sdk_factory)
    assert decision.judge_mode == "deepseek"
    assert decision.decision == "番茄叶霉病"
    assert decision.judge_analysis["confidence_design"]["self_report"] == 0.81
    assert 0.05 <= decision.confidence <= 0.95
    assert decision.token_usage == {
        "judge_prompt_tokens": 20,
        "judge_completion_tokens": 10,
        "judge_total_tokens": 30,
    }
    assert seen_headers and seen_headers[0].startswith("Bearer ")


def test_invalid_or_infinite_timeout_uses_bounded_default() -> None:
    config = resolve_judge_config({"AGRI_AI_JUDGE_TIMEOUT_SECONDS": "inf"})
    assert config.timeout_seconds == 60.0
