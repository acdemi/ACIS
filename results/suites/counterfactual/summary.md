# Evaluation Summary

- Generated: 2026-08-01T14:47:16+00:00
- Dataset: `E:\knowledge_database\ACIS\benchmarks\datasets\counterfactual.json` (3 cases)
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
| accuracy | 1.00 (3/3 scored) |
| average_confidence | 0.75 |
| average_runtime (s) | 0.024 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 8 |
| debate_rounds | 2.00 |
| counterfactual_count | 24 |
| collective_omission_count | 1 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tomato_mold_blight_ambiguous | 1.00 | 0.75 | 0.024 | 1.00 | 1.00 | 3 | 2 | 8 | 0 | 早疫病 | 病理判断首选：番茄早疫病 |
| tomato_early_blight_alternatives | 1.00 | 0.75 | 0.024 | 1.00 | 1.00 | 3 | 2 | 8 | 0 | 早疫病 | 病理判断首选：番茄早疫病 |
| sugar_beet_root_rot_nonpathogenic | 1.00 | 0.75 | 0.026 | 1.00 | 1.00 | 2 | 2 | 8 | 1 | 根腐病 | 病理判断首选：甜菜根腐病 |
