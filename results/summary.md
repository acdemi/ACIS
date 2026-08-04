# Evaluation Summary

- Generated: 2026-08-02T04:09:47+00:00
- Dataset: `benchmarks.datasets.enriched` (18 cases)
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
| accuracy | 1.00 (18/18 scored) |
| average_confidence | 0.65 |
| average_runtime (s) | 0.054 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 35 |
| debate_rounds | 1.56 |
| counterfactual_count | 120 |
| collective_omission_count | 19 |

## Capability Performance

| capability | average | cases | positive |
|---|---|---|---|
| conflict_resolution | 0.11 | 18 | 2 |
| counterfactual_reasoning | 1.00 | 18 | 18 |
| information_gathering | 1.00 | 18 | 18 |
| knowledge_retrieval | 1.00 | 18 | 18 |
| multi_step_planning | 1.00 | 18 | 18 |
| sensor_cross_validation | 0.33 | 18 | 6 |
| uncertainty_quantification | 1.00 | 18 | 18 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mi_tomato_growth_slow | 1.00 | 0.58 | 0.025 | 1.00 | 1.00 | 2 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| mi_sugar_beet_partial | 1.00 | 0.58 | 0.025 | 1.00 | 1.00 | 1 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| mi_cotton_unclear | 1.00 | 0.58 | 0.029 | 1.00 | 1.00 | 1 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| ce_tomato_mold_dry | 1.00 | 0.60 | 0.036 | 1.00 | 1.00 | 3 | 2 | 8 | 1 | 叶霉病 | 已生成栽培管理建议 |
| ce_sugar_beet_root_rot_dry | 1.00 | 0.75 | 0.033 | 1.00 | 1.00 | 2 | 2 | 8 | 1 | 根腐病 | 病理判断首选：甜菜根腐病 |
| ce_cotton_wilt_hot | 1.00 | 0.76 | 0.028 | 1.00 | 1.00 | 2 | 2 | 8 | 0 | 黄萎病 | 病理判断首选：棉花黄萎病 |
| md_tomato_mold_blight | 1.00 | 0.75 | 0.030 | 1.00 | 1.00 | 3 | 2 | 8 | 0 | 早疫病 | 病理判断首选：番茄早疫病 |
| md_sugar_beet_root_rot_plus | 1.00 | 0.74 | 0.026 | 1.00 | 1.00 | 2 | 2 | 8 | 0 | 褐斑病 | 病理判断首选：甜菜褐斑病 |
| md_cotton_two_wilts | 1.00 | 0.75 | 0.029 | 1.00 | 1.00 | 2 | 2 | 8 | 0 | 黄萎病 | 病理判断首选：棉花黄萎病 |
| rk_cucumber_downy | 1.00 | 0.76 | 0.514 | 1.00 | 1.00 | 3 | 2 | 8 | 0 | 霜霉病 | 病理判断首选：黄瓜霜霉病 |
| rk_tomato_nutrient | 1.00 | 0.58 | 0.024 | 1.00 | 1.00 | 2 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| rk_sugar_beet_cracking | 1.00 | 0.58 | 0.023 | 1.00 | 1.00 | 1 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| sc_tomato_irrigate_after_rain | 1.00 | 0.59 | 0.028 | 1.00 | 1.00 | 3 | 2 | 8 | 1 | 叶霉病 | 气象条件支持灌溉 |
| sc_cotton_wilt_anomaly | 1.00 | 0.75 | 0.029 | 1.00 | 1.00 | 2 | 2 | 8 | 0 | 黄萎病 | 病理判断首选：棉花黄萎病 |
| sc_sugar_beet_overwatered | 1.00 | 0.67 | 0.022 | 1.00 | 1.00 | 2 | 2 | 8 | 1 | 根腐病 | 病理判断首选：甜菜根腐病 |
| ig_tomato_missing_info | 1.00 | 0.58 | 0.020 | 1.00 | 1.00 | 2 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| ig_sugar_beet_missing_info | 1.00 | 0.58 | 0.021 | 1.00 | 1.00 | 1 | 1 | 5 | 1 | 证据不足 | 已生成栽培管理建议 |
| ig_cotton_missing_info | 1.00 | 0.58 | 0.023 | 1.00 | 1.00 | 1 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
