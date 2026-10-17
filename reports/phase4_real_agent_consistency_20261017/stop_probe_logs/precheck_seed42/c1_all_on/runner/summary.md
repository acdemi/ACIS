# Evaluation Summary

- Generated: 2026-10-17T15:19:56+00:00
- Dataset: `reports\phase4_real_agent_consistency_20261017\stop_probe_logs\precheck_seed42\_flattened\challenge_set_v1_flattened.json` (1 cases)
- Seed: 42
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
| accuracy | 1.00 (1/1 scored) |
| average_confidence | 0.75 |
| average_runtime (s) | 11.599 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 3 |
| debate_rounds | 2.00 |
| counterfactual_count | 8 |
| collective_omission_count | 0 |
| judge_total_tokens | 0 |

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
| ms_tomato_blight_stem | 1.00 | 0.75 | 11.599 | 1.00 | 1.00 | 3 | 2 | 8 | 0 | 早疫病 | 病理判断首选：番茄早疫病 |
