# ACIS Changelog

## [2.1E-Sprint02] — 2026-08-01

### Added
- Evaluation Runner (`evals/runner.py`)
- Evaluation Metrics (`evals/metrics.py`) — 9 metrics derived from Unified Trace
- Report Generator (`evals/report.py`) — CSV + Markdown output
- Eval Config (`evals/config.py`) — EvalCase schema, dataset loading
- 18 unit tests for metrics and config (`tests/test_metrics.py`)

### Frozen
- All cognitive modules unchanged (Planner, Judge, Debate, Tool Router, Memory, DecisionOutput)

### Known Limitations
- Runtime measures `run()` wall clock only (warm-up absorbed)
- `memory_hits` uses ≥0.5 confidence heuristic
- `debate_rounds` derived from text markers, not a first-class Trace field
- Tool router requires planner on

---

## [2.1E-Sprint01] — 2026-07-28

### Added
- Unified Trace infrastructure
- 57 regression tests

---

## [2.1] — 2026-07-25

### Added
- Planner
- Tool Router
- LangGraph Workflow with 7 nodes
- Meta-Critic (cascade error detection)
- Procedural Memory Agent
- Economic Agent
- Ecology Agent

---

## [2.0] — 2026-07-10

### Added
- Multi-Agent System (9 agents)
- Debate Engine with 5 conflict types
- Critic with intent-aware routing
- Judge Agent (rule + DeepSeek dual mode)
- Counterfactual Reasoning
- Confidence Calibration (Isotonic Regression)
- Knowledge Graph Adapter (Neo4j + memory fallback)
- RAG with Qdrant + memory fallback
- SQLite Decision Persistence
- FastAPI Gateway + Streamlit UI + TUI
- 12 fixture regression cases