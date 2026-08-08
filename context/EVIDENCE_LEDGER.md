# ACIS Evidence Ledger

> 证据台账：仅登记经过验证的事实/观察与明确标注的假设。未经验证的声称不入账。
> 更新：2026-08-09（Phase 2 证据更新）

## 已登记证据

| ID | Claim | Type | Evidence | Status |
|---|---|---|---|---|
| E007 | Phase 2 experiment execution is stable across seeds | Fact | Phase 2 experiment: 630/630 runs successful, all seeds consistent | Confirmed |
| E008 | Module ablation causes corresponding capability scores to drop to zero | Observation | Phase 2 capability matrix (no_memory → knowledge_retrieval 0.00, no_debate → conflict_resolution 0.00, no_counterfactual → counterfactual_reasoning 0.00, no_planner → multi_step_planning 0.00) | Confirmed |
| E009 | Accuracy is saturated at 1.0 on enriched dataset across all configurations | Fact | Phase 2 accuracy table (7 configs × 5 seeds, mean=1.000, std=0.000) | Confirmed |
| E010 | Confidence varies significantly with module ablation (e.g., no_memory reduces confidence by 0.066) | Observation | Phase 2 effect size table (all_on 0.476 vs no_memory 0.410) | Confirmed |
| E011 | Confidence variation reflects case difficulty | Hypothesis | None (accuracy ceiling prevents calibration) | Untested |
| E012 | Modular multi-agent architecture improves task performance | Hypothesis | None (accuracy saturated) | Untested |

## 数据来源

- Phase 2 实验：`results/experiments/phase2_multiseed__20260808_143600/`
  - 汇总：`PHASE_2_EVIDENCE_SUMMARY.md`、`analysis.json`、`REPORT.md`
  - 数据集指纹：enriched.json SHA-256 `5efc214f7fd8204793df649a2003348f85e1d8e78229babd375e93fea424abe8`（写入 manifest `dataset_sha256`）
