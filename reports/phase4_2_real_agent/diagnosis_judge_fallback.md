# Phase 4.2-R2 — Judge Fallback Root-Cause Diagnosis

> Generated: 2026-08-13 | Mode: read-only diagnosis (no code/parameter changes)
> Scope: 216 real-agent executions of Phase 4.2-R (deepseek=25, rules=191)

---

## 1. Executive Summary

- `judge_mode` 由 `agents/judge_agent.py` 单点决定。**rules 分支仅在
  `_run_llm_judge` 抛出异常时触发**（`JudgeAgent.run` 的 except 分支）；
  本实验中 3 个配置均以 `use_llm_judge=True` 构造，不存在任何
  rules-only 的配置设计。
- **191/191 条 rules 记录全部携带 fallback 标记**
  `"DeepSeek Judge 不可用，已回退规则裁决：Connection error."` ——
  异常类型统一为 openai SDK 的 `APIConnectionError`（`str(exc) ==
  "Connection error."`）。无 timeout、无 429/5xx、无 JSON 解析失败。
- 失败在时间上呈**开关式模式**：25 次成功全部集中在
  `10:51:50–11:05:37`（seed42 C0 的 24 次 + seed42 C1 case20 的 1 次），
  之后 191/192 次尝试失败（唯一例外即 case20 的那次成功），直到运行
  结束（12:30）。
- **审计声明与可重建配置不一致**：审计方声明测试应使用 opencode go
  提供的免费 deepseek-v4-flash（网关）；可重建的执行配置（执行命令 +
  `.env` + 代码默认值）为 `https://api.deepseek.com` + `deepseek-chat`
  + `.env` 中的 `sk-` key。这构成 configuration/path mismatch 的候选，
  但运行期进程未记录端到端请求日志，无法直接证实进程实际端点。
- 2026-08-13 探针：免费网关 `opencode.ai/zen/go/v1` +
  `deepseek-v4-flash` **当前可用**（2.7s OK）；付费端点
  `api.deepseek.com` 返回 **402 Insufficient Balance**；opencode token
  打付费端点返回 401。这些状态只描述"今天"，不回溯证明 08-12 运行期
  状态。
- **根因信心**：rules 触发机制与异常层 = CONFIRMED；连接层不可达 =
  PROBABLE；"Connection error." 的底层网络子因与运行期实际端点 =
  UNKNOWN。

---

## 2. Exact fallback decision path

```
case (challenge_set_v1, 24 cases)
  → scripts/run_phase4_2_real_agent.py run_real_agent()
      → EvalConfig(use_llm_judge=True, use_langgraph=True)   [硬编码 True，3 配置相同]
      → evals.runner.run_evaluation(config)
          → AgentOrchestrator(use_llm_judge=True)
              → self.judge_agent = JudgeAgent(use_llm=True)   [agents/judge_agent.py:104]
              → orchestrator.run(query)
                  → judge_agent.run(context, outputs, debate) [orchestrator.py:194]
                      → if self.use_llm:                        [judge_agent.py:38]
                          → try: return self._run_llm_judge(...)
                          → except Exception as exc:            [judge_agent.py:41-44]
                              → decision = self._run_rule_judge(...)
                              → decision.debate.missing_evidence.append(
                                  f"DeepSeek Judge 不可用，已回退规则裁决：{exc}")
                              → return decision                 [judge_mode="rules"]
```

### judge_mode 的唯一定义点
| 分支 | 设置位置 | 触发条件 |
|---|---|---|
| `deepseek` | `_run_llm_judge` 返回的 `DecisionOutput(judge_mode="deepseek")` | API 调用成功 **且** `json.loads(resp...content)` 成功 |
| `rules` | `_run_rule_judge` 返回的 `DecisionOutput(judge_mode="rules")` | `use_llm=False`（本实验不存在）**或** `_run_llm_judge` 抛任意异常 |

