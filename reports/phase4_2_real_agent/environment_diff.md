# Phase 4.2-R — Execution Environment Comparison (Phase 4.1 vs Phase 4.2-R)

> Generated: 2026-08-13 | Read-only comparison; nothing fixed.
> Label conventions: **FACT** (code/commits/executed commands/recorded
> fields), **OBSERVATION** (reconstruction from available artifacts),
> **HYPOTHESIS** (no direct evidence, clearly marked).
> User declaration (audit): 测试使用 opencode go 提供的免费
> deepseek-v4-flash。

---

## 1. Version / code path

| 项 | Phase 4.1 (08-09) | Phase 4.2-R (08-12) | 判定 |
|---|---|---|---|
| HEAD commit | 7113011（对话开始时记录） | d4a56e0（freeze 文件记录） | FACT |
| judge/runner/orchestrator 代码 | 相同 | 相同 | **FACT**：`git diff 7113011..d4a56e0` 仅含 AGENTS.md 与 context/archive（文档），无代码变更 |
| judge 调用路径 | `evals.runner.run_evaluation` → JudgeAgent(use_llm=True) | 同一路径（`run_phase4_2_real_agent.run_real_agent` → 同一 runner） | FACT |
| 执行包装 | 3 个独立进程（每 arm 一次 bash 调用） | 单进程 9 次 arm-run（一次 bash 调用） | OBSERVATION；对 judge 调用无影响（每次调用新建 OpenAI client） |

## 2. API endpoint

| 项 | Phase 4.1 | Phase 4.2-R | 判定 |
|---|---|---|---|
| base_url 来源 | `.env` `DEEPSEEK_BASE_URL`（经 `_env.load_env()`，模块级） | 相同 | FACT（重建：执行命令未注入 base_url，进程读 .env = `https://api.deepseek.com`） |
| 实际端点 | `https://api.deepseek.com` | `https://api.deepseek.com` | OBSERVATION（重建，无端到端请求日志） |
| 审计声明端点 | — | opencode go 免费网关（`opencode.ai/zen/go/v1`，deepseek-v4-flash） | USER DECLARATION；与重建配置**不一致** |
| 08-13 探针：网关 | — | 2.7s OK（deepseek-v4-flash, opencode token） | FACT（今日状态，不回溯 08-12） |
| 08-13 探针：付费端点 | — | 402 Insufficient Balance（.env sk- key）；401（opencode token） | FACT（今日状态） |

## 3. Model identifier

| 项 | 值 | 判定 |
|---|---|---|
| judge 模型解析链 | `AGRI_AI_JUDGE_MODEL or DEEPSEEK_MODEL or "deepseek-chat"`（judge_agent.py:224） | FACT |
| 两轮环境变量 AGRI_AI_JUDGE_MODEL / DEEPSEEK_MODEL | 均未设置 | FACT（08-09 检查记录；.env 无此类键） |
| 实际模型 | `deepseek-chat`（两轮相同） | OBSERVATION（重建） |
| 审计声明模型 | 免费 `deepseek-v4-flash`（opencode go） | USER DECLARATION；与重建模型不一致 |
| harness（08-10，辅助） | `deepseek-v4-flash` 打 `api.deepseek.com`，216/216 成功 | FACT：api.deepseek.com 接受该模型 id（08-10 探针亦证实），排除"模型 id 无效"假说 |

## 4. Sampling / request parameters

| 项 | 两轮值 | 判定 |
|---|---|---|
| temperature | 0.1（judge_agent.py:225） | FACT（同一代码） |
| response_format | `{"type": "json_object"}` | FACT（同一代码） |
| timeout | 未显式设置（SDK 默认 600s） | FACT（同一代码）；两轮相同 |
| retry | 未自定义（SDK 默认 max_retries=2，覆盖连接错误/429/5xx） | FACT（同一代码）；两轮相同 |
| seed 参数 | 两轮 judge 调用均不传 seed | FACT（同一代码） |

## 5. Prompt / tool calling / fallback policy

| 项 | 两轮值 | 判定 |
|---|---|---|
| judge system prompt | `judge_agent._judge_system_prompt()`（同一文件，未变更） | FACT |
| user payload 结构 | `_build_judge_payload`（同一代码） | FACT |
| tool calling | judge 无工具调用；两者相同 | FACT |
| fallback 策略 | `except Exception → _run_rule_judge` + missing_evidence 记录 `str(exc)` | FACT（同一代码）；行为已验证：191/191 rules 带标记 |

