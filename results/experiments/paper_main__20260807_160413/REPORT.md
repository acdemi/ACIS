# Experiment Report: paper_main

- Description: Main paper experiment - baseline plus key ablation arms on the enriched dataset.
- Dataset: benchmarks.datasets.enriched
- Capability eval: True
- Git: ff825c9 (0.45C-Capability_Evaluation_Engine)
- Python: 3.13.3
- Platform: Windows-11-10.0.26100-SP0
- Started: 2026-08-07T16:04:13.629580+00:00
- Ended: 2026-08-07T16:04:20.448139+00:00
- Duration: 6.819s
- Metadata: author=ACIS version=1.0 tags=paper,main,enriched paper=-

## Run Metrics

| run | cases | accuracy | average_confidence | average_runtime | planner_usage | tool_usage | memory_hits | debate_rounds |
|---|---|---|---|---|---|---|---|---|
| all_on | 6 | 1.000 | 0.642 | 0.015 | 1.000 | 1.000 | 11 | 1.500 |
| no_memory | 6 | 1.000 | 0.642 | 0.012 | 1.000 | 1.000 | 0 | 1.500 |
| no_debate | 6 | 1.000 | 0.635 | 0.014 | 1.000 | 1.000 | 11 | 0.000 |
| no_counterfactual | 6 | 1.000 | 0.642 | 0.017 | 1.000 | 1.000 | 11 | 1.500 |

## Capability Summary

| run | conflict_resolution | counterfactual_reasoning | information_gathering | knowledge_retrieval | multi_step_planning | sensor_cross_validation | uncertainty_quantification |
|---|---|---|---|---|---|---|---|
| all_on | 0.167 | 1.000 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| no_memory | 0.167 | 1.000 | 1.000 | 0.000 | 1.000 | 0.500 | 1.000 |
| no_debate | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| no_counterfactual | 0.167 | 0.000 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |

