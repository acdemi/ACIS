# ACIS Evidence Ledger

> 证据台账：只登记有来源、可复核的事实/观察与明确标注的假设；未经验证的声称不入账。
> 更新：2026-10-24（补充 Phase 6 基线与指标口径；历史材料移出公开树后仅保留摘要）。
> 口径提醒：历史报告中的 `accuracy` 在部分报告里指 **factor coverage**，不是诊断准确率；
> 引用前先读 `reports/experiment_audit_20261024.md`。

## 已登记证据

| ID | Claim | Type | Evidence | Status |
|---|---|---|---|---|
| E007 | Phase 2 experiment execution is stable across seeds | Fact | Phase 2 experiment: 630/630 runs successful, all seeds consistent | Confirmed（历史数据集） |
| E008 | Module ablation causes corresponding capability scores to drop to zero | Observation | Phase 2 capability matrix（no_memory → knowledge_retrieval 0.00、no_debate → conflict_resolution 0.00、no_counterfactual → counterfactual_reasoning 0.00、no_planner → multi_step_planning 0.00） | Confirmed（历史数据集） |
| E009 | 在旧 enriched 数据集上，各配置准确率饱和于 1.0 | Fact | Phase 2 accuracy table（7 configs × 5 seeds，mean=1.000，std=0.000） | Confirmed（仅限该数据集，不代表当前挑战集） |
| E010 | 模块消融会显著改变置信度（如 no_memory 降低约 0.066） | Observation | Phase 2 effect size table（all_on 0.476 vs no_memory 0.410） | Confirmed（历史数据集） |
| E011 | 置信度变化反映案例难度 | Hypothesis | 无直接证据（准确率天花板使校准不可测） | Untested |
| E012 | 模块化多智能体架构提升任务表现 | Hypothesis | 无证据（准确率饱和；Phase 4/6 未支持） | Untested |
| E013 | 历史“accuracy=1.00 / factor coverage=0.00 / coherence=0”三元组源于指标契约缺陷，而非模型决策错误 | Observation | `reports/phase4_evaluation_metric_contract_audit.md`：修复契约后 factor coverage 0.00→0.25，label accuracy 保持 1.00；coherence 实为量化覆盖率 | Confirmed |
| E014 | 真实 LLM Judge 凭证曾无效，真实 Agent 评测链路处于 BLOCKED | Fact | 历史预检记录 HTTP 401 / judge_mode=rules / outcome=fallback；后被 E015 取代 | Superseded by E015 |
| E015 | 真实 LLM Judge 恢复并完成受控验证 | Fact | `reports/phase4_judge_recovery_20261019/judge_recovery_report.md`：1 次受控验证 PASS + 6 次预检零回退（6/6 judge_mode=deepseek） | Confirmed（小样本） |
| E016 | 弃权案例 case14 跨 seed 决策翻转（seed42 误判疾病 / seed43 弃权），GT 命中 5/6 | Observation | 历史六次预检报告；1 案例 × 2 seed，不足以外推 | Confirmed（小样本） |
| E017 | Phase 6 baseline seed42：真实 Judge 72/72 成功、0 回退；label accuracy C0 20/24、C1 19/24、C2 24/24 | Fact | `reports/phase6_baseline_20261023/raw_results.json` + `baseline_analysis.md`；复算见 `reports/experiment_audit_20261024.md` | Confirmed（单 seed，n=24；不能证明架构收益） |
| E018 | C1 自一致性：seed42 13/24 可评（11 次连接失败回退），seed43 24/24；ECE/corr 依赖 trace 中的 agreement | Observation | `reports/phase6_sc_20261023/`、`reports/phase6_sc43_20261024/`；trace 重建见实验审计 | Confirmed（仅 C1、两 seed；不是普遍校准结论） |
| E019 | Phase 4.2-R 真实链路 216 次调用中 191 次规则回退，服务仍可用 | Observation | 历史 raw 结果与诊断报告（现保存在仓库外本地归档）；公开报告保留摘要 | Confirmed（回退率事实，不是模型效果） |
| E020 | 离线固定评测（12 例）可重复：两次运行输出哈希一致 | Fact | `reports/delivery_eval/summary.json` / `.md`；`scripts/run_delivery_eval.py` | Confirmed |

## 数据来源

- Phase 2：`results/experiments/phase2_multiseed__20260808_143600/`（本地运行目录，不公开）；
  enriched.json SHA-256 `5efc214f7fd8204793df649a2003348f85e1d8e78229babd375e93fea424abe8`。
- Phase 4 可靠性/指标契约：`reports/phase4_evaluation_reliability_repair.md`、
  `reports/phase4_evaluation_metric_contract_audit.md`、`reports/phase4_judge_recovery_20261019/`。
- Phase 6：`reports/phase6_baseline_20261023/`、`reports/phase6_sc_20261023/`、
  `reports/phase6_sc43_20261024/`、`reports/phase6_redesign_20261023/`。
- C0/C1/C2 指标审计：`reports/experiment_audit_20261024.md`。

## 公开边界

- 非技术个人材料、内部交付审计、AI 会话归档与 AG-DISTILL 支线已移出公开仓库；
  需要复核时从仓库外本地归档恢复，不把候选知识当作已验证知识。
- 历史报告中的 `accuracy` 一律先确认口径；无法确认的不用作“诊断准确率”证据。
