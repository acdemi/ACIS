# ACIS Ablation Report

- Generated: 2026-08-01T14:48:02+00:00
- Dataset: `E:\knowledge_database\ACIS\benchmarks\datasets\debate.json`
- Combos: 7（baseline: `all_on`）

## 配置矩阵

| combo | description | planner | debate | critic | memory | tool_router | counterfactual |
|---|---|---|---|---|---|---|---|
| all_on | 全开基线：所有认知模块启用 | on | on | on | on | on | on |
| no_planner | 关闭 Planner（任务规划） | off | on | on | on | on | on |
| no_debate | 关闭 Debate 与多轮辩论，保留 Critic | on | off | on | on | on | on |
| no_memory | 关闭 RAG/KG/案例记忆 | on | on | on | off | on | on |
| no_counterfactual | 移除所有反事实推理 | on | on | on | on | on | off |
| no_tool_router | 关闭 Tool Router（工具路由） | on | on | on | on | off | on |
| no_critic | 关闭 Critic（反驳降权） | on | on | off | on | on | on |

## 绝对指标

| metric | all_on | no_planner | no_debate | no_memory | no_counterfactual | no_tool_router | no_critic |
|---|---|---|---|---|---|---|---|
| accuracy | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| disease_recall | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| average_confidence | 0.595 | 0.595 | 0.647 | 0.595 | 0.595 | 0.595 | 0.657 |
| memory_hits | 9 | 9 | 9 | 0 | 9 | 9 | 9 |
| debate_rounds | 1.750 | 1.750 | 0 | 1.750 | 1.750 | 1.750 | 2 |
| counterfactual_count | 29 | 29 | 20 | 29 | 0 | 29 | 32 |
| collective_omission_count | 3 | 3 | 3 | 3 | 4 | 3 | 3 |
| average_runtime (s) | 0.021 | 0.032 | 0.025 | 0.017 | 0.023 | 0.025 | 0.024 |
| planner_usage | 1 | 0 | 1 | 1 | 1 | 1 | 1 |
| tool_usage | 1 | 0 | 1 | 1 | 1 | 0 | 1 |

## 贡献度矩阵（Δ = baseline − combo）

| metric | no_planner | no_debate | no_memory | no_counterfactual | no_tool_router | no_critic |
|---|---|---|---|---|---|---|
| accuracy | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| disease_recall | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| average_confidence | 0.000 | -0.052 | 0.000 | 0.000 | 0.000 | -0.062 |
| memory_hits | 0.000 | 0.000 | +9.000 | 0.000 | 0.000 | 0.000 |
| debate_rounds | 0.000 | +1.750 | 0.000 | 0.000 | 0.000 | -0.250 |
| counterfactual_count | 0.000 | +9.000 | 0.000 | +29.000 | 0.000 | -3.000 |
| collective_omission_count | 0.000 | 0.000 | 0.000 | -1.000 | 0.000 | 0.000 |
| average_runtime (s) | -0.011 | -0.004 | +0.003 | -0.002 | -0.004 | -0.003 |
| planner_usage | +1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| tool_usage | +1.000 | 0.000 | 0.000 | 0.000 | +1.000 | 0.000 |

## 关键发现

### no_planner

- 关闭 Planner（任务规划）
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.595 → 0.595（Δ 0.000）
- 其他显著变化：planner_usage Δ +1.000；tool_usage Δ +1.000

### no_debate

- 关闭 Debate 与多轮辩论，保留 Critic
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.595 → 0.647（Δ -0.052）
- 其他显著变化：counterfactual_count Δ +9.000；debate_rounds Δ +1.750

### no_memory

- 关闭 RAG/KG/案例记忆
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.595 → 0.595（Δ 0.000）
- 其他显著变化：memory_hits Δ +9.000；average_runtime Δ +0.003

### no_counterfactual

- 移除所有反事实推理
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.595 → 0.595（Δ 0.000）
- 其他显著变化：counterfactual_count Δ +29.000；collective_omission_count Δ -1.000

### no_tool_router

- 关闭 Tool Router（工具路由）
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.595 → 0.595（Δ 0.000）
- 其他显著变化：tool_usage Δ +1.000；average_runtime Δ -0.004

### no_critic

- 关闭 Critic（反驳降权）
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.595 → 0.657（Δ -0.062）
- 其他显著变化：counterfactual_count Δ -3.000；debate_rounds Δ -0.250

## 雷达图数据（归一化 0–1）

| combo | accuracy | average_confidence | memory_hits | debate_rounds | counterfactual_count | collective_omission_count | planner_usage | tool_usage |
|---|---|---|---|---|---|---|---|---|
| all_on | 1 | 0.905 | 1 | 0.875 | 0.906 | 0.750 | 1 | 1 |
| no_planner | 1 | 0.905 | 1 | 0.875 | 0.906 | 0.750 | 0 | 0 |
| no_debate | 1 | 0.985 | 1 | 0 | 0.625 | 0.750 | 1 | 1 |
| no_memory | 1 | 0.905 | 0 | 0.875 | 0.906 | 0.750 | 1 | 1 |
| no_counterfactual | 1 | 0.905 | 1 | 0.875 | 0 | 1 | 1 | 1 |
| no_tool_router | 1 | 0.905 | 1 | 0.875 | 0.906 | 0.750 | 1 | 0 |
| no_critic | 1 | 1 | 1 | 1 | 1 | 0.750 | 1 | 1 |

## 建议

在当前数据集上，所有被消融模块对 accuracy 的边际贡献均为 0（baseline `all_on` accuracy 与各组合一致）。建议在 medium/hard 数据集上复跑以区分模块贡献。
