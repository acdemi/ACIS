# Current Sprint

Phase: 2.1E
Sprint: 03
Goal: Benchmark Dataset Framework with Trace Export

## Read Order
1. docs/architecture/architecture.md
2. docs/architecture/principles.md
3. context/ARCHITECTURE_STATE.md
4. context/KNOWN_DEBT.md

## Scope

### Allowed Files
- `benchmarks/` (new directory)
  - `schema.py`
  - `datasets/easy.json`
  - `datasets/medium.json`
  - `datasets/hard.json`
  - `loader.py`
- `evals/config.py` (minor adjustment to support JSON dataset loading)
- `evals/runner.py` (add `--save-traces` option, default off)
- `tests/test_benchmarks.py` (new)

### Forbidden Files
- ALL files in `agents/`, `planner/`, `debate/`, `rag/`, `rule_engine/`, `storage/`, `gateway/`, `ui/`
- `orchestrator.py`, `workflow.py`, `kg_adapter.py`
- Any module marked Frozen in ARCHITECTURE_STATE.md

## Deliverables
1. Benchmark dataset schema compatible with EvalCase.
2. Three datasets: easy (≥10 cases), medium (≥10), hard (≥5).
3. Dataset loader that works with existing `evals/runner.py`.
4. Lightweight trace export: `--save-traces` flag on runner, saving each trace to `results/traces/{trace_id}.json`.
5. Unit tests for benchmark loading and validation.

## Acceptance Criteria
- `python evals/runner.py --dataset benchmarks.datasets.easy --save-traces` runs successfully and produces `results/metrics.csv`, `results/summary.md`, and trace files in `results/traces/`.
- `pytest tests/test_benchmarks.py` passes.
- `ruff` and `mypy` clean on new files.

## Stop Conditions
- Acceptance criteria met.
- Sprint Report generated.
- **Do NOT proceed to next Sprint.**