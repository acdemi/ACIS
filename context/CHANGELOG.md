# ACIS Changelog

## [Phase 4.2-R] — 2026-08-31

### Added
- 真实 Agent 评测与诊断：`scripts/run_phase4_2_real_agent.py`、`scripts/generate_stability_report.py`、`scripts/stress_test_judge.py`
- 报告：`reports/phase4_2_real_agent/`（稳定性 / judge 回退诊断 / 环境差异 / 预检）、`reports/phase4_2_r3_stability_report.md`、`reports/phase4_2_r3_stress_test.md`、`reports/phase4_2_r4_precheck_report.json`

### Findings
- R2 诊断：216 次真实运行中 191 次 judge 回退 rules（`APIConnectionError: Connection error.`）；端点配置不一致（免费网关 vs 付费端点 402）为候选根因
- R3 稳定性（rule-engine coherence judge）：C0 accuracy 0.3623±0.1624 > C1 0.2799±0.1505、C2 0.2975±0.1247；排名跨 seed 翻转
- R3 压力测试：C1/seed42/`amb_tomato_mold_blind_leaf` 30/30 PASS（均值 179.8s/次）
- R4 预检：harness 与真实 Agent 决策对比 **FAIL**（C0 置信度偏移 0.320、C2 0.750，C2 标签 ABSTAIN vs 叶霉病）

### Known Issues
- judge 端点/连接性配置需统一（含重试策略）
- harness 与真实链路结果不一致，评分口径需对齐

---

## [Phase 4.2] — 2026-08-10

### Added
- Challenge Set v1：`benchmarks/challenge_set_v1.json`（24 案例，5 类挑战）
- 多 seed 验证：3 seeds × 3 configs × 24 cases = 216 calls（`reports/phase4_validation_report.md`）
- `src/openmetaphysics/evaluation/`（challenge_scorer / challenge_report）

### Findings
- C1/C2 相对 C0：弃权率下降（41/33/31）、平均置信度上升（0.39/0.50/0.52），accuracy 未显著改善
- 1 条 malformed output（seed 44 / C2 / case 8）

---

## [Phase 4.1] — 2026-08-09

### Added
- Phase 4 pilot：3 configs × 24 cases = 72 calls（`reports/phase4_evaluation_pilot.md`）

### Findings
- accuracy：C0 0.5611 / C1 0.5451 / C2 0.5062；仅 ECE C1 略优（0.4571）
- C1 未在任一维度显著优于 C0

---

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
