# Experiment Manager — Sprint 05 Report

- **Phase:** 2.1E
- **Sprint:** 05 — Experiment Manager (实验即代码，结果即资产)
- **Branch:** `0.45C-Capability_Evaluation_Engine`
- **Git (short):** `ff825c9`
- **Python:** 3.13.3
- **Status:** Complete — all 8 acceptance criteria verified.

## 1. Overview

Sprint 05 introduces an **Experiment Manager** that unifies experiment
configuration, execution, archiving, and reproducibility across ACIS. An
experiment is now described by a single declarative YAML/JSON definition; the
manager parses it, drives the existing evaluation runner / ablation framework
through a thin adapter, and archives an **immutable result bundle**
(configuration, environment snapshot, manifest, per-run metrics, and a summary
report) so any historical conclusion can be precisely reproduced.

The existing cognitive pipeline (`Memory → Experts → Debate → Critic → Judge`,
plus optional Planner / Tool Router) is **untouched**. The manager is a purely
additive layer; no frozen module was modified.

## 2. Modified / New Files

### New files
- `experiments/__init__.py` — package marker.
- `experiments/schema.py` — frozen dataclasses (`ExperimentDefinition`,
  `RunSpec`, `AblationSpec`, `ExperimentMetadata`) + YAML/JSON load/dump.
- `experiments/runner_adapter.py` — `RunnerAdapter` Protocol +
  `DefaultRunnerAdapter`; maps specs onto frozen `EvalConfig`/`AblationConfig`.
- `experiments/archive.py` — immutable bundle writers (`config.yaml`,
  `environment.txt`, `manifest.json`) + git/environment capture.
- `experiments/catalog.py` — read-only index: `list`, `filter`, `compare`,
  `latest`, `load_record`.
- `experiments/manager.py` — orchestration core + CLI
  (`run` / `list` / `compare` / `latest`) + `REPORT.md` renderer.
- `experiments/definitions/baseline.yaml`
- `experiments/definitions/ablation_full.yaml`
- `experiments/definitions/capability_sweep.yaml`
- `experiments/definitions/paper_main.yaml`
- `tests/test_experiments.py` — 18 tests (fake-adapter DI; no orchestrator).
- `docs/EXPERIMENT_MANAGER_SPRINT_05_REPORT.md` — this file.

### Modified files
- **None.** No frozen module was changed. `evals/runner.py` and
  `evals/ablation.py` were left untouched (the optional `run_from_config`
  hook from the spec was not needed — the adapter calls
  `run_evaluation(EvalConfig)` / `run_ablation(AblationConfig)` directly).

## 3. Architecture Decisions

- **Adapter seam (dependency injection).** `RunnerAdapter` is a `Protocol`;
  `DefaultRunnerAdapter` lazily imports and calls the frozen
  `evals.runner.run_evaluation` / `evals.ablation.run_ablation`. This is the
  single integration point and the test-injection seam — tests supply a fake
  adapter, so the suite stays fast and orchestrator-free. A future Dashboard
  can reuse the same seam.
- **Lazy imports.** The heavy runner/ablation/orchestrator stack is imported
  only inside the default adapter methods, so merely importing
  `experiments.manager` (or the catalog) does not load the model stack.
- **Frozen, serializable schema.** `ExperimentDefinition` and friends are
  `@dataclass(frozen=True)`, round-trippable to YAML/JSON via PyYAML. No new
  runtime dependency was added (PyYAML was already present).
- **Write-once immutable archives.** Each run produces
  `results/experiments/<name>__<utc-stamp>/` containing `config.yaml`,
  `environment.txt`, `manifest.json`, `REPORT.md`, plus `runs/<name>/` and
  `ablation/<ts>/` subtrees written by the runner. Archives are never mutated
  by later runs.
- **Uniform run/ablation summary.** `RunSummary` is reused for both evaluation
  runs and ablation combos, so the catalog can compare them in one table.
- **Read-only catalog.** `catalog.py` only reads `manifest.json`; it never
  writes to archives.

## 4. Compatibility Notes

- **No public API changes.** No existing function signature, dataclass, or CLI
  was altered. The manager is an optional, additive subsystem.
- **No frozen-module changes.** `agents/`, `planner/`, `debate/`, `rag/`,
  `rule_engine/`, `storage/`, `gateway/`, `ui/`, `orchestrator.py`,
  `kg_adapter.py`, and the `evals` runner/ablation cores are untouched.
