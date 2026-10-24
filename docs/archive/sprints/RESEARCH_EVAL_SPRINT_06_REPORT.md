# Research Evaluation Infrastructure - Sprint 06 Report

- **Phase:** 2.1E -> 2.2 Transition
- **Sprint:** 06 - Research Evaluation Infrastructure (论文级统计引擎、数据集指纹、图表生成)
- **Branch:** `0.45C-Capability_Evaluation_Engine`
- **Git (short):** `57176ae` (Sprint 05 committed; Sprint 06 work uncommitted)
- **Python:** 3.13.3
- **Status:** Complete - all 7 acceptance criteria verified.

## 1. Overview

Sprint 06 promotes the Experiment Manager from Sprint 05 into a **research
evaluation infrastructure**: a statistical analysis engine (bootstrap CI +
effect sizes), mandatory dataset fingerprinting for reproducibility,
publication figure generation, and a LaTeX-ready report generator. Every
number now traces back to per-case `metrics.csv` rows and a pinned dataset
version, and every conclusion carries an effect-size estimate with a
confidence interval.

The existing cognitive pipeline and the Sprint 05 experiment archives are
**untouched**. All new code is additive under `experiments/`; no frozen module
was modified and `evals` core logic is consumed read-only.

## 2. Modified / New Files

### New files
- `experiments/analysis.py` - statistical engine: bootstrap mean/CI, effect
  sizes (Δ = baseline − ablated) with bootstrap p-values, multi-seed
  aggregation, module×capability association matrix, Markdown + JSON output.
- `experiments/fingerprint.py` - dataset SHA-256 fingerprinting, mandatory
  `manifest.json` injection, and `verify` logic.
- `experiments/figures.py` - four matplotlib PNG figures (Agg backend,
  bilingual 中/EN labels).
- `experiments/report.py` - LaTeX `tabular` report generator with
  significance markers and figure embedding.
- `experiments/definitions/paper_evaluation.yaml` - 4 module combos × 5 seeds
  (20 runs).
- `tests/test_analysis.py` - 8 tests (synthetic archives, no orchestrator).
- `tests/test_fingerprint.py` - 7 tests (temp datasets, verify pass/fail).
- `docs/RESEARCH_EVAL_SPRINT_06_REPORT.md` - this file.

### Modified files
- `experiments/manager.py` - extended (no rewrite): injected
  `dataset_sha256` into the manifest in `run()`; added `analyze` / `figure` /
  `report` / `verify` subcommands and a name/dir/path experiment resolver.
  Existing `run` / `list` / `compare` / `latest` behavior is unchanged.

### New dependency
- `matplotlib 3.11.1` (installed from the configured PyPI mirror). numpy,
  scipy, Pillow, and PyYAML were already present. matplotlib is the only new
  runtime dependency and is mandated by the Sprint 06 spec for PNG figures.

## 3. Architecture Decisions

- **Bootstrap inference, stdlib-only.** `analysis.py` implements the percentile
  bootstrap (1000 resamples, 95% CI) and a bootstrap difference distribution
  for effect sizes using only `random` - no scipy dependency for the core
  statistics. The two-sided p-value is `2·min(P(Δ≤0), P(Δ≥0))`.
- **Unit of replication = seed when available.** Runs are grouped by module
  toggles. When a group has ≥2 seeds, stats aggregate at the seed level
  (bootstrap over per-seed means); with a single seed they aggregate over
  cases. This keeps single-seed (e.g. `paper_main`) and multi-seed
  (e.g. `paper_evaluation`) experiments on one consistent code path.
- **Fingerprint via the frozen loader.** `fingerprint.py` resolves dataset
  sources to their backing JSON file through the frozen
  `benchmarks.loader.resolve_dataset` and hashes the file bytes (so editing the
  dataset changes the digest). Module datasets without a file backing are
  hashed over the canonical JSON of their loaded cases. `dataset_sha256` is
  injected as a mandatory manifest field without modifying `archive.py`.
- **Lazy heavy imports.** `manager.py` imports `analysis`/`fingerprint` at
  module load (light, stdlib-only) but imports `figures`/`report` (matplotlib)
  lazily inside the `figure`/`report` commands, so `run`/`list`/`compare`/
  `latest`/`analyze`/`verify` stay import-cheap.
- **Degradation over crash.** Figures with no data write a labelled placeholder
  PNG instead of raising; `verify` on a legacy archive without a fingerprint
  returns `verified=False` with a clear reason instead of erroring.

## 4. Compatibility Notes

- **No public API changes.** No existing function signature or dataclass was
  altered. `manager.run/list/compare/latest` behave exactly as in Sprint 05.
- **No frozen-module changes.** `agents/`, `planner/`, `debate/`, `rag/`,
  `rule_engine/`, `storage/`, `gateway/`, `ui/`, `orchestrator.py`,
  `kg_adapter.py`, `trace/types.py`, and the `evals` runner/ablation cores are
  untouched; `evals/metrics.py` and `evals/capability_metrics.py` are read-only.
