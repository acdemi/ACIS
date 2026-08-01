# Sprint 04.5B Report — Verifiable Capability Contract (Phase 2.1E)

## Summary

Sprint 04.5B upgrades the Capability Framework from an inference model to a
**verifiable data contract** (设计原则：**可验证优先于完整性**). All 36
capability-focused cases (enriched 18, five capability suites 18) now carry
explicit `capabilities` annotations plus structured `observable_evidence`
(`capability` / `expected_behavior` / `success_condition`); difficulty-tier
datasets are annotated value-first (16 clearly-inferable cases, zero forced
annotations). `enriched.json` gains 3 new `information_gathering` cases
(6 annotated total). A new Capability Consistency Check verifies the
`capabilities ↔ observable_evidence ↔ design_intent` triple for every
annotated case: **52/52 consistent, 0 inconsistent** in
`CAPABILITY_CONSISTENCY_REPORT.md`. The annotated dataset runs cleanly
(18/18 accuracy) and the ablation report now includes per-capability
contribution statistics, with every capability showing measurable
process-metric deltas.

## Implementation

### Files changed

| File | Change |
|------|--------|
| `benchmarks/metadata.py` | Frozen `ObservableEvidence` schema (`capability` / `expected_behavior` / `success_condition`); `BenchmarkMetadata.observable_evidence`; `validate_observable_evidence` / `validate_observable_evidence_list` enforcing evidence ↔ capability consistency (1:1 coverage) |
| `benchmarks/capability_matrix.py` | Reads annotations from `metadata.capabilities` or case-level `capabilities`; Capability Consistency Check (`check_case_consistency`, `build_consistency_rows`, `render/write_consistency_report` → `CAPABILITY_CONSISTENCY_REPORT.md`); per-capability ablation stats appended to `REPORT.md` |
| `benchmarks/datasets/enriched.json` | 15 existing cases explicitly annotated (`capabilities` + `observable_evidence` in metadata; a few `design_intent` strings aligned to declared capabilities); **3 new `information_gathering` cases** (`ig_tomato_missing_info`, `ig_sugar_beet_missing_info`, `ig_cotton_missing_info`) → 18 cases, 6 information_gathering-annotated |
| `benchmarks/datasets/planning.json` / `memory.json` / `debate.json` / `counterfactual.json` / `adversarial.json` | All 18 suite cases annotated with case-level `capabilities` + `observable_evidence` (2 adversarial design_intents aligned to include `冲突`/`矛盾` and `传感器`) |
| `benchmarks/datasets/easy.json` / `medium.json` / `hard.json` | Value-first annotations (16 cases) where capability is clearly inferable: uncertainty_quantification / multi_step_planning / conflict_resolution / sensor_cross_validation / counterfactual_reasoning; pure feature-matching cases left unannotated |
| `benchmarks/CAPABILITY_COVERAGE.md` | Regenerated: 52 annotated cases, information_gathering annotated = 6, 7/7 capabilities covered |
| `benchmarks/CAPABILITY_CONSISTENCY_REPORT.md` | New auto-generated report: 52 annotated, 52 consistent, 0 inconsistent |
| `benchmarks/CAPABILITY_ANNOTATION_SUGGESTIONS.md` | Regenerated: only the 12 intentionally-unannotated difficulty cases remain listed |
| `tests/test_capabilities.py` | Extended (10 new tests): ObservableEvidence validation, evidence↔capability consistency, consistency check, 100%-consistency assertion on real data, capability ablation stats |
| `tests/test_enriched.py` | Fixtures aligned (metadata helper now includes `observable_evidence`; enriched counts 15→18) |
| `context/KNOWN_DEBT.md` | Capability Annotation debt status: 36/36 capability-focused annotated, 16/28 difficulty annotated, 12 unannotated by design |
| `results/ablation/enriched_annotated/20260801_163043/` | Ablation run on the annotated set with challenge + capability grouped statistics |
| `docs/VERIFIABLE_CAPABILITY_SPRINT_04_5B_REPORT.md` | This report |

### Design decisions

- **Dual annotation locations.** Enriched cases carry `capabilities` +
  `observable_evidence` inside `metadata` (the standard
  `BenchmarkMetadata` home); suite and difficulty cases carry them at case
  level (those datasets have no `metadata`). The scanner and consistency
  check read both locations, so the contract is uniform without forcing an
  artificial `metadata` onto every dataset.
- **Evidence is 1:1 with capabilities.** `validate_observable_evidence_list`
  requires every declared capability to have at least one evidence entry and
  every evidence entry to reference a declared capability — an annotation is
  only valid if it is machine-checkable.
