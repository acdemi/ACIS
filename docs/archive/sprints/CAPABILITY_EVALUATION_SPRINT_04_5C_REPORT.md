# Sprint 04.5C Report — Capability Evaluation Engine (Phase 2.1E)

## Summary

Sprint 04.5C connects the capability contract to runtime: a new
`evals/capability_metrics.py` translates each capability's observable
evidence into executable, Trace-driven checks, and the evaluation runner now
records per-case `capability_scores` (0–1) for all seven capabilities. Scores
flow into `CaseMetrics`, `metrics.csv` (per-capability columns), and a
"Capability Performance" section in `summary.md`. The scoring is fully
automatic — read from the unified Trace (planner / memory / debate / critic /
judge / tool_router / perception events) — making the benchmark a true Agent
Capability Test Suite (设计原则：从"静态标签"到"运行时验证"). Ablation
linkage is verified: `--planner-off` zeroes `information_gathering` and
`multi_step_planning`; `--memory-off` zeroes `knowledge_retrieval`.

## Implementation

### Files changed

| File | Change |
|------|--------|
| `evals/capability_metrics.py` | New: Trace-driven scorers for all 7 capabilities, `compute_capability_scores`, `declared_capabilities`, `declared_capability_satisfaction`, `CAPABILITY_SCORE_KEYS` |
| `evals/metrics.py` | `CaseMetrics.capability_scores` field; `compute_trace_metrics(..., capability_scores=...)`; `aggregate_capability_scores` (average / cases / positive per capability) |
| `evals/runner.py` | `_run_case` computes capability scores from the Trace + case and passes them into `compute_trace_metrics` (core reasoning untouched) |
| `evals/report.py` | `CAPABILITY_SCORE_COLUMNS` appended to `CSV_FIELDS`; `_row_dict` emits per-capability score cells; `write_summary_markdown` gains "## Capability Performance" (average / cases / positive) |
| `tests/test_capability_metrics.py` | 12 unit tests: all 7 scoring logics with simulated Traces, missing-evidence handling, declared-capability satisfaction, metrics aggregation |
| `results/` | Acceptance artifacts: enriched run with capability columns + Capability Performance summary; planner-off / memory-off toggle runs; ablation smoke |
| `docs/CAPABILITY_EVALUATION_SPRINT_04_5C_REPORT.md` | This report |

### Scoring rules (executable success conditions)

| Capability | Trace evidence used | Score = 1.0 when |
|---|---|---|
| information_gathering | planner goal/steps + judge action_plan | planner enabled and any text contains info-request keywords (询问/补充/检查/取样/送检/观察/信息 …) |
| knowledge_retrieval | memory events | memory_hits ≥ 1 (confidence ≥ 0.5) |
| conflict_resolution | debate + critic events | debate present and critic `triggered` is true |
| counterfactual_reasoning | any event payloads | counterfactual / counterfactual_observations non-empty (≥ 1) |
| uncertainty_quantification | judge confidence + case ground truth | evidence-insufficient → confidence ≤ 0.7; otherwise confidence ≥ 0.5 |
| multi_step_planning | planner payload | planner enabled and steps ≥ 2 |
| sensor_cross_validation | perception sensor claim + judge sensor_readings + tool requests | sensor anomaly detected and readings used, or `sensor_verify` tool requested |

All scores are 0.0/1.0, always in [0, 1], and computed without external
judgment.

## Validation

- **pytest**: 189 passed (12 new `tests/test_capability_metrics.py` + 177
  existing). No regressions.
- **ruff**: clean on all new/modified files (`capability_metrics.py`,
  `metrics.py`, `runner.py`, `report.py`, `test_capability_metrics.py`).
- **mypy**: 0 errors in the new/modified files (33 pre-existing transitive
  frozen-module errors unchanged).
- **Acceptance 1**: `python evals/runner.py --dataset
  benchmarks.datasets.enriched` → every case row in `metrics.csv` carries all
  7 `capability_*` columns with values in {0.0, 1.0}.
- **Acceptance 2**: 49/52 declared-capability pairs score > 0. Three
  `conflict_resolution` annotations (`ce_sugar_beet_root_rot_dry`,
  `ce_cotton_wilt_hot`, `sc_cotton_wilt_anomaly`) score 0 because the final
  Trace shows no critic participation (their multi-round debate was driven by
  missing image evidence, not a surfaced conflict) — consistent with the
  "unless the system truly does not exhibit the capability" clause and
  reported as a genuine finding.
- **Acceptance 3**: `--planner-off` → `capability_information_gathering` and
  `capability_multi_step_planning` all 0 across the enriched set;
  `--memory-off` → `capability_knowledge_retrieval` all 0.
- **Acceptance 4**: `results/summary.md` contains the "## Capability
  Performance" table (e.g. information_gathering 1.00 / 18, conflict_resolution
  0.11 / 2, sensor_cross_validation 0.33 / 6).
- **Acceptance 5**: all 7 scoring logics covered by unit tests with simulated
  Traces (including missing/degraded traces and planner/memory disabled
  states); `pytest` 189 green.
- **Acceptance 6**: ruff & mypy zero errors on new/modified files.
- **Ablation linkage**: `evals/ablation.py` smoke run succeeds
  (`--dataset evals.fixtures --max-cases 1`, 7 combos); capability score
  columns flow into every combo's `metrics.csv`, and toggle effects on scores
  are verified (acceptance 3).

## Architecture Review

- **Adherence to frozen modules**: no changes to `agents/`, `planner/`,
  `debate/`, `rag/`, `rule_engine/`, `storage/`, `gateway/`, `ui/`,
  `orchestrator.py`, `workflow.py`, `kg_adapter.py`, any benchmark JSON
  dataset (read-only this sprint), or the public signatures of
  `benchmarks/capabilities.py` / `benchmarks/metadata.py`.
- **New abstractions**: `compute_capability_scores` (all additive), the
  `capability_scores` field on `CaseMetrics` (defaulted, backward
  compatible), `aggregate_capability_scores`, CSV columns, summary section.
- **Dependency direction**: `evals.capability_metrics` →
  `benchmarks.capabilities` (standalone enum) and `trace.types` (frozen,
  read-only); `evals.metrics` stays domain-free (no benchmark imports);
  `runner`/`report` consume the new module without touching core logic.

## Known Issues

1. `conflict_resolution` is intentionally strict (critic `triggered`); three
   env-contradiction annotations score 0 because the current pipeline's final
   Trace does not surface critic participation for those queries — either the
   annotations or the pipeline behavior should be revisited with the
   architect.
2. `information_gathering` detection uses keyword heuristics over planner /
   judge text; it is calibrated to the current rule-based judge and may need
   re-tuning if prompts or planner wording change.
3. `sensor_cross_validation` requires an actual sensor anomaly (or
   `sensor_verify` tool request); sensor data that is merely present does not
   score.

## Future Work

- Evaluate `success_condition` strings directly (structured condition DSL)
  instead of per-capability keyword rules.
- Wire capability scores into the ablation per-capability tables for
  module-contribution analysis beyond accuracy.
- Surface capability scores in trace export and experiment manager (Sprint 05).

## Technical Debt

- Unchanged pre-existing debt: mypy errors in frozen modules, E402 in
  `orchestrator.py` / `fixture_eval.py` / `smoke_eval.py`, planner overload
  warning; Capability Annotation status in `context/KNOWN_DEBT.md`.