### `_run_llm_judge` 内部（judge_agent.py:218-240）
- `api_key = os.environ.get("DEEPSEEK_API_KEY","").strip()`；为空 → 抛
  `ValueError("未设置 DEEPSEEK_API_KEY")` → rules。
- `client = OpenAI(api_key, base_url=os.environ.get("DEEPSEEK_BASE_URL",
  "https://api.deepseek.com"))` —— **无显式 timeout**（SDK 默认 600s）、
  **无自定义 retry**（SDK 默认 max_retries=2）、temperature=0.1、
  `response_format={"type":"json_object"}`。
- `model = AGRI_AI_JUDGE_MODEL or DEEPSEEK_MODEL or "deepseek-chat"`。
- 异常原样经 `except Exception` 捕获，`str(exc)` 写入
  `debate.missing_evidence` → 随 trace 的 debate 事件序列化
  （`trace/collector.py:_serialize_debate`，deep-copy 于记录时刻，即
  judge 返回之后 → fallback 原因可见于 trace）。

### 证据可追溯性（Task 2 要求）
每条 rules 记录的 fallback 原因来自
`logs/phase4_2_real_agent/run_{seed}/config_{C}/{arm}/runner/traces/{trace_id}.json`
的 `debate[0].missing_evidence`（示例：
`logs/phase4_2_real_agent/run_42/config_C1/c1_all_on/runner/traces/1bea7cfd….json`），
并经 `raw_results.json` 的 `judge_mode` 交叉确认（216/216 一致）。

---

## 3. Fallback reason taxonomy

| 类别 | 定义 | 本数据集中数量 | 证据 |
|---|---|---|---|
| A. timeout | 显式超时异常（APITimeoutError/ReadTimeout） | 0 | 无此类字符串 |
| B. API/network error | 连接层/网络层失败（APIConnectionError 等） | **191** | `"Connection error."`（全部） |
| C. rate limit | 429 / rate limit 字样 | 0 | 无 HTTP 状态码（连接层失败无响应） |
| D. malformed LLM response | 响应内容结构性错误 | 0 | — |
| E. JSON parse failure | `json.loads` 失败 | 0 | — |
| F. explicit rule-path selection | use_llm=False 设计路径 | 0 | 全部 216 次构造为 use_llm=True |
| G. configuration/path mismatch | 端点/模型/key 配置与预期不符 | 候选（见 §9） | 审计声明 vs 重建配置不一致；运行期无直接证据 |
| H. unknown | 无证据 | 0（子因层见 §9） | — |

---

## 4. 191 records classification table

分类汇总（逐条证据 = trace 中 `missing_evidence` 的 fallback 字符串）：

| 分类 | 数量 | 占 rules 比例 |
|---|---|---|
| B. API/network error（`Connection error.`，APIConnectionError） | 191 | 100% |
| A / C / D / E / F | 0 | 0% |
| 无 fallback 标记（即非异常触发的 rules） | 0 | 0% |

191 条记录的 trace_id ↔ seed/config/case 完整映射见
`raw_results.json`（`trace_id` 字段）与
`logs/phase4_2_real_agent/run_*/config_*/*/runner/traces/`。

---

## 5. Per-config breakdown

| config | 调用数 | deepseek | rules | rules 占比 |
|---|---|---|---|---|
| C0 | 72 | 24 | 48 | 66.7% |
| C1 | 72 | 1 | 71 | 98.6% |
| C2 | 72 | 0 | 72 | 100.0% |

C0 的 24 次 deepseek 全部来自 seed42（首个执行的 arm）；配置本身不
影响 judge 路径（三配置 `use_llm_judge=True` 相同）。

---

## 6. Per-seed breakdown

| seed | 调用数 | deepseek | rules |
|---|---|---|---|
| 42 | 72 | 25 | 47 |
| 43 | 72 | 0 | 72 |
| 44 | 72 | 0 | 72 |

seed42 的 25 次成功 = C0 全 24 + C1 case20 的 1 次。失败始于 seed42
的 C1 arm（~10:52），此后 seed43/44 全部失败——**与 seed 数值无关，
纯时间序现象**（seed42 先跑，赶上了连接尚可的窗口）。

---

## 7. Per-case breakdown

| 维度 | 结果 |
|---|---|
| case 1–24（seed42 C0） | 24/24 deepseek |
| case 20 | 全实验中唯一出现 2 次 deepseek 的 case（seed42 C0 + seed42 C1），即连接窗口内唯一成功重复 |
| 其余 case × (config, seed) 组合 | 0 次 deepseek |

case 分布无异常模式：case20 的第二次成功是时间窗口的偶然落入
（11:05:37 唯一一次恢复），与 case 内容无关。

---

## 8. DeepSeek success/failure breakdown

| 项 | 值 |
|---|---|
| 总尝试（full run） | 216 |
| 成功（deepseek） | 25（11.6%） |
| 失败（rules，`Connection error.`） | 191（88.4%） |
| 成功时间窗 | 10:51:50 – 11:05:37（arm 完成时间戳） |
| 失败时间窗 | 11:05:37 – 12:30:52（arm 完成时间戳；实际失败始于 ~10:52 C1 arm 开始） |
| 运行前同期尝试（precheck，10:20） | 3/3 成功（judge_mode=deepseek） |
| 更早历史 | 08-09 Phase 4.1 72/72 成功；08-10 harness 216/216 成功（deepseek-v4-flash，同一 base_url） |
| 08-13 探针：免费网关（opencode.ai/zen/go/v1, deepseek-v4-flash） | 成功（2.7s，200） |
| 08-13 探针：api.deepseek.com（.env sk- key） | **402 Insufficient Balance** |
| 08-13 探针：api.deepseek.com（opencode token） | 401 invalid key |

失败形态 = 连接层错误（SDK 重试 2 次后抛 APIConnectionError），
**不是** HTTP 层 4xx/5xx（无响应到达）。

---

## 9. Unknown cases

| 未知项 | 说明 |
|---|---|
| 底层网络子因 | `APIConnectionError` 的细节（连接被拒 / TLS / DNS / 读超时 / 对端节流）未被捕获：`judge_agent.py` 仅存储 `str(exc)`（"Connection error."），SDK 的 `.error`/`__cause__` 未保存。**无证据区分 → UNKNOWN**，禁止推测为 timeout/429。 |
| 运行期实际端点 | 重建（执行命令注入仅 DEEPSEEK_API_KEY；`load_env()` 从 .env 读 base_url）指向 `api.deepseek.com`；审计声明测试应使用 opencode go 免费网关。进程未记录端到端请求日志（无 httpx 请求行落盘），无法直接证实。→ **UNKNOWN（运行期）**，与 G 类候选并存。 |
| 08-12 运行期账号/网关状态 | 今日探针（402 / 网关 OK）不回溯证明 08-12 10:52 后的状态；11:05 的一次成功说明当时至少一次调用可扣费/可连通。→ UNKNOWN。 |

---

## 10. Root-cause confidence

### ROOT CAUSE CONFIRMED
1. rules 分支的**精确触发机制**：唯一触发条件 = `_run_llm_judge` 异常
   （`JudgeAgent.run` except 分支）；191/191 条带 fallback 标记，无
   显式 rules 选择路径存在。
2. 异常类别统一为 **连接层失败（APIConnectionError, "Connection
   error."）**；非 timeout、非 429、非解析失败（异常在 HTTP 响应到达
   之前发生）。
3. Phase 4.1（72/72 deepseek）与 Phase 4.2-R（25/216）**调用完全相同的
   judge 代码路径**：`git diff 7113011..d4a56e0 -- agents/judge_agent.py
   evals/runner.py orchestrator.py agents/types.py` 为空；两轮均
   `use_llm_judge=True`、temperature=0.1、response_format=json_object、
   SDK 默认 timeout/retry、无并发。**差异不在代码与参数，而在执行时点
   的端点连通性。**

