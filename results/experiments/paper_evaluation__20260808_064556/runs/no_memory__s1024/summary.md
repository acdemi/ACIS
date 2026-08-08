# Evaluation Summary

- Generated: 2026-08-08T06:46:03+00:00
- Dataset: `benchmarks.datasets.enriched` (4 cases)
- Seed: 1024
- LangGraph: on

## Configuration

| toggle | value |
|---|---|
| planner | on |
| debate | on |
| memory | off |
| tool_router | on |

## Metrics

| metric | value |
|---|---|
| accuracy | 1.00 (4/4 scored) |
| average_confidence | 0.58 |
| average_runtime (s) | 0.014 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 0 |
| debate_rounds | 1.25 |
| counterfactual_count | 23 |
| collective_omission_count | 7 |

## Capability Performance

| capability | average | cases | positive |
|---|---|---|---|
| conflict_resolution | 0.25 | 4 | 1 |
| counterfactual_reasoning | 1.00 | 4 | 4 |
| information_gathering | 1.00 | 4 | 4 |
| knowledge_retrieval | 0.00 | 4 | 0 |
| multi_step_planning | 1.00 | 4 | 4 |
| sensor_cross_validation | 0.25 | 4 | 1 |
| uncertainty_quantification | 1.00 | 4 | 4 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mi_tomato_growth_slow | 1.00 | 0.58 | 0.016 | 1.00 | 1.00 | 0 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| mi_sugar_beet_partial | 1.00 | 0.58 | 0.013 | 1.00 | 1.00 | 0 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| mi_cotton_unclear | 1.00 | 0.58 | 0.013 | 1.00 | 1.00 | 0 | 1 | 5 | 2 | 证据不足 | 已生成栽培管理建议 |
| ce_tomato_mold_dry | 1.00 | 0.60 | 0.016 | 1.00 | 1.00 | 0 | 2 | 8 | 1 | 叶霉病 | 已生成栽培管理建议 |