- **Consistency = triple alignment.** `check_case_consistency` verifies
  evidence coverage (schema) and that `design_intent` mentions each declared
  capability (by English value or Chinese keyword alias). This forced a
  handful of `design_intent` alignments in the data (e.g. sensor-conflict
  cases now mention `传感器`, multi-disease cases mention `候选/排除`) so the
  assertion is honest rather than nominal.
- **Value-first difficulty annotations.** Only clearly-inferable cases in
  easy/medium/hard were annotated (uncertainty / planning / conflict /
  sensor / counterfactual signals); pure feature-matching disease cases
  (e.g. simple leaf-mold recognition) are intentionally left unannotated —
  宁可少标，不可乱标.

## Validation

- **pytest**: 177 passed (10 new capability tests + 167 existing). No
  regressions.
- **ruff**: clean on all new/modified files (`capabilities.py`,
  `metadata.py`, `capability_matrix.py`, `test_capabilities.py`,
  `test_enriched.py`).
- **mypy**: 0 errors in the new/modified files (33 pre-existing transitive
  frozen-module errors unchanged).
- **Acceptance 1**: 33+ capability-focused cases annotated — actually 36/36
  (enriched 18 + suites 18), plus 16/28 clearly-inferable difficulty cases;
  the remaining 12 difficulty cases are unannotated by design.
- **Acceptance 2**: `ObservableEvidence` schema defined and frozen; all 52
  annotated cases' evidence validates (format + capability coverage).
- **Acceptance 3**: `CAPABILITY_CONSISTENCY_REPORT.md` generated;
  **52/52 consistent, 0 unresolved ⚠️ markers**.
- **Acceptance 4**: `enriched.json` adds 3 `information_gathering` cases,
  all with `capabilities` + `observable_evidence` (18 total cases).
- **Acceptance 5**: `CAPABILITY_COVERAGE.md` shows `information_gathering`
  annotated = **6** (≥6).
- **Acceptance 6**: per-capability ablation statistics appended to
  `results/ablation/enriched_annotated/20260801_163043/REPORT.md`; every
  capability shows process-metric deltas (e.g.
  `no_counterfactual` → counterfactual_count Δ +18..+40 across capability
  groups; `no_memory` → memory_hits Δ; `no_debate` → debate_rounds Δ;
  `no_planner` → planner_usage Δ).
- **Acceptance 7**: `pytest` 177 green; `ruff`/`mypy` zero errors on new
  files.
- **Runtime sanity**: `python evals/runner.py --dataset
  benchmarks.datasets.enriched` → 18 cases, accuracy 1.00 (all ground truths
  hold after annotation; the three new cases score correctly).

## Architecture Review

- **Adherence to frozen modules**: no changes to `agents/`, `planner/`,
  `debate/`, `rag/`, `rule_engine/`, `storage/`, `gateway/`, `ui/`,
  `orchestrator.py`, `workflow.py`, `kg_adapter.py`, `evals/runner.py`,
  `evals/ablation.py`, `benchmarks/schema.py`, or `benchmarks/capabilities.py`.
  Dataset JSON files were modified only where the sprint explicitly allows
  (enriched + five suites + difficulty tiers value-first).
- **New abstractions**: `ObservableEvidence` (frozen schema), evidence
  validators, consistency check + report, per-capability ablation stats.
  All additive and backward compatible.
- **Dependency direction**: `metadata` → `capabilities`;
  `capability_matrix` → `capabilities` / `metadata` / `loader` / `taxonomy`;
  no new dependencies on frozen modules.

## Known Issues

1. 12 difficulty-tier cases remain unannotated by design (value-first);
   they are still listed in `CAPABILITY_ANNOTATION_SUGGESTIONS.md` for
   optional review, but no forced labels were added.
2. Evidence `success_condition` strings are human-readable checkable
   assertions, not yet wired into automated metric evaluation (e.g. no
   runner assertion checks `memory_hits >= 1` against the evidence).
3. The PR step of the stop condition is blocked locally: `gh` auth token is
   invalid, no `GITHUB_TOKEN` env var is set, and local `main` has diverged
   from `origin/HEAD` with 23 entries of accumulated uncommitted sprint work.
   PR creation requires either a re-authenticated `gh`/token or an explicit
   approval to commit and push a branch.

## Future Work

- Wire `success_condition` assertions into the runner/metrics layer so
  evidence is evaluated automatically per case.
- After Chief Maintainer review: merge annotations into any remaining
  datasets and archive the suggestions file.
- Automate PR creation from the sprint report once credentials are restored.

## Technical Debt

- Unchanged pre-existing debt: mypy errors in frozen modules, E402 in
  `orchestrator.py` / `fixture_eval.py` / `smoke_eval.py`, planner overload
  warning; plus the Capability Annotation status now tracked in
  `context/KNOWN_DEBT.md`.