- **No storage / gateway changes.** The manager writes only to the filesystem
  under the configured `output_root` (default `results/experiments`).
- **Existing pipeline unchanged.** The frozen `Memory → Experts → Debate →
  Critic → Judge` flow continues to work exactly as before; the manager simply
  drives it with reproducible configs.

## 5. Validation

Run from the repo root with the offline environment
(`DEEPSEEK_API_KEY=''`, memory KG/RAG backends, HF offline):

| Check | Result |
|---|---|
| `ruff check experiments tests/test_experiments.py` | All checks passed |
| `mypy --follow-imports=silent experiments` | Success: no issues (6 files) |
| `pytest tests/test_experiments.py -q` | 18 passed |
| `pytest -q` (full suite) | 207 passed |

### Acceptance criteria (all verified)

1. **`run baseline.yaml`** — succeeded (~10 s). Archive bundle contains
   `metrics.csv`, `summary.md`, `config.yaml`, `manifest.json`,
   `environment.txt`, `REPORT.md`.
2. **`run ablation_full.yaml`** — succeeded (~12 s). 7 combos
   (`all_on`, `no_planner`, `no_debate`, `no_memory`, `no_counterfactual`,
   `no_tool_router`, `no_critic`) archived under `ablation/<ts>/`, each with
   `metrics.csv` + `summary.md`; all combos recorded in `manifest.json`.
3. **`list`** — lists 4 experiments sorted by `started_at`;
   `--filter dataset=...` and `--filter experiment=...` both work.
4. **`compare <exp1> <exp2>`** — renders an overview + per-run tables that
   include capability-score columns (e.g. `counterfactual_reasoning`,
   `knowledge_retrieval`, `conflict_resolution`). Ablation effects are visible:
   `no_memory` → `knowledge_retrieval=0.000`, `no_debate` →
   `conflict_resolution=0.000`, `no_counterfactual` →
   `counterfactual_reasoning=0.000`.
5. **All 4 templates parse and run without fatal errors** —
   `capability_sweep` (5 suite runs) and `paper_main` (4 runs) completed.
6. **`manifest.json` reproducibility fields** — git short+full+branch, Python
   version, platform, dataset identifier, `environment.txt` (pip freeze),
   started/ended timestamps, duration, per-run aggregate + capability scores.
7. **`pytest tests/test_experiments.py`** — 18 passed.
8. **`ruff` / `mypy`** — zero errors on new files.

## 6. Archive Bundle Layout

```
results/experiments/<name>__<UTC stamp>/
├── config.yaml          # copy of the experiment definition
├── environment.txt      # pip freeze snapshot
├── manifest.json        # git, python, platform, dataset, timing, runs[], ablation{}
├── REPORT.md            # overview + run-metrics + capability summary tables
├── runs/<run_name>/
│   ├── metrics.csv      # written by evals.runner
│   └── summary.md       # written by evals.runner
└── ablation/<ts>/       # only when ablation.enabled
    ├── REPORT.md
    └── <combo_name>/{metrics.csv, summary.md}
```

## 7. Known Limitations

- **Offline / text-only execution.** In this environment `DEEPSEEK_API_KEY` is
  unset, so the orchestrator runs text/rules-only (no network, no transformers
  loaded). Resulting accuracy is ~1.0 and is **not** representative of LLM
  quality; it validates plumbing and reproducibility, not model performance.
  Production runs require a live API key.
- **Reduced `max_cases`.** Templates use small `max_cases` (3–6) for fast
  verification. A complete run sets `max_cases: null`.
- **Dataset checksum.** `manifest.json` records the dataset identifier but not
  a content checksum (the spec marks this optional). Can be added later without
  API changes.
- **`capability_sweep` uses suite JSON paths** (`benchmarks/datasets/<suite>.json`)
  because module-style names do not resolve for suite datasets.
- **No tool execution / MCP.** The manager only orchestrates evaluation runs;
  tool execution remains delegated to the Tool Router / future MCP layer.
- **No Dashboard.** `compare` is CLI text output (Markdown); a persisted
  comparison artifact / Dashboard is a future-Sprint concern.
- **Archives are filesystem-only.** No database index; the catalog scans the
  output root on each invocation (sufficient for current experiment volumes).

## 8. Design Principle

> **实验即代码，结果即资产。**
> Every experiment's configuration, environment, parameters, results, and
> report are archived as immutable assets so any historical conclusion can be
> precisely reproduced. The Experiment Manager is the infrastructure that moves
> ACIS from a research prototype toward a publishable scientific platform.