# Evaluation Summary

- Generated: 2026-08-01T14:48:02+00:00
- Dataset: `E:\knowledge_database\ACIS\benchmarks\datasets\debate.json` (4 cases)
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
| accuracy | 1.00 (4/4 scored) |
| average_confidence | 0.65 |
| average_runtime (s) | 0.025 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 9 |
| debate_rounds | 0.00 |
| counterfactual_count | 20 |
| collective_omission_count | 3 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tomato_irrigate_leaf_mold | 1.00 | 0.65 | 0.027 | 1.00 | 1.00 | 3 | 0 | 5 | 1 | 叶霉病 | 气象条件支持灌溉 |
| sugar_beet_irrigate_leaf_spot | 1.00 | 0.65 | 0.022 | 1.00 | 1.00 | 2 | 0 | 5 | 1 | 褐斑病 | 气象条件支持灌溉 |
| cotton_irrigate_verticillium | 1.00 | 0.64 | 0.028 | 1.00 | 1.00 | 1 | 0 | 5 | 1 | 黄萎病 | 气象条件支持灌溉 |
| tomato_irrigate_early_blight | 1.00 | 0.65 | 0.022 | 1.00 | 1.00 | 3 | 0 | 5 | 0 | 早疫病 | 气象条件支持灌溉 |
