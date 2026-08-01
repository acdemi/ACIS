# Evaluation Runner — Sprint 02 Report (Phase 2.1E)

Sprint: 2.1E / Sprint 02
Scope: Reproducible Evaluation Runner over the unified Trace.
Status: Complete. Cognitive features frozen; Planner / Judge / Debate / Tool
Router / Memory / DecisionOutput unchanged.

---

## 1. Implementation Report

### Deliverables

| File | Role |
|------|------|
| `evals/config.py` | `EvalConfig` (toggles, seed, dataset, output), `EvalCase`, `load_dataset` |
| `evals/metrics.py` | Trace-derived `CaseMetrics` + `aggregate_metrics` (domain-free) |
| `evals/report.py` | `metrics.csv` + `summary.md` writers |
| `evals/runner.py` | CLI + orchestrator runner, toggle wiring, warm-up |
| `evals/__init__.py` | Makes `evals` a regular package (mypy package-base fix) |
| `tests/test_metrics.py` | 18 unit tests for metrics, reports, config/dataset |
| `results/metrics.csv`, `results/summary.md` | Sample full-run artifacts (12 fixtures) |

### Pipeline

```
dataset + toggles
      ↓
orchestrator.run(case)  →  unified Trace (reused from Sprint 01)
      ↓
metrics (from Trace payloads + runner runtime + dataset label)
      ↓
results/metrics.csv  →  results/summary.md
```

### Runner

- Accepts `dataset` and `planner_on/off`, `debate_on/off`, `memory_on/off`,
  `tool_router_on/off` (CLI `--planner-on` … `--tool-router-off`, all on by
  default), plus `--output-dir`, `--seed` (default 7), `--rules-only`,
  `--max-cases`.
- One orchestrator is constructed per evaluation run (matching the existing
  `fixture_eval` reuse pattern; the judge calibrator is read-only during runs,
  so reuse is safe), then one untimed warm-up query absorbs cold-start
  (lazy imports / backend init) so `average_runtime` reflects steady state.
- Each case seeds `random.seed(config.seed)` before its run for reproducible
  sensor/weather readings, honors per-case `sensor_override`, and records
  `AGRI_AI_DB_PATH=data/eval.db` while `AGRI_AI_PERSIST=0` keeps evaluation
  runs write-free.

### Toggle wiring (no frozen module changes)

| Toggle | Mechanism |
|---|---|
| `planner_on/off` | Existing `ACIS_ENABLE_PLANNER` env switch read by `build_planner` |
| `tool_router_on/off` | Clears `orchestrator.tool_router` instance attribute (route step is skipped by `run()`) |
| `memory_on/off` | Replaces `rag_agent` / `knowledge_graph_agent` / `case_memory_agent` / `outcome_agent` with duck-typed no-op agents (zero-confidence 记忆层 outputs) |
| `debate_on/off` | Replaces `debate_engine` / `critic_engine` with no-op engines (empty `DebateResult`, pass-through critic) |

All substitution happens on orchestrator instances at runtime — Planner,
Judge, Debate, Tool Router, Memory, and `DecisionOutput` source modules are
untouched, and no API changes were made.

### Metrics (from Trace)

| Metric | Source in Trace |
|---|---|
| `accuracy` | pathology `claim` vs dataset `ground_truth` (special-cases `证据不足` → `病理证据不足`) |
| `average_confidence` | `judge` event payload `confidence` |
| `average_runtime` | runner-measured wall clock per case (steady state after warm-up) |
| `planner_usage` | `metrics` payload `planner.enabled` → 1.0/0.0 |
| `tool_usage` | `metrics` payload `tool_router.requests > 0` → 1.0/0.0 |
| `memory_hits` | count of `memory` events with `confidence >= 0.5` |
| `debate_rounds` | 0 when debate off; else max round from `【多轮辩论·第N轮】` markers (default 1) |
| `counterfactual_count` | events with non-empty `counterfactual` or `counterfactual_observations` |
| `collective_omission_count` | `judge_analysis.collective_omission.ignored_candidates` length |

Aggregation: rates/averages are means; counts are totals; `accuracy` ignores
cases without `ground_truth` (reported as `x/y scored`).

### Sample run (built-in `evals.fixtures`, 12 cases, all toggles on)

`results/metrics.csv` + `results/summary.md` were generated with
`python evals/runner.py --dataset evals.fixtures`:

- accuracy 1.00 (11/12 scored; 1 case has no ground truth)
- average_confidence 0.66, average_runtime ≈ 0.014 s (steady state)
- planner_usage 1.00, tool_usage 1.00, memory_hits 26
- debate_rounds 1.67 (multi-round rebuttal fired on 8/12 cases)
- counterfactual_count 84, collective_omission_count 12

An all-off smoke run (`--planner-off --debate-off --memory-off
--tool-router-off`) verified the toggles: planner_usage 0, tool_usage 0,
memory_hits 0, debate_rounds 0.

### Validation

- **pytest**: 75 passed (18 new + 57 from Sprint 01). No regressions.
- **ruff**: new files clean under `--select E,F` and `--select E4,E7,E9,F`.
  The only `evals/` findings are pre-existing E402 in `fixture_eval.py` /
  `smoke_eval.py` (intentional `sys.path` + `os.environ` preamble pattern).
- **mypy**: 0 errors in `evals/` and `tests/test_metrics.py`. The 33 reported
  errors are the same pre-existing transitive errors in frozen modules
  (`agents/`, `planner/`, `rag/`, `rule_engine/`, `debate/`, `storage/`,
  `utils/`) already documented in Sprint 01.

---

## 2. Architecture Review

### Trace as the single source of truth
`metrics.py` reads only `Trace` payload dicts (`judge`, `metrics`, `memory`,
`debate`, per-agent events) plus two external inputs that a Trace cannot
contain: runner-measured wall-clock runtime (the Trace is snapshotted at the
end of a run) and dataset ground-truth labels. Every pipeline-derived metric
comes from the Trace, so metrics and pipeline state cannot disagree.

### Domain-free metrics layer
`metrics.py` and `report.py` import no agent / planner / tool-router code;
`config.py` only loads datasets. This keeps the metrics layer unit-testable in
isolation and avoids dragging the frozen modules' typing debt into the new
code (mypy on the new files is clean).

### Runner isolation vs frozen modules
The runner's toggle mechanism is instance-level substitution on the
orchestrator. This satisfies "No Planner / Judge / Debate / Tool Router /
Memory / DecisionOutput changes" while still genuinely exercising the
pipeline variants the sprint requires. The substitution is visible in the
Trace (e.g. zero-confidence memory events when memory is off), so results
remain explainable.

### Reproducibility
Fixed seed per case, write-free evaluation (`AGRI_AI_PERSIST=0`), pinned
dataset path, recorded config in `summary.md`, and per-case `trace_id` in the
CSV make a run reproducible and auditable.

### Report shape
`metrics.csv` is a per-case table with a trailing `__aggregate__` row;
`summary.md` contains config, aggregate metrics, and the per-case table. Both
are deterministic apart from the generation timestamp.

---

## 3. Known Limitations

1. **Runtime metric** measures orchestrator `run()` wall clock only; one-time
   cold-start (lazy imports, backend init) is absorbed by an untimed warm-up
   query, but orchestrator construction time is not included.
2. **`memory_hits` threshold**: a `confidence >= 0.5` heuristic over memory
   events. Low-score RAG matches (confidence 0.35-0.49) are counted as misses;
   the threshold is a documented constant (`MEMORY_HIT_CONFIDENCE`).
3. **`debate_rounds`** defaults to 1 when debate runs; round 2 is detected via
   the `【多轮辩论·第N轮】` consensus marker. Debate rounds are not stored as
   a first-class field in the Trace.
4. **Accuracy** is scored against the pathology claim using the existing
   fixture convention (`ground_truth` substring match, `证据不足` special
   case); cases without `ground_truth` are unscored and excluded from the
   aggregate.
5. **Tool router depends on planner**: with `planner_on=False` the tool router
   cannot run (orchestrator only builds it when the planner exists), so
   `tool_usage` is 0 even if `tool_router_on=True`.
6. **Disabled stages are represented by no-op substitutes**, not by removing
   the stage: memory-off emits zero-confidence memory events, debate-off emits
   an empty `DebateResult`. Metrics still reflect the disabled state.
7. **In-memory traces**: results reference `trace_id` but the Trace payloads
   are not persisted to disk (Sprint 01 limitation); the CSV/Markdown reports
   are the durable output.
8. **Baseline lint/type debt** (unchanged, out of scope): 15x E402 in
   `orchestrator.py` (intentional `load_env()` ordering), E402 in
   `evals/fixture_eval.py` / `evals/smoke_eval.py`, the `planner/planner.py`
   mypy overload + ruff S110/BLE001, and the pre-existing typing debt in
   `agents/`, `rag/`, `rule_engine/`, `debate/`, `storage/`, `utils/`.
