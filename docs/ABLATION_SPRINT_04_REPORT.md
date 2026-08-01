# Sprint 04 Report — Ablation Framework (Phase 2.1E)

## Summary

Sprint 04 delivers the Ablation Framework: a fixed set of seven module toggle
combinations (`all_on` baseline + six single-module ablations), an ablation
runner (`evals/ablation.py`) that reuses the evaluation runner per combo, and
a comparison report (configuration matrix, absolute metrics, contribution
matrix Δ = baseline − combo, normalized radar data, key findings,
recommendations). The acceptance command
(`python evals/ablation.py --dataset benchmarks.datasets.easy
--output-dir results/ablation`) completed successfully: all seven combos ran,
each wrote `metrics.csv` under
`results/ablation/<timestamp>/<combo_name>/`, and `REPORT.md` contains the
contribution matrix with data-backed per-module accuracy deltas.

## Implementation

### Files changed

| File | Change |
|------|--------|
| `evals/ablation.py` | New: `AblationCombo`, 7 arms, `run_ablation`, per-combo execution via `evals.runner.run_evaluation`, CLI (`--dataset`, `--output-dir`, `--seed`, `--max-cases`, `--rules-only`, `--combo`) |
| `evals/config.py` | `EvalConfig` gains independent `critic_on` / `counterfactual_on` toggles (default on); new `AblationConfig` (dataset, output_dir, seed, max_cases, use_langgraph, combos) |
| `evals/runner.py` | `--critic-on/off` and `--counterfactual-on/off` CLI toggles; `_apply_toggles` keeps Critic independent of Debate; `_CounterfactualFreeAgent` + `_disable_counterfactual` strip counterfactual fields from every agent output (instance-level substitution, no frozen module touched) |
| `evals/report.py` | New ablation report section: `AblationResult`, `compute_ablation_metrics` (adds `disease_recall`), `contribution_deltas`, `write_ablation_report` (config matrix, absolute/Δ matrices, findings, radar data, recommendations) |
| `tests/test_ablation.py` | 11 unit tests: combo generation, config passing, delta math, report matrix, end-to-end runs over fixtures (all combos) |
| `results/ablation/20260801_142853/` | Acceptance-run artifacts (7 × metrics.csv + summary.md + REPORT.md) |
| `docs/ABLATION_SPRINT_04_REPORT.md` | This report |

### Design decisions

- **One runner, many configs.** Each combo maps onto an `EvalConfig` and is
  executed by the existing `run_evaluation`, so warm-up, toggles, metrics,
  and CSV writing are identical across arms; the ablation layer only
  orchestrates and aggregates. No `--ablate` mode was needed in the runner.
- **`no_debate` keeps Critic.** The runner previously disabled Debate and
  Critic together when `debate_on=False`. Sprint 04 makes Critic an
  independent toggle (`critic_on`, default on), so `no_debate` = debate off,
  critic on, per the sprint spec. This is a documented behavior change for
  the runner's `--debate-off` flag; `--critic-off` now controls Critic.
- **`no_counterfactual` intervenes on agent outputs.** All 12 orchestrator
  agents are wrapped at instance level; each `AgentOutput` has its
  `counterfactual` / `counterfactual_observations` fields cleared before
  debate, critic, judge, or the Trace sees them. Verified end-to-end:
  `counterfactual_count` drops from 81 to 0. No frozen module is modified.
- **Δ = baseline − combo** follows the sprint formula: a positive Δ means the
  ablated module contributed to the metric (closing it reduces the metric).
- **`disease_recall`** (mean accuracy over concrete-disease cases) answers the
  "召回率" requirement without inventing a new pipeline metric; the rest of
  the matrix uses the existing 9 metrics.

## Validation

- **pytest**: 110 passed (11 new `tests/test_ablation.py` + 99 Sprint 01–03
  regression). The end-to-end test runs all seven combos over the fixture
  dataset and asserts the toggles take effect: `no_memory` → memory_hits 0,
  `no_debate` → debate_rounds 0, `no_counterfactual` → counterfactual_count 0,
  `no_planner` → planner_usage 0.
- **ruff**: `ruff check evals/ablation.py evals/config.py evals/runner.py
  evals/report.py tests/test_ablation.py` — clean (0 warnings).
- **mypy**: 0 errors in the new/modified files. The 33 reported errors are
  the same pre-existing transitive errors in frozen modules
  (`agents/`, `planner/`, `rag/`, `rule_engine/`, `debate/`, `storage/`,
  `utils/`).
- **Acceptance run**: `python evals/ablation.py --dataset
  benchmarks.datasets.easy --output-dir results/ablation` → 7 combos,
  `results/ablation/20260801_142853/REPORT.md` + per-combo `metrics.csv`.
  Every combo scores accuracy 1.00 / disease_recall 1.00 on the easy dataset.
- **CLI smoke**: `--combo all_on --combo no_memory --max-cases 1
  --rules-only` into a temp dir ran only the two selected combos.

### Acceptance-run findings (benchmarks.datasets.easy)

- All accuracy and disease_recall deltas are 0.000 — no single module removal
  changes correctness on the easy dataset (canonical cases).
- `no_debate`: average_confidence 0.671 → 0.661 (Δ +0.010); debate_rounds
  1.583 → 0 (Δ +1.583); counterfactual_count 81 → 60 (Δ +21.000) — the
  multi-round rebuttal loop also drives counterfactual generation.
- `no_counterfactual`: counterfactual_count 81 → 0 (Δ +81.000);
  collective_omission_count 11 → 14 (Δ −3.000) — without expert
  counterfactuals the judge flags more collective-omission candidates.
- `no_memory`: memory_hits 25 → 0 (Δ +25.000); accuracy unchanged.
- `no_planner` / `no_tool_router`: only usage metrics change
  (planner_usage/tool_usage → 0), accuracy/confidence unchanged.
- Recommendation generated by the report: rerun on medium/hard datasets to
  differentiate module contributions, since easy yields zero accuracy deltas.

## Architecture Review

- **Adherence to frozen modules**: no changes to Planner, Judge, Debate,
  Critic, Tool Router, Memory, DecisionOutput, Unified Trace, Perception
  Agents, `orchestrator.py`, `workflow.py`, `kg_adapter.py`, or any file in
  `agents/`, `planner/`, `debate/`, `rag/`, `rule_engine/`, `storage/`,
  `gateway/`, `ui/`. `benchmarks/` and `trace/` are read-only as required.
  All ablation toggles are instance-level substitutions on the orchestrator
  (no-op engines, wrapped agents), the same pattern Sprint 02 introduced.
- **New abstractions**: `AblationConfig`, `AblationCombo`, `AblationResult`,
  `run_ablation`, `compute_ablation_metrics`, `contribution_deltas`,
  `write_ablation_report`, `_CounterfactualFreeAgent`. All additive.
- **Backward compatibility**: all existing config fields, CLI flags, and
  report functions keep their signatures and defaults; the only semantic
  change is `--debate-off` no longer implies critic-off (documented above).
  All 99 pre-existing tests still pass.
- **Dependency direction**: `evals.ablation` → `evals.runner` / `evals.report`
  / `evals.config`; `evals.report` → `evals.metrics`; no new dependencies on
  frozen modules from the new code.

## Known Issues

1. On the easy benchmark dataset every ablation arm scores accuracy 1.00, so
   the accuracy contribution matrix is all zeros; module contributions show
   up only in confidence/memory/debate/counterfactual metrics. The report
   explicitly recommends medium/hard runs.
2. `no_debate` keeps Critic but `_NoopDebateEngine` produces an empty
   `DebateResult`; the real CriticEngine then no-ops on empty conflicts, so
   the combo measures "debate absent" rather than "debate present but
   single-round". Multi-round behavior is disabled via the no-op debate
   engine, which matches the sprint intent.
3. `results/ablation/` accumulates a new timestamped folder per run; there is
   no retention/cleanup policy yet.
4. Runner CLI `--debate-off` semantics changed (critic now stays on unless
   `--critic-off`); callers relying on the old combined behavior must pass
   `--critic-off` explicitly.

## Future Work

- Run the ablation matrix over `benchmarks.datasets.medium` / `hard` and
  publish per-difficulty contribution tables.
- Add `--clean` / retention policy for `results/ablation/` run folders.
- Radar chart rendering (the normalized data table is already emitted).
- Per-module cost metrics (runtime, token usage) in the Δ matrix.

## Technical Debt

- Unchanged pre-existing debt: mypy errors in frozen modules, E402 in
  `orchestrator.py` / `fixture_eval.py` / `smoke_eval.py`, planner overload
  warning (see `context/KNOWN_DEBT.md`).
