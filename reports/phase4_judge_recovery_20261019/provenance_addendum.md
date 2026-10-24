# Phase 4 Judge Recovery Precheck — Runtime Provenance Addendum (2026-10-19)

> Type: evidence-recovery addendum. No new experiment, no API/network request.
> Scope: verify the runtime provenance of the six precheck reports in this
> directory against existing traces. The six original reports are evidence and
> remain byte-identical (hashes in §2).

## 1. Audit identity

| item | value |
|---|---|
| Audit branch | `work/20261019-judge-provenance-verify` (created from `work/20261017-phase4-eval-reliability` at tip `4b4c898`) |
| Audit HEAD | `4b4c898ba67e2215b11cbc9e20f6170fcad77921` |
| Comparator contract audited | `decision_semantics.py`, `scripts/run_phase4_2_real_agent.py::compare_decision_outputs`, `tests/test_phase4_reliability.py` at this HEAD |
| Worktree history during audit | the untracked six files were first reviewed on `work/20261019-t2e-t2f-release-readiness` @ `f8ea0ca`; branch switch to the audit branch was the only worktree mutation, per task authorization |
| No commit made | the addendum and the six reports remain untracked/unchanged |

## 2. Original six report hashes (SHA-256, verified before and after this audit)

| report | SHA-256 |
|---|---|
| precheck_case14_seed42.md | `571BC84A155ED97497C27335F9AD854B6BAD30F994665B448111257552E8A1A2` |
| precheck_case14_seed43.md | `FBA0C1D8F702BF911E7045CFB35461379A5979265AA10B51294AA8CCFFFEAC2C` |
| precheck_case23_seed42.md | `22D1C08A16DDFF7CA2CDC30632CA2C7D4408A368E55727BCEF8F0CB746860D82` |
| precheck_case23_seed43.md | `EE56E3F5F81097529AD988364A07B7AC3C0EE01A60BFE929CCA60A4D16DADC68` |
| precheck_case9_seed42.md | `27178F0A76337BE0B0B0F1BC3077D38F5907939C0194D10AE2A0CD5549B917BE` |
| precheck_case9_seed43.md | `F9AD6F69D16BEC10B8FCA88BC4D673BF0CC481C9C9ED7D67870A2006F1268B8A` |

## 3. Evidence location and a source-path deviation

- The task expected traces under `logs/phase4_2_real_agent/`. That directory contains **only 2026-08/09-era** artifacts (`run_42/43/44`, `precheck_seed42` with C0/C1/C2 case-1 traces dated 2026-08-12; nothing newer than 2026-09-01).
- The actual traces of the six 2026-10-19 prechecks were found under
  `logs/phase4_judge_recovery_20261019/<case>_<seed>/precheck_seed<seed>/c1_all_on/runner/{traces,metrics.csv,summary.md}`
  plus `…/precheck_seed<seed>/_flattened/challenge_set_v1_flattened.json`.
  The precheck invocation evidently used a per-run `--log-dir` (documented
  invocation shape in `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md` §1). This deviation is recorded, not corrected.

## 4. Six-row evidence matrix

All runtime fields below are **verified from the trace** (`judge[0].judge_analysis.judge_runtime`); association fields are **verified from direct artifacts** (metrics.csv, flattened dataset, runner summary.md). No field is inferred from `.env`, current configuration, historical manifests, or model names.