- **Backward-compatible archives.** Sprint 05 archives lack `dataset_sha256`;
  `verify` reports `FAIL: dataset_sha256 missing from manifest` (exit 1) rather
  than crashing. New runs always include the fingerprint.
- **Archive layout preserved.** Sprint 05's `config.yaml` / `manifest.json` /
  `environment.txt` / `REPORT.md` / `runs/` / `ablation/` structure is
  unchanged; Sprint 06 only *adds* `figures/`, `analysis.json`, and
  `RESEARCH_REPORT.md` on demand.

## 5. Intentional Deviations

- **matplotlib dependency introduced.** The architecture freeze says "no new
  dependencies", but the Sprint 06 spec explicitly mandates matplotlib PNG
  figures. This is the smallest compatible way to satisfy the deliverable; the
  dependency is isolated to `figures.py` (lazy-imported).
- **Fingerprint covers the primary dataset.** `manifest.json` records a single
  top-level `dataset` (as in Sprint 05); `dataset_sha256` fingerprints that
  source. Experiments with per-run datasets (e.g. `capability_sweep`) are
  fingerprinted on the top-level dataset, matching the manifest's existing
  dataset field rather than adding per-run fingerprints (out of scope).
- **Bootstrap p-value is non-parametric.** Chosen over a t-test because
  capability scores are bounded {0,1}-ish and sample sizes are small; it is
  conservative and appropriate for the data, consistent with the sprint
  principle "effect size before p-value".

## 6. Validation

Run from the repo root with the offline environment
(`DEEPSEEK_API_KEY=''`, memory KG/RAG backends, HF offline):

| Check | Result |
|---|---|
| `ruff check experiments tests/test_analysis.py tests/test_fingerprint.py tests/test_experiments.py` | All checks passed |
| `mypy --follow-imports=silent experiments` | Success: no issues (10 files) |
| `pytest tests/test_analysis.py tests/test_fingerprint.py -q` | 15 passed |
| `pytest -q` (full suite) | 222 passed |

### Acceptance criteria (all verified)

1. **`analyze paper_main`** - outputs mean ± std [95% CI] for run metrics and
   capabilities, plus 27 effect sizes; writes `analysis.json`.
2. **`verify <experiment>`** - `verify paper_main` → `PASS` (dataset intact).
   Mutating the dataset changes the digest and fails verification (covered by
   `test_fingerprint.py::test_verify_fails_when_dataset_changed`). Legacy
   archives without a fingerprint fail gracefully with a clear reason.
3. **`figure paper_main`** - generates 4 PNGs in `figures/`
   (`ablation_capability_impact`, `capability_radar`, `calibration_curve`,
   `comparison_heatmap`), each with bilingual titles/labels.
4. **`report paper_main`** - `RESEARCH_REPORT.md` with LaTeX `tabular` blocks
   (run statistics + effect sizes, escaped), significance markers, a
   module×capability matrix, and embedded figures.
5. **`run paper_evaluation.yaml`** - 20 runs (4 combos × 5 seeds) archived in
   one experiment dir; `analyze` aggregates at the seed level (seeds=5,
   cases=20 per combo).
6. **`manifest.json`** - contains mandatory `dataset_sha256`
   (e.g. `5efc214f…`) and `dataset_source`.
7. **`pytest` / `ruff` / `mypy`** - 222 passed; ruff and mypy clean on Sprint
   06 scope.

### Scientific soundness check
The effect sizes are meaningful: `no_memory` → `knowledge_retrieval` Δ=1.000
(***), `no_counterfactual` → `counterfactual_reasoning` Δ=1.000 (***),
`no_debate` → `conflict_resolution` Δ=0.167 (ns at n=6) - each module's
ablation selectively zeroes its target capability, validating that the
statistical engine correctly links modules to capabilities.

## 7. Known Limitations

- **Offline determinism.** With `DEEPSEEK_API_KEY=''` the orchestrator runs
  text/rules-only and is largely deterministic, so multi-seed runs show ~0
  variance (degenerate CIs). Production runs with a live LLM are needed for
  meaningful confidence intervals; the engine itself is correct.
- **CJK font dependence.** Figure labels are bilingual; if no CJK font is
  installed, Chinese glyphs render as boxes (PNGs still generate). On this
  Windows host `Microsoft YaHei` is available.
- **Small-n inference.** Bootstrap p-values with few seeds/cases are
  conservative; significance should be interpreted alongside the effect size
  and CI per the sprint principle.
- **No Dashboard.** `compare`/`list` remain Sprint 05 CLI text output; a
  persisted visual Dashboard is a future concern.
- **Pre-existing lint debt.** 20 ruff errors exist in 6 unrelated, pre-existing
  test files (`test_metrics.py`, `test_trace.py`, …) from earlier sprints -
  outside Sprint 06 scope and intentionally untouched.

## 8. Design Principle

> **可信度优先于完整度。效应量优先于 p 值。复现优先于美观。**
> Credibility over completeness, effect size over p-value, reproduction over
> aesthetics. Every number traces to the original Traces and a pinned dataset
> version; every run is reproducible; every conclusion carries an effect-size
> estimate and a confidence interval.