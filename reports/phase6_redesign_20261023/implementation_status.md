# Phase 6 Redesign — Implementation Status & Evidence (2026-10-23)

> Branch: `work/20261023-phase6-arch-redesign`
> ADR: ADR-005（决策聚合与置信度链路重构，Proposed → 实施中）

## 1. What was implemented

1. `utils/confidence_calibration.py`
   - `compute_decision_signals`：从 Judge 输出提取结构信号（自评、KG 支持率、证据强度、
     冲突数、集体忽略数、critic escalate、KG 贡献增量）
   - `combine_decision_score`：文档化权重的确定性聚合（0.45 自评 + 0.35 证据 + 0.20 KG − 惩罚）
   - `DecisionCalibrator`：isotonic/Platt/constant 校准，数据来自
     `utils/decision_calibration_data.json`，可用 `AGRI_AI_DECISION_CALIBRATION=0` 关闭
2. `agents/judge_agent.py`
   - 真实 LLM 路径不再直接把 `final_confidence` 当作最终置信度；改为
     `derived = calibrate(combine(signals))`，自评值保留在
     `judge_analysis.confidence_design.self_report`
   - `_apply_abstention_policy`：弃权须由证据不足"挣得"——证据充分（KG 支持 + 证据强度
     均值 ≥ 阈值）且无冲突时，用专家多数意见覆盖误弃权，并置 `need_human_review`
   - `_gate_memory_outputs`：记忆层输出在进入 Judge payload 前按置信度/无匹配过滤
     （`AGRI_AI_MEMORY_GATE`, `AGRI_AI_MEMORY_GATE_MIN_CONF`）
3. `scripts/fit_decision_calibration.py`：从真实 Judge 运行的 trace + metrics 重算结构分，
   生成校准样本；契约要求"一个 seed 拟合、另一个 seed 评估"
4. `tests/test_judge_runtime.py`：两处旧契约断言（`confidence == LLM 自报值`）更新为
   "自评值记录在 confidence_design 中 + 派生置信度落在 [0.05,0.95]"

**测试**：321 passed（含新增派生逻辑路径）。

## 2. Honest limitation — the acceptance criterion that is NOT met

留一交叉验证（seed 42，72 样本）对比同一批决策：

| 指标 | 旧（LLM 自评） | 新（派生 + 校准，LOO） |
|---|---:|---:|
| mean confidence | 0.4703 | 0.8647 |
| ECE(10-bin) | 0.4047 | **0.0127** |
| corr(confidence, correct) | 0.204 | **-0.005** |

ECE 大幅改善，但**判别力反而归零**：isotonic 把所有输入映射到 ≈0.84（≈总体准确率 0.875），
等价于一个常数。这不是实现缺陷，而是**输入信号本身的判别力不足**。

特征扫描（seed 42，63 正确 / 9 错误）：

| 特征 | 正确均值 | 错误均值 | 分离度 |
|---|---:|---:|---:|
| self_report | 0.480 | 0.403 | 0.077 |
| evidence_strength | 0.402 | 0.417 | 0.014 |
| kg_support | 0.480 | 0.495 | 0.015 |
| expert_support | 0.011 | 0.000 | 0.011 |
| conflict_count | 3.175 | 3.000 | 0.175（方向相反） |
| vision_absent | 0 | 0 | 0 |

结论：**当前 trace 中记录的任何聚合信号都无法区分对错**。ADR-005 的
`corr ≥ 0.5` 判据在该证据下不可达，需改变信号来源而非继续调参。

## 3. Candidate fix requiring an architecture decision

**自一致性采样（self-consistency）**：对同一 payload 采样 Judge k 次（temperature > 0），
用"判定一致率"作为置信度的判别信号，再叠加校准。这是唯一能在不改模块骨架的前提下
引入新信息的方案，代价是 Judge 调用 ×k（当前网关免费，但运行时长 ×k）。

## 4. Status against ADR-005 acceptance criteria

| 判据 | 状态 |
|---|---|
| ECE ≤ 0.10 | 达成（0.0127，LOO） |
| corr(confidence, correct) ≥ 0.5 | **未达成（-0.005）**，需自一致性采样 |
| accuracy 不低于基线最好配置 | 待 seed 43 验证运行结果 |
| 明确病害零误弃权 | 已实现规则，待验证运行确认 |
| 记忆门控可解释 | 已实现，待验证运行确认（门控默认开） |
