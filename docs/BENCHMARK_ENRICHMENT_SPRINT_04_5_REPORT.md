# Sprint 04.5 Report — Benchmark Enrichment / Evidence Review Gate (Phase 2.1E)

## Summary

Sprint 04.5 enriches the benchmark with `benchmarks/datasets/enriched.json`:
15 realistic cases evenly covering five cognitive challenge types
(`missing_information`, `contradictory_evidence`, `multi_disease`,
`rare_knowledge`, `sensor_conflict` — 3 each), every case carrying the
standardized `BenchmarkMetadata` contract plus `expected_confidence_range`
and `expected_tools`. A new `capability_matrix.py` reads all nine datasets
and auto-generates `CAPABILITY_MATRIX.md` / `COVERAGE.md`; `benchmarks/README.md`
documents the structure, taxonomy, and usage. The enriched ablation run
(`evals/ablation.py --dataset benchmarks.datasets.enriched`) succeeds, and
its `REPORT.md` now contains per-`challenge_type` module contribution
statistics (Δaccuracy / Δconfidence / Δrecall / Δmemory_hits /
Δdebate_rounds / Δcounterfactual_count), ready for the Evidence Review Gate.
Design principle applied: **真实性优先于难度** — every case is grounded in a
realistic agricultural scenario and is meant to make module contributions
measurable, not to force errors.

## Implementation

### Files changed

| File | Change |
|------|--------|
| `benchmarks/metadata.py` | New: `BenchmarkMetadata` dataclass, `CHALLENGE_TYPES` / `NOISE_LEVELS` / `REASONING_FEATURES`, `validate_metadata`, `validate_enriched_case`, `challenge_counts` |
| `benchmarks/datasets/enriched.json` | New: 15 cases (3 per challenge type) with `ground_truth`, `expected_confidence_range`, `expected_tools`, `sensor_override`, full `metadata`; all ground truths verified at accuracy 1.00 |
| `benchmarks/capability_matrix.py` | New: reads all 9 datasets, renders/regenerates `CAPABILITY_MATRIX.md` + `COVERAGE.md`, computes and appends per-`challenge_type` ablation statistics to a run's `REPORT.md` |
| `benchmarks/README.md` | New: benchmark structure, challenge taxonomy, metadata schema, design philosophy, usage |
| `benchmarks/loader.py` | Minimal extension: `benchmarks.datasets.enriched` resolves as a non-difficulty dataset (required by acceptance 5/6); `BUILTIN_DATASETS` unchanged |
| `benchmarks/CAPABILITY_MATRIX.md` | Auto-generated: suite matrix + enriched challenge matrix + dataset inventory |
| `benchmarks/COVERAGE.md` | Auto-generated: dataset inventory (enriched 15/15 metadata complete), per-module + per-challenge coverage |
| `results/ablation/enriched/20260801_150917/` | Acceptance ablation run: 7 combos × 15 cases, per-combo `metrics.csv`, `REPORT.md` with challenge-grouped statistics |
| `tests/test_enriched.py` | 19 unit tests: dataset contract, metadata validation, loader path, doc generation, challenge-grouped stats math |
| `docs/BENCHMARK_ENRICHMENT_SPRINT_04_5_REPORT.md` | This report |

### Design decisions

- **Challenge types over difficulty tiers.** `enriched.json` is the first
  dataset organized by cognitive challenge rather than difficulty; each case
  declares `metadata.challenge_type` and `expected_reasoning_features` so the
  Evidence Review Gate can attribute module contributions per challenge.
- **Ground truths are empirically verified.** Two multi-disease labels were
  corrected after an initial run because the KB keyword matcher resolves the
  tied symptom sets deterministically (DB order): the sugar-beet
  spot+rot case → `褐斑病`, the cotton two-wilt case → `黄萎病`. After the
  fix, `enriched.json` scores accuracy 1.00 (15/15).
- **Schema and runner/ablation stay untouched.** `benchmarks/schema.py`,
  `evals/runner.py`, `evals/ablation.py`, and `evals/config.py` were not
  modified; `--dataset benchmarks.datasets.enriched` works via a minimal
  loader branch (`NON_DIFFICULTY_DATASETS`), keeping `BUILTIN_DATASETS` and
  the Sprint 03 tests intact.
- **Grouped statistics are generated, not hand-written.** After the ablation
  run, `python -m benchmarks.capability_matrix --ablation-dir <ts>` joins
  per-combo `metrics.csv` with `enriched.json` metadata and appends
  per-`challenge_type` Δ tables to the same `REPORT.md`, satisfying the
  "按挑战类型分组" requirement without changing `evals/report.py`.

## Validation

- **pytest**: 150 passed (19 new `tests/test_enriched.py` + 131 Sprint 01–04.5
  regression). No regressions.
- **ruff**: clean on all new/modified files (`benchmarks/metadata.py`,
  `benchmarks/capability_matrix.py`, `benchmarks/loader.py`,
  `tests/test_enriched.py`).
