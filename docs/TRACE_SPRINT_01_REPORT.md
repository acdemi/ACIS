# Unified Trace Infrastructure — Sprint 01 Report (Phase 2.1E)

Sprint: 2.1E / Sprint 01
Scope: Introduce a unified Trace system as the single source of truth for one orchestrator run.
Status: Complete. Cognitive features frozen; no Planner/Judge/Debate/DecisionOutput changes.

---

## 1. Implementation Report

### Deliverables

| File | Role |
|------|------|
| `trace/types.py` | Immutable `TraceEvent`, single-source `Trace`, `STAGE_ORDER`, `REQUIRED_STAGES` (domain-free) |
| `trace/collector.py` | `TraceCollector` + domain serializers + `collect_pipeline_trace` (only domain-aware module) |
| `trace/exporter.py` | `trace_to_dict`, `export_trace_json` (domain-free) |
| `trace/__init__.py` | Public API surface |
| `tests/test_trace.py` | 16 unit tests (collection + JSON export + immutability + snapshot independence) |
| `orchestrator.py` | Non-invasive wiring: `last_trace` attr + `_build_trace()` called from `run()` |

### Core types

- `TraceEvent` (`@dataclass(frozen=True)`): `{stage, timestamp, payload}`. Frozen so fields cannot
  be reassigned; `payload` is `copy.deepcopy`-ed in `__post_init__`, so each event is an independent
  snapshot — later mutation of a source domain object cannot retroactively alter a recorded event.
  The constructor rejects unknown stages with `ValueError`.
- `Trace`: `{trace_id, timestamp, events}`. `events` is the canonical append-only, chronologically
  ordered log. Per-stage views (`request`, `perception`, `memory`, `experts`, `debate`, `critic`,
  `judge`, `planner`, `tool_router`, `metrics`) are read-only filtered views over `events` — there
  is exactly one source of data, no duplicated storage.

### Stages captured

`request, perception, memory, experts, debate, critic, judge, planner, tool_router, metrics`.

The spec's required set is `request, memory, experts, debate, critic, judge, planner, tool_router,
metrics` (all present). `perception` is added so that **every** pipeline stage appends an event
(the orchestrator has a distinct perception stage: vision/sensor/weather agents); the required
stages remain the trace's mandated surface. Agent outputs are bucketed into perception / memory /
experts by `AgentOutput.layer` (`感知层` / `记忆层` / `专家层`).

### Collector

`TraceCollector.record(stage, payload)` builds an immutable `TraceEvent` and appends it. Typed
helpers (`record_request`, `record_agents`, `record_debate`, `record_critic`, `record_judge`,
`record_planner`, `record_tool_router`, `record_metrics`) serialize domain artifacts via
`dataclasses.asdict` / manual dicts. `collect_pipeline_trace(...)` builds a complete trace from one
run's artifacts in canonical stage order. Planner and tool-router artifacts are optional
(`ExecutionPlan | None`, `ToolRoutingResult | None`), so Planner ON and OFF both yield a valid trace;
a `metrics` event records `enabled` flags, counts, and `total_events`.

### Exporter

`trace_to_dict` mirrors the Trace surface: `trace_id`, `timestamp`, one key per stage (list of
payload dicts), and the full ordered `events` log. `export_trace_json` serializes to JSON
(`default=str` fallback for safety). Output is JSON-native for all current payloads.

### Orchestrator integration (non-invasive)

- `__init__`: `self.last_trace: Trace | None = None`.
- `run()`: after persist + optional planner/tool-router, calls
  `self.last_trace = self._build_trace(decision, query, image_path)` before returning `decision`.
- `_build_trace()` builds the request context and delegates to `collect_pipeline_trace` with
  `decision.traces`, `decision.debate`, `decision`, `self.last_execution_plan`,
  `self.last_tool_requests`.

No change to `run()`'s signature or return type, no `DecisionOutput` modification, no cognitive
logic touched. The trace is observational only.

### Validation

- **pytest**: 57 passed (16 new trace tests + 41 existing). No regressions.
- **ruff** (new files `trace/`, `tests/test_trace.py`): clean under `--select E,F` and
  `--select E4,E7,E9,F`. `orchestrator.py`: clean under `--select F`; the trace additions add 0 new
  findings (pre-existing baseline findings listed in Known limitations).
- **mypy**: 0 errors in `trace/`, `tests/test_trace.py`, and `orchestrator.py` itself. Pre-existing
  errors in imported modules are out of scope (see Known limitations).
- **End-to-end smoke** (rules path): Planner OFF and Planner ON both build a 19-event trace with all
  required stages and correct `enabled` flags; JSON export round-trips.

---

## 2. Architecture Review

### Single source of truth
`Trace.events` is the only stored log; per-stage properties are derived filters, not copies. This
guarantees consistency (no two views can disagree) and keeps memory proportional to event count.

### Immutability model
`TraceEvent` is `frozen` with a deep-copied payload → true snapshot semantics. The aggregate `Trace`
is mutable only by appending immutable events (`append`), matching "every pipeline stage appends
immutable TraceEvent objects". Mutating source objects after recording does not affect recorded
events (covered by `test_recorded_events_are_independent_of_source_mutation`).

### Non-invasive integration
Integration is confined to the `run()` chokepoint, which already has access to every stage's output
(`decision.traces`, `decision.debate`, planner/tool-router results). Both execution paths (rules and
LangGraph) converge here and produce a `DecisionOutput`, so the trace is built uniformly without
instrumenting each graph node or `run_rules` line — no cognitive code touched, no API change.

### Snapshot-at-chokepoint vs live streaming
The trace is assembled once at the end of `run()` from the run's artifacts (each stage still appends
an immutable `TraceEvent` to the collector in canonical order). This trades live per-stage
observability for zero coupling to stage internals and zero risk to the frozen cognitive pipeline.
Live streaming instrumentation is a future option if real-time observability is required.

### Layered decoupling
`trace/types.py` and `trace/exporter.py` are domain-free (reusable, unit-testable in isolation).
Only `trace/collector.py` knows the domain data contracts (`agents.types`, `planner.types`,
`tool_router.types`) and only reads them — never mutates. No circular imports (`trace` imports from
`agents`/`planner`/`tool_router`; none import `trace`).

### Planner ON/OFF
`collect_pipeline_trace` accepts `plan=None` / `tool_result=None`; both states record a
`planner`/`tool_router` event with `enabled=False` and metrics reflect disabled state. Verified
end-to-end for both modes.

### Re-export hygiene
`orchestrator.py` re-exports `AgentOutput`/`DebateResult` (consumed by `debate/critic.py` under
`TYPE_CHECKING`). These were made explicit re-exports (`import X as X`) to resolve the pre-existing
F401 without changing the public surface.

---

## 3. Known Limitations

1. **Snapshot timing**: the trace is assembled at the end of `run()` rather than appended live
   during each stage execution. Every stage still appends an immutable `TraceEvent` (via
   `collect_pipeline_trace`), but there is no per-stage streaming hook. Live instrumentation is
   deferred to a later sprint if real-time observability is needed.
2. **`perception` stage added beyond the required list**: included so every pipeline stage appends
   an event (the required stages are unchanged). Flagged for explicitness.
3. **`trace` package shadows the stdlib `trace` module** when the repo root is first on `sys.path`.
   No code in the repo imports stdlib `trace`, so there is no conflict today; renaming (e.g.
   `acis_trace`) would remove the shadow if desired in a future sprint.
4. **Pre-existing baseline lint/type findings (out of scope)**:
   - `orchestrator.py`: 15× E402 from the intentional `load_env()`-between-imports pattern
     (env vars must load before agent imports); not introduced or fixed here.
   - `planner/planner.py`: pre-existing mypy `call-overload` on the DeepSeek `create` call (line 131)
     and ruff S110/BLE001 on its `except Exception: pass` fallback. Surfaces transitively whenever
     `planner.types` is imported (same as the existing `tool_router` and `test_planner`). "No Planner
     changes" forbids fixing it.
   - Other pre-existing mypy errors in `rag/`, `rule_engine/`, `agents/`, `debate/`, `utils/`,
     `storage/` (missing third-party stubs / typing gaps) — untouched, several in frozen modules.
   - Ruff on this machine defaults to a broad rule set under which the baseline repo already fails;
     the new trace code is clean under the project's `E`/`F` standard implied by the existing
     `# noqa: E402` convention.
5. **Multi-round debate**: rebuttal-round expert outputs are classified into the `experts` stage
   (round number is preserved inside each output's `evidence`); there is no dedicated `rebuttal`
   stage in this sprint.
6. **In-memory only**: traces live on `orchestrator.last_trace` and are not persisted. Persistence
   (e.g. alongside `storage.repository`) and an `AGRI_AI_TRACE` toggle are natural follow-ups.
7. **LangGraph intermediate state**: only the final `DecisionOutput` (and its `traces`/`debate`) is
   captured; per-node intermediate states inside the compiled graph are not separately traced.