| run | trace_id (=filename) | trace SHA-256 (full) | trace timestamp | outcome | provider | endpoint_id | model | config_sources | timeout / sdk_retries / retry_exhausted | token_usage (prompt/completion/total) | judge_mode | decision / conf (trace) | report row match | provenance status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| case23_seed42 | `6791d4481f27465eae0ddd6ed0d2fdf7` | `5555eb1eac74da0b85201da198df8d4fbe644428a70ac7bc500b173fa3fde90d` | 2026-10-19T11:52:57.862221+00:00 | success | deepseek | `https://api.deepseek.com` | deepseek-chat | api_key=`DEEPSEEK_API_KEY`; base_url=`DEEPSEEK_BASE_URL`; model/provider/timeout/max_retries=`default` | 60.0 s / 2 / false | 8613 / 1603 / 10216 | deepseek | 番茄早疫病 / 0.72 | exact | VERIFIED |
| case23_seed43 | `13ef138523ee4eafbbb6832081854fb8` | `63a857b7bfb970c486aed4baf7ce59edd8e58f19476a561627f3ac5346737bff` | 2026-10-19T11:53:53.505820+00:00 | success | deepseek | `https://api.deepseek.com` | deepseek-chat | same labels | 60.0 s / 2 / false | 8612 / 1508 / 10120 | deepseek | 番茄早疫病 / 0.62 | exact | VERIFIED |
| case14_seed42 | `c4b941f27c1043eeb034d0045b0041d4` | `9624d4c4cff2047f00c37084e744fabf19b8082e012a40e5537e85c3be815b03` | 2026-10-19T11:54:26.704592+00:00 | success | deepseek | `https://api.deepseek.com` | deepseek-chat | same labels | 60.0 s / 2 / false | 6709 / 1364 / 8073 | deepseek | 番茄早疫病 / 0.45 | exact | VERIFIED |
| case14_seed43 | `66ad4d9dd1f6435ead4a7aba8d0d742f` | `41ac4ec74b1a716c2a78ee1a94c79cddd4318a1e6edb657498954cff80562002` | 2026-10-19T11:55:03.129927+00:00 | success | deepseek | `https://api.deepseek.com` | deepseek-chat | same labels | 60.0 s / 2 / false | 6708 / 1361 / 8069 | deepseek | 无法定论（番茄早疫病与番茄叶霉病均证据不足） / 0.35 | exact | VERIFIED |
| case9_seed42 | `df6a0b4f697c4aba8124e49863534625` | `7a6c2841c49e2200b6b13658f619fd0df2d05f10aee0f83a5bf3c609d73b8a21` | 2026-10-19T11:55:50.302735+00:00 | success | deepseek | `https://api.deepseek.com` | deepseek-chat | same labels | 60.0 s / 2 / false | 8613 / 1512 / 10125 | deepseek | 番茄早疫病 / 0.62 | exact | VERIFIED |
| case9_seed43 | `d81fce0ecabd4a82901bfe53812dc2ee` | `6e30c7244b8d88e0702e10b4d1395f65b64d3cd3ac11e88d060de2eaff1dccd0` | 2026-10-19T11:56:24.586769+00:00 | success | deepseek | `https://api.deepseek.com` | deepseek-chat | same labels | 60.0 s / 2 / false | 6715 / 1397 / 8112 | deepseek | 番茄早疫病 / 0.55 | exact | VERIFIED |

Shared secondary corroboration in every run directory: runner `metrics.csv` carries the same `trace_id`, identical `accuracy`, `confidence`, and `judge_total_tokens` as the trace; runner `summary.md` repeats seed, dataset path, configuration toggles, token usage, and per-case decision/confidence.

## 5. Report-to-trace association (direct evidence chain, per run)

For each report `precheck_<case>_<seed>.md` the association rests on the
following chain, **independent of timestamp proximity**:

1. One run directory per report:
   `logs/phase4_judge_recovery_20261019/<case>_<seed>/precheck_seed<seed>/` —
   exactly one trace, one metrics.csv, one flattened dataset per directory.
2. Flattened dataset pins the case identity: hashed content of one case
   (`case23_seed42/43` → `ms_tomato_blight_stem`, query
   "…同心轮纹病斑已蔓延至茎部，果实即将膨大，防治顺序怎么安排？";
   `case14_seed42/43` → `inc_tomato_vague_spot`, query "…叶片出现斑点，没有其他信息…";
   `case9_seed42/43` → `conf_tomato_blight_cool_rain`, query "…叶片同心轮纹病斑，近期低温多雨…").
   Flattened SHA-256 pair per case: `8db127d2…` (case23), `9a649cf8…`
   (case14), `ec354092…` (case9); identical across both seeds of a case.
3. The trace's `request[0].query` equals the same case query in every trace —
   case identity inside the trace itself, not only in the wrapper directory.
4. Runner `metrics.csv` row: `case_id` ↔ `trace_id` ↔ `accuracy` ↔ `confidence`
   ↔ `judge_total_tokens` — all consistent with the trace and with the report row.
5. Exact value equality between the report row (`real decision`, `real
   confidence`, `judge_mode=deepseek`) and the trace's
   `judge[0].decision/confidence/judge_mode`.
6. File mtime of each report equals the completion/trace-write time within
   ~1 s (secondary corroboration only).

