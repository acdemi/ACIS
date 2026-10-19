# CURRENT SPRINT

Phase: 4.2-R — Challenge Set Evaluation (Real Agent)
Sprint: 06 (completed) -> Phase 4 Evaluation Campaign
Status: **Phase 4 评测可靠性修复 + 指标契约修复完成（2026-10-17/18）；真实 Judge 恢复 BLOCKED（凭证 401，2026-10-18）— 等待凭证更新与架构决策**
Goal: Architecture impact assessment — Challenge Set multi-seed validation + real agent evaluation

## 结论摘要（截至 2026-08-31）

| 轮次 | 规模 | 结果 |
|---|---|---|
| Phase 4.1 pilot（08-09） | 3 configs × 24 cases = 72 calls | accuracy C0 0.5611 / C1 0.5451 / C2 0.5062；仅 ECE C1 略优 |
| Phase 4.2 验证（08-10） | 3 seeds × 3 configs × 24 cases = 216 calls | 弃权率 41/33/31、平均置信度 0.39/0.50/0.52；accuracy 未显著改善 |
| Phase 4.2-R 真实 Agent（08-12） | 216 calls | judge 191/216 回退 rules（APIConnectionError） |
| R3 稳定性（08-16/17） | 3 seeds × 3 configs × 24 cases（rule-engine coherence） | C0 0.3623±0.1624 > C1 0.2799±0.1505、C2 0.2975±0.1247；排名跨 seed 翻转 |
| R3 压力测试（08-13） | C1 seed42 单案例 30 次 | 30/30 PASS（均值 179.8s/次） |
| R4 预检（08-30） | harness vs 真实决策 | **FAIL**（置信度偏移 0.320 / 0.750，C2 标签不一致） |
| 可靠性修复（10-17） | judge 配置集中化 + 重试归属 + 共享决策语义 | 完成；无 benchmark/架构变更 |
| 契约审计（10-17） | 同一 trace 修复前后对比 | factor coverage 0.00 → 0.25；coherence 实为量化覆盖率 |
| Judge 恢复（10-18） | 认证验证 + 六次最小预检 | **BLOCKED**：DEEPSEEK_API_KEY 401（authentication_error） |

**核心结论**：当前证据不支持"完整 ACIS（C1）优于裸基线（C0）"；R3 显示排名随 seed 翻转、方差大。

## 待决策与解除阻塞

- **阻塞（需用户操作）**：通过正常 `.env` 渠道更新 `DEEPSEEK_API_KEY`（当前凭证 HTTP 401 authentication_error；
  `AGRI_AI_JUDGE_API_KEY` 不存在）。更新后按
  `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md` 重做 judge 认证验证 + 六次最小预检。
- **Phase 5**：扩展评测（更多 seed / 更大样本 / 统一评分口径），补足证据。
- **Phase 6**：架构重设计。
- 决策前置条件：
  1. 统一 judge 端点与重试策略 — 已落地（2026-10-17，`utils/judge_runtime.py` + SDK 重试预算）；
  2. 对齐 harness 与真实 Agent 的决策与置信度口径（R4 预检 FAIL）— 语义规范已建（`decision_semantics.py`），数值对齐待真实 Judge 恢复；
  3. 明确 accuracy/ECE/abstention/coherence 的判定口径 — 已修复（2026-10-17，指标契约审计 + 修复）。

## 产物索引

- `benchmarks/challenge_set_v1.json`（Challenge Set v1，24 案例）
- `reports/phase4_evaluation_pilot.md`（Phase 4.1）
- `reports/phase4_validation_report.md`（Phase 4.2）
- `reports/phase4_2_real_agent/`（真实 Agent：stability_report / diagnosis_judge_fallback / environment_diff / precheck_report）
- `reports/phase4_2_r3_stability_report.md`、`reports/phase4_2_r3_stress_test.md`
- `reports/phase4_2_r4_precheck_report.json`
- `scripts/run_phase4_2.py`、`scripts/run_phase4_2_real_agent.py`、`scripts/generate_stability_report.py`、`scripts/stress_test_judge.py`
- `src/openmetaphysics/evaluation/`（challenge_scorer / challenge_report）
- `utils/judge_runtime.py`（judge 配置集中解析 + 运行时元数据，2026-10-17）
- `decision_semantics.py`（共享决策语义规范，2026-10-17）
- `reports/phase4_evaluation_reliability_repair.md`（评测可靠性修复，2026-10-17）
- `reports/phase4_evaluation_metric_contract_audit.md`（指标契约审计与修复，2026-10-17）
- `reports/phase4_real_agent_consistency_20261017/`（真实 Agent 一致性预检产物）
- `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md`（Judge 恢复 BLOCKED 报告）

## Read Order

1. `reports/phase4_evaluation_metric_contract_audit.md`
2. `reports/phase4_evaluation_reliability_repair.md`
3. `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md`
4. `reports/phase4_2_r3_stability_report.md`
5. `reports/phase4_2_real_agent/diagnosis_judge_fallback.md`
6. `decision_semantics.py`、`utils/judge_runtime.py`

## Stop Conditions

- 用户经 `.env` 更新有效凭证后，方可恢复真实 Judge 认证验证与最小预检。
- 架构师审查 Phase 4 结论并决定 Phase 5（扩展评测）或 Phase 6（架构重设计）。
- 未获指示前不进入下一阶段；不做无证据的工程增量。