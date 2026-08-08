# Evaluation Summary

- Generated: 2026-08-07T16:04:11+00:00
- Dataset: `benchmarks/datasets/adversarial.json` (3 cases)
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
| average_confidence | 0.60 |
| average_runtime (s) | 0.026 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 8 |
| debate_rounds | 2.00 |
| counterfactual_count | 24 |
| collective_omission_count | 2 |

## Capability Performance

| capability | average | cases | positive |
|---|---|---|---|
| conflict_resolution | 0.67 | 3 | 2 |
| counterfactual_reasoning | 1.00 | 3 | 3 |
| information_gathering | 1.00 | 3 | 3 |
| knowledge_retrieval | 1.00 | 3 | 3 |
| multi_step_planning | 1.00 | 3 | 3 |
| sensor_cross_validation | 1.00 | 3 | 3 |
| uncertainty_quantification | 1.00 | 3 | 3 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tomato_mold_low_humidity | 1.00 | 0.60 | 0.029 | 1.00 | 1.00 | 3 | 2 | 8 | 1 | 叶霉病 | 已生成栽培管理建议 |
| tomato_irrigate_after_rain_anomaly | 1.00 | 0.59 | 0.025 | 1.00 | 1.00 | 3 | 2 | 8 | 1 | 叶霉病 | 气象条件支持灌溉 |
| cotton_wilt_hot_dry | 1.00 | 0.60 | 0.025 | 1.00 | 1.00 | 2 | 2 | 8 | 0 | 黄萎病 | 已生成栽培管理建议 |
