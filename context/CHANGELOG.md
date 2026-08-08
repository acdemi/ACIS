# ACIS Changelog

## [2.1E-Sprint04.5C] — 2026-08-02

### Added
- Capability Evaluation Engine（`evals/capability_metrics.py`）：7 种能力的 Trace 打分（0/1）
- `CaseMetrics.capability_scores`、`metrics.csv` 能力列、`summary.md` “Capability Performance”
- Ablation 联动：`--planner-off` → information_gathering / multi_step_planning 归零；`--memory-off` → knowledge_retrieval 归零
- 12 个单测（`tests/test_capability_metrics.py`）；pytest 总计 189 passed

### Known Issues
- `conflict_resolution` 严格依赖 critic triggered：3 个环境矛盾案例分数为 0
- `information_gathering` 依赖关键词启发式（提示词变更需重新校准）
- `sensor_cross_validation` 需要真实传感器异常或 `sensor_verify` 请求

---

## [2.1E-Sprint04.5B] — 2026-08-01

### Added
- Verifiable Capability Contract：`observable_evidence`（capability / expected_behavior / success_condition）
- 36/36 能力案例 + 16/28 难度案例显式标注；12 个纯特征匹配难度案例按设计不标注
- `enriched.json` 新增 3 个 information_gathering 案例（15→18）
- `CAPABILITY_CONSISTENCY_REPORT.md`：52/52 一致、0 不一致
- 10 个新单测（`tests/test_capabilities.py`）；pytest 总计 177 passed

---

## [2.1E-Sprint04.5A] — 2026-08-01

### Added
- Capability Framework：`benchmarks/capabilities.py`（7 能力枚举）、`CAPABILITY_COVERAGE.md`、`CAPABILITY_ANNOTATION_SUGGESTIONS.md`
- 17 个新单测；pytest 总计 167 passed

---

## [2.1E-Sprint04] — 2026-08-01

### Added
- Ablation Framework（`evals/ablation.py`）：all_on 基线 + 6 个关闭组合
- `results/ablation/` 报告；模块贡献度（memory_hits / debate_rounds / counterfactual_count / runtime）可测量

---

## [2.1E-Sprint03] — 2026-08-01

### Added
- Benchmark Framework：9 数据集（schema / loader / taxonomy / metadata / capability_matrix）
- 难度分层（easy/medium/hard）+ 五类能力套件 + enriched 挑战集

---

## [2.1E-Sprint02] — 2026-08-01

### Added
- Evaluation Runner（`evals/runner.py`）
- Evaluation Metrics（`evals/metrics.py`）— 9 metrics derived from Unified Trace
- Report Generator（`evals/report.py`）— CSV + Markdown output
- Eval Config（`evals/config.py`）— EvalCase schema, dataset loading
- 18 unit tests for metrics and config（`tests/test_metrics.py`）

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
