# ACIS Evidence Ledger

> 证据台账：仅登记经过验证的事实/观察与明确标注的假设。未经验证的声称不入账。
> 更新：2026-10-19（Phase 4 评测可靠性 / 契约审计 / Judge 恢复 BLOCKED 证据更新）

## 已登记证据

| ID | Claim | Type | Evidence | Status |
|---|---|---|---|---|
| E007 | Phase 2 experiment execution is stable across seeds | Fact | Phase 2 experiment: 630/630 runs successful, all seeds consistent | Confirmed |
| E008 | Module ablation causes corresponding capability scores to drop to zero | Observation | Phase 2 capability matrix (no_memory → knowledge_retrieval 0.00, no_debate → conflict_resolution 0.00, no_counterfactual → counterfactual_reasoning 0.00, no_planner → multi_step_planning 0.00) | Confirmed |
| E009 | Accuracy is saturated at 1.0 on enriched dataset across all configurations | Fact | Phase 2 accuracy table (7 configs × 5 seeds, mean=1.000, std=0.000) | Confirmed |
| E010 | Confidence varies significantly with module ablation (e.g., no_memory reduces confidence by 0.066) | Observation | Phase 2 effect size table (all_on 0.476 vs no_memory 0.410) | Confirmed |
| E011 | Confidence variation reflects case difficulty | Hypothesis | None (accuracy ceiling prevents calibration) | Untested |
| E012 | Modular multi-agent architecture improves task performance | Hypothesis | None (accuracy saturated) | Untested |
| E013 | 历史 "accuracy=1.00 / factor coverage=0.00 / coherence=0" 三元组源于指标契约缺陷，而非模型决策错误 | Observation | `reports/phase4_evaluation_metric_contract_audit.md`：同一 trace 契约修复后 factor coverage 0.00→0.25，label accuracy 保持 1.00；coherence 实为量化覆盖率 | Confirmed |
| E014 | 真实 LLM Judge 凭证无效，真实 Agent 评测链路处于 BLOCKED 状态 | Fact | `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md`：真实 trace 记录 HTTP 401 authentication_error / judge_mode=rules / outcome=fallback；无凭证经正常渠道更新的证据 | Confirmed |

## 数据来源

- Phase 2 实验：`results/experiments/phase2_multiseed__20260808_143600/`
  - 汇总：`PHASE_2_EVIDENCE_SUMMARY.md`、`analysis.json`、`REPORT.md`
  - 数据集指纹：enriched.json SHA-256 `5efc214f7fd8204793df649a2003348f85e1d8e78229babd375e93fea424abe8`（写入 manifest `dataset_sha256`）
- Phase 4（2026-10）：`reports/phase4_evaluation_reliability_repair.md`、`reports/phase4_evaluation_metric_contract_audit.md`、
  `reports/phase4_real_agent_consistency_20261017/`、`reports/phase4_real_judge_recovery_20261018/`