## 6. Concurrency / rate limiting

| 项 | 两轮值 | 判定 |
|---|---|---|
| 并发 | 均串行（单进程顺序调用） | FACT |
| 请求节奏 | 4.1：72 次/~2h；4.2-R：216 次/1h39m（含失败快速返回，实际连通期 ~10:52 结束） | OBSERVATION |
| rate limiting 证据 | 无 429/Retry-After 响应（失败均在连接层） | FACT（trace 中无 HTTP 状态码痕迹） |
| 对端节流表现 | 连接层失败可能与对端边缘节流/封锁一致，也可能为本地网络 | HYPOTHESIS（无法区分） |

## 7. Environment variables / proxy

| 项 | 值 | 判定 |
|---|---|---|
| 执行命令注入 | 仅 `DEEPSEEK_API_KEY`（来自 .env，sk- 35 字符）；base_url/model 未注入 | FACT（执行命令记录） |
| .env 内容 | DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / NEO4J_* / HF_HUB_OFFLINE 等；无代理变量 | FACT（今日读取）；两轮期间 .env 是否有过修改无快照 → UNKNOWN |
| 当前 shell 代理变量 | 无 HTTP(S)_PROXY / NO_PROXY | FACT（今日）；4.2-R 进程环境与此一致无法证实 → OBSERVATION |
| 历史代理迹象 | commit 7113011 "bypass system proxy for localhost (NO_PROXY) in launchers" | FACT（代码历史）；launchers 与 judge 调用无关 |
| httpx 代理行为 | 默认 trust_env 读 env 代理变量；Windows 系统代理（注册表）不被 httpx 读取 | FACT（SDK 行为）；→ 无代理变量时走直连 |

## 8. Billing / account state（HYPOTHESIS 区）

| 项 | 值 | 判定 |
|---|---|---|
| 付费账号（.env sk-）累计成功调用 | 08-09: 72；08-10: 216（harness）；08-12: 3（precheck）+ 25 = 25 之后连接失败；08-13: 402 | FACT（各轮记录 + 今日探针） |
| 余额耗尽时点 | 08-12 11:05 之后至 08-13 02:29（报告生成）之间的某时刻 | OBSERVATION（402 首次观测于 08-13；11:05 仍有成功） |
| 余额耗尽是否导致 4.2-R 的 Connection error | 时间线不支持（11:05 成功时余额可扣费；失败早于且晚于该点均有） | OBSERVATION → 余额耗尽**不解释** 10:52–12:30 的连接失败 |
| 免费网关在 08-12 运行期状态 | 无运行期记录；今日可用 | UNKNOWN |

## 9. 两轮差异总结

| 差异维度 | 是否影响 judge 结果 |
|---|---|
| HEAD commit（仅文档变更） | 否（代码相同） |
| 执行包装（进程数） | 否（调用链相同） |
| 调用量与时点（72 vs 216；08-09 vs 08-12） | 是——失败集中在 08-12 10:52 后的窗口 |
| 端点/模型配置（重建） | 否（两轮同为 api.deepseek.com + deepseek-chat）；但与审计声明的免费网关配置不一致（G 类候选） |
| 账号余额 | 08-09 充足（72/72）；08-13 耗尽（402）；08-12 10:52–12:30 连接失败与余额无直接证据关联 |
| 连通性 | 08-09 稳定；08-12 10:52 后间歇性连接失败（191/192） |

## 10. 结论（事实分层）

- **FACT**：两轮执行同一 judge 代码路径与同一批参数；失败形态为连接层
  异常；审计声明与重建配置存在端点/模型不一致；今日网关可用、付费端点
  402。
- **OBSERVATION**：4.2-R 失败是时间窗口现象（10:52–12:30 间歇性连接
  失败 + 1 次恢复）；余额耗尽时点晚于最后一次成功，不解释连接失败。
- **HYPOTHESIS**（未证实）：对端边缘对高频连接的节流/封锁表现为连接
  重置；或本地网络路径在该时段不稳定；或进程实际连接端点与重建不同。
- **UNKNOWN**：08-12 运行期进程实际端点（无端到端日志）；"Connection
  error." 的底层子因；08-12 期间账号与网关状态。
