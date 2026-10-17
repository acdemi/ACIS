# Phase 4 Evaluation Reliability Repair

> Date: 2026-10-17  
> Branch: `fix/phase4-eval-reliability`  
> Scope: Judge configuration observability, fallback semantics, retry ownership,
> and harness/real-agent decision semantics. No benchmark case was modified and
> no large evaluation was run.

## 1. Judge configuration and runtime record

Provider/model resolution is now centralized in `utils/judge_runtime.py`:

| setting | precedence | default |
|---|---|---|
| API key | `AGRI_AI_JUDGE_API_KEY` → `DEEPSEEK_API_KEY` | empty |
| base URL | `AGRI_AI_JUDGE_BASE_URL` → `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` |
| model | `AGRI_AI_JUDGE_MODEL` → `DEEPSEEK_MODEL` | `deepseek-chat` |
| provider | `AGRI_AI_JUDGE_PROVIDER` → inferred from endpoint | domain-derived |
| timeout | `AGRI_AI_JUDGE_TIMEOUT_SECONDS` | 60 seconds (bounded at 300) |
| SDK retries | `AGRI_AI_JUDGE_MAX_RETRIES` | 2 (capped at 5) |

Every Judge decision stores additive `judge_analysis.judge_runtime` metadata:
outcome, mode, provider, sanitized endpoint ID, model, source provenance,
timeout, SDK retry budget, retry exhaustion, fallback reason code/detail, and
token usage when available. API keys, Authorization headers, URL user-info,
URL query strings, and masked-key suffixes are not persisted.

Failure codes distinguish `missing_credentials`, `authentication_error`,
`billing_error`, `rate_limit`, `timeout`, `connection_error`,
`response_format_error`, `server_error`, `api_http_error`, and
`provider_error`. Explicit `use_llm=False` is recorded separately as
`disabled_by_configuration`.

## 2. Retry ownership

- `JudgeAgent` makes one SDK call and lets the OpenAI SDK perform the configured
  retry budget. There is no independent Judge retry loop.
- The legacy Phase 4.2 direct-call harness owns its retry loop and constructs
  the SDK client with `max_retries=0`, preventing multiplied retries.
- The harness no longer retries without `seed` after every exception. It does so
  only when the provider explicitly rejects the `seed` parameter with HTTP
  400/422.
- Timeout is explicit and bounded; no unbounded wait path remains.

## 3. Shared decision semantics

`decision_semantics.py` is the canonical definition used by evaluation and
Phase 4 adapters:

- `decision` / `claim` is the final decision text.
- `ABSTAIN` is a decision status, never a disease label.
- `confidence` means confidence that the final decision label is correct.
- `accuracy` compares the benchmark label with the final Judge decision, not an
  intermediate pathology claim.
- An expected `证据不足` label is correct only when the final decision abstains.
- A committed diagnosis cannot be relabeled as abstention solely because another
  expert text contains an abstention phrase.

Real-agent and challenge-run manifests now declare
`execution_semantics=acis_real_agent`, `decision_semantics=final_judge_decision`,
and the confidence definition. The direct Phase 4.2 harness declares
`execution_semantics=direct_llm_baseline`.

## 4. R4 root cause

The historical R4 comparison was between two different execution systems:

- reference: `run_phase4_2.py`, one direct LLM prompt, model-self-assessed
  confidence and coherence;
- real output: the ACIS AgentOrchestrator/Judge path, with expert fusion and,
  in the historical run, a different configured model ID.

Consequences:

- C0 offset `0.320` is an observed difference between a single-model
  self-assessment and a fused Judge confidence, not evidence of a data
  conversion bug.
- C2 `无法定论（待实验室病原鉴定）` is semantically `ABSTAIN`; the direct
  harness diagnosed `番茄叶霉病`. This is a cross-path/model behavior
  difference and cannot be interpreted as confidence equivalence.
- The old code allowed a cross-path confidence difference to be treated as a
  pass/fail equality gate. The new comparator marks unlike execution paths as
  `incomparable`; confidence offsets remain diagnostic data.
- Historical manifests did not persist provider/model provenance. New runs do,
  and therefore avoid relying on reconstruction from `.env` and source defaults.

Reproducible regressions are in `tests/test_phase4_reliability.py`,
`tests/test_phase4_harness_runtime.py`, and `tests/test_metrics.py`.

## 5. Live probe

A single explicit probe was run through the real `JudgeAgent.run()` path with
`AGRI_AI_JUDGE_TIMEOUT_SECONDS=15` and `AGRI_AI_JUDGE_MAX_RETRIES=0`.

Observed resolved configuration:

- provider: `deepseek`
- endpoint ID: `https://api.deepseek.com`
- model: `deepseek-chat`
- timeout: 15 seconds
- SDK retries: 0

The endpoint returned HTTP 401 `AuthenticationError`; the Judge recorded
`fallback_reason_code=authentication_error` and returned `judge_mode=rules`.
This confirms the runtime path and failure classification, but does not
constitute a successful live LLM run. No credential is reproduced here.

## 6. Verification

- `pytest -q tests`: **289 passed**, 22 non-blocking Qdrant compatibility
  warnings.
- Targeted Judge/R4/harness/metrics/scorer/evaluation tests: **71 passed**.
- `ruff check` on all changed Python files: **All checks passed**.
- `mypy decision_semantics.py utils/judge_runtime.py`: **Success**.
- Broader mypy remains blocked by the pre-existing repository module name
  collision (`agents/types.py` shadows the standard-library `types` module).

## 7. Remaining risks

1. The current configured live credential is invalid (HTTP 401). A successful
   live Judge probe must be repeated after credentials are corrected.
2. Historical Phase 4.2/R4 artifacts are intentionally unchanged. They remain
   useful evidence of the old behavior but cannot be retroactively assigned
   runtime provenance.
3. The direct harness and real ACIS remain distinct execution systems. Future
   equivalence prechecks must use an `acis_real_agent` reference; cross-path
   comparisons are explicitly marked incomparable.
4. No large evaluation or Phase 5 work was performed.
