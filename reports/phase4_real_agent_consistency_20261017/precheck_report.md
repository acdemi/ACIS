# ACIS Phase 4 Real-Agent Consistency Precheck

> Date: 2026-10-17
> Branch: `work/20261017-phase4-eval-reliability`
> Precheck commit: `f4be5b7` (repair commit `340857f`)
> Verdict: **FAIL**
> Phase 5 recommendation: **No**

## 1. Experiment Design

The minimal representative set was selected from the frozen Challenge Set v1:

| case | id | role | ground truth | executed |
|---|---|---|---|---|
| 23 | `ms_tomato_blight_stem` | ordinary deterministic diagnosis | 早疫病 | yes |
| 14 | `inc_tomato_vague_spot` | evidence insufficient / abstention | 证据不足 | no |
| 9 | `conf_tomato_blight_cool_rain` | conflicting evidence | 早疫病 | no |

Cases 14 and 9 were not executed because the first real case triggered a stop
condition. No sample expansion or repeat runs were performed.

Data version and fingerprint:

- Version: `1`
- Cases: `24`
- SHA-256: `ad39b08f91361d37242fd1e087ce6b03712f2c71cc9b5291f5c0934de1a4846c`

## 2. Effective Configuration

| field | value |
|---|---|
| config | C1: planner/debate/critic/memory/tool_router/counterfactual all on |
| execution | LangGraph on, real ACIS runner, LLM Judge requested |
| seed | `42` |
| provider | `deepseek` |
| endpoint ID | `https://api.deepseek.com` |
| model | `deepseek-chat` |
| Judge timeout | `30s` |
| SDK retries | `0` for this explicit probe |
| config fingerprint SHA-256 | `c75a88874fe325639cdf3d49e02f9c9fd5677f54afea704460eed5065cf37802` |

The actual model and provider are traceable and match the effective defaults.
The configured credential is not usable: the endpoint returned HTTP 401.

## 3. Execution Result

- Case: `ms_tomato_blight_stem`
- Trace: `d432f0d40e704dd89cab6dd508185913`
- Runtime: `11.5988s`
- Final real decision: `病理判断首选：番茄早疫病`
- Canonical label: `早疫病`
- Confidence: `0.75`
- Judge mode: `rules`
- Fallback: `authentication_error`
- Judge tokens: `0`

The process observed three Judge request failures during the run: two
authentication failures and one connection failure. This includes the evaluator
warm-up; the persisted target-case trace records the final authentication
failure as the authoritative case-level reason.

Qdrant returned HTTP 503 and the memory layer used its fallback. This is a
separate environment degradation and did not cause the direct Judge
authentication failure.

## 4. Real Agent vs Evaluator

| field | real trace | evaluator | exact match |
|---|---|---|---|
| final decision | 病理判断首选：番茄早疫病 | 病理判断首选：番茄早疫病 | yes |
| confidence | 0.75 | 0.75 | yes |
| canonical label | 早疫病 | 早疫病 | yes |
| abstained | false | false | yes |
| judge_mode | rules | rules | yes |
| fallback reason | authentication_error | authentication_error | yes |

Metric comparison for the same case:

| metric | result |
|---|---|
| runner label accuracy | 1.00 |
| challenge factor coverage accuracy | 0.00 |
| challenge factor coherence (0-3) | 0 |
| abstention rate | 0.00 |
| memory hits | 3 |
| debate rounds | 2 |
| Judge tokens | 0 |

The evaluator faithfully preserved the final decision, confidence, label,
abstention status, Judge mode, and fallback reason. It did not make the rules
fallback look like a successful LLM decision.

However, the score definitions are not interchangeable for this run. The
runner's `accuracy` is final-label accuracy, while challenge-report `accuracy`
is expected-key-factor coverage. The rules fallback's `reasoning_trace` does not
contain the diagnostic factors, and the canonical scorer also does not include
`action_plan` in its factor text. Therefore the same decision can be label
correct (`1.0`) but factor coverage incorrect (`0.0`).

## 5. Required Equality and Allowed Variation

Required exact equality for the same execution:

- input/case ID and dataset fingerprint;
- effective provider, endpoint ID, model, seed, and config fingerprint;
- trace decision and evaluator decision;
- trace confidence and evaluator confidence;
- canonical label and abstention status;
- Judge mode and fallback reason code.

Allowed model variation across repeated LLM executions:

- confidence;
- final label for ambiguity/conflicting cases;
- LLM-generated reasoning and factor coverage.

The current run cannot measure those variations because no successful LLM call
was available and the stop condition prohibited repeats.

## 6. Failure and Root Cause

1. **Unexpected Judge fallback — confirmed.** The real path was requested with
   an LLM Judge but the credential was invalid. Two authenticated failures and
   one connection failure occurred; the final trace correctly recorded
   `judge_mode=rules` and `fallback_reason_code=authentication_error`.
2. **Scoring definition mismatch — confirmed for the fallback run.** Runner
   label accuracy and challenge factor coverage measure different things and
   currently share the name `accuracy`. The rules reasoning trace lacks the
   expected factors, and `action_plan` is not consumed by the scorer text.
3. **Repeatability — not assessed.** Stopping prevented the planned repeated
   executions and the abstention/conflict cases.

## 7. Conclusion

**FAIL.** The repaired evaluator correctly preserved the real decision and
fallback semantics, but the experiment definition requires a successful LLM
Judge and a resolved scoring definition. With authentication failure and
`0.0` factor coverage versus `1.0` label accuracy for the same decision, Phase 5
must not start.

## 8. Artifacts

- Precheck runner report: `reports/phase4_real_agent_consistency_20261017/stop_probe_case23.md`
- Machine-readable summary: `reports/phase4_real_agent_consistency_20261017/precheck_summary.json`
- Metrics: `reports/phase4_real_agent_consistency_20261017/stop_probe_logs/precheck_seed42/c1_all_on/runner/metrics.csv`
- Summary: `reports/phase4_real_agent_consistency_20261017/stop_probe_logs/precheck_seed42/c1_all_on/runner/summary.md`
- Trace: `reports/phase4_real_agent_consistency_20261017/stop_probe_logs/precheck_seed42/c1_all_on/runner/traces/d432f0d40e704dd89cab6dd508185913.json`
- Flattened input: `reports/phase4_real_agent_consistency_20261017/stop_probe_logs/precheck_seed42/_flattened/challenge_set_v1_flattened.json`
