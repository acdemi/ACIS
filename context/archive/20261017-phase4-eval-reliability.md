# 2026-10-17 Phase 4 Evaluation Reliability Repair

## 对话主题与目标

修复 ACIS Phase 4 评测链路中有证据支持的可追溯性和语义一致性问题，使 Judge
实际运行配置、fallback 原因、真实 Agent 与 harness 的决策/置信度/弃权语义一致。
不修改冻结 benchmark 案例，不运行大规模评测，不进入 Phase 5。

## 分支与提交

- Branch: `work/20261017-phase4-eval-reliability`
- Main code/report commit: `340857f`
- Merge / push: 未执行

## 变更文件

新增：

- `decision_semantics.py`
- `utils/judge_runtime.py`
- `tests/test_judge_runtime.py`
- `tests/test_phase4_harness_runtime.py`
- `tests/test_phase4_reliability.py`
- `reports/phase4_evaluation_reliability_repair.md`
- `context/archive/20261017-phase4-eval-reliability.md`

修改：

- `agents/judge_agent.py`
- `evals/metrics.py`
- `src/openmetaphysics/evaluation/challenge_scorer.py`
- `scripts/run_challenge_evaluation.py`
- `scripts/run_phase4_2.py`
- `scripts/run_phase4_2_real_agent.py`
- `tests/test_challenge_scorer.py`
- `tests/test_metrics.py`

删除：无。

## 变更摘要

1. Judge 运行配置统一解析，记录脱敏 provider/endpoint/model、来源、超时、
   SDK retry 预算、fallback code/detail 和 token usage。
2. 区分缺凭证、认证、余额、限流、超时、连接、响应格式、服务端/API 和未知
   provider 故障；不记录 API Key、Authorization header 或 endpoint query。
3. Judge 只使用 SDK 一层重试；direct harness 自己持有重试并设置 SDK retries=0；
   非瞬时认证/余额/格式错误不重试。
4. 最终 decision、confidence、accuracy、abstention 统一由最终 Judge decision
   定义，不再混用病理 Agent 中间 claim。
5. R4 根因明确为直连 LLM baseline 与真实 ACIS Judge 的执行路径/输入/置信度
   来源不同；跨路径 confidence 不再作为等价门禁，不同路径标为 incomparable。
6. C2 的 `无法定论（待实验室病原鉴定）` 始终归一化为 `ABSTAIN`，不会转换成
   确定性疾病诊断。

## 验证结果

- `pytest -q tests`: 289 passed，22 个 Qdrant 兼容性 warning。
- 目标回归：71 passed。
- `ruff check`（全部修改 Python 文件）：All checks passed。
- `mypy decision_semantics.py utils/judge_runtime.py`：Success。
- 更大范围 mypy 受既有 `agents/types.py` 与标准库 `types` 同名冲突阻断。
- 实际小探针：通过真实 `JudgeAgent.run()` 到 `api.deepseek.com` /
  `deepseek-chat`，15 秒超时、SDK retries=0；返回 HTTP 401，正确分类为
  `authentication_error` 并回退 rules。当前凭证无效，未获得成功 live LLM 运行。

## 未完成 / 剩余风险

- 修复有效 API 凭证后，需重新执行一次单案例 live probe 和同执行语义 precheck。
- 历史 Phase 4.2/R4 产物保持不变，不能追溯补写其当时实际 provider/model。
- 工作区中原有的 `README.md`、`context/ARCHITECTURE_STATE.md`、
  `context/KNOWN_DEBT.md` 文档差异与本轮无关，未纳入本轮提交。
