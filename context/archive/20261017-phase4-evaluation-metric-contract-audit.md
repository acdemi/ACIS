# 2026-10-17 Phase 4 Evaluation Metric Contract Audit

## 对话主题与目标

审计 ACIS Phase 4 指标的数学定义、数据来源、调用路径和报告命名，解释真实 Agent
预检中的 label accuracy / factor coverage / factor coherence 差异，并实施最小
契约修复。

## 分支与提交

- Branch: `work/20261017-phase4-eval-reliability`
- Metric contract commit: `d9fcb7b`
- Merge / push: 未执行
- Phase 5: 未进入

## 变更文件

新增：

- `reports/phase4_evaluation_metric_contract_audit.md`
- `tests/test_stability_metric_contract.py`
- `context/archive/20261017-phase4-evaluation-metric-contract-audit.md`

修改：

- `benchmarks/CHALLENGE_SET_V1_REPORT.md`
- `evals/metrics.py`
- `evals/report.py`
- `evals/runner.py`
- `scripts/generate_stability_report.py`
- `scripts/run_challenge_evaluation.py`
- `scripts/run_phase4_2_real_agent.py`
- `src/openmetaphysics/evaluation/challenge_report.py`
- `src/openmetaphysics/evaluation/challenge_scorer.py`
- `tests/test_challenge_scorer.py`
- `tests/test_challenge_evaluation.py`
- `tests/test_metrics.py`

## 变更摘要

1. 最终标签准确率与因素覆盖率彻底分开。
2. 因素覆盖改为读取正式 `decision`、`reasoning_trace`、`summary` 和结构化
   `action_plan`；内部专家 Trace 不作为当前最终输出因素覆盖率输入。
3. 历史 `coherence` 明确更名为 factor coverage level；它不代表逻辑一致性。
4. ECE 区分 label correctness 与 factor correctness 两个域。
5. 无标签、无决策、无 factors、无 confidence 时返回未评分，不映射为 0 或成功。
6. 增加 Judge fallback rate、reason 分布、correct/false abstention rate。
7. 旧指标名在报告中以 legacy 名称显式展示，历史报告不重写。

## 实际 trace 重放

`ms_tomato_blight_stem`：

- label accuracy: `1.00`
- factor coverage: `0.00` -> `0.25`
- factor coverage level: `0` -> `1`
- Judge fallback: `100%`
- fallback reason: `authentication_error`

剩余三个诊断因素存在于内部专家 Trace 中，但不在最终用户可见输出中。完整 Trace
因素覆盖若要实施，应作为独立指标另行定义。

## 验证结果

- Focused metric contract/schema tests: **83 passed**
- Full repository tests: **307 passed**，22 个非阻断 Qdrant warnings
- Ruff（全部修改 Python 文件）：All checks passed
- Mypy targeted（8 个相关源码文件，external imports skipped）：Success
- 历史 stability report 使用 rules-only 本地重生成成功

## 剩余风险

- 无成功的真实 LLM Judge 运行；当前凭证错误仍需解决。
- 旧真实 Agent 数据可能缺少 `judge_runtime`，fallback rate 显示 unknown。
- factor scorer 自身的 LLM/rule fallback 尚无逐案例 provenance。
- 24 案例分 10 个 ECE bins 样本较小。
- 当前未实现独立 factor consistency 或 full-trace factor coverage 指标。

## 工作区说明

原有 `README.md`、`context/ARCHITECTURE_STATE.md`、`context/KNOWN_DEBT.md`
未提交改动保持不变，未纳入本轮提交。
