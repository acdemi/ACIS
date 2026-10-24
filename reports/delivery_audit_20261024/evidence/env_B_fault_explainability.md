# B 项 — 故障可解释性审计（ACIS @ work/20261024-delivery-audit）

> 审计员：env-auditor（task-3）｜时间：2026-10-24 14:07–14:30 (+08:00)
> HEAD：`6420e34`｜解释器 Python 3.13.3｜只读源码 + 本地桩故障注入（无真实 LLM/外网）
> 证据：`fault_injection_probe.json`（8 类故障实测）、`probe_fault_injection.py`（复跑脚本）、`clean_run_probe.json`

## 结论速览

| 故障类型 | 记录位置 | 是否可追踪 |
|---|---|---|
| 无凭证 / key 缺失 | `judge_analysis.judge_runtime.fallback_reason_code=missing_credentials`；`debate.missing_evidence`；WARNING 日志 | ✅ 实测通过 |
| 认证失败 401/403 | `=authentication_error`（含 HTTP 401 原文，已脱敏） | ✅ 实测通过（401） |
| 计费 402 / 余额不足 | `=billing_error` | ✅ 单测覆盖（test_judge_runtime.py:216-228） |
| 限流 429 | `=rate_limit` + `retry_exhausted=true` | ✅ 实测通过（429） |
| 超时 | `=timeout` + `retry_exhausted=true` | ✅ 实测通过（本地桩 sleep） |
| 连接失败 | `=connection_error` + `retry_exhausted=true` | ✅ 实测通过（桩中途断连 → `APIConnectionError`） |
| 无效输出（非 JSON / 空响应 / 缺字段 / 置信度越界） | `=response_format_error` | ✅ 实测通过（非 JSON、空响应） |
| 5xx 服务端错误 | `=server_error` | ✅ 实测通过（500） |
| 其他 HTTP / 未知 provider 错误 | `=api_http_error` / `provider_error` | ✅ 分类存在（utils/judge_runtime.py:140-144） |
| 显式 rules-only | `outcome=rules` + `fallback_reason_code=disabled_by_configuration` | ✅ clean 副本实测 |

所有 8 类实测均为：`judge_mode=rules`、`outcome=fallback`、`fallback_reason_code` 存在、**trace 的 judge 事件内携带同一 `judge_runtime`**（`trace_has_reason=True`）、**假 key 未泄漏**（`key_leaked=False`）、均有 `WARNING agents.judge_agent Judge fallback: code=...` 日志行。

## B1 Unified Trace 是否记录 judge_runtime / 每阶段事件 / 可导出落盘 — **PASS（记录）/ PARTIAL（落盘）**

- **每阶段事件**：`trace/types.py:36-47` 定义 10 个 stage（request/perception/memory/experts/debate/critic/judge/planner/tool_router/metrics）；`trace/collector.py:222-262 collect_pipeline_trace()` 逐阶段记录；每事件 `TraceEvent` 冻结并深拷贝（types.py:63-83）。
- **judge_runtime 是否进 trace**：是。`trace/collector.py:190-191 record_judge()` → `_serialize_decision()`（collector.py:72-87）把整个 `decision.judge_analysis`（含 `judge_runtime`，judge_agent.py:82-84）与 `token_usage`（collector.py:85-86）写入 judge 事件 payload。实测 `trace_judge_runtime` 与 decision 内完全一致。
- **token_usage**：成功路径写入 `decision.token_usage`（judge_agent.py:402,450）与 `judge_runtime.token_usage`（judge_agent.py:77-78,451-458）；fallback 路径无 usage（合理）。
- **导出**：`trace/exporter.py:17-53 trace_to_dict()/export_trace_json()`；但**只有评测 runner 落盘**——`evals/runner.py:234-243`，且 `--save-traces` 默认关闭（`evals/config.py:51`；CLI `evals/runner.py:328-332`）。
- **缺口**：`orchestrator.py` CLI（276-280）与 `gateway/app.py:36-42` **不导出/不落盘**统一 Trace；SQLite 只存 agent 输出、debate、judge_analysis（`storage/repository.py:14-38`，表结构 storage/db.py:15-38），**不存** Trace 的 stages/events。即：交互式使用没有 per-run trace 文件；trace 文件只在评测脚本/`--save-traces` 时存在。

## B2 Judge 失败分类 / 重试 / 脱敏 / 日志 — **PASS**

- 配置解析与优先级：`utils/judge_runtime.py:67-114 resolve_judge_config()`（`AGRI_AI_JUDGE_*` → `DEEPSEEK_*` → 默认；timeout 上限 300s、retries 上限 5）。
- 失败分类：`utils/judge_runtime.py:117-144 classify_failure()`，共 10 个稳定 code（missing_credentials / response_format_error / authentication_error / billing_error / rate_limit / timeout / connection_error / server_error / api_http_error / provider_error）。
- 脱敏：`_SECRET_PATTERNS`（judge_runtime.py:27-32）覆盖 `sk-…`、`Bearer …`、`api_key: …`、掩码 key 后缀；`redact_error_detail()`（207-219）截断 300 字符；`sanitize_endpoint()`（191-204）去掉 user-info/query/fragment；`public_metadata()`（55-64）只暴露 provider/endpoint/model/timeout/retries/sources。实测 8 类故障序列化后均不含假 key。
- 重试归属：`_run_llm_judge` 只发一次 SDK 调用（judge_agent.py:367-368），重试交给 OpenAI SDK 预算；`retry_exhausted` 在 judge_agent.py:136-138 对 connection/timeout/rate_limit/server_error 置 true。
- 日志：请求 INFO（judge_agent.py:354-362）、异常 ERROR（370-377）、成功 INFO（403-409）、回退 WARNING（145-154，含 code/provider/endpoint/model/sdk_max_retries/detail）。
- 回退可解释链：`debate.missing_evidence.append("LLM Judge 不可用…[reason_code]…")`（141-144）→ 经 `_serialize_debate`（collector.py:59-65）进入 trace 的 debate 事件；`judge_runtime` 进 judge 事件。

## B3 evals 指标是否反映 fallback / 是否保留 per-case 错误 — **PARTIAL**

- `evals/metrics.py:49-92 compute_trace_metrics()` 的 `CaseMetrics`（27-47）**没有** judge_mode / fallback 字段；`aggregate_metrics()`（95-122）也没有 fallback 率；`evals/report.py:33-50 CSV_FIELDS` 无 judge_mode / fallback_reason_code 列。→ **evals/runner 路径无法从 metrics.csv/summary.md 看出该 run 是否回退**。
- 但另一条评测链（Phase 4/6 challenge）已实现该契约：`scripts/run_challenge_evaluation.py:230-231` 把 `judge_analysis.judge_runtime` 写入 per-case raw；`src/openmetaphysics/evaluation/challenge_report.py:155-176 _fallback_state()` + 聚合字段 `judge_fallback_rate / judge_fallback_known / judge_fallback_unknown / judge_modes / fallback_reasons`（challenge_report.py:110-114）；测试 `tests/test_challenge_evaluation.py:423-463`、`tests/test_stability_metric_contract.py:29-38`。
- 这与 2026-10-17 指标契约的要求不完全一致：`reports/phase4_evaluation_metric_contract_audit.md:51-53` 明确"结果必须按 judge_mode 分层并伴随 fallback rate"，其 A1 实现点名 `evals.metrics.compute_trace_metrics`——但该文件至今未实现（仅 challenge_report 实现）。**这是交付项 3 的指标层缺口**。
- per-case 错误保留：runner 的 `metrics.csv` 无错误列；原始错误只能从 `--save-traces` 的 trace（debate.missing_evidence）或 challenge 脚本的 per-case raw JSON 读到。

## B4 仍会静默失败的路径清单（文件:行 + 影响 + 严重度）

| # | 路径 | 证据（文件:行） | 影响 | 严重度 |
|---|---|---|---|---|
| 1 | SQLite 持久化失败被吞 | `orchestrator.py:157-162`（`except Exception: pass`） | 决策无 `decision_id`、无审计记录，接口仍返回成功；无任何日志/字段 | **中** |
| 2 | LangGraph 主图执行失败只写 `missing_evidence` | `orchestrator.py:140-149` | 无 reason_code、无 `judge_runtime` 字段、无日志；trace 仅 debate 事件里有中文文字，`judge_runtime.outcome` 仍是 rules/disabled，无法区分"图坏了"与"没开 LLM" | **中** |
| 3 | self-consistency 采样失败只计数 | `agents/judge_agent.py:486-517`（`except Exception: failures += 1`） | 只有 `confidence_design.self_consistency.failures`/`samples_used`；不分类（timeout? 429? 格式错?）、无日志；全部失败时 agreement=None→置信度封顶 0.65+人工复核（状态可辨，原因不可辨） | **中** |
| 4 | gateway `/diagnose` 无异常边界；`/health` 静态 | `gateway/app.py:31-33, 36-42` | 任何未捕获异常 → 500 裸响应，无 trace_id/错误码；健康检查不能反映 Judge/Neo4j/Qdrant 降级 | **中** |
| 5 | VisionAgent 读错结果字段 | `agents/vision_agent.py:20`（`top_prediction`）vs `agents/vision.py:155-165`（返回 `diagnosis`） | 有图像时静默变成"未知类别"/置信度 0，且**无 warning**（用户以为视觉已工作） | **中** |
| 6 | RAG `retrieve()` 静默回退 | `rag/retriever.py:252-267` | 后端异常被吞、无日志；Agent 走 `retrieve_with_backend` 才把 `backend=fallback`+`error` 放进 evidence（`agents/rag_memory_agent.py:9-13`），但不进 judge_runtime | 低 |
| 7 | KG/Neo4j 连接异常被吞、error 被丢弃 | `kg_adapter.py:210-246`（`_neo4j_available/_get_driver/_query_neo4j` 全静默）、`396-442`；`judge_agent.py:338,450` 只保留 `backend` | trace 只能看到 `backend=memory`，看不到"Neo4j 不可达/查询失败/无命中"的具体原因，无日志 | 低 |
| 8 | 记忆层 SQLite 读失败伪装成"无历史" | `agents/case_memory_agent.py:41-42`、`agents/outcome_agent.py:17-18` | 读库异常 → 空结果，置信度 0.3，用户无法区分"确实没有"与"库坏了" | 低 |
| 9 | KG 草稿写入失败静默 | `kg_adapter.py:460-477`（`except Exception: return None`） | `propose_triple` 失败与"幂等跳过"不可区分 | 低 |
| 10 | `get_decision` JSON 解析失败静默 | `storage/repository.py:63-69` | 返回原始字符串字段，不报错 | 低 |
| 11 | `retry_exhausted` 语义不精确 | `judge_agent.py:136-138` | 按异常类别置 true，与实际重试预算无关（实测 `AGRI_AI_JUDGE_MAX_RETRIES=0` 时仍为 true），可能误导排障 | 低 |
| 12 | Planner/LangGraph import 失败静默降级 | `orchestrator.py:196-201` | 属设计降级，但无日志说明"为什么用了规则路径" | 低 |

说明：1-5 中，#1/#2/#3 直接影响"故障可解释"的完整性（评测/审计场景）；#4 影响 API 使用者；#5 是功能性静默错误。其余为可接受的降级，但都缺少一行 warning 日志。

## B5 历史故障 → 根因 → 修复/遗留 是否闭环 — **PASS（Judge 链已闭环，旁路未审计）**

| 时间 | 事件 | 证据 |
|---|---|---|
| 2026-08-13 | Phase 4.2-R：191/216 次 judge 回退 rules，统一 `APIConnectionError("Connection error.")`；当时只有 `str(exc)` 写入 missing_evidence，无 reason_code；建议记录异常类型/原因 | `reports/phase4_2_real_agent/diagnosis_judge_fallback.md:8-34, 86-97, 224-251` |
| 2026-10-17/18 | 修复：`utils/judge_runtime.py` 集中配置 + 10 类失败码 + 脱敏 + `judge_runtime` 元数据 + SDK 重试归属；指标契约审计定义 fallback rate/分层；全量回归 307 passed | `reports/phase4_evaluation_reliability_repair.md:9-43`；`reports/phase4_evaluation_metric_contract_audit.md:38-160, 264-274` |
| 2026-10-18 | 新可观测性生效：真实 trace 记录 `judge_mode=rules`、`outcome=fallback`、`fallback_reason_code=authentication_error`、HTTP 401；因凭证无效判 BLOCKED（未伪造成功） | `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md:49-56, 139-142` |
| 2026-10-19 | 凭证更新后 6/6 预检 `judge_mode=deepseek`、零回退、零 authentication_error；trace 记录 outcome=success + token usage | `reports/phase4_judge_recovery_20261019/judge_recovery_report.md:1-6, 54-56` |
| 遗留（未闭环） | ① harness 与真实链路 INCOMPARABLE（口径对齐仍开放，judge_recovery_report.md:64-66）；② factor-scorer 回退无法 per-case 归因（metric audit:282-284）；③ evals/runner 无 fallback 指标（本报告 B3）；④ RAG/KG/持久化降级从未纳入可解释性审计（本报告 B4） | 同上 |

