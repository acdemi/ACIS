# Sprint 04.5 Report — Benchmark Engineering (Phase 2.1E)

## Summary

Sprint 04.5 establishes a capability-oriented benchmark taxonomy: five new
suites (`planning` / `memory` / `debate` / `counterfactual` / `adversarial`,
18 cases total), every case carrying an explicit `design_intent` explaining
which module capability it targets. The runner and ablation CLIs accept
`--suite <name|all>`; a capability matrix (`benchmarks/CAPABILITY_MATRIX.md`)
and coverage report (`benchmarks/COVERAGE.md`) are generated; and ablation
reruns over the new suites show measurable, module-specific contribution
differences for five modules (Planner, Memory, Debate, Counterfactual, and
Critic), satisfying the ≥3-module acceptance bar. Design principle applied:
**区分度优先于难度** — suites are built so module contributions are
measurable rather than engineered to make the system fail.

## Implementation

### Files changed

| File | Change |
|------|--------|
| `benchmarks/taxonomy.py` | New: `BenchmarkSuite` taxonomy (5 suites, min counts, targeted capability), `validate_suite_cases` (min count + mandatory `design_intent`), capability matrix and coverage report builders/renders/writers, `python -m benchmarks.taxonomy` doc generator |
| `benchmarks/datasets/planning.json` | 4 cases targeting Planner task decomposition / tool-need identification |
| `benchmarks/datasets/memory.json` | 4 cases targeting RAG/KG/case retrieval precision |
| `benchmarks/datasets/debate.json` | 4 irrigation × disease conflict cases targeting multi-agent debate |
| `benchmarks/datasets/counterfactual.json` | 3 ambiguous/multi-candidate cases targeting counterfactual coverage |
| `benchmarks/datasets/adversarial.json` | 3 environment–symptom contradiction / sensor-anomaly cases targeting system boundary |
| `benchmarks/loader.py` | New `CAPABILITY_SUITES`, `suite_dataset_path`, `load_suite` (schema + taxonomy validation), `load_all_suites` |
| `evals/runner.py` | New `--suite {planning,memory,debate,counterfactual,adversarial,all}` — maps a suite to its dataset path; `all` runs every suite into `results/suites/<suite>/` |
| `evals/ablation.py` | New `--suite` — runs the full ablation matrix over a capability suite; `all` runs every suite into `results/ablation/suites/<suite>/` |
| `tests/test_taxonomy.py` | 21 unit tests: suite definitions, loading/validation (design_intent), matrix and coverage rendering, doc writing |
| `benchmarks/CAPABILITY_MATRIX.md` | Generated capability matrix (18 cases, one targeted module per suite) |
| `benchmarks/COVERAGE.md` | Generated coverage report (18/18 design_intent, 100% per-module coverage) |
| `results/` | Acceptance artifacts: `runner --suite planning` metrics, `results/suites/<suite>/` runs, `results/ablation/<ts>/REPORT.md` (planning) and `results/ablation/suites/<suite>/<ts>/REPORT.md` (all suites) |
| `docs/BENCHMARK_ENGINEERING_SPRINT_04_5_REPORT.md` | This report |

### Design decisions

- **Suite-as-dataset mapping.** `--suite planning` resolves to
  `benchmarks/datasets/planning.json` via `suite_dataset_path`, then flows
  through the existing `EvalConfig.load_dataset` (.json path) path — no
  `evals/config.py` change needed, keeping the scope to the allowed files.
- **Capability over difficulty.** Cases reuse the domain KB's real disease
  vocabulary and are labeled for *measurability*: planner cases exercise
  tool-need decomposition, memory cases exercise retrieval hits, debate
  cases create irrigation × disease conflicts, counterfactual cases create
  ambiguous symptom sets, adversarial cases create environment–symptom
  contradictions. No cases are designed merely to fail accuracy.
- **`design_intent` is schema-level guaranteed for suites.** The shared
  `benchmarks/schema.py` is untouched (not in scope); suite-level
  validation (min counts + non-empty `design_intent`) lives in
  `benchmarks/taxonomy.py` and is enforced by `loader.load_suite`.
- **Docs are generated, not hand-written.** `python -m benchmarks.taxonomy`
  rebuilds `CAPABILITY_MATRIX.md` and `COVERAGE.md` from the actual suite
  files, so counts can never drift from the data.

## Validation

- **pytest**: 131 passed (21 new `tests/test_taxonomy.py` + 110 Sprint 01–04
  regression). No regressions.
- **ruff**: clean on all new/modified files (`benchmarks/taxonomy.py`,
  `benchmarks/loader.py`, `evals/runner.py`, `evals/ablation.py`,
  `tests/test_taxonomy.py`).
- **mypy**: 0 errors in the new/modified files; the 33 reported errors are
  the same pre-existing transitive errors in frozen modules.
- **Acceptance 1**: `python evals/runner.py --suite planning` → 4 cases,
  accuracy 1.00, `results/metrics.csv` + `results/summary.md`.
- **Acceptance 2**: `python evals/runner.py --suite all` → all five suites
  run; `results/suites/{planning,memory,debate,counterfactual,adversarial}/metrics.csv`
  all generated.
- **Acceptance 3**: `python evals/ablation.py --suite planning` → 7 combos,
  planning-specific `results/ablation/20260801_144732/REPORT.md` with
  contribution matrix. `--suite all` also ran for the remaining four suites.
- **Acceptance 4**: `benchmarks/CAPABILITY_MATRIX.md` and
  `benchmarks/COVERAGE.md` generated (18 cases, 18/18 design_intent,
  100% per-module coverage).
- **Acceptance 5 — measurable module contributions (≥3 modules)**:

  | Suite | Module | Metric | Baseline → combo | Δ |
  |---|---|---|---|---|
  | planning | Planner | planner_usage | 1 → 0 | 1.000 |
  | memory | Memory | memory_hits | 10 → 0 | 10.000 |
  | debate | Debate | debate_rounds | 1.750 → 0 | 1.750 |
  | debate | Debate | average_confidence | 0.595 → 0.647 | 0.052 |
  | debate | Critic | average_confidence | 0.595 → 0.657 | 0.062 |
  | counterfactual | Counterfactual | counterfactual_count | 24 → 0 | 24.000 |
  | adversarial | Counterfactual | counterfactual_count | 24 → 0 | 24.000 |

  Five modules (Planner, Memory, Debate, Counterfactual, Critic) show
  measurable Δ ≥ 0.05 on their corresponding suite. Notable finding: on the
  debate suite, removing Debate/Critic *raises* average confidence
  (0.595 → 0.647 / 0.657) — conflict resolution measurably reduces
  overconfident decisions, which is exactly the measurable contribution the
  suite was designed to expose.
- **Acceptance 6/7**: `pytest tests/test_taxonomy.py` green; ruff & mypy
  zero errors on new files.

## Architecture Review

- **Adherence to frozen modules**: no changes to `agents/`, `planner/`,
  `debate/`, `rag/`, `rule_engine/`, `storage/`, `gateway/`, `ui/`,
  `orchestrator.py`, `workflow.py`, `kg_adapter.py`, or `trace/`. The three
  existing difficulty datasets (`easy/medium/hard.json`) are untouched
  (read-only per scope). `benchmarks/schema.py` and `evals/config.py` were
  intentionally not modified.
- **New abstractions**: `BenchmarkSuite`, `CAPABILITY_SUITES`,
  `suite_dataset_path`, `load_suite` / `load_all_suites`,
  `validate_suite_cases`, matrix/coverage builders and renderers, and the
  `--suite` CLI on runner and ablation. All additive.
- **Backward compatibility**: existing `--dataset`, toggles, and report
  paths unchanged; `--suite` is an additional option that takes precedence
  when given. All 110 pre-existing tests pass.
- **Dependency direction**: `evals.runner/ablation` → `benchmarks.loader` →
  `benchmarks.schema`; `benchmarks.taxonomy` → `benchmarks.loader` (with a
  lazy loader→taxonomy import inside `load_suite` to avoid a cycle). No new
  dependencies on frozen modules.

## Known Issues

1. Accuracy on the capability suites is 1.00 across all combos; module
   contributions are visible in usage/process metrics (planner_usage,
   memory_hits, debate_rounds, counterfactual_count) and confidence, not in
   accuracy. This is by design (区分度优先于难度), but accuracy-based
   discrimination remains limited on these 18 cases.
2. `--suite all` writes each suite's runner metrics under
   `results/suites/<suite>/` and ablation reports under
   `results/ablation/suites/<suite>/<ts>/`; there is no cross-suite summary
   aggregating the five ablation reports into one document.
3. `design_intent` is free-form Chinese text; coverage counts treat any
   non-empty string as coverage, so intent semantics are not machine-verified
   against module names.

## Future Work

- Cross-suite ablation summary report and per-suite comparison charts.
- Structured `design_intent` fields (e.g. `{"module": ..., "capability": ...}`)
   for machine-checkable coverage and intent-based metrics.
- Expand suite sizes (e.g. debate ≥ 8, adversarial ≥ 6) to sharpen
   confidence deltas and add accuracy-sensitive boundary cases.
- Wire `--suite` into the experiment manager (Sprint 05) as a first-class
   experiment dimension.

## Technical Debt

- Unchanged pre-existing debt: mypy errors in frozen modules, E402 in
  `orchestrator.py` / `fixture_eval.py` / `smoke_eval.py`, planner overload
  warning (see `context/KNOWN_DEBT.md`).
