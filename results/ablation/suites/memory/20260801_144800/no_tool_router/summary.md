# Evaluation Summary

- Generated: 2026-08-01T14:48:01+00:00
- Dataset: `E:\knowledge_database\ACIS\benchmarks\datasets\memory.json` (4 cases)
- Seed: 7
- LangGraph: on

## Configuration

| toggle | value |
|---|---|
| planner | on |
| debate | on |
| memory | on |
| tool_router | off |

## Metrics

| metric | value |
|---|---|
| accuracy | 1.00 (4/4 scored) |
| average_confidence | 0.73 |
| average_runtime (s) | 0.021 |
| planner_usage | 1.00 |
| tool_usage | 0.00 |
| memory_hits | 10 |
| debate_rounds | 2.00 |
| counterfactual_count | 32 |
| collective_omission_count | 2 |

## Per-case

| case_id | accuracy | confidence | runtime_s | planner | tool | memory_hits | rounds | counterfactual | omission | expected | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tomato_leaf_mold_memory | 1.00 | 0.66 | 0.022 | 1.00 | 0.00 | 3 | 2 | 8 | 1 | 叶霉病 | 病理判断首选：番茄叶霉病 |
| sugar_beet_leaf_spot_memory | 1.00 | 0.75 | 0.018 | 1.00 | 0.00 | 2 | 2 | 8 | 1 | 褐斑病 | 病理判断首选：甜菜褐斑病 |
| cotton_fusarium_memory | 1.00 | 0.75 | 0.022 | 1.00 | 0.00 | 2 | 2 | 8 | 0 | 枯萎病 | 病理判断首选：棉花枯萎病 |
| cucumber_downy_memory | 1.00 | 0.76 | 0.022 | 1.00 | 0.00 | 3 | 2 | 8 | 0 | 霜霉病 | 病理判断首选：黄瓜霜霉病 |
