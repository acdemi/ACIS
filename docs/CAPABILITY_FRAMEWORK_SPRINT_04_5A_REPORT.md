# Sprint 04.5A Report — Capability Framework (Phase 2.1E)

## Summary

Sprint 04.5A establishes ACIS's stable cognitive capability model
(设计原则：**能力抽象化，测量标准化**). Seven capabilities are defined in
`benchmarks/capabilities.py`, each with a Chinese description and typical
trigger scenarios. `BenchmarkMetadata` gains a required `capabilities`
field; the doc generator scans all nine datasets (61 cases), infers
recommended annotations for unannotated cases, and produces
`benchmarks/CAPABILITY_COVERAGE.md` (per-capability counts, coverage density,
under-covered flags) plus `benchmarks/CAPABILITY_ANNOTATION_SUGGESTIONS.md`
for human review. No dataset file is modified — the 61 cases remain pending
annotation pending Chief Architect review.

## Implementation

### Files changed

| File | Change |
|------|--------|
| `benchmarks/capabilities.py` | New: `Capability` enum (7 stable capabilities) with Chinese descriptions + trigger scenarios, `parse_capabilities`, `capability_from_reasoning_feature` |
| `benchmarks/metadata.py` | `BenchmarkMetadata.capabilities` added; `validate_metadata` requires a non-empty `capabilities` list (strict for new cases, lenient scan for legacy datasets); `challenge_type` retained as a secondary dimension |
| `benchmarks/capability_matrix.py` | Enhanced: scans every case's `capabilities` annotation, infers recommendations from reasoning features / challenge_type / design_intent / query keywords, generates `CAPABILITY_COVERAGE.md` + `CAPABILITY_ANNOTATION_SUGGESTIONS.md`; existing suite/challenge matrices preserved |
| `benchmarks/CAPABILITY_COVERAGE.md` | Auto-generated capability coverage matrix (7/7 capabilities with ≥2 cases) |
| `benchmarks/CAPABILITY_ANNOTATION_SUGGESTIONS.md` | Auto-generated per-case annotation suggestions for all 61 unannotated cases |
| `tests/test_capabilities.py` | 17 unit tests: enum completeness, metadata validation, coverage matrix, suggestions, doc generation |
| `tests/test_enriched.py` | Test fixture alignment only: `_metadata()` helper now includes `capabilities` (keeps the existing 150 tests green under the new contract) |
| `docs/CAPABILITY_FRAMEWORK_SPRINT_04_5A_REPORT.md` | This report |

### Design decisions

- **Capability model is module-agnostic.** The seven capabilities
  (`information_gathering`, `knowledge_retrieval`, `conflict_resolution`,
  `counterfactual_reasoning`, `uncertainty_quantification`,
  `multi_step_planning`, `sensor_cross_validation`) name what the system
  should be able to do cognitively, not which modules implement it, so
  benchmarks stay valid across refactors.
- **Strict for new, lenient for legacy.** `validate_metadata` now rejects
  metadata without `capabilities` (acceptance 4). Legacy `enriched.json`
  predates the framework, so scanning uses `require_capabilities=False` and
  reports those cases as 待标注 (pending) rather than invalid — keeping all
  150 pre-existing tests green without touching read-only datasets.
- **Suggestions never write data.** Inference (from
  `expected_reasoning_features`, `challenge_type`, `design_intent`, and
  query keywords) is emitted only into
  `CAPABILITY_ANNOTATION_SUGGESTIONS.md`; dataset files are byte-identical
  after generation (covered by a test).
- **Coverage is measured, not assumed.** `CAPABILITY_COVERAGE.md` reports
  annotated vs inferred counts, coverage density (%), and ⚠ under-covered
  flags (<2 cases), so gaps are visible to the architect.

## Validation

- **pytest**: 167 passed (17 new `tests/test_capabilities.py` + 150
  existing). No regressions.
- **ruff**: clean on all new/modified files (`capabilities.py`,
  `metadata.py`, `capability_matrix.py`, `test_capabilities.py`,
  `test_enriched.py`).
- **mypy**: 0 errors in the new/modified files (33 pre-existing transitive
  frozen-module errors unchanged).
- **Acceptance 1**: `capabilities.py` defines 7 capabilities, each with a
  non-empty Chinese description and trigger scenarios.
- **Acceptance 2**: `python -m benchmarks.capability_matrix` generates
  `CAPABILITY_COVERAGE.md` (9 datasets, 61 cases).
- **Acceptance 3**: all 7 capabilities have case coverage
  (3–18 cases each, 0 under-covered), exceeding the ≥5 requirement.
- **Acceptance 4**: `validate_metadata` rejects metadata with missing /
  empty / unknown `capabilities` (covered by tests).
- **Acceptance 5**: `pytest tests/test_capabilities.py` green; full suite
  167 passed (150 existing + 17 new).
- **Acceptance 6**: ruff & mypy zero errors on new files.

## Architecture Review

- **Adherence to frozen modules**: no changes to `agents/`, `planner/`,
  `debate/`, `rag/`, `rule_engine/`, `storage/`, `gateway/`, `ui/`,
  `orchestrator.py`, `workflow.py`, `kg_adapter.py`, `evals/runner.py`, or
  `evals/ablation.py`. All nine dataset JSON files are untouched (read-only,
  verified byte-identical by a test).
- **New abstractions**: `Capability` enum + helpers, `capabilities` field on
  `BenchmarkMetadata`, capability coverage scanner/renderer, annotation
  suggestion generator. All additive.
- **Backward compatibility**: existing metadata contract validators remain
  lenient for legacy data; existing suite/challenge docs still generated;
  all 150 pre-existing tests pass.
- **Dependency direction**: `metadata` → `capabilities`;
  `capability_matrix` → `capabilities` / `metadata` / `loader` / `taxonomy`.
  `capabilities.py` is standalone and domain-free.

## Known Issues

1. No dataset carries explicit `capabilities` yet (0/61 annotated) —
  coverage is entirely inferred. The suggestions file is the input for the
  Chief Architect review; annotation should be applied to dataset metadata
  in a later approved sprint.
2. Inference is keyword/rule-based; easy/medium/hard cases (no
  `design_intent` or metadata) sometimes get no suggestion ("—"), so their
  coverage contribution is partial.
3. `uncertainty_quantification` is inferred from `证据不足` ground truths and
  physiological keywords only; it is not yet measured from judge confidence
  behavior.

## Future Work

- After Chief Architect approval: annotate `metadata.capabilities` in
  datasets and re-run coverage to move counts from 待标注 to 已标注.
- Capability-scored evaluation (per-capability metrics from runner traces).
- LLM-assisted or expert-curated inference to reduce heuristic noise for
  difficulty-tier datasets.

## Technical Debt

- Unchanged pre-existing debt: mypy errors in frozen modules, E402 in
  `orchestrator.py` / `fixture_eval.py` / `smoke_eval.py`, planner overload
  warning (see `context/KNOWN_DEBT.md`).
