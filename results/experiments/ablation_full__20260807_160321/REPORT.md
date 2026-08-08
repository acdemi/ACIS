# Experiment Report: ablation_full

- Description: Full ablation sweep over every cognitive module on the enriched dataset.
- Dataset: benchmarks.datasets.enriched
- Capability eval: True
- Git: ff825c9 (0.45C-Capability_Evaluation_Engine)
- Python: 3.13.3
- Platform: Windows-11-10.0.26100-SP0
- Started: 2026-08-07T16:03:21.887591+00:00
- Ended: 2026-08-07T16:03:30.765733+00:00
- Duration: 8.878s
- Metadata: author=ACIS version=1.0 tags=ablation,enriched paper=-

## Capability Summary

| run | conflict_resolution | counterfactual_reasoning | information_gathering | knowledge_retrieval | multi_step_planning | sensor_cross_validation | uncertainty_quantification |
|---|---|---|---|---|---|---|---|
| all_on | 0.250 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_planner | 0.250 | 1.000 | 0.000 | 1.000 | 0.000 | 0.250 | 1.000 |
| no_debate | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_memory | 0.250 | 1.000 | 1.000 | 0.000 | 1.000 | 0.250 | 1.000 |
| no_counterfactual | 0.250 | 0.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_tool_router | 0.250 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |
| no_critic | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 | 1.000 |

## Ablation

- Run dir: `results\experiments\ablation_full__20260807_160321\ablation\20260807_160324`
- Report: `results\experiments\ablation_full__20260807_160321\ablation\20260807_160324\REPORT.md`
- Combos: 7