Timestamp-semantics note (not an inconsistency, but affects naive reading):
each report's `> Generated:` header equals the precheck **invocation** time —
`run_precheck` composes the header lines *before* executing the agent — while
the file mtime and trace timestamp record completion, 30–95 s later. The
`Generated:` value therefore precedes the trace and must not be used for
report↔trace matching.

## 6. Plausible-alternative scans and preserved-ambiguity notes

A full scan of `logs/phase4_2_real_agent/` and
`logs/phase4_judge_recovery_20261019/` for traces whose
`(decision, confidence)` matches a report row produced the following
additional candidates. Both are resolved on direct field evidence, not
timestamp proximity; ambiguity is preserved here explicitly:

1. **case23_seed42 — one extra candidate**:
   `logs/phase4_2_real_agent/run_42/config_C0/c0_bare_baseline/runner/traces/152488a5adee42839b9904ef7ad1b161.json`
   (2026-08-12T10:51:38+00:00) shares the identical decision/confidence pair
   (番茄早疫病 / 0.72) for the same case query. It is **ruled out** for this
   report because: it belongs to the 2026-08-12 R2-era C0 (bare-baseline)
   run; carries no `judge_runtime` block (old trace format ⇒ provenance
   `unknown` per the metric-contract audit §A8, and it cannot verify this
   report's runtime claims); its epoch differs from the report's 2026-10-19
   invocation as recorded in the generation sequence. Decisive grounds are
   era/config/provenance-record fields, not closeness of timestamps.
2. **case23_seed43 ↔ case9_seed42 — cross-coincidence**: both traces record
   the same `(decision, confidence)` = (番茄早疫病, 0.62). They are
   disambiguated by the per-run identity chain (§5 items 1–4): case-23
   dataset/query vs case-9 dataset/query, distinct trace IDs, and distinct
   metrics.csv rows. Noted because a (decision, confidence)-only matcher
   would double-associate these two reports.

No further ambiguous candidates were found; no candidate remains unresolved.

## 7. Stop conditions, mismatches, missing fields

- **No stop condition triggered.** All six traces were reliably associated;
  all six outcomes are `success`; the recorded provider/endpoint/model are
  consistent with each report's `judge_mode=deepseek` claim; every required
  provenance field is present; no contradictions found.
- No `fallback_reason_code` and no `retry_exhausted=true` in any trace;
  timeout 60 s and `sdk_max_retries=2` are the code-documented defaults
  (`config_sources` label `default`; values recorded by the resolver itself).
- No per-run manifest/call-log JSON exists for precheck mode (that feature is
  `full`-mode only); the trace-level `judge_runtime` block is the complete
  recorded provenance and it is present in all six traces.

## 8. Conclusion

All six 2026-10-19 precheck reports' implicit LLM-success claims are
**fully verified at the trace level**: in every run the Judge runtime recorded
`outcome=success`, `judge_mode=deepseek`, provider `deepseek`, endpoint
`https://api.deepseek.com`, model `deepseek-chat`, with resolved
configuration sources, nonzero token usage, and no fallback or retry
exhaustion — and the final decision, confidence, and judge mode in each
report match the trace and runner artifacts exactly.

Boundary of this verification: trace metadata is the runtime's own record;
network-level delivery (server-side confirmation) is not independently
provable from repository evidence and is out of scope. The provenance claim
is therefore "verified from the trace and runner artifacts", the strongest
evidence class available in-repo. Cross-path comparability still stands as
incomparable per the comparator contract; nothing in this addendum changes
that classification or validates Phase 5 readiness.

## 9. Artifacts referenced (read-only)

- Six reports: as listed in §2.
- Six traces + `metrics.csv` + `summary.md` + flattened datasets under
  `logs/phase4_judge_recovery_20261019/<case>_<seed>/precheck_seed<seed>/`.
- Comparator/metric contracts at `4b4c898`: `decision_semantics.py`,
  `scripts/run_phase4_2_real_agent.py`, `tests/test_phase4_reliability.py`.
- Historical bases: `reports/phase4_2_raw_results.json`,
  `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md`,
  `reports/phase4_evaluation_metric_contract_audit.md`.

No report, trace, log, configuration, source file, test, or dataset was
modified by this verification. This addendum was written to
`reports/phase4_judge_recovery_20261019/provenance_addendum.md`.
