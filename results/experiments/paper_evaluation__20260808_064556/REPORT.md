# Experiment Report: paper_evaluation

- Description: Multi-seed reproducibility study - 4 module combos x 5 seeds (Phase 2.1E->2.2, Sprint 06).
- Dataset: benchmarks.datasets.enriched
- Capability eval: True
- Git: 57176ae (0.45C-Capability_Evaluation_Engine)
- Python: 3.13.3
- Platform: Windows-11-10.0.26100-SP0
- Started: 2026-08-08T06:45:56.372262+00:00
- Ended: 2026-08-08T06:46:04.492124+00:00
- Duration: 8.120s
- Metadata: author=ACIS version=1.0 tags=paper,evaluation,multi-seed paper=-

## Run Metrics

| run | cases | accuracy | average_confidence | average_runtime | planner_usage | tool_usage | memory_hits | debate_rounds |
|---|---|---|---|---|---|---|---|---|
| all_on__s42 | 4 | 1.000 | 0.585 | 0.015 | 1.000 | 1.000 | 7 | 1.250 |
| all_on__s123 | 4 | 1.000 | 0.585 | 0.015 | 1.000 | 1.000 | 7 | 1.250 |
| all_on__s456 | 4 | 1.000 | 0.585 | 0.014 | 1.000 | 1.000 | 7 | 1.250 |
| all_on__s789 | 4 | 1.000 | 0.585 | 0.013 | 1.000 | 1.000 | 7 | 1.250 |
| all_on__s1024 | 4 | 1.000 | 0.585 | 0.013 | 1.000 | 1.000 | 7 | 1.250 |
| no_memory__s42 | 4 | 1.000 | 0.585 | 0.010 | 1.000 | 1.000 | 0 | 1.250 |
| no_memory__s123 | 4 | 1.000 | 0.585 | 0.011 | 1.000 | 1.000 | 0 | 1.250 |
| no_memory__s456 | 4 | 1.000 | 0.585 | 0.015 | 1.000 | 1.000 | 0 | 1.250 |
| no_memory__s789 | 4 | 1.000 | 0.585 | 0.015 | 1.000 | 1.000 | 0 | 1.250 |
| no_memory__s1024 | 4 | 1.000 | 0.585 | 0.014 | 1.000 | 1.000 | 0 | 1.250 |
| no_debate__s42 | 4 | 1.000 | 0.585 | 0.019 | 1.000 | 1.000 | 7 | 0.000 |
| no_debate__s123 | 4 | 1.000 | 0.585 | 0.020 | 1.000 | 1.000 | 7 | 0.000 |
| no_debate__s456 | 4 | 1.000 | 0.585 | 0.020 | 1.000 | 1.000 | 7 | 0.000 |
| no_debate__s789 | 4 | 1.000 | 0.585 | 0.020 | 1.000 | 1.000 | 7 | 0.000 |
| no_debate__s1024 | 4 | 1.000 | 0.585 | 0.019 | 1.000 | 1.000 | 7 | 0.000 |
| no_counterfactual__s42 | 4 | 1.000 | 0.585 | 0.018 | 1.000 | 1.000 | 7 | 1.250 |
| no_counterfactual__s123 | 4 | 1.000 | 0.585 | 0.018 | 1.000 | 1.000 | 7 | 1.250 |
| no_counterfactual__s456 | 4 | 1.000 | 0.585 | 0.018 | 1.000 | 1.000 | 7 | 1.250 |
| no_counterfactual__s789 | 4 | 1.000 | 0.585 | 0.017 | 1.000 | 1.000 | 7 | 1.250 |
| no_counterfactual__s1024 | 4 | 1.000 | 0.585 | 0.018 | 1.000 | 1.000 | 7 | 1.250 |

## Capability Summary

| run | conflict_resolution | counterfactual_reasoning | information_gathering | knowledge_retrieval | multi_step_planning | sensor_cross_validation | uncertainty_quantification |
|---|---|---|---|---|---|---|---|
| all_on__s42 | 0.250 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| all_on__s123 | 0.250 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| all_on__s456 | 0.250 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| all_on__s789 | 0.250 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| all_on__s1024 | 0.250 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_memory__s42 | 0.250 | 1.000 | 1.000 | 0.000 | 1.000 | 0.250 | 1.000 |
| no_memory__s123 | 0.250 | 1.000 | 1.000 | 0.000 | 1.000 | 0.250 | 1.000 |
| no_memory__s456 | 0.250 | 1.000 | 1.000 | 0.000 | 1.000 | 0.250 | 1.000 |
| no_memory__s789 | 0.250 | 1.000 | 1.000 | 0.000 | 1.000 | 0.250 | 1.000 |
| no_memory__s1024 | 0.250 | 1.000 | 1.000 | 0.000 | 1.000 | 0.250 | 1.000 |
| no_debate__s42 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_debate__s123 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_debate__s456 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_debate__s789 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_debate__s1024 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_counterfactual__s42 | 0.250 | 0.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_counterfactual__s123 | 0.250 | 0.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_counterfactual__s456 | 0.250 | 0.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_counterfactual__s789 | 0.250 | 0.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_counterfactual__s1024 | 0.250 | 0.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |

