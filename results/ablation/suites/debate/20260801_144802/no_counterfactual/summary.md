# Evaluation Summary

- Generated: 2026-08-01T14:48:02+00:00
- Dataset: `E:\knowledge_database\ACIS\benchmarks\datasets\debate.json` (4 cases)
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
| average_confidence | 0.59 |
| average_runtime (s) | 0.023 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 9 |
| debate_rounds | 1.75 |
| counterfactual_count | 0 |
| collective_omission_count | 4 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tomato_irrigate_leaf_mold | 1.00 | 0.59 | 0.022 | 1.00 | 1.00 | 3 | 2 | 0 | 1 | 叶霉病 | 气象条件支持灌溉 |
| sugar_beet_irrigate_leaf_spot | 1.00 | 0.60 | 0.023 | 1.00 | 1.00 | 2 | 2 | 0 | 1 | 褐斑病 | 气象条件支持灌溉 |
| cotton_irrigate_verticillium | 1.00 | 0.59 | 0.021 | 1.00 | 1.00 | 1 | 1 | 0 | 1 | 黄萎病 | 气象条件支持灌溉 |
| tomato_irrigate_early_blight | 1.00 | 0.60 | 0.025 | 1.00 | 1.00 | 3 | 2 | 0 | 1 | 早疫病 | 气象条件支持灌溉 |
