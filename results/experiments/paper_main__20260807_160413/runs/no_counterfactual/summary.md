# Evaluation Summary

- Generated: 2026-08-07T16:04:20+00:00
- Dataset: `benchmarks.datasets.enriched` (6 cases)
- Seed: 7
- LangGraph: on

## Configuration

| toggle | value |
|---|---|
| planner | on |
| debate | on |
| memory | on |
| tool_router | on |

## Metrics

| metric | value |
|---|---|
| accuracy | 1.00 (6/6 scored) |
| average_confidence | 0.64 |
| average_runtime (s) | 0.017 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 11 |
| debate_rounds | 1.50 |
| counterfactual_count | 0 |
| collective_omission_count | 9 |

## Capability Performance

| capability | average | cases | positive |
|---|---|---|---|
| conflict_resolution | 0.17 | 6 | 1 |
| counterfactual_reasoning | 0.00 | 6 | 0 |
| information_gathering | 1.00 | 6 | 6 |
| knowledge_retrieval | 1.00 | 6 | 6 |
| multi_step_planning | 1.00 | 6 | 6 |
| sensor_cross_validation | 0.50 | 6 | 3 |
| uncertainty_quantification | 1.00 | 6 | 6 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mi_tomato_growth_slow | 1.00 | 0.58 | 0.014 | 1.00 | 1.00 | 2 | 1 | 0 | 2 | 证据不足 | 已生成栽培管理建议 |
| mi_sugar_beet_partial | 1.00 | 0.58 | 0.014 | 1.00 | 1.00 | 1 | 1 | 0 | 2 | 证据不足 | 已生成栽培管理建议 |
| mi_cotton_unclear | 1.00 | 0.58 | 0.014 | 1.00 | 1.00 | 1 | 1 | 0 | 2 | 证据不足 | 已生成栽培管理建议 |
| ce_tomato_mold_dry | 1.00 | 0.60 | 0.016 | 1.00 | 1.00 | 3 | 2 | 0 | 1 | 叶霉病 | 已生成栽培管理建议 |
| ce_sugar_beet_root_rot_dry | 1.00 | 0.75 | 0.021 | 1.00 | 1.00 | 2 | 2 | 0 | 1 | 根腐病 | 病理判断首选：甜菜根腐病 |
| ce_cotton_wilt_hot | 1.00 | 0.76 | 0.025 | 1.00 | 1.00 | 2 | 2 | 0 | 1 | 黄萎病 | 病理判断首选：棉花黄萎病 |
