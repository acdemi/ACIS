# 2026-10-17 Phase 4 Real-Agent Consistency Precheck

## 对话主题与目标

在已修复的 Phase 4 评测链路上执行最小真实 Agent 一致性预检，并在停止条件
触发时停止扩样，输出失败证据、根因和 PASS/FAIL 结论。

## 分支与提交

- Branch: `work/20261017-phase4-eval-reliability`
- Repair commit: `340857f`
- Precheck artifact commit: `f4be5b7`
- Merge / push: 未执行

## 预检范围

计划覆盖三类案例：

- 23 `ms_tomato_blight_stem`：普通确定性诊断，已执行；
- 14 `inc_tomato_vague_spot`：证据不足/弃权，未执行；
- 9 `conf_tomato_blight_cool_rain`：冲突证据，未执行。

因首个案例发生意外 Judge fallback，立即停止，未扩大样本，也未执行必要的重复
运行验证。

## 实验配置

- 数据：`benchmarks/challenge_set_v1.json`，version 1，24 cases
- 数据 SHA-256：`ad39b08f91361d37242fd1e087ce6b03712f2c71cc9b5291f5c0934de1a4846c`
- 配置：C1 全模块开启，LangGraph + LLM Judge requested，seed 42
- Provider：`deepseek`
- Endpoint：`https://api.deepseek.com`
- Model：`deepseek-chat`
- Judge timeout：30 秒
- 本次探针 SDK retries：0
- Config fingerprint SHA-256：`c75a88874fe325639cdf3d49e02f9c9fd5677f54afea704460eed5065cf37802`

## 结果摘要

- 真实 decision：`病理判断首选：番茄早疫病`
- 置信度：`0.75`
- canonical label：`早疫病`
- abstained：`false`
- Judge mode：`rules`
- fallback：`authentication_error`
- Judge tokens：`0`
- runtime：`11.5988s`

真实 trace 与 evaluator 的 decision、confidence、label、abstention、Judge mode
和 fallback reason 完全一致，说明评测器忠实保留了真实决策和失败状态。

但同一案例 Runner label accuracy 为 `1.0`，challenge scorer 的 factor
coverage accuracy 为 `0.0`。原因是两者定义不同，且 rules fallback 的
reasoning trace 不含预期因子；canonical scorer 也未将 `action_plan` 纳入因子
文本。该评分口径差异在 Phase 5 前必须明确。

## 停止原因

1. 真实 LLM Judge 意外 fallback：进程观察到两次认证失败和一次连接失败；
   最终 trace 记录 `authentication_error`，`judge_mode=rules`。
2. 同一 decision 的 label accuracy 与 factor coverage 不可互换，当前仍共享
   `accuracy` 名称，存在评测指标歧义。
3. 因停止条件触发，重复执行与弃权/冲突案例未运行，模型波动无法评估。

## 结论

**FAIL**。不提出进入 Phase 5 的建议。

## 产物

- `reports/phase4_real_agent_consistency_20261017/precheck_report.md`
- `reports/phase4_real_agent_consistency_20261017/precheck_summary.json`
- `reports/phase4_real_agent_consistency_20261017/stop_probe_case23.md`
- `reports/phase4_real_agent_consistency_20261017/stop_probe_logs/precheck_seed42/c1_all_on/runner/metrics.csv`
- `reports/phase4_real_agent_consistency_20261017/stop_probe_logs/precheck_seed42/c1_all_on/runner/summary.md`
- `reports/phase4_real_agent_consistency_20261017/stop_probe_logs/precheck_seed42/c1_all_on/runner/traces/d432f0d40e704dd89cab6dd508185913.json`
- `reports/phase4_real_agent_consistency_20261017/stop_probe_logs/precheck_seed42/_flattened/challenge_set_v1_flattened.json`

## 工作区说明

原有 `README.md`、`context/ARCHITECTURE_STATE.md`、`context/KNOWN_DEBT.md`
未提交改动保持不变，与本轮预检无关。
