# CURRENT SPRINT

Phase: 4.2-R — Challenge Set Evaluation (Real Agent)
Sprint: 06 (completed) -> Phase 4 Evaluation Campaign
Status: **Phase 4.2-R R2/R3/R4 完成（2026-08-31）— 等待架构决策**
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

**核心结论**：当前证据不支持"完整 ACIS（C1）优于裸基线（C0）"；R3 显示排名随 seed 翻转、方差大。

## 待架构决策

- **Phase 5**：扩展评测（更多 seed / 更大样本 / 统一评分口径），补足证据。
- **Phase 6**：架构重设计。
- 决策前置条件：
  1. 统一 judge 端点与重试策略（R2 诊断：端点/连接性不一致）；
  2. 对齐 harness 与真实 Agent 的决策与置信度口径（R4 预检 FAIL）；
  3. 明确 accuracy/ECE/abstention/coherence 的判定口径。

## 产物索引

- `benchmarks/challenge_set_v1.json`（Challenge Set v1，24 案例）
- `reports/phase4_evaluation_pilot.md`（Phase 4.1）
- `reports/phase4_validation_report.md`（Phase 4.2）
- `reports/phase4_2_real_agent/`（真实 Agent：stability_report / diagnosis_judge_fallback / environment_diff / precheck_report）
- `reports/phase4_2_r3_stability_report.md`、`reports/phase4_2_r3_stress_test.md`
- `reports/phase4_2_r4_precheck_report.json`
- `scripts/run_phase4_2.py`、`scripts/run_phase4_2_real_agent.py`、`scripts/generate_stability_report.py`、`scripts/stress_test_judge.py`
- `src/openmetaphysics/evaluation/`（challenge_scorer / challenge_report）

## Read Order

1. `reports/phase4_2_r3_stability_report.md`
2. `reports/phase4_2_real_agent/diagnosis_judge_fallback.md`
3. `reports/phase4_2_r4_precheck_report.json`
4. `benchmarks/challenge_set_v1.json`
5. `scripts/run_phase4_2_real_agent.py`
6. `src/openmetaphysics/evaluation/challenge_scorer.py`

## Stop Conditions

- 架构师审查 Phase 4 结论并决定 Phase 5（扩展评测）或 Phase 6（架构重设计）。
- 未获指示前不进入下一阶段；不做无证据的工程增量。