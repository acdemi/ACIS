# Evaluation Summary

- Generated: 2026-08-02T04:09:50+00:00
- Dataset: `evals.fixtures` (1 cases)
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
| accuracy | 1.00 (1/1 scored) |
| average_confidence | 0.72 |
| average_runtime (s) | 0.024 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 3 |
| debate_rounds | 0.00 |
| counterfactual_count | 5 |
| collective_omission_count | 0 |

## Capability Performance

| capability | average | cases | positive |
|---|---|---|---|
| conflict_resolution | 0.00 | 1 | 0 |
| counterfactual_reasoning | 1.00 | 1 | 1 |
| information_gathering | 1.00 | 1 | 1 |
| knowledge_retrieval | 1.00 | 1 | 1 |
| multi_step_planning | 1.00 | 1 | 1 |
| sensor_cross_validation | 0.00 | 1 | 0 |
| uncertainty_quantification | 1.00 | 1 | 1 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tomato_leaf_mold | 1.00 | 0.72 | 0.024 | 1.00 | 1.00 | 3 | 0 | 5 | 0 | 叶霉病 | 病理判断首选：番茄叶霉病 |
