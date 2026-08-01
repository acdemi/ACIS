# Evaluation Summary

- Generated: 2026-08-01T15:09:22+00:00
- Dataset: `benchmarks.datasets.enriched` (15 cases)
- Seed: 7
- LangGraph: on

## Configuration

| toggle | value |
|---|---|
| planner | on |
| debate | off |
| memory | on |
| tool_router | on |

## Metrics

| metric | value |
|---|---|
| accuracy | 1.00 (15/15 scored) |
| average_confidence | 0.66 |
| average_runtime (s) | 0.014 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 31 |
| debate_rounds | 0.00 |
| counterfactual_count | 75 |
| collective_omission_count | 14 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mi_tomato_growth_slow | 1.00 | 0.58 | 0.018 | 1.00 | 1.00 | 2 | 0 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| mi_sugar_beet_partial | 1.00 | 0.58 | 0.013 | 1.00 | 1.00 | 1 | 0 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| mi_cotton_unclear | 1.00 | 0.58 | 0.013 | 1.00 | 1.00 | 1 | 0 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| ce_tomato_mold_dry | 1.00 | 0.60 | 0.012 | 1.00 | 1.00 | 3 | 0 | 5 | 1 | 叶霉病 | 已生成栽培管理建议 |
| ce_sugar_beet_root_rot_dry | 1.00 | 0.73 | 0.012 | 1.00 | 1.00 | 2 | 0 | 5 | 1 | 根腐病 | 病理判断首选：甜菜根腐病 |
| ce_cotton_wilt_hot | 1.00 | 0.74 | 0.013 | 1.00 | 1.00 | 2 | 0 | 5 | 0 | 黄萎病 | 病理判断首选：棉花黄萎病 |
| md_tomato_mold_blight | 1.00 | 0.73 | 0.015 | 1.00 | 1.00 | 3 | 0 | 5 | 0 | 早疫病 | 病理判断首选：番茄早疫病 |
| md_sugar_beet_root_rot_plus | 1.00 | 0.72 | 0.014 | 1.00 | 1.00 | 2 | 0 | 5 | 0 | 褐斑病 | 病理判断首选：甜菜褐斑病 |
| md_cotton_two_wilts | 1.00 | 0.73 | 0.013 | 1.00 | 1.00 | 2 | 0 | 5 | 0 | 黄萎病 | 病理判断首选：棉花黄萎病 |
| rk_cucumber_downy | 1.00 | 0.74 | 0.012 | 1.00 | 1.00 | 3 | 0 | 5 | 0 | 霜霉病 | 病理判断首选：黄瓜霜霉病 |
| rk_tomato_nutrient | 1.00 | 0.58 | 0.012 | 1.00 | 1.00 | 2 | 0 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| rk_sugar_beet_cracking | 1.00 | 0.58 | 0.013 | 1.00 | 1.00 | 1 | 0 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| sc_tomato_irrigate_after_rain | 1.00 | 0.65 | 0.015 | 1.00 | 1.00 | 3 | 0 | 5 | 1 | 叶霉病 | 气象条件支持灌溉 |
| sc_cotton_wilt_anomaly | 1.00 | 0.73 | 0.014 | 1.00 | 1.00 | 2 | 0 | 5 | 0 | 黄萎病 | 病理判断首选：棉花黄萎病 |
| sc_sugar_beet_overwatered | 1.00 | 0.66 | 0.013 | 1.00 | 1.00 | 2 | 0 | 5 | 1 | 根腐病 | 病理判断首选：甜菜根腐病 |
