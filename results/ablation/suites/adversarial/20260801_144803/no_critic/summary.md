# Evaluation Summary

- Generated: 2026-08-01T14:48:04+00:00
- Dataset: `E:\knowledge_database\ACIS\benchmarks\datasets\adversarial.json` (3 cases)
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
| average_confidence | 0.62 |
| average_runtime (s) | 0.027 |
| planner_usage | 1.00 |
| tool_usage | 1.00 |
| memory_hits | 8 |
| debate_rounds | 2.00 |
| counterfactual_count | 24 |
| collective_omission_count | 2 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tomato_mold_low_humidity | 1.00 | 0.60 | 0.021 | 1.00 | 1.00 | 3 | 2 | 8 | 1 | 叶霉病 | 已生成栽培管理建议 |
| tomato_irrigate_after_rain_anomaly | 1.00 | 0.66 | 0.034 | 1.00 | 1.00 | 3 | 2 | 8 | 1 | 叶霉病 | 气象条件支持灌溉 |
| cotton_wilt_hot_dry | 1.00 | 0.60 | 0.024 | 1.00 | 1.00 | 2 | 2 | 8 | 0 | 黄萎病 | 已生成栽培管理建议 |
