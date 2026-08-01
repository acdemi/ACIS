# Evaluation Summary

- Generated: 2026-08-01T14:47:40+00:00
- Dataset: `E:\knowledge_database\ACIS\benchmarks\datasets\planning.json` (4 cases)
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
| accuracy | 1.00 (4/4 scored) |
| average_confidence | 0.70 |
| average_runtime (s) | 0.023 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 8 |
| debate_rounds | 2.00 |
| counterfactual_count | 0 |
| collective_omission_count | 4 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tomato_leaf_mold_action_plan | 1.00 | 0.74 | 0.022 | 1.00 | 1.00 | 3 | 2 | 0 | 1 | 叶霉病 | 病理判断首选：番茄叶霉病 |
| tomato_early_blight_inspection_plan | 1.00 | 0.75 | 0.021 | 1.00 | 1.00 | 3 | 2 | 0 | 1 | 早疫病 | 病理判断首选：番茄早疫病 |
| sugar_beet_root_rot_weekly_plan | 1.00 | 0.65 | 0.024 | 1.00 | 1.00 | 1 | 2 | 0 | 1 | 根腐病 | 病理判断首选：甜菜根腐病 |
| cotton_verticillium_quarantine_plan | 1.00 | 0.65 | 0.025 | 1.00 | 1.00 | 1 | 2 | 0 | 1 | 黄萎病 | 病理判断首选：棉花黄萎病 |
