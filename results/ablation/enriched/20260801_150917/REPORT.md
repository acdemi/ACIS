# ACIS Ablation Report

- Generated: 2026-08-01T15:09:23+00:00
- Dataset: `benchmarks.datasets.enriched`
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
| average_confidence | 0.664 | 0.664 | 0.662 | 0.664 | 0.664 | 0.664 | 0.673 |
| memory_hits | 31 | 31 | 31 | 0 | 31 | 31 | 31 |
| debate_rounds | 1.667 | 1.667 | 0 | 1.667 | 1.667 | 1.667 | 1.667 |
| counterfactual_count | 105 | 105 | 75 | 105 | 0 | 105 | 105 |
| collective_omission_count | 14 | 14 | 14 | 14 | 19 | 14 | 14 |
| average_runtime (s) | 0.032 | 0.014 | 0.014 | 0.012 | 0.017 | 0.016 | 0.016 |
| planner_usage | 1 | 0 | 1 | 1 | 1 | 1 | 1 |
| tool_usage | 1 | 0 | 1 | 1 | 1 | 0 | 1 |

## 贡献度矩阵（Δ = baseline − combo）

| metric | no_planner | no_debate | no_memory | no_counterfactual | no_tool_router | no_critic |
|---|---|---|---|---|---|---|
| accuracy | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| disease_recall | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| average_confidence | 0.000 | +0.002 | 0.000 | 0.000 | 0.000 | -0.009 |
| memory_hits | 0.000 | 0.000 | +31.000 | 0.000 | 0.000 | 0.000 |
| debate_rounds | 0.000 | +1.667 | 0.000 | 0.000 | 0.000 | 0.000 |
| counterfactual_count | 0.000 | +30.000 | 0.000 | +105.000 | 0.000 | 0.000 |
| collective_omission_count | 0.000 | 0.000 | 0.000 | -5.000 | 0.000 | 0.000 |
| average_runtime (s) | +0.018 | +0.018 | +0.020 | +0.015 | +0.015 | +0.016 |
| planner_usage | +1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| tool_usage | +1.000 | 0.000 | 0.000 | 0.000 | +1.000 | 0.000 |

## 关键发现

### no_planner

- 关闭 Planner（任务规划）
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.664 → 0.664（Δ 0.000）
- 其他显著变化：planner_usage Δ +1.000；tool_usage Δ +1.000

### no_debate

- 关闭 Debate 与多轮辩论，保留 Critic
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.664 → 0.662（Δ +0.002）
- 其他显著变化：counterfactual_count Δ +30.000；debate_rounds Δ +1.667

### no_memory

- 关闭 RAG/KG/案例记忆
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.664 → 0.664（Δ 0.000）
- 其他显著变化：memory_hits Δ +31.000；average_runtime Δ +0.020

### no_counterfactual

- 移除所有反事实推理
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.664 → 0.664（Δ 0.000）
- 其他显著变化：counterfactual_count Δ +105.000；collective_omission_count Δ -5.000

### no_tool_router

- 关闭 Tool Router（工具路由）
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.664 → 0.664（Δ 0.000）
- 其他显著变化：tool_usage Δ +1.000；average_runtime Δ +0.015

### no_critic

- 关闭 Critic（反驳降权）
- accuracy：1 → 1（Δ 0.000）
- average_confidence：0.664 → 0.673（Δ -0.009）
- 其他显著变化：average_runtime Δ +0.016；disease_recall Δ 0.000

## 雷达图数据（归一化 0–1）

| combo | accuracy | average_confidence | memory_hits | debate_rounds | counterfactual_count | collective_omission_count | planner_usage | tool_usage |
|---|---|---|---|---|---|---|---|---|
| all_on | 1 | 0.987 | 1 | 1 | 1 | 0.737 | 1 | 1 |
| no_planner | 1 | 0.987 | 1 | 1 | 1 | 0.737 | 0 | 0 |
| no_debate | 1 | 0.984 | 1 | 0 | 0.714 | 0.737 | 1 | 1 |
| no_memory | 1 | 0.987 | 0 | 1 | 1 | 0.737 | 1 | 1 |
| no_counterfactual | 1 | 0.987 | 1 | 1 | 0 | 1 | 1 | 1 |
| no_tool_router | 1 | 0.987 | 1 | 1 | 1 | 0.737 | 1 | 0 |
| no_critic | 1 | 1 | 1 | 1 | 1 | 0.737 | 1 | 1 |

## 建议

在当前数据集上，所有被消融模块对 accuracy 的边际贡献均为 0（baseline `all_on` accuracy 与各组合一致）。建议在 medium/hard 数据集上复跑以区分模块贡献。

## 按 challenge_type 分组的模块贡献统计

### missing_information

| combo | accuracy | disease_recall | average_confidence | memory_hits | debate_rounds | counterfactual_count |
|---|---|---|---|---|---|---|
| no_counterfactual | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | +15.000 |
| no_critic | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_debate | 0.000 | 0.000 | 0.000 | 0.000 | +1.000 | 0.000 |
| no_memory | 0.000 | 0.000 | 0.000 | +4.000 | 0.000 | 0.000 |
| no_planner | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_tool_router | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

### contradictory_evidence

| combo | accuracy | disease_recall | average_confidence | memory_hits | debate_rounds | counterfactual_count |
|---|---|---|---|---|---|---|
| no_counterfactual | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | +24.000 |
| no_critic | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_debate | 0.000 | 0.000 | +0.013 | 0.000 | +2.000 | +9.000 |
| no_memory | 0.000 | 0.000 | 0.000 | +7.000 | 0.000 | 0.000 |
| no_planner | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_tool_router | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

### multi_disease

| combo | accuracy | disease_recall | average_confidence | memory_hits | debate_rounds | counterfactual_count |
|---|---|---|---|---|---|---|
| no_counterfactual | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | +24.000 |
| no_critic | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_debate | 0.000 | 0.000 | +0.020 | 0.000 | +2.000 | +9.000 |
| no_memory | 0.000 | 0.000 | 0.000 | +7.000 | 0.000 | 0.000 |
| no_planner | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_tool_router | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

### rare_knowledge

| combo | accuracy | disease_recall | average_confidence | memory_hits | debate_rounds | counterfactual_count |
|---|---|---|---|---|---|---|
| no_counterfactual | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | +18.000 |
| no_critic | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_debate | 0.000 | 0.000 | +0.007 | 0.000 | +1.333 | +3.000 |
| no_memory | 0.000 | 0.000 | 0.000 | +6.000 | 0.000 | 0.000 |
| no_planner | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_tool_router | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

### sensor_conflict

| combo | accuracy | disease_recall | average_confidence | memory_hits | debate_rounds | counterfactual_count |
|---|---|---|---|---|---|---|
| no_counterfactual | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | +24.000 |
| no_critic | 0.000 | 0.000 | -0.043 | 0.000 | 0.000 | 0.000 |
| no_debate | 0.000 | 0.000 | -0.030 | 0.000 | +2.000 | +9.000 |
| no_memory | 0.000 | 0.000 | 0.000 | +7.000 | 0.000 | 0.000 |
| no_planner | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| no_tool_router | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

