# Reports

本目录只保留**当前有效、可复核**的实验证据与评测记录；历史报告在 `archive/`，
原始模型输出、内部审计与未采纳支线材料在仓库外本地归档。

## 当前证据

| 路径 | 内容 | 说明 |
|---|---|---|
| `experiment_audit_20261024.md` | C0/C1/C2 实验与指标口径审计 | 先读指标定义再看数字 |
| `phase6_baseline_20261023/` | Phase 6 基线：72 次真实 Judge、C0/C1/C2 | 单 seed、n=24；不能证明架构收益 |
| `phase6_sc_20261023/`、`phase6_sc43_20261024/` | C1 自一致性两个 seed 的原始结果 | ECE/corr 依赖 trace agreement |
| `phase6_redesign_20261023/` | ADR-005 实现状态与最终证据 | 置信度链路；accuracy 未提升 |
| `phase4_evaluation_metric_contract_audit.md` | 指标契约缺陷审计 | factor coverage 与 label accuracy 的差异 |
| `phase4_evaluation_reliability_repair.md` | Phase 4 评测可靠性修复 | 历史修复记录 |
| `phase4_2_real_agent/diagnosis_judge_fallback.md` | 真实链路的 Judge 回退诊断 | 端点/连接问题 |
| `phase4_judge_recovery_20261019/judge_recovery_report.md` | 真实 Judge 恢复验证 | 1 次受控验证 + 6 次预检 |
| `delivery_eval/` | 12 例固定离线评测结果 | 两次运行哈希一致 |
| `acceptance_20261024.md` | MVP 端到端验收记录 | 环境限制逐条列出 |
| `public_docs_cleanup_20261024.md` | 公开仓库文档清理记录 | 归档/删除/校验摘要；本地归档在仓库外 |

## 历史报告

`archive/phase4/` 与 `archive/phase4_2/` 保留 Phase 4.1/4.2/R2/R3 等历史摘要。
注意：这些报告中的 `accuracy` 在原始报告中多指 **factor coverage**，不是诊断准确率；
`scripts/generate_stability_report.py` 的历史字段名也保留了该口径。

## 复现

```powershell
python scripts/run_delivery_eval.py
python evals/fixture_eval.py
python evals/smoke_eval.py
```

原始 raw JSON（phase4_2 等约 1.5 MB）与内部审计证据不在此目录，已移出公开仓库；
需要复核时请使用本地归档并参考 `experiment_audit_20261024.md` 中的来源说明。
