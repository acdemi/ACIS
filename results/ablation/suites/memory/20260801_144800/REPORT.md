# ACIS Ablation Report

- Generated: 2026-08-01T14:48:02+00:00
- Dataset: `E:\knowledge_database\ACIS\benchmarks\datasets\memory.json`
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
| average_confidence | 0.730 | 0.730 | 0.713 | 0.730 | 0.730 | 0.730 | 0.730 |
| memory_hits | 10 | 10 | 10 | 0 | 10 | 10 | 10 |
| debate_rounds | 2 | 2 | 0 | 2 | 2 | 2 | 2 |
| counterfactual_count | 32 | 32 | 20 | 32 | 0 | 32 | 32 |
| collective_omission_count | 2 | 2 | 2 | 2 | 3 | 2 | 2 |
| average_runtime (s) | 0.098 | 0.021 | 0.016 | 0.015 | 0.022 | 0.021 | 0.026 |
| planner_usage | 1 | 0 | 1 | 1 | 1 | 1 | 1 |
| tool_usage | 1 | 0 | 1 | 1 | 1 | 0 | 1 |

## 贡献度矩阵（Δ = baseline − combo）

| metric | no_planner | no_debate | no_memory | no_counterfactual | no_tool_router | no_critic |
|---|---|---|---|---|---|---|
| accuracy | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| disease_recall | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| average_confidence | 0.000 | +0.017 | 0.000 | 0.000 | 0.000 | 0.000 |
| memory_hits | 0.000 | 0.000 | +10.000 | 0.000 | 0.000 | 0.000 |
| debate_rounds | 0.000 | +2.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| counterfactual_count | 0.000 | +12.000 | 0.000 | +32.000 | 0.000 | 0.000 |
| collective_omission_count | 0.000 | 0.000 | 0.000 | -1.000 | 0.000 | 0.000 |
| average_runtime (s) | +0.077 | +0.082 | +0.083 | +0.075 | +0.077 | +0.072 |
| planner_usage | +1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| tool_usage | +1.000 | 0.000 | 0.000 | 0.000 | +1.000 | 0.000 |

## 关键发现

### no_planner

- 关闭 Planner（任务规划）
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.730 → 0.730（Δ 0.000）
- 其他显著变化：planner_usage Δ +1.000；tool_usage Δ +1.000

### no_debate

- 关闭 Debate 与多轮辩论，保留 Critic
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.730 → 0.713（Δ +0.017）
- 其他显著变化：counterfactual_count Δ +12.000；debate_rounds Δ +2.000

### no_memory

- 关闭 RAG/KG/案例记忆
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.730 → 0.730（Δ 0.000）
- 其他显著变化：memory_hits Δ +10.000；average_runtime Δ +0.083

### no_counterfactual

- 移除所有反事实推理
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.730 → 0.730（Δ 0.000）
- 其他显著变化：counterfactual_count Δ +32.000；collective_omission_count Δ -1.000

### no_tool_router

- 关闭 Tool Router（工具路由）
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.730 → 0.730（Δ 0.000）
- 其他显著变化：tool_usage Δ +1.000；average_runtime Δ +0.077

### no_critic

- 关闭 Critic（反驳降权）
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.730 → 0.730（Δ 0.000）
- 其他显著变化：average_runtime Δ +0.072；disease_recall Δ 0.000

## 雷达图数据（归一化 0–1）

| combo | accuracy | average_confidence | memory_hits | debate_rounds | counterfactual_count | collective_omission_count | planner_usage | tool_usage |
|---|---|---|---|---|---|---|---|---|
| all_on | 1 | 1 | 1 | 1 | 1 | 0.667 | 1 | 1 |
| no_planner | 1 | 1 | 1 | 1 | 1 | 0.667 | 0 | 0 |
| no_debate | 1 | 0.976 | 1 | 0 | 0.625 | 0.667 | 1 | 1 |
| no_memory | 1 | 1 | 0 | 1 | 1 | 0.667 | 1 | 1 |
| no_counterfactual | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 |
| no_tool_router | 1 | 1 | 1 | 1 | 1 | 0.667 | 1 | 0 |
| no_critic | 1 | 1 | 1 | 1 | 1 | 0.667 | 1 | 1 |

## 建议

在当前数据集上，所有被消融模块对 accuracy 的边际贡献均为 0（baseline `all_on` accuracy 与各组合一致）。建议在 medium/hard 数据集上复跑以区分模块贡献。
