# Sprint 03 Report — Benchmark Dataset Framework with Trace Export (Phase 2.1E)

## Summary

Sprint 03 delivers the Benchmark Dataset Framework: a schema-validated JSON
dataset contract, three built-in datasets (easy 12 / medium 10 / hard 6
cases), a loader that plugs into the existing evaluation runner, and a
`--save-traces` option that persists each case's unified Trace to
`results/traces/{trace_id}.json`. The acceptance run
(`python evals/runner.py --dataset benchmarks.datasets.easy --save-traces`)
completes with accuracy 1.00 and produces `results/metrics.csv`,
`results/summary.md`, and 12 trace files.

## Implementation

### Files changed

| File | Change |
|------|--------|
| `benchmarks/__init__.py` | New package marker (mypy package-base fix, same rationale as `evals/__init__.py` in Sprint 02) |
| `benchmarks/schema.py` | Dataset schema + validation (`id`/`query` required, unique ids, per-difficulty minimum counts, `ground_truth` / `sensor_override` typing) |
| `benchmarks/loader.py` | Resolves `benchmarks.datasets.<name>` module-style names and `.json` paths, validates, returns JSON-native case dicts |
| `benchmarks/datasets/easy.json` | 12 canonical single-signal cases (all three crops + cucumber) |
| `benchmarks/datasets/medium.json` | 10 cases with combined signals (irrigation × disease, environment context, monitoring) |
| `benchmarks/datasets/hard.json` | 6 adversarial cases (ambiguous symptoms, environment–disease contradictions, sensor anomalies) |
| `evals/config.py` | `load_dataset` accepts `benchmarks.datasets.*` names via `benchmarks.loader`; `EvalConfig.save_traces` field (default off) |
| `evals/runner.py` | `--save-traces` CLI flag (default off); per-case Trace export via the frozen `trace.exporter.export_trace_json`; `_run_case` returns `(CaseMetrics, Trace)`; `EvaluationResult.trace_dir` |
| `tests/test_benchmarks.py` | 24 unit tests: schema validation, loader resolution, built-in dataset invariants, `evals.config` integration, `save_traces` default |
| `docs/BENCHMARK_SPRINT_03_REPORT.md` | This report |
| `results/` | Acceptance-run artifacts (metrics.csv, summary.md, traces/) |

### Design decisions

- **Schema is domain-free and EvalCase-compatible.** `benchmarks.schema`
  validates JSON-native dicts only; `evals.config._to_case` wraps them into
  `EvalCase`, so no new dependency is added to frozen modules and the runner's
  existing metrics/accuracy contract is unchanged. Extra metadata
  (`crop`, `intent`, `disease`, `expect_critic`) is preserved in
  `EvalCase.raw`.
- **Loader resolves module-style names to JSON files.** The CLI accepts
  `--dataset benchmarks.datasets.easy` while the data stays in JSON, matching
  the sprint's deliverable shape. `evals.config` delegates to
  `benchmarks.loader` only for the `benchmarks.datasets.*` prefix, keeping the
  existing module and `.json` loading paths untouched.
- **Trace export reuses the frozen exporter.** `evals/runner.py` calls
  `trace.exporter.export_trace_json` (Unified Trace is Frozen and unmodified);
  trace ids are `uuid4().hex`, safe as filenames. Export is off by default.
- **Datasets are grounded in the domain knowledge base.** Ground truths are
  derived from `rag.knowledge_base` disease vocabulary and symptom keywords so
  scoring reflects actual pipeline behavior. The one ambiguous hard case
  (`tomato_ambiguous_mold_blight`) is labeled `早疫病` because concentric-ring
  keywords outscore the mold keywords in the KB matcher.

## Validation

- **pytest**: 99 passed (24 new `tests/test_benchmarks.py` + 75 Sprint
  01/02 regression). No regressions.
- **ruff**: `ruff check benchmarks tests/test_benchmarks.py evals/config.py
  evals/runner.py` — clean (0 warnings).
- **mypy**: 0 errors in the new/modified files (`benchmarks/`,
  `tests/test_benchmarks.py`, `evals/config.py`, `evals/runner.py`). The 33
  reported errors are the same pre-existing transitive errors in frozen
  modules (`agents/`, `planner/`, `rag/`, `rule_engine/`, `debate/`,
  `storage/`, `utils/`, `agents/vision.py`) documented in Sprint 01/02.
- **Acceptance run**: `python evals/runner.py --dataset
  benchmarks.datasets.easy --save-traces` → 12 cases, accuracy 1.00,
  `results/metrics.csv`, `results/summary.md`, 12 traces in
  `results/traces/`. Each trace file is valid JSON containing the full
  ordered `events` log and all 10 stage views.
- **Smoke runs (temp dirs)**: medium → 10/10 accuracy 1.00; hard → 6/6
  accuracy 1.00; both with `--save-traces` producing trace files.

## Architecture Review

- **Adherence to frozen modules**: no changes to Planner, Judge, Debate,
  Critic, Tool Router, Memory, DecisionOutput, Unified Trace, Perception
  Agents, or the forbidden files (`orchestrator.py`, `workflow.py`,
  `kg_adapter.py`, and all `agents/`, `planner/`, `debate/`, `rag/`,
  `rule_engine/`, `storage/`, `gateway/`, `ui/` modules). Trace export calls
  the existing frozen exporter rather than reimplementing it.
- **New abstractions**: `BenchmarkValidationError`, `validate_dataset`,
  `benchmarks.loader.load_dataset/resolve_dataset`, `EvalConfig.save_traces`,
  `EvaluationResult.trace_dir`, `--save-traces`. All additions are optional /
  backward compatible.
- **Backward compatibility**: `load_dataset` behavior for `evals.fixtures`
  and `.json` paths is unchanged; `EvalConfig` and `EvaluationResult` only
  gain defaulted fields; existing CLI flags are untouched; all 75 pre-existing
  tests still pass.
- **Dependency direction**: `evals.config` → `benchmarks.loader` →
  `benchmarks.schema`; `benchmarks` imports no evals/agent/planner code, so
  the framework stays domain-free and testable in isolation.

## Known Issues

1. `results/traces/` accumulates trace files across runs (no cleanup of
   stale traces); the runner writes a fresh UUID per case. Consider a
   `--clean-traces` flag or run-scoped subdirectory in a later sprint.
2. Hard-case labeling depends on the knowledge base's keyword matcher
   (e.g. the ambiguous mold/blight case resolves to `早疫病`); labels should
   be re-audited if the KB matcher changes.
3. `--save-traces` only writes the Trace; per-case metrics are still
   recovered by re-running or by joining `metrics.csv` on `trace_id`.

## Future Work

- Sprint 04: Ablation Framework (systematic toggle ablation over these
  datasets).
- Run-scoped experiment directories and trace cleanup.
- Dataset provenance/metadata (`name`, `difficulty`, `description`) surfaced
  in `summary.md`.

## Technical Debt

- Unchanged pre-existing debt: mypy errors in frozen modules, E402 in
  `orchestrator.py` / `fixture_eval.py` / `smoke_eval.py`, planner overload
  warning (see `context/KNOWN_DEBT.md`).
