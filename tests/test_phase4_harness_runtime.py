"""Phase 4.2 direct-harness retry and runtime semantics regressions."""

from __future__ import annotations

from typing import ClassVar

import pytest

from scripts import run_phase4_2


class _Usage:
    prompt_tokens = 7
    completion_tokens = 5
    total_tokens = 12


class _Message:
    content = '{"diagnosis":"叶霉病","confidence":0.8,"coherence":4,"reasoning":"ok"}'


class _Choice:
    message = _Message()


class _Response:
    choices: ClassVar[list[_Choice]] = [_Choice()]
    usage: ClassVar[_Usage] = _Usage()


class _SeedRejectingCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "seed" in kwargs:
            exc = RuntimeError("unsupported parameter: seed")
            exc.status_code = 400
            raise exc
        return _Response()


class _SeedRejectingClient:
    init_kwargs: ClassVar[dict] = {}

    def __init__(self, **kwargs) -> None:
        type(self).init_kwargs = kwargs
        self.chat = type("Chat", (), {})()
        self.chat.completions = _SeedRejectingCompletions()


def test_seed_fallback_is_recorded_and_sdk_retries_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openai

    monkeypatch.setattr(openai, "OpenAI", _SeedRejectingClient)
    result = run_phase4_2.call_deepseek_api(
        "prompt",
        seed=42,
        model="m",
        base_url="https://example.invalid/v1",
        api_key="secret",
        timeout_seconds=5,
    )
    assert result["status"] == "ok"
    assert result["seed_accepted"] is False
    assert result["attempts"] == 1
    assert result["request_count"] == 2
    assert result["retry_count"] == 1
    assert _SeedRejectingClient.init_kwargs["max_retries"] == 0
    assert _SeedRejectingClient.init_kwargs["timeout"] == 5


class _FailingCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        raise ConnectionError("Connection error.")


class _FailingClient:
    instances: ClassVar[list[_FailingClient]] = []
    init_kwargs: ClassVar[dict] = {}

    def __init__(self, **kwargs) -> None:
        type(self).init_kwargs = kwargs
        self.chat = type("Chat", (), {})()
        self.chat.completions = _FailingCompletions()
        type(self).instances.append(self)


def test_connection_retries_have_one_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openai

    monkeypatch.setattr(openai, "OpenAI", _FailingClient)
    monkeypatch.setattr(run_phase4_2, "MAX_ATTEMPTS", 2)
    monkeypatch.setattr(run_phase4_2.time, "sleep", lambda _: None)
    _FailingClient.instances.clear()

    result = run_phase4_2.call_deepseek_api(
        "prompt",
        seed=42,
        model="m",
        base_url="https://example.invalid/v1",
        api_key="secret",
    )

    assert result["status"] == "error"
    assert result["failure_code"] == "connection_error"
    assert result["attempts"] == 2
    assert result["request_count"] == 2
    assert result["retry_count"] == 1
    assert _FailingClient.init_kwargs["max_retries"] == 0
    assert len(_FailingClient.instances) == 1
    assert _FailingClient.instances[0].chat.completions.calls == 2


class _AuthenticationCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        exc = RuntimeError("invalid api key")
        exc.status_code = 401
        raise exc


class _AuthenticationClient:
    last: _AuthenticationClient | None = None

    def __init__(self, **kwargs) -> None:
        self.chat = type("Chat", (), {})()
        self.chat.completions = _AuthenticationCompletions()
        type(self).last = self


def test_non_retryable_authentication_error_is_not_repeated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openai

    monkeypatch.setattr(openai, "OpenAI", _AuthenticationClient)
    monkeypatch.setattr(run_phase4_2, "MAX_ATTEMPTS", 3)
    monkeypatch.setattr(run_phase4_2.time, "sleep", lambda _: None)

    result = run_phase4_2.call_deepseek_api(
        "prompt",
        seed=42,
        model="m",
        base_url="https://example.invalid/v1",
        api_key="bad-secret",
    )

    assert result["failure_code"] == "authentication_error"
    assert result["attempts"] == 1
    assert result["request_count"] == 1
    assert result["retry_count"] == 0
    assert _AuthenticationClient.last is not None
    assert _AuthenticationClient.last.chat.completions.calls == 1
