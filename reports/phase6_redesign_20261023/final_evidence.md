# Phase 6 — Decision Confidence Redesign: Final Evidence (2026-10-24)

> Branch: `work/20261023-phase6-arch-redesign` | ADR: ADR-005
> Channel: opencode zen gateway + `deepseek-v4.1-flash` (free), self-consistency k=3

## 1. What the redesign does

Real-LLM Judge path (`agents/judge_agent.py`):

1. `_gate_memory_outputs` — 记忆层（RAG / 知识图谱 / 历史病例 / 经验回放）输出在进入 Judge payload
   前按置信度与"无匹配"措辞过滤（`AGRI_AI_MEMORY_GATE`, `AGRI_AI_MEMORY_GATE_MIN_CONF`）。
2. `_sample_self_consistency` — 同一 payload 采样 k=3 次（`AGRI_AI_JUDGE_SELF_CONSISTENCY_K`，
   temperature 0.7，每个样本最多重试 3 次），用判定一致率作为唯一判别信号。
3. `combine_decision_score` — 有信号时 **confidence = 一致率**；无信号时用结构分并**封顶 0.65**。
4. `_apply_abstention_policy` — 弃权必须由证据不足"挣得"：证据充分且无冲突时用专家多数意见
   覆盖误弃权，并置 `need_human_review`。
5. `DecisionCalibrator` — isotonic/Platt 校准，**样本数 < 50 时不启用**（见 §3 的反证）。

## 2. Result (final design: confidence = min(0.95, agreement))

| seed | 用途 | 可评案例 | accuracy | ECE(10-bin) | corr(conf, correct) |
|---|---|---:|---:|---:|---:|
| 42 | 拟合 | 13 / 24 | 0.846 | **0.0769** | **0.778** |
| 43 | 未见验证 | 24 / 24 | 0.792 | **0.0708** | **0.538** |

ADR-005 判据：ECE ≤ 0.10 ✅（两个 seed 均达成）；corr ≥ 0.5 ✅（0.778 / 0.538）。

一致率分层（seed43，未见数据）：

| agreement | n | accuracy |
|---|---:|---:|
| 0.0 | 3 | 0.333 |
| 0.5 | 5 | 0.600 |
| 1.0 | 16 | 0.938 |

单调且方向正确：**判定越一致，越可能正确**。这是本系统第一个被证明具有判别力的置信度信号。

## 3. Rejected designs (recorded because they looked better than they were)

| 方案 | ECE | corr | 结论 |
|---|---:|---:|---|
| LLM 自报 `final_confidence`（原实现） | 0.405 | 0.204 | 几乎无信息 |
| 结构信号派生 + isotonic 校准 | **0.013** | **-0.005** | 校准把一切压成常数：ECE 好看、判别力归零 |
| 一致率占 30% 权重 | — | -0.135 | 被无关信号稀释 |
| isotonic（13 样本拟合）后处理 | 0.175 | 0.508 | **校准比不校准更差**，故设 50 样本门槛 |
| **一致率直接作为置信度（采用）** | **0.071–0.077** | **0.538–0.778** | 唯一同时满足 ECE 与 corr 的方案 |

## 4. Coverage caveat

seed42 那次运行只有 13/24 采到一致率（网关 `APIConnectionError`，样本静默丢失）。
加入采样重试后 seed43 达到 **24/24（零缺失、零连接错误）**。
因此 seed43 的指标才是生产条件下的可信读数；seed42 的 13 例仅作拟合参考。

## 5. Still open

- **accuracy 未提升**：C1 seed43 = 0.792，与改造前基线持平。置信度与聚合链路修好了，
  决策质量本身没有变好——这是下一个独立课题。
- 仅覆盖 **C1**；C0/C2 与新指标的对照尚未跑。
- 只有 2 个 seed；一致率分层在 agreement=0.0 时 n=3，样本仍小。
- ADR-005 的 "GT 为明确病害零误弃权" 与 "记忆门控可解释" 两条需 C0/C2 对照运行才能定论。

## 6. Artifacts

- 拟合/验证运行：`logs/phase6_sc_20261023/run_42`、`logs/phase6_sc43_20261024/run_43`
- 原始结果：`reports/phase6_sc_20261023/raw_results_c1_seed42.json`、`reports/phase6_sc43_20261024/raw_results_c1_seed43.json`
- 分析脚本（gitignored）：`logs/final_eval.py`、`logs/restricted_eval.py`、`logs/mapping_compare.py`