结论：**Judge 故障链已闭环**（机制定位→可观测性修复→真实恢复验证）；**评测层 fallback 记账部分闭环**；**旁路降级（RAG/KG/SQLite/LangGraph）仍缺结构化记录**。

## B6 测试覆盖 — **PARTIAL**

- `tests/test_judge_runtime.py`（9 个测试）覆盖：配置优先级（:19）、成功元数据 + key 不泄漏（:123-150）、连接失败回退（:162-177）、无凭证回退且不建 client（:180-197）、无效 JSON 回退（:206-213）、失败分类参数化 6 类（:216-228）、掩码 key 脱敏（:231-237）、真实 SDK MockTransport 成功（:240-299）、非法 timeout 边界（:302-304）。
- `tests/test_trace.py`（16 个测试）覆盖 stage 顺序/不可变/深拷贝/planner on-off/导出 JSON（:138-309），**没有**断言 judge 事件携带 `judge_runtime`/`fallback_reason_code`（本次实测确认行为正确，但缺回归保护）。
- 另：`tests/test_challenge_evaluation.py:423-463, 539-548, 723-726` 覆盖 challenge 报表的 fallback rate/reason；`tests/test_stability_metric_contract.py:29-38` 覆盖稳定性报表的 fallback 分层。
- **未覆盖**：self-consistency 采样失败路径、`_persist` 失败、LangGraph 回退原因、RAG/KG 降级记录、gateway 异常响应。

---

## B 项总判定：**PARTIAL**

- 交付项 3 明确列举的"超时、连接失败、回退、无效输出"四类：**全部有 reason_code、写 trace、落日志、且实测可追踪（PASS）**。
- 但"故障可解释"作为整体仍有多条静默路径（B4 的 1-5），且评测指标层（evals/runner）没有 fallback 维度、交互式运行不落 trace 文件。故判 **PARTIAL**。

## 最小整改建议（按优先级）

1. **（高，交付项 2）** 补依赖锁定 + `.env.example`：加 `requirements.lock`（或 pin 主版本）与 `.env.example`；README「环境准备」补 `.env` 创建步骤与全部 `AGRI_AI_JUDGE_*` 说明，并写明 `OPENCODE_API_KEY/BASE_URL → AGRI_AI_JUDGE_API_KEY/BASE_URL` 的映射（或让 `judge_runtime` 直接读取 `OPENCODE_*`）。并统一 Dockerfile 基础镜像与本地 Python 版本（3.13）。
2. **（高，交付项 3）** 消除 B4-1/2/3 静默：`_persist` 失败 `logger.warning` 并在 DecisionOutput 标记；LangGraph 回退写入 `judge_runtime`/trace 事件（reason_code=graph_execution_error）；self-consistency 失败用 `classify_failure` 计数并记日志。
3. **（中，交付项 3）** evals/runner 指标补 `judge_mode` + `judge_fallback_rate`（对齐 phase4 指标契约 A1），metrics.csv 增列；在 README「测试与评估」注明 `--save-traces` 才落 trace。
4. **（中，交付项 2/3）** Docker：compose 透传 `AGRI_AI_JUDGE_*` 与 `NO_PROXY`；README 注明 Neo4j APOC 首次启动需联网、`./data` 需预先存在；`/health` 增加 `judge_configured`/后端字段或单独 `/ready`。
5. **（低）** 修 VisionAgent 字段名（`diagnosis`）并加 warning；RAG/KG 回退各加一行 warning 日志（含 backend+error），使 trace 之外的运维日志也可解释。
