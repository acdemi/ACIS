# ACIS Changelog

## [Phase 6 Decision Confidence Redesign] — 2026-10-24

### Added
- `utils/confidence_calibration.py`：`compute_decision_signals` / `combine_decision_score` / `DecisionCalibrator`（ADR-005）
- `agents/judge_agent.py`：自一致性采样（k=3，含重试）、记忆层输出门控、弃权判定规则
- `scripts/fit_decision_calibration.py`：从真实运行 trace 生成校准样本，支持 `--scored-only`
- `utils/judge_runtime.py`：opencode zen 网关 `x-opencode-session` 头支持
- 报告：`reports/phase6_baseline_20261023/baseline_analysis.md`、
  `reports/phase6_redesign_20261023/implementation_status.md`、`final_evidence.md`
- 测试：`tests/test_decision_confidence.py`（10 项）

### Findings
- 真实 Judge 全量基线（3 configs × 24 × seed42，零回退）：置信度均值 0.46–0.50 对 accuracy 0.79–1.00，
  ECE 0.34–0.50；**LLM 自评与全部结构信号均无判别力**（特征分离度 ≤ 0.077）
- C1 与 C2 仅差 `memory_on`：19/24 vs 24/24，5 例翻转 → 记忆层注入噪声
- **Judge 三次采样判定一致率是唯一有判别力的信号**：seed42 corr 0.778、seed43 corr 0.538；
  建立 `confidence = min(0.95, agreement)` 后 ECE 0.071–0.077（ADR 判据达成）
- 被否证：结构信号 + isotonic 曾给出 ECE 0.013 / corr -0.005（校准压成常数）；
  13 样本 isotonic 使 ECE 0.104→0.175、corr 0.539→0.508 → 设 50 样本门槛

### Known Issues
- accuracy 未提升（C1 seed43 0.792 与改造前持平）
- 仅覆盖 C1、2 seeds；C0/C2 对照与零误弃权判据待补

---

## [Phase 4 Real Judge Recovery] — 2026-10-19

### Added
- 真实 LLM Judge 恢复验证：单次受控验证探针（`logs/judge_auth_probe_20261019.py`，gitignored）
  + 六次最小预检（`reports/phase4_judge_recovery_20261019/`：总结报告 + 3 案例 × seed 42/43 报告与 trace）

### Findings
- 凭证更新后 6/6 运行 `judge_mode=deepseek`、零 rules 回退、零 authentication_error；trace 记录 outcome=success 与完整 token usage
- GT 标签 5/6：case14（弃权案例）seed42 误判为番茄早疫病，seed43 弃权——跨 seed 决策翻转，再次印证方差风险
- 全部 6 轮 harness 对比按修复后契约判 INCOMPARABLE（执行语义不同）；置信度偏移 0.10–0.52 仅作诊断
- 观察：API 响应 `model=deepseek-flash`（请求 `deepseek-chat`），服务端伺服型号命名

### Known Issues
- harness 与真实链路口径对齐（原 R4 FAIL）仍开放
- Phase 5（扩展评测）vs Phase 6（架构重设计）架构决策仍未决

---

## [Phase 4 Reliability & Contract Repair] — 2026-10-17/18

### Added
- `utils/judge_runtime.py`：Judge 配置集中解析（key / base URL / model / 超时 / SDK 重试预算），
  每个 Judge 决策记录脱敏 `judge_runtime` 元数据（outcome、mode、provider、端点 ID、失败码、token usage 等）
- 失败码分类：`missing_credentials` / `authentication_error` / `billing_error` / `rate_limit` / `timeout` /
  `connection_error` / `response_format_error` / `server_error` / `api_http_error` / `provider_error`
- `decision_semantics.py`：评测与 Phase 4 适配器共享的决策语义规范（ABSTAIN 是状态不是标签；
  accuracy 对比最终 Judge 决策；期望「证据不足」仅在弃权时判对）
- 评测层指标契约修复（d9fcb7b）：factor coverage 计入 formal action_plan、abstention 判定、
  fallback 分层与缺失事件不计分等口径修复；新增评测层单测
- 报告：`reports/phase4_evaluation_reliability_repair.md`、`reports/phase4_evaluation_metric_contract_audit.md`、
  `reports/phase4_real_agent_consistency_20261017/`、`reports/phase4_real_judge_recovery_20261018/`

### Findings
- 历史 "label accuracy=1.00 / factor coverage=0.00 / coherence=0" 三元组为三个不同因素叠加
  （指标口径不同 + action_plan 被丢弃 + coherence 实为量化覆盖率非逻辑一致性）；
  同一 trace 契约修复后 factor coverage 0.00 → 0.25，label accuracy 保持 1.00
- 重试归属修复：JudgeAgent 单次 SDK 调用交由 SDK 重试预算；legacy harness `max_retries=0`，
  仅在 provider 明确拒绝 `seed`（HTTP 400/422）时重试
- 真实 Judge 凭证无效：真实 trace 记录 HTTP 401 `authentication_error`、`judge_mode=rules`；
  `AGRI_AI_JUDGE_API_KEY` 不存在 → 恢复 BLOCKED（2026-10-18）

### Known Issues
- `DEEPSEEK_API_KEY` 待经正常 `.env` 渠道更新后重做 judge 认证验证与六次最小预检
- Phase 5（扩展评测）vs Phase 6（架构重设计）架构决策仍未决

---

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