### ROOT CAUSE PROBABLE
1. 08-12 10:52–12:30 期间执行主机到所用端点的**连接层不可达（间歇性）**
   ：191/192 失败 + 1 次成功（11:05），开关式时间分布。
2. **端点/模型配置与审计声明的测试配置不一致**（G 类候选）：审计声明
   "使用 opencode go 提供的免费 deepseek-v4-flash"；重建配置 =
   `api.deepseek.com` + `deepseek-chat`。若预期端点确为免费网关，则
   进程未配置该端点属于配置不一致；若预期即付费端点，则属账号/连通性
   问题。两种解释均与"25 次成功发生在付费端点"的时序兼容。

### ROOT CAUSE UNKNOWN
1. "Connection error." 的底层网络子因（被拒/TLS/DNS/对端节流）——
   无证据，禁止归因于 timeout/parse/API error。
2. 运行期进程实际连接的端点（无端到端日志）。
3. 08-12 运行期账号余额与网关状态（仅"今天"有探针）。

### 当前账号/端点状态（08-13，影响任何重跑/Phase 4.3 决策）
- 免费网关：可用（探针 OK）。
- 付费端点：余额耗尽（402）——**重跑前必须处理计费或改走网关**。

---

## 11. Remediation recommendation（仅诊断后建议，未执行任何修改）

### ROOT CAUSE CONFIRMED（机制层，无需"修复"）
- fallback 机制与异常触发条件符合设计且证据完整；不修改
  judge/runner/脚本。
- 保留现状：`judge_mode` 逐条落盘 + trace 中 fallback 原因字符串，是
  本次诊断得以完成的关键证据。

### ROOT CAUSE PROBABLE（配置/运行层候选修复）
1. **消除端点/模型歧义（先于任何重跑）**：明确并显式记录预期端点——
   免费网关（`opencode.ai/zen/go/v1` + `deepseek-v4-flash`）还是付费
   端点（`api.deepseek.com` + `deepseek-chat`）。当前 `.env` 与审计
   声明不一致，属 G 类候选。
2. **预检门禁**：任何重跑/Phase 4.3 前执行 1 次连通性+计费探针，断言
   HTTP 200 且非 402/401（对所选端点与模型各一次）。
3. **计费处理**：若走付费端点，需充值（当前 402）；若走免费网关，
   确认 opencode token 有效（今日探针 OK）。
4. **运行期实时监控**（不改变行为）：沿用现有 per-call 日志，在连续
   N 次 fallback 时中止并提示（属运行编排层，不动 agent/脚本逻辑——
   具体实现需审计批准）。

### ROOT CAUSE UNKNOWN（禁止调参，禁止"提高 deepseek 比例"类方案）
- "Connection error." 的底层子因未知 → **不得**通过调整 timeout/
  retry/prompt/模型参数来"提高 deepseek 比例"——此类调整在根因未知时
  无法验证有效性，且可能掩盖真实问题。
- 若未来需要更细诊断：建议（需审计批准，涉及 `agents/` 修改，当前
  受约束禁止）在 fallback 消息中记录异常 `type(exc).__name__` 与
  `exc.__cause__`，以便区分 refused/TLS/DNS/节流。

---

## 12. Final status

**Phase 4.2-R2 Diagnosis COMPLETE — BLOCKED FOR EVIDENCE REVIEW**
- S1 ✅ 191/191 完成分类（B 类 100%，子因 UNKNOWN 已如实标注）
- S2 ✅ judge_mode 代码路径定位（`agents/judge_agent.py` 单点决定）
- S3 ✅ 环境对比（`environment_diff.md`，FACT/OBSERVATION/HYPOTHESIS 分层）
- S4 ✅ CONFIRMED（触发机制/异常层）/ PROBABLE（连接层可达性、
  端点配置不一致）/ UNKNOWN（子因、运行期端点、余额时点）
- S5 ✅ Git working tree 无新增修改（仅两份报告文件，见下）
- S6 ✅ agents/、benchmarks/、challenge_scorer.py 零修改