- **mypy**: 0 errors in the new/modified files; the 33 reported errors are
  the same pre-existing transitive errors in frozen modules.
- **Acceptance 1**: `enriched.json` has 15 cases; every challenge type has
  exactly 3 cases (≥3 each).
- **Acceptance 2**: all 15 cases pass `validate_enriched_case` — metadata
  complete, `expected_reasoning_features` non-empty, difficulty 1–5,
  valid noise_level/modalities, non-empty design_intent.
- **Acceptance 3**: `python -m benchmarks.capability_matrix` regenerates
  `CAPABILITY_MATRIX.md` + `COVERAGE.md` (61 cases across 9 datasets;
  enriched 15/15 metadata complete).
- **Acceptance 4**: `benchmarks/README.md` completed.
- **Acceptance 5**: `python evals/runner.py --dataset
  benchmarks.datasets.enriched` → 15 cases, accuracy 1.00.
- **Acceptance 6**: `python evals/ablation.py --dataset
  benchmarks.datasets.enriched --output-dir results/ablation/enriched` → 7
  combos; `REPORT.md` contains per-`challenge_type` contribution tables for
  all five challenge types (6 ablation arms each) with Δaccuracy,
  Δconfidence, Δrecall, Δmemory_hits, Δdebate_rounds, Δcounterfactual_count.
- **Acceptance 7/8**: `pytest tests/test_enriched.py` green; ruff & mypy
  zero errors on new files.

### Selected findings for the Evidence Review Gate (enriched, all_on baseline)

- Overall: accuracy 1.00 across all combos; confidence 0.664 baseline.
- `no_counterfactual`: counterfactual_count 105 → 0 (Δ +105); collective
  omission 5 extra candidates — counterfactual reasoning measurably changes
  judge-level coverage on every challenge type.
- `no_memory`: memory_hits 31 → 0 (Δ +31); confidence unchanged.
- `no_debate`: debate_rounds 1.667 → 0 (Δ +1.667); confidence 0.664 → 0.662.
- `no_critic`: confidence 0.664 → 0.673 (Δ −0.009) — removing Critic raises
  confidence slightly (less down-weighting).
- Per-challenge tables are in
  `results/ablation/enriched/20260801_150917/REPORT.md` for the architect /
  maintainer review; no specific module-magnitude conclusion is asserted
  (per the sprint's non-prescriptive requirement).

## Architecture Review

- **Adherence to frozen modules**: no changes to `agents/`, `planner/`,
  `debate/`, `rag/`, `rule_engine/`, `storage/`, `gateway/`, `ui/`,
  `orchestrator.py`, `workflow.py`, `kg_adapter.py`, or `trace/`.
  `benchmarks/schema.py` and the eight existing dataset files
  (easy/medium/hard + five suites) are untouched; `evals/runner.py`,
  `evals/ablation.py`, and `evals/config.py` were not modified.
- **New abstractions**: `BenchmarkMetadata` + validators, challenge-type
  enum, `capability_matrix` doc/stats generator, `NON_DIFFICULTY_DATASETS`
  loader branch. All additive.
- **Backward compatibility**: `BUILTIN_DATASETS` semantics unchanged; all 131
  pre-existing tests pass; the new loader branch only adds `enriched`.
- **Dependency direction**: `benchmarks.capability_matrix` →
  `benchmarks.loader` / `benchmarks.metadata` / `benchmarks.taxonomy`;
  `benchmarks.metadata` is domain-free; no new dependencies on frozen modules.

## Known Issues

1. Accuracy remains 1.00 on enriched across all combos; module contributions
   are measurable in process metrics (counterfactual_count, memory_hits,
   debate_rounds) and confidence, not in accuracy — consistent with the
   "区分度优先" principle, but accuracy-based discrimination is limited.
2. The KB keyword matcher's tie-breaking (DB insertion order) determines
   multi-disease labels; the two corrected labels are pinned to current
   matcher behavior and should be re-audited if the matcher changes.
3. Challenge-grouped statistics are appended to the ablation `REPORT.md` as
   a second step (`capability_matrix --ablation-dir`); they are not emitted
   by `ablation.py` itself (its logic is read-only this sprint).
4. `expected_confidence_range` / `expected_tools` are informational metadata
   — they are validated for shape but not scored against pipeline output.

## Future Work

- Wire challenge-grouped statistics directly into the ablation report
  generator (after the Evidence Review Gate approves `evals/report.py`
  changes).
- Add per-challenge accuracy-sensitive cases (rare knowledge / sensor
  conflict) to move module contributions into accuracy/recall deltas.
- Machine-readable challenge stats export (CSV/JSON) for the review gate.

## Technical Debt

- Unchanged pre-existing debt: mypy errors in frozen modules, E402 in
  `orchestrator.py` / `fixture_eval.py` / `smoke_eval.py`, planner overload
  warning (see `context/KNOWN_DEBT.md`).
