# Experiment Report: capability_sweep

- Description: Run each capability suite to exercise every cognitive dimension.
- Dataset: benchmarks/datasets/planning.json
- Capability eval: True
- Git: ff825c9 (0.45C-Capability_Evaluation_Engine)
- Python: 3.13.3
- Platform: Windows-11-10.0.26100-SP0
- Started: 2026-08-07T16:04:03.686165+00:00
- Ended: 2026-08-07T16:04:11.925982+00:00
- Duration: 8.240s
- Metadata: author=ACIS version=1.0 tags=capability,sweep paper=-

## Run Metrics

| run | cases | accuracy | average_confidence | average_runtime | planner_usage | tool_usage | memory_hits | debate_rounds |
|---|---|---|---|---|---|---|---|---|
| suite_planning | 4 | 1.000 | 0.698 | 0.025 | 1.000 | 1.000 | 8 | 2.000 |
| suite_memory | 4 | 1.000 | 0.730 | 0.105 | 1.000 | 1.000 | 10 | 2.000 |
| suite_debate | 4 | 1.000 | 0.595 | 0.022 | 1.000 | 1.000 | 9 | 1.750 |
| suite_counterfactual | 3 | 1.000 | 0.750 | 0.024 | 1.000 | 1.000 | 8 | 2.000 |
| suite_adversarial | 3 | 1.000 | 0.597 | 0.026 | 1.000 | 1.000 | 8 | 2.000 |

## Capability Summary

| run | conflict_resolution | counterfactual_reasoning | information_gathering | knowledge_retrieval | multi_step_planning | sensor_cross_validation | uncertainty_quantification |
|---|---|---|---|---|---|---|---|
| suite_planning | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 |
| suite_memory | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 |
| suite_debate | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 |
| suite_counterfactual | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 |
| suite_adversarial | 0.667 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

