# Evaluation Summary

- Generated: 2026-08-01T14:28:59+00:00
- Dataset: `benchmarks.datasets.easy` (12 cases)
- Seed: 7
- LangGraph: on

## Configuration

| toggle | value |
|---|---|
| planner | off |
| debate | on |
| memory | on |
| tool_router | on |

## Metrics

| metric | value |
|---|---|
| accuracy | 1.00 (12/12 scored) |
| average_confidence | 0.67 |
| average_runtime (s) | 0.016 |
| planner_usage | 0.00 |
| tool_usage | 0.00 |
| memory_hits | 25 |
| debate_rounds | 1.58 |
| counterfactual_count | 81 |
| collective_omission_count | 11 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tomato_leaf_mold | 1.00 | 0.74 | 0.017 | 0.00 | 0.00 | 3 | 2 | 8 | 0 | 叶霉病 | 病理判断首选：番茄叶霉病 |
| tomato_early_blight | 1.00 | 0.75 | 0.017 | 0.00 | 0.00 | 3 | 2 | 8 | 0 | 早疫病 | 病理判断首选：番茄早疫病 |
| tomato_monitor | 1.00 | 0.58 | 0.014 | 0.00 | 0.00 | 2 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| tomato_irrigate | 1.00 | 0.58 | 0.014 | 0.00 | 0.00 | 2 | 1 | 5 | 2 | 证据不足 | 气象条件支持灌溉 |
| cucumber_downy_mildew | 1.00 | 0.76 | 0.016 | 0.00 | 0.00 | 3 | 2 | 8 | 0 | 霜霉病 | 病理判断首选：黄瓜霜霉病 |
| sugar_beet_leaf_spot | 1.00 | 0.75 | 0.017 | 0.00 | 0.00 | 2 | 2 | 8 | 1 | 褐斑病 | 病理判断首选：甜菜褐斑病 |
| sugar_beet_root_rot | 1.00 | 0.75 | 0.017 | 0.00 | 0.00 | 2 | 2 | 8 | 1 | 根腐病 | 病理判断首选：甜菜根腐病 |
| sugar_beet_alert | 1.00 | 0.58 | 0.016 | 0.00 | 0.00 | 1 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| cotton_verticillium_wilt | 1.00 | 0.75 | 0.016 | 0.00 | 0.00 | 2 | 2 | 8 | 0 | 黄萎病 | 病理判断首选：棉花黄萎病 |
| cotton_fusarium_wilt | 1.00 | 0.65 | 0.016 | 0.00 | 0.00 | 2 | 2 | 8 | 1 | 枯萎病 | 病理判断首选：棉花枯萎病 |
| cotton_irrigate | 1.00 | 0.58 | 0.014 | 0.00 | 0.00 | 1 | 1 | 5 | 1 | 证据不足 | 气象条件支持灌溉 |
| tomato_consult | 1.00 | 0.58 | 0.015 | 0.00 | 0.00 | 2 | 1 | 5 | 1 | 证据不足 | 气象条件支持灌溉 |
