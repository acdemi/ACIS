# ACIS Evidence Ledger

> 证据台账：仅登记经过验证的事实/观察与明确标注的假设。未经验证的声称不入账。
> 更新：2026-10-19（Judge 恢复验证：E014 被 E015 取代，新增 E016）

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
| E014 | 真实 LLM Judge 凭证无效，真实 Agent 评测链路处于 BLOCKED 状态 | Fact | `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md`：真实 trace 记录 HTTP 401 authentication_error / judge_mode=rules / outcome=fallback；无凭证经正常渠道更新的证据 | Superseded by E015（凭证已更新并验证） |
| E015 | 真实 LLM Judge 恢复并验证：评测链路可在真实 Judge 下运行 | Fact | `reports/phase4_judge_recovery_20261019/judge_recovery_report.md`：1 次受控验证 PASS + 六次预检 6/6 judge_mode=deepseek、零 fallback；trace 记录 outcome=success 与 token usage | Confirmed |
| E016 | 弃权案例（case14）跨 seed 决策翻转（seed42 误判为疾病 / seed43 弃权），GT 命中 5/6 | Observation | `reports/phase4_judge_recovery_20261019/` 六次预检报告；样本量 1 案例 × 2 seed，不足以扩展为总体结论 | Confirmed |

## 数据来源

- Phase 2 实验：`results/experiments/phase2_multiseed__20260808_143600/`
  - 汇总：`PHASE_2_EVIDENCE_SUMMARY.md`、`analysis.json`、`REPORT.md`
  - 数据集指纹：enriched.json SHA-256 `5efc214f7fd8204793df649a2003348f85e1d8e78229babd375e93fea424abe8`（写入 manifest `dataset_sha256`）
- Phase 4（2026-10）：`reports/phase4_evaluation_reliability_repair.md`、`reports/phase4_evaluation_metric_contract_audit.md`、
  `reports/phase4_real_agent_consistency_20261017/`、`reports/phase4_real_judge_recovery_20261018/`
