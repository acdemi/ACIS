"""Judge runtime configuration resolution and safe observability.

The Judge supports OpenAI-compatible providers.  Judge-specific variables take
precedence over the legacy ``DEEPSEEK_*`` names so a run can select a provider
without mutating unrelated model configuration.  Resolved metadata is safe to
persist: it contains provenance and a sanitized endpoint identifier, never the
API key, authorization headers, query strings, or URL user-info.
"""

from __future__ import annotations

import json
import math
import os
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT_SECONDS = 60.0
MAX_TIMEOUT_SECONDS = 300.0
DEFAULT_MAX_RETRIES = 2

_SECRET_PATTERNS = (
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{6,}\b"),
    re.compile(r"(?i)\bbearer\s+[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key|authorization)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)(api\s*key\s*:?\s*)(?:\*{2,}|sk-)[^\s,;)]+"),
)


@dataclass(frozen=True)
class JudgeRuntimeConfig:
    """Resolved Judge endpoint/model settings with source provenance."""

    api_key: str
    base_url: str
    model: str
    provider: str
    timeout_seconds: float
    max_retries: int
    sources: dict[str, str]

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def endpoint_id(self) -> str:
        return sanitize_endpoint(self.base_url)

    def public_metadata(self) -> dict[str, object]:
        """Return trace-safe configuration metadata (no credentials)."""
        return {
            "provider": self.provider,
            "endpoint_id": self.endpoint_id,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "sdk_max_retries": self.max_retries,
            "config_sources": dict(self.sources),
        }


def resolve_judge_config(
    environ: Mapping[str, str] | None = None,
) -> JudgeRuntimeConfig:
    """Resolve Judge settings using explicit, documented precedence."""
    env = os.environ if environ is None else environ
    api_key, api_source = _first(env, "AGRI_AI_JUDGE_API_KEY", "DEEPSEEK_API_KEY")
    base_url, base_source = _first(
        env,
        "AGRI_AI_JUDGE_BASE_URL",
        "DEEPSEEK_BASE_URL",
        default=DEFAULT_BASE_URL,
    )
    model, model_source = _first(
        env,
        "AGRI_AI_JUDGE_MODEL",
        "DEEPSEEK_MODEL",
        default=DEFAULT_MODEL,
    )
    provider, provider_source = _first(env, "AGRI_AI_JUDGE_PROVIDER")
    timeout, timeout_source = _first(
        env,
        "AGRI_AI_JUDGE_TIMEOUT_SECONDS",
        default=str(DEFAULT_TIMEOUT_SECONDS),
    )
    retries, retry_source = _first(
        env,
        "AGRI_AI_JUDGE_MAX_RETRIES",
        default=str(DEFAULT_MAX_RETRIES),
    )
    parsed_timeout = _positive_float(timeout, DEFAULT_TIMEOUT_SECONDS)
    parsed_retries = _nonnegative_int(retries, DEFAULT_MAX_RETRIES)
    provider = provider.strip().lower() if provider.strip() else infer_provider(base_url)
    return JudgeRuntimeConfig(
        api_key=api_key.strip(),
        base_url=base_url.rstrip("/"),
        model=model.strip() or DEFAULT_MODEL,
        provider=provider,
        timeout_seconds=parsed_timeout,
        max_retries=parsed_retries,
        sources={
            "api_key": api_source,
            "base_url": base_source,
            "model": model_source,
            "provider": provider_source or "inferred_from_base_url",
            "timeout_seconds": timeout_source,
            "max_retries": retry_source,
        },
    )


def classify_failure(exc: Exception) -> str:
    """Map an SDK/provider/parser failure to a stable reason code."""
    names = " ".join(cls.__name__ for cls in type(exc).__mro__).lower()
    text = str(exc).lower()
    status = getattr(exc, "status_code", None)
    try:
        status = int(status) if status is not None else None
    except (TypeError, ValueError):
        status = None
    if "judgeconfiguration" in names or "missing credentials" in text:
        return "missing_credentials"
    if isinstance(exc, json.JSONDecodeError) or "responseformat" in names:
        return "response_format_error"
    if status in {401, 403} or "authentication" in names:
        return "authentication_error"
    if status == 402 or "insufficient balance" in text or "insufficient_quota" in text:
        return "billing_error"
    if status == 429 or "ratelimit" in names or "rate limit" in text:
        return "rate_limit"
    if "timeout" in names or "timed out" in text:
        return "timeout"
    if "apiconnection" in names or "connection" in names or "connecterror" in names:
        return "connection_error"
    if status is not None and status >= 500:
        return "server_error"
    if status is not None:
        return "api_http_error"
    return "provider_error"


def infer_provider(base_url: str) -> str:
    """Infer a stable provider label from an OpenAI-compatible base URL."""
    host = (urlsplit(base_url).hostname or "").lower()
    if "opencode" in host:
        return "opencode"
    if "deepseek" in host:
        return "deepseek"
    if "volcengine" in host or "volces" in host:
        return "volcengine"
    return "openai-compatible"


SESSION_HEADER = "x-opencode-session"
_SESSION_ID: str | None = None


def _session_id(env: Mapping[str, str]) -> str:
    """Per-process stable opencode session identifier (env override wins)."""
    global _SESSION_ID
    explicit = env.get("AGRI_AI_JUDGE_SESSION_ID", "").strip()
    if explicit:
        return explicit
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
    return _SESSION_ID


def judge_default_headers(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return provider-specific default headers for the Judge client.

    The opencode zen gateway requires an x-opencode-session header on every
    request (routing hint).  For opencode endpoints a per-process session
    identifier is generated automatically (or pinned via the env variable
    AGRI_AI_JUDGE_SESSION_ID).  Other providers get no extra headers unless
    that variable is set explicitly.
    """
    env = os.environ if environ is None else environ
    cfg = resolve_judge_config(env)
    if "opencode" in cfg.provider or "opencode" in cfg.base_url.lower():
        return {SESSION_HEADER: _session_id(env)}
    explicit = env.get("AGRI_AI_JUDGE_SESSION_ID", "").strip()
    return {SESSION_HEADER: explicit} if explicit else {}


def sanitize_endpoint(base_url: str) -> str:
    """Return scheme/host/path only; drop credentials, query, and fragment."""
    try:
        parts = urlsplit(base_url)
    except ValueError:
        return "<invalid>"
    if not parts.scheme or not parts.hostname:
        return "<invalid>"
    host = parts.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parts.port}" if parts.port is not None else ""
    path = parts.path.rstrip("/")
    return f"{parts.scheme}://{host}{port}{path}"


def redact_error_detail(
    value: object,
    *,
    api_key: str = "",
    limit: int = 300,
) -> str:
    """Redact credentials from exception text and bound its stored length."""
    text = str(value)
    if api_key:
        text = text.replace(api_key, "<redacted>")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("<redacted>", text)
    return text[:limit]


def _first(
    env: Mapping[str, str],
    *names: str,
    default: str = "",
) -> tuple[str, str]:
    for name in names:
        value = env.get(name)
        if value is not None and str(value).strip():
            return str(value), name
    return default, "default"


def _positive_float(value: str, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed) or parsed <= 0:
        return default
    return min(parsed, MAX_TIMEOUT_SECONDS)


def _nonnegative_int(value: str, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(parsed, 5) if parsed >= 0 else default


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_TIMEOUT_SECONDS",
    "JudgeRuntimeConfig",
    "classify_failure",
    "SESSION_HEADER",
    "infer_provider",
    "judge_default_headers",
    "redact_error_detail",
    "resolve_judge_config",
    "sanitize_endpoint",
]
