# Evaluation Summary

- Generated: 2026-08-07T16:04:11+00:00
- Dataset: `benchmarks/datasets/debate.json` (4 cases)
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
| average_runtime (s) | 0.022 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 9 |
| debate_rounds | 1.75 |
| counterfactual_count | 29 |
| collective_omission_count | 3 |

## Capability Performance

| capability | average | cases | positive |
|---|---|---|---|
| conflict_resolution | 1.00 | 4 | 4 |
| counterfactual_reasoning | 1.00 | 4 | 4 |
| information_gathering | 1.00 | 4 | 4 |
| knowledge_retrieval | 1.00 | 4 | 4 |
| multi_step_planning | 1.00 | 4 | 4 |
| sensor_cross_validation | 0.00 | 4 | 0 |
| uncertainty_quantification | 1.00 | 4 | 4 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tomato_irrigate_leaf_mold | 1.00 | 0.59 | 0.021 | 1.00 | 1.00 | 3 | 2 | 8 | 1 | 叶霉病 | 气象条件支持灌溉 |
| sugar_beet_irrigate_leaf_spot | 1.00 | 0.60 | 0.023 | 1.00 | 1.00 | 2 | 2 | 8 | 1 | 褐斑病 | 气象条件支持灌溉 |
| cotton_irrigate_verticillium | 1.00 | 0.59 | 0.021 | 1.00 | 1.00 | 1 | 1 | 5 | 1 | 黄萎病 | 气象条件支持灌溉 |
| tomato_irrigate_early_blight | 1.00 | 0.60 | 0.021 | 1.00 | 1.00 | 3 | 2 | 8 | 0 | 早疫病 | 气象条件支持灌溉 |
