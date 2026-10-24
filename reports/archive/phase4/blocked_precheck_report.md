# ACIS Phase 4 Recovery — Real Judge Minimal Precheck

> Date: 2026-10-18
> Branch: `work/20261017-phase4-eval-reliability`
> Initial HEAD: `4861b9f`
> Verdict: **BLOCKED**
> Phase 5: **Not allowed**

## 1. Step 0 — Initial State

- Current branch: `work/20261017-phase4-eval-reliability`
- Initial HEAD: `4861b9f`
- Verified history contains `d9fcb7b` and `4861b9f`.
- Uncommitted modifications at start: only
  `README.md`, `context/ARCHITECTURE_STATE.md`, `context/KNOWN_DEBT.md`.
- These unrelated modifications were not reset, cleaned, overwritten, or committed.
- Important ignored evidence remains present:
  - `logs/`: 1742 files, about 51.5 MB
  - `data/`: 189 files, about 275.8 MB
  - `results/`: 1239 files, about 59.5 MB
  - `reports/`: 23 files before this report, about 1.76 MB
  - `logs/phase4_2_real_agent/`: 469 files, about 16.1 MB
- `.env` is ignored by Git and was not read or printed.

Existing minimal precheck entry:

```text
.venv/Scripts/python.exe scripts/run_phase4_2_real_agent.py   --mode precheck --configs C1 --case CASE --seed SEED   --compare-harness reports/phase4_2_raw_results.json   --output REPORT --log-dir LOG_DIR
```

The existing six-run target contract would use three representative Challenge Set
cases, two repeats each, with trace files under the selected `--log-dir`.

## 2. Step 1 — Authentication Diagnosis

Presence and precedence were checked without displaying values:

| item | observed |
|---|---|
| `AGRI_AI_JUDGE_API_KEY` | absent |
| `DEEPSEEK_API_KEY` | present |
| resolved key source | `DEEPSEEK_API_KEY` |
| provider | `deepseek` |
| endpoint ID | `https://api.deepseek.com` |
| model | `deepseek-chat` |
| proxy variables | `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` all absent |
| `.env` last write | 2026-07-09 UTC |

The last real trace records:

- `judge_mode=rules`
- `runtime.outcome=fallback`
- `fallback_reason_code=authentication_error`
- `token_usage=None`
- Provider structured error: HTTP 401, `authentication_error`,
  `invalid_request_error`

The endpoint, provider, and model are consistent with the project’s existing
OpenAI-compatible adapter. No project-level custom authentication-header mismatch
was found. Because no proxy
variable is configured and the error came from the target API’s structured error
payload, the evidence points to provider-side rejection of the configured
credential. A network-level intermediary cannot be ruled out with absolute
certainty, but no such evidence exists.

`.env` has not been modified since 2026-07-09, predating the 2026-10-17 HTTP 401.
There is therefore no evidence that a new credential was supplied through the
normal configuration channel after the failure.

## 3. Gate Decision

The stop condition **“无法安全取得有效凭证”** was triggered.

Consequently:

- no new network request was made;
- no repeated request was used to guess credential behavior;
- Step 2 authentication validation was not run;
- the six real Agent executions were not started;
- no rules fallback was treated as a real LLM Judge success;
- no Benchmark case, ground truth, factor, threshold, or scoring definition was changed;
- no provider or model was switched.

## 4. Planned Cases Not Executed

| role | case ID | ground truth | repeats | status |
|---|---|---|---:|---|
| explicit diagnosis | `ms_tomato_blight_stem` | 早疫病 | 2 | not started |
| abstention | `inc_tomato_vague_spot` | 证据不足 | 2 | not started |
| multi-factor challenge | `conf_tomato_blight_cool_rain` | 早疫病 | 2 | not started |

No execution records or traces exist for this 2026-10-18 attempt.

## 5. Metrics and Reliability

No new six-run metrics were computed. The prior safe trace remains interpretable
under the repaired contract:

| field | prior safe trace |
|---|---|
| final decision | 病理判断首选：番茄早疫病 |
| ground truth | 早疫病 |
| label correct | true |
| factor coverage | 0.25 |
| factor coverage level | 1 |
| Judge mode | rules |
| runtime outcome | fallback |
| fallback reason | authentication_error |
| real LLM Judge success | false |

The factor-scorer execution mode for a successful Judge run is not available
because no successful LLM run occurred.

## 6. Artifacts

- Existing safe trace:
  `reports/phase4_real_agent_consistency_20261017/stop_probe_logs/precheck_seed42/c1_all_on/runner/traces/d432f0d40e704dd89cab6dd508185913.json`
- Existing precheck report:
  `reports/phase4_real_agent_consistency_20261017/precheck_report.md`
- Metric contract audit:
  `reports/phase4_evaluation_metric_contract_audit.md`
- This blocked report:
  `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md`

No historical report, cache, log, data file, or ignored evidence was deleted or
overwritten.

## 7. Minimum Human Action

Update the existing `DEEPSEEK_API_KEY` through the repository’s normal `.env`
channel using a valid DeepSeek credential for the configured
`https://api.deepseek.com` endpoint. Do not paste the key into chat.

Keep the current provider/model unless the experiment definition is explicitly
changed. After the local `.env` is updated, rerun this recovery process from
Step 1 and perform exactly one controlled Judge validation request before any
six-case precheck.

## 8. Final Decision

**BLOCKED.** The evaluator and metric contract remain ready, but no real LLM Judge
can be verified with the unchanged rejected credential. Phase 5 must not start.
