# ACIS 交付清单填写与审计报告（2026-10-24）

> 审计对象：`E:\knowledge_database\ACIS` @ `main` HEAD `6420e34`（2026-10-24 13:11）
> 审计分支：`work/20261024-delivery-audit`　｜　审计时间：2026-10-24 14:02–15:10（Asia/Hong_Kong）
> 审计方式：3 条独立证据线（流程实测 / 指标复算 / 环境与故障静态审计）+ Lead 交叉复核；
> **未调用付费 LLM、未访问外网**；Docker 不可用，容器路径为静态核验。
> 工作树原有未提交改动（5 个被跟踪文件 + `reports/phase6_ablation_20261024/` + `tests/fixtures/`）非本审计所为，审计未触碰、未纳入结论。
> 证据副本：本目录 `evidence/`（18 个文件）；原始输出：`logs/delivery_audit_20261024/`（gitignored）。

---

## 一、交付清单（填写结果）

| # | 交付项 | 判定 | 能否勾选 | 一句话结论 |
|---|---|---|---|---|
| 1 | **核心流程可运行** —— 从真实输入到最终输出完整打通，不依赖人工修改中间数据 | **PASS** | ✅ 可勾选 | 单条命令即可从真实中文咨询跑出诊断/置信度/行动计划/落库，统一 Trace 10/10 阶段齐全，CLI/API/TUI 三条入口均实测通过 |
| 2 | **环境可复现** —— 按 README 在干净环境启动；依赖、配置和模型凭证要求清楚 | **PARTIAL** | ⚠️ 有条件 | 干净副本可用现有 venv 离线跑通；但依赖无锁定、无 `.env.example`、Judge/opencode 凭证链未文档化、Docker 与本地版本不一致、README 状态与数字过期 |
| 3 | **故障可解释** —— 超时、连接失败、回退和无效输出有可追踪的记录 | **PARTIAL** | ⚠️ 有条件 | 四类指定故障均有 reason_code + trace 字段 + 日志 + 脱敏，8 类故障实测通过；但持久化/LangGraph 回退/采样失败等旁路仍静默，交互式运行不落 trace 文件 |
| 4 | **效果可验证** —— 固定测试集、明确标签、原始结果和评测脚本能够相互对应 | **PARTIAL** | ⚠️ 有条件 | 24+64 例测试集与标签、评分代码、baseline 指标基本可复算；但 Phase 6 关键信号（agreement）只存在于 gitignored trace，分析脚本/生成器未入库，报告数字存在文档错误，闭环不完整 |
| 5 | **技术取舍可解释** —— 能说明为什么需要检索、规则或 Agent，以及它们带来的实际收益和代价 | **PARTIAL** | ⚠️ 有条件 | 设计动机、消融数据、运行/Token 成本、被否证方案均有记录（本报告 §2.5 已汇总成一页可讲稿）；但架构级收益未被证明（C1 ≤ C0、记忆注入有害），不能以"收益已验证"口径勾选 |
| 6 | **演示可完成** —— 有一段 3–5 分钟演示，包含正常任务、证据追溯和异常处理 | **PASS**（本次补齐 runbook） | ✅ 可勾选 | TUI 6 场景实测跑通（12.2s 出完整链路），CLI 9s 出全量裁决；本次新增 `docs/DEMO_RUNBOOK.md` 固化 3–5 分钟脚本与异常处理演示 |

**总体结论**：**2 项可勾选、4 项有条件（PARTIAL）、无 FAIL**。
当前状态适合"研究原型演示 / 内部验收"，不适合以"架构有效性已被证明"或"干净环境一键复现"的措辞交付；按 §四 的 P0 清单整改后，第 2、3、4 项可转为 PASS。

---

## 二、逐项审计

### 2.1 核心流程可运行 —— ✅ PASS

**要求拆解**：真实输入 → 完整链路（感知→记忆→专家→辩论→Critic→Judge）→ 最终输出（裁决/置信度/行动建议/持久化），全程无人工改中间数据。

**实测证据（离线、零真实 API）**

| 检查 | 命令/方法 | 结果 |
|---|---|---|
| 规则路径端到端 | `orchestrator.py --rules-only "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"` | exit 0；8.55s；`decision=病理判断首选：番茄叶霉病`；`judge_mode=rules`；`confidence=0.72`；12 个 Agent；6 条行动建议；`decision_id` 已落 SQLite |
| LangGraph 默认路径 | `orchestrator.py "<同句>"` | exit 0；9.06s；同裁决；多出一轮辩论（15 条 Agent trace）；`confidence=0.74` |
| 统一 Trace | 进程内读 `orchestrator.last_trace` | 规则 19 事件 / LangGraph 22 事件；**10/10 阶段齐全**（request, perception, memory, experts, debate, critic, judge, planner, tool_router, metrics），`required_stages_missing=[]`（`trace/types.py:36-47`、`trace/collector.py:222-262`） |
| Plan→Tool 全链路 | 开 `ACIS_ENABLE_PLANNER=1` 补测 | 离线可跑：`required_tools` 3 项、tool_router 3 条请求 0 未解析、1.45s |
| HTTP API | `TestClient` GET `/health`、POST `/diagnose` | 200 / 200；`/diagnose` 7.55s，返回 decision/judge_mode/confidence/traces/action_plan/judge_runtime（`gateway/app.py:24-42`） |
| 回归脚本 | `evals/smoke_eval.py`、`evals/fixture_eval.py` | 均 exit 0；30.98s / 28.56s；3 套×3 场景通过；12/12 fixture 通过 |
| 单元测试 | `python -m pytest -q`（沙箱 TEMP 重定向） | 规范命令 `1 failed / 286 passed / 44 errors`；44 errors 为沙箱 `0o700` 目录 ACL、1 failed 为沙箱禁止子进程管道；用仅存在于证据目录的 ACL shim 复跑得 **3 failed / 328 passed**，3 个失败仍全是子进程管道 → **代码级失败 = 0**（331 用例 / 23 个测试文件） |
| 无人工改中间数据 | 全流程复跑 4 个独立进程 | 同输入结果一致（`0.72/medium/12`），无任何手改文件步骤 |

**判定理由**：真实输入、单条命令、完整链路、结构化输出与持久化均已实测；RAG/KG 不可用时自动降级且不阻断。README 宣称的核心链路真实存在且可跑。

**条件与局限**
- Planner / Tool Router **默认关闭**，需 `ACIS_ENABLE_PLANNER=1`（`planner/planner.py:187-195`），README 未写该开关。
- 本机存在系统代理时，localhost 服务会被劫持为 502，需设 `NO_PROXY`；否则 RAG 静默回退（不崩，但少一层能力）。
- 统一 Trace 只存在于进程内（`orchestrator.last_trace`），CLI/HTTP/TUI 均无出口（见 §三-G3）。

---

### 2.2 环境可复现 —— ⚠️ PARTIAL

**结论**：**核心链路在干净副本可离线跑通（PASS 面）；但"按 README 在干净环境重建等价环境"不成立（缺口面）。**

| 分项 | 判定 | 关键证据 |
|---|---|---|
| A1 依赖与凭证声明 | **PARTIAL（高）** | `requirements.txt` / `requirements.docker.txt` 全为 `>=` 下界，仅 `mcp` 有上界（`requirements.txt:5`）；无 lock / `pyproject.toml` / `.env.example`；README「环境准备」仅 4 行、无 venv 创建与 `.env` 步骤（`README.md:92-104`）；**`AGRI_AI_JUDGE_*`、`AGRI_AI_MEMORY_GATE*`、`AGRI_AI_DB_PATH` 等 10+ 变量未文档化**；`.env` 中 `OPENCODE_*` 无任何代码读取（死配置），opencode 网关只能经 `AGRI_AI_JUDGE_*` 配置，README 未说明映射 |
| A2 干净副本自包含 | **PASS（核心）/ PARTIAL（完整）** | `git archive HEAD` 导出干净副本（无 `.env`/`data`/`results`/`logs`），用现有 venv 解释器：rules-only 3.78s、LangGraph 2.05s 均出决策，`data/agri.db` 自动创建；视觉真实推理需 HF 缓存、真实 Judge 需凭证、Qdrant/Neo4j 可选 |
| A3 Docker / 启动脚本 | **PARTIAL** | 端口 8000/17474、Neo4j 密码、healthcheck、`DEEPSEEK_API_KEY` 透传与 README 一致；但 `Dockerfile:2` 为 **python:3.11-slim** vs 本地 3.13.3；compose 未透传 `AGRI_AI_JUDGE_*`/`NO_PROXY`；`start.ps1/sh` 的 `NO_PROXY` 只作用于宿主 shell（README:242「已自动处理」对 CLI 误导）；Neo4j APOC 首次启动需联网；`neo4j:community`、`qdrant:latest` 浮动 tag |
| A4 README / 审计文档时效 | **FAIL** | README 仍写 2026-09-20 / 267 passed / 18 测试文件 / 处于 Phase 4.2-R（实际 331 用例 / 23 文件 / Phase 6 + ADR-005）；judge 端点债务已于 10-19 解除但 README 仍列为已知债务；`IMPLEMENTATION_AUDIT.md` 仍写 189/222/267 passed、ruff/mypy 未安装、`src/` 为空（实际已有 `src/openmetaphysics/` 代码） |
| A5 无后端 / 无 key 降级 | **PARTIAL** | 离线可启动并出决策；Judge 降级有 `outcome/fallback_reason_code/missing_evidence/日志`；RAG/KG/传感器/校准器降级有字段；但 RAG/KG/SQLite 降级**无日志**，VisionAgent 读错字段导致"图像→未知类别"静默 |

**判定理由**：清单要求"按 README 在干净环境启动；依赖、配置和模型凭证要求清楚"。实测干净副本能跑，但依赖不可锁定、凭证链不完整、README 过期，因此不能判 PASS。

---

### 2.3 故障可解释 —— ⚠️ PARTIAL

**要求拆解**：超时、连接失败、回退、无效输出 → 有可追踪记录。

**逐类实测（本地桩，无真实 LLM；均为 `judge_mode=rules` + `outcome=fallback` + `fallback_reason_code` + trace 内同一 `judge_runtime` + WARNING 日志 + 假 key 不泄漏）**

| 故障类型 | reason_code | 记录位置 | 实测 |
|---|---|---|---|
| 无凭证 | `missing_credentials` | judge_runtime / missing_evidence / WARNING | ✅ |
| 认证失败 401/403 | `authentication_error` | 同上（含 HTTP 401 原文，已脱敏） | ✅（401） |
| 计费 402 | `billing_error` | 同上 | ✅（单测覆盖） |
| 限流 429 | `rate_limit` + `retry_exhausted` | 同上 | ✅（429） |
| 超时 | `timeout` + `retry_exhausted` | 同上 | ✅（本地桩 sleep） |
| 连接失败 | `connection_error` + `retry_exhausted` | 同上 | ✅（桩断连；设 `NO_PROXY` 后） |
| 无效输出（非 JSON/空/缺字段/越界） | `response_format_error` | 同上 | ✅（非 JSON、空响应） |
| 5xx | `server_error` | 同上 | ✅（500；未设 NO_PROXY 时 127.0.0.1:9 被代理 502 掩盖为 server_error） |
| 显式 rules-only | `disabled_by_configuration` | 同上 | ✅ |

- 分类实现：`utils/judge_runtime.py:117-144`（10 个稳定 code）；脱敏：`judge_runtime.py:191-219`（`sk-`/Bearer/api_key/掩码、截断 300 字符）；日志三行链：`judge_agent.py:354-362`（INFO 请求）→ `:370-377`（ERROR 异常）→ `:145-154`（WARNING 回退）。
- Trace 写入：`trace/collector.py:72-87,190-191` 把 `judge_analysis`（含 `judge_runtime`）写入 judge 事件；故障注入实测 `trace_has_reason=True`。
- 历史闭环：2026-08-13 定位 191/216 回退（`reports/phase4_2_real_agent/diagnosis_judge_fallback.md`）→ 10-17 修复（`reports/phase4_evaluation_reliability_repair.md`）→ 10-18 401 可观测（`blocked_precheck_report.md`）→ 10-19 恢复 6/6 zero fallback（`judge_recovery_report.md`），**Judge 故障链已闭环**。

**为什么不是 PASS —— 仍会静默失败的路径（按严重度）**

| # | 路径 | 文件:行 | 影响 | 严重度 |
|---|---|---|---|---|
| 1 | SQLite 持久化失败被吞 | `orchestrator.py:157-162` | 决策无 `decision_id`/无审计记录，接口仍成功，无日志 | 中 |
| 2 | LangGraph 执行失败只写一句 `missing_evidence` | `orchestrator.py:140-149` | 无 reason_code/无日志，`judge_runtime` 仍显示 rules/disabled，无法区分"图坏了"与"没开 LLM" | 中 |
| 3 | 自一致性采样失败只计数 | `agents/judge_agent.py:486-517` | 只有 `failures/samples_used`，不分类（timeout?429?格式?）、无日志 | 中 |
| 4 | gateway `/diagnose` 无异常边界、`/health` 静态 | `gateway/app.py:31-42` | 未捕获异常→500 裸响应；健康检查不反映降级 | 中 |
| 5 | VisionAgent 读错结果字段 | `agents/vision_agent.py:20` vs `agents/vision.py:155-165` | 有图时静默"未知类别"，无 warning | 中 |
| 6-12 | RAG 静默回退、KG error 丢弃、记忆读库失败伪装无历史、`propose_triple` 静默、JSON 解析静默、`retry_exhausted` 语义不精确 | `rag/retriever.py:252-267`、`kg_adapter.py:210-246,396-442`、`agents/case_memory_agent.py:41-42`、`storage/repository.py:63-69`、`judge_agent.py:136-138` | 排障信息缺失 | 低 |

**另外两项结构缺口**
- **Trace 不落盘**：只有 `evals/runner.py:217-243` 在 `--save-traces`（默认关）时导出；CLI/HTTP/TUI 无 per-run trace 文件。
- **评测指标不含 fallback**：`evals/metrics.py:49-92`、`evals/report.py:33-50` 无 `judge_mode`/`judge_fallback_rate` 列，与 2026-10-17 指标契约 A1 不符；challenge 链（`scripts/run_challenge_evaluation.py:230`、`challenge_report.py:110-176`）已实现。

---

### 2.4 效果可验证 —— ⚠️ PARTIAL

**固定测试集与标签（PASS 面）**

| 名称 | 案例 | 标签 | 路径/加载 |
|---|---|---|---|
| Challenge Set v1 | 24（4 组×6） | `ground_truth` 24/24、`expected_key_factors` 2–5/例、`design_intent` 24/24、crop/intent/difficulty；**无 capability** | `benchmarks/challenge_set_v1.json`；`scripts/run_challenge_evaluation.py:128` 独立加载 |
| easy/medium/hard + 5 能力套件 + enriched | 64（12/10/6 + 18 + 18） | `ground_truth` 64/64、`capabilities` 52/64、`observable_evidence`、`design_intent` | `benchmarks/datasets/*.json` |
| 汇总 | 64（9 数据集） | 24 例 id 与 64 例零冲突；34 个因子全部在 `FACTOR_ALIASES` | `benchmarks/loader.py` |

**复算结果（用已提交评分代码 + 独立脚本，对照报告表格）**

| 数据/配置 | 报告 accuracy | 复算 | 报告 ECE | 复算 | 报告 corr | 复算 |
|---|---|---|---|---|---|---|
| baseline C0 | .833（20/24） | ✅ | .373 | .3729 ✅ | .249 | .2491 ✅ |
| baseline C1 | .792（19/24） | ✅ | .339 | **.3758 ❌（区间分箱 .3392 ✅）** | .155 | .1546 ✅ |
| baseline C2 | 1.000（24/24） | ✅ | .502 | .5021 ✅ | n/a | None ✅ |
| SC seed42 | .846（11/13） | ✅ | .0769 | **.0741/.1268 ❌** | .778 | **−.1231 ❌** |
| SC seed43 | .792（19/24） | ✅ | .0708 | **.175 ❌** | .538 | **.5078 ❌** |

- 基线 3×8 指标中 **23/24 精确可复算**；C1 ECE 差异根因已定位：已提交 `challenge_scorer.py:154` 用 `int(conf/bin_size)`，`0.3/0.1=2.9999…→2` 的浮点边界 bug；报告用的是区间分箱。
- SC 两跑的 ECE/corr **不能**用 committed raw 复算：报告用的是 `confidence := min(0.95, agreement)`，agreement 只存在于 **gitignored trace**；从 traces 重建后 **ECE .076923/.070833、corr .7785/.5379 与报告逐位吻合** → 报告数字诚实，但交付物不闭合。
- `baseline_analysis.md:6` 声称「84/84 Judge 调用」，实际 manifest/run log 为 **72**。
- `reports/phase6_ablation_20261024/raw_results_c0c2_seed43.json`（未跟踪 WIP）C0/C2 均 9/24、无报告 → **不可作为交付证据**。

**可追溯性**
- case_id ↔ trace_id：baseline 72/72、SC 24/24、SC43 24/24、ablation 48/48 全部在本机 `logs/` 找到，decision/confidence 逐条一致；168 条记录与数据集字段 0 不一致。
- 但 `git ls-files results/` 与 `git ls-files logs/` 均为空（`.gitignore:37,40`），`data/` 也忽略 → **traces、metrics.csv、per-case raw 不随仓库交付**。
- Phase 6 bundle 无 `dataset_sha256`；指纹机制只落在 ignored `results/`。

**脚本入库性缺口**
- G1 Phase 6 `{manifest,results}` bundle 生成器未入库；G2 无被跟踪脚本消费 `reports/phase6_*/raw_results.json`；G3/G4 `logs/final_eval.py`、`analyze_baseline.py`、`restricted_eval.py` 等确为 gitignored，报告数字无入库脚本可复现；G5 全仓无已提交 corr 实现；G6 `reports/phase4_evaluation_pilot.md` 与当前报告器 schema 漂移；G7 `evals/runner.py` CLI 无 `--llm-judge`。

**离线实测**
- `evals/runner.py --dataset benchmarks.datasets.enriched --rules-only`：18 例 40.0s、accuracy **0.4444（8/18）**、两次一致、零 API；与文档声称的 accuracy=1.00 不可比（后者依赖 Qdrant/Neo4j + 真 Agent）。
- 文档数字错误：`CHALLENGE_SET_V1_REPORT.md:62` 难度 d2/d3 实为 9/13（声称 10/12）；`:26`「49 个带 GT」实为 64/64；README:99 的 1.00 未标注运行条件。

**判定理由**：数据集、标签、评分代码、原始结果三者"物理上存在且大多能对上"，但"原始结果 ↔ 报告数字"在 Phase 6 关键指标上依赖未入库中间量，评测脚本链不完整，因此 PARTIAL。

---

### 2.5 技术取舍可解释 —— ⚠️ PARTIAL

**已有的解释材料**
- `MODEL_AGENT_ORCHESTRATION.md:3-11`：明确的编排原则——"便宜、确定、可解释优先"：规则/小模型先处理窄任务 → 专家 Agent 聚合证据 → Debate 只比较证据冲突 → Judge 最终裁决（必要时 LLM）→ 任一模型失败回退规则 + 人工复核。
- `docs/ARCHITECTURE_DECISIONS.md:160-224`（ADR-005）：记录了三处缺陷、最终方案、**被否证方案**（结构信号 + isotonic 校准 ECE 0.013 但 corr −0.005，属"ECE 好看、判别力归零"；13 样本 isotonic 后处理更差，故设 50 样本门槛）以及自一致性采样"调用 ×k、时长 ×k"的代价。
- 消融：`results/ablation/enriched/20260801_150917/REPORT.md`（7 组合，accuracy 全 1.0，Δ=0；runtime all_on 0.032s vs 关闭后 0.012–0.017s；memory_hits 31→0）；能力分数随模块开关归零（E008）。
- 真实 Judge 基线：`reports/phase6_baseline_20261023/baseline_analysis.md`（C0 0.833 / C1 0.792 / C2 1.000；ECE .34–.50；corr .155–.249；false abstention 3/4/0；单例 43.7/54.6/42.5s、9.3k/11.0k/9.6k tokens）。
- 自一致性收益：`reports/phase6_redesign_20261023/final_evidence.md`（agreement 分层 .333/.600/.938，ECE .071–.077、corr .538–.778——但复算需 trace，见 §2.4）。

**一页式取舍说明（可直接用于答辩）**

| 组成 | 为什么需要（设计意图） | 实测收益 | 实测代价 |
|---|---|---|---|
| 规则引擎 / 主链 | 确定性、离线、低延迟，作为一切故障的回退底座 | 单次 1.4s（预热后）、0 Token；Phase 4.2-R 191/216 次 Judge 回退时系统仍可用 | accuracy 有天花板；误弃权（C0 3 例、C1 4 例） |
| RAG / KG 检索 | 注入病害知识与硬约束，把"生成"锚定到可核对证据 | memory_hits 31（enriched 消融）；KG 硬约束可触发否决；`kg_backend/backend` 可审计 | 在 Challenge Set 上 C1（开记忆）19/24 vs C2（关记忆）24/24，5 例翻转；seed43 未复现 C2 优势；低置信检索注入噪声 → ADR-005 增加记忆门控 |
| 多 Agent / Debate / Critic | 交叉证据、暴露冲突、降权可疑专家，提升可解释性 | 冲突可见、Critic 降权在 fixture 的 2 个场景触发；能力分数可由 trace 自动打分 | 消融 accuracy Δ=0（数据饱和）；真实 LLM 路径单例 43–55s；多一轮辩论增加时延；capability 分数是"自证"指标 |
| LLM Judge | 结构化融合与置信度输出，处理规则写不出的歧义 | 10-19 恢复验证 6/6 `judge_mode=deepseek`、零回退；输出结构化 reasoning/action_plan | 9–11k tokens/例；网络/凭证故障面大（历史 191/216 回退） |
| 自一致性 k=3 | 唯一被证明有判别力的置信度信号（agreement 越高越准） | agreement 分层 0.0→33%、0.5→60%、1.0→94%（seed43） | Judge 调用 ×3；seed43 单例均值 134s；n=24 仍小 |
| 置信度校准 | 让"置信度"可解释、可判定弃权 | 校准后 ECE 达标（但判别力需一致率信号） | 13 样本 isotonic 会压成常数 → 设 50 样本门槛；当前生产路径实际"一致率直出" |

**为什么不是 PASS**
- "实际收益"证据是混合/负向的：**C1（完整架构）在 Challenge Set 上未优于 C0（裸基线）**，R3 排名跨 seed 翻转，记忆注入被证明有害；`final_evidence.md:54-60` 自述"accuracy 未提升…决策质量本身没有变好"。
- 缺少一份单一文档把上述取舍与数字串起来（本报告 §2.5 是首次汇总）。
- 若以"收益已被证明"口径勾选第 5 项，会与仓库自身证据冲突；建议口径：**"设计取舍可解释；规则/检索保证可运行与可审计；Agent/LLM 的架构级增益尚未被证明"**。

---

### 2.6 演示可完成 —— ✅ PASS（本次补齐 runbook）

**既有能力（实测）**
- TUI 6 个演示场景（`ui/tui.py:73-122`；README 写 5 个，过期）：番茄叶霉病诊断 / 灌溉-病害冲突（Critic 反驳降权）/ 甜菜褐斑病 / 棉花枯萎病 / 环境预警 / 高湿病害 vs 低湿环境（诊断存疑）。
- 非交互实测 `python -m ui.tui`（stdin 重定向 `"1\n\nq\n"`）：exit 0、12.2s、24,444B 输出，完整走完 菜单 → Agent 执行轨迹（逐行动画）→ ★最终裁决 → 辩论与反驳 → KG 锚定裁决分析 → 行动建议 → 退出；含 `judge_mode`、置信度条、KG 后端、`reasoning_trace`（`ui/tui.py:268-292,393-457,503-509`）。
- 无 key 时 `[j]/[c]` 明确拒绝；Judge 失败自动回退规则并在"缺失证据"区显示回退文案；`random.seed(7)` 保证演示可复现（`ui/tui.py:495`）。
- CLI 内置 demo `python orchestrator.py`（无参数）9.02s 出 2 个完整裁决；`POST /diagnose` 200 可演示 API。

**演示短板与本次补齐**
| 短板 | 本次处理 |
|---|---|
| 无脚本化 demo、无预置输入序列 | 新增 `docs/DEMO_RUNBOOK.md`：0–5 分钟逐段时间轴、两条终端命令、正常任务/证据追溯/异常处理演练、兜底预案 |
| 统一 Trace 无可视化（TUI 的"轨迹"是 `decision.traces`，不是 10 阶段 Trace） | runbook 给出 `python -c` 一行命令打印 `trace_id/stages_present/judge_runtime`，作为"证据追溯"环节 |
| LLM Judge 演示未离线验证、TUI 不展示 `fallback_reason_code` | runbook 明确默认讲离线规则版；异常处理环节用故障注入命令展示 `fallback_reason_code` + 日志 |
| 本机代理坑（未设 `NO_PROXY` 时 RAG 502） | runbook 前置检查写死 `NO_PROXY` |
| README 宣称"<1s"实测 1.4–2.7s | runbook 按实测节奏排 2–3 个场景，不承诺 <1s |

**判定理由**：演示链路本身可用且实测跑通；本次补 runbook 后，"正常任务 + 证据追溯 + 异常处理"三要素齐备，3–5 分钟可完成。

---

## 三、全局发现（影响多项）

| # | 发现 | 影响 | 证据 |
|---|---|---|---|
| G1 | **工作树 ≠ HEAD**：5 个被跟踪文件未提交（`decision_semantics.py`、`evals/metrics.py`、`challenge_report.py`、`tests/test_challenge_evaluation.py`、`tests/test_metrics.py`）+ 未跟踪 `reports/phase6_ablation_20261024/`、`tests/fixtures/` | 交付态不可复现/评审基线不明确 | `git status`（审计开始时即存在） |
| G2 | README 状态与数字过期（267→331 用例、18→23 文件、5→6 场景、<1s、Phase 4.2-R→Phase 6、judge 债务已解除） | 第 2/4 项判据受损 | `README.md:9,13,15,22-23,159,161,194` |
| G3 | 统一 Trace 无 CLI/HTTP/TUI 出口；SQLite 不存 Trace；仅评测 `--save-traces` 落盘 | 第 3/6 项可观测性卖点打折 | `trace/exporter.py:17-53`、`evals/config.py:51`、`gateway/app.py`、`ui/tui.py` |
| G4 | `results/`、`logs/`、`data/` 全 gitignored | 原始结果/trace/指标不随仓库交付，全新 clone 无法完整复核 | `.gitignore:20,37,40` |
| G5 | 本机系统代理劫持 localhost（Qdrant 502 / Judge 误判 server_error） | 故障分类与 RAG 能力依赖 `NO_PROXY` | `start.ps1:17-20`、`docs` 实测 |
| G6 | Phase 6 seed43 WIP 结果（C0/C2 均 9/24）与 seed42 差异极大且无报告 | 不可作为证据；提示小样本方差风险 | `reports/phase6_ablation_20261024/` |
| G7 | 评分函数浮点分箱 bug（`challenge_scorer.py:154`） | ECE 口径不一致，报告数字难复算 | §2.4 |
| G8 | GT 判分为子串包含，否定语境可"白送分"（实测 20/72 条病名只出现在"需排除…"中仍判对） | 第 4 项标签严格性风险 | `decision_semantics.py:62-72` |
| G9 | `ui/tui.py:221` 明文打印 Neo4j 密码 | 低危（README 已公开该 dev 密码），但不应硬编码 | `ui/tui.py:221` |
| G10 | 无 `pytest.ini`/`pyproject.toml`；根目录遗留不可列举目录会让 README 的 `pytest -q` 收集中断 | 一键复现脆弱 | 实测 `pytest-of-lkl` |
| G11 | `smoke_eval` 第三套标称 llm-judge 但回退 rules 仍判 pass；`retry_exhausted` 与实际重试预算无关（MAX_RETRIES=0 仍 true） | 测试/字段语义有盲区 | `evals/smoke_eval.py:37,76-81`、`judge_agent.py:136-138` |

---

## 四、最小整改清单（交付前）

### P0（对应第 2/3/4 项，建议优先）
1. **README 事实校正 + 凭证文档**：更新状态/用例数/场景数/延迟/Phase 6；补 `AGRI_AI_JUDGE_*`、`AGRI_AI_MEMORY_GATE*`、`AGRI_AI_DB_PATH`、`ACIS_ENABLE_PLANNER` 说明；新增 `.env.example` 并写明 `OPENCODE_* → AGRI_AI_JUDGE_*` 映射；把"Docker/NO_PROXY/APOC 需联网/data 需预置"写成前置条件。
2. **依赖可复现**：增加 `requirements.lock`（或 pin 主版本）；`Dockerfile` 对齐 Python 3.13；compose 透传 `AGRI_AI_JUDGE_*`、`NO_PROXY`；镜像 tag 固定版本。
3. **Phase 6 证据闭环**：把 `logs/final_eval.py`、`analyze_baseline.py` 及 bundle 生成器提升为 `scripts/`；每条 raw 记录补 `agreement`、`dataset_sha256`、`scorer_commit`；修正 `baseline_analysis.md` 84→72、挑战集难度 9/13、"49 个 GT"措辞。
4. **静默失败三处**：`_persist` 失败 warning + DecisionOutput 标记；LangGraph 回退写入 reason_code/日志；self-consistency 失败用 `classify_failure` 分类并记日志；`evals/runner` 指标补 `judge_mode/judge_fallback_rate`。
5. **指标修复**：`challenge_scorer.py:154` 分箱边界；补一个入库的 `corr(conf,correct)` 实现；明确否定语境计分（`excluded_labels`/`acceptable_alternatives`）。

### P1（增强可信度）
6. Trace 出口：CLI 增加 `--trace-out` 或 `--json` 内含 trace_id/stages；TUI 展示 `judge_runtime.outcome/fallback_reason_code`。
7. 修 `VisionAgent` 字段名错误并加 warning；RAG/KG 回退各加一行 warning。
8. 演示机固定 `NO_PROXY`；在 TUI 状态条显示 RAG 后端与降级原因。
9. 删除根目录遗留 `pytest-of-lkl` 等不可列举目录，加 `pytest.ini`（testpaths 限定 `tests`）。

### P2（卫生）
10. 不再明文打印 Neo4j 密码；统一用 env。
11. `reports/phase4_evaluation_pilot.md` 按当前 schema 重新生成。
12. 清理/归档 `results/` 与 `logs/` 的本地产物策略，在交付说明中声明"结果不随仓库"。

---

## 五、证据索引与复现

**本目录（已入库）**
- `evidence/flow_evidence.md`：第 1/6 项实测全记录（243 行）+ 同目录原始 JSON 摘要
- `evidence/eval_AUDIT_REPORT.md`：第 4 项复核（清点/复算/缺口）+ `eval_recompute_results.json`
- `evidence/env_A_env_reproducibility.md`：第 2 项审计（A1–A5）
- `evidence/env_B_fault_explainability.md`：第 3 项审计（8 类故障矩阵 + 12 条静默路径）
- `evidence/env_clean_run_probe.json`、`env_fault_injection_probe.json`、`flow_orchestrator_probe.json`、`flow_fault_injection.json`、`flow_fastapi_probe.json`、`flow_timing_probe.json`、`eval_report_signal_mapping.json` 等原始证据

**本机原始输出（gitignored，复跑时生成）**
- `logs/delivery_audit_20261024/flow/`（pytest 5515 行原始输出、TUI 24KB 渲染、故障注入 stdout/stderr、计时等 81 个文件）
- `logs/delivery_audit_20261024/eval/`（recompute.py、trace 互查、challenge 报告重生成等）
- `logs/delivery_audit_20261024/env/`（干净副本 `clean/`、`acis_head.tar`、135 包基线）

**关键代码位置**
- 主链：`orchestrator.py:112-201`；Trace：`trace/types.py:36-47`、`trace/collector.py:72-87,190-191,222-262`、`trace/exporter.py:17-53`
- Judge 故障链：`agents/judge_agent.py:119-166,354-377,486-517`；`utils/judge_runtime.py:67-219`
- 评测：`src/openmetaphysics/evaluation/challenge_scorer.py:114-167`、`challenge_report.py:110-176,442-470`、`scripts/run_challenge_evaluation.py:128,230`
- 取舍依据：`MODEL_AGENT_ORCHESTRATION.md:3-11`、`docs/ARCHITECTURE_DECISIONS.md:160-224`、`results/ablation/enriched/20260801_150917/REPORT.md:19-47`、`reports/phase6_baseline_20261023/baseline_analysis.md`、`reports/phase6_redesign_20261023/final_evidence.md`

**复现命令（离线、零真实 API）**
```powershell
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONPATH='.'; $env:NO_PROXY='localhost,127.0.0.1'
$py='E:\knowledge_database\ACIS\.venv\Scripts\python.exe'
& $py orchestrator.py --rules-only "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"
& $py evals/smoke_eval.py
& $py evals/fixture_eval.py
& $py evals/runner.py --dataset benchmarks.datasets.enriched --rules-only
& $py -m pytest -q            # 注意本机沙箱 ACL：见 evidence/flow_evidence.md §1
# 故障注入（演示"回退可解释"）
$env:AGRI_AI_JUDGE_API_KEY='sk-test'; $env:AGRI_AI_JUDGE_BASE_URL='http://127.0.0.1:9'
$env:AGRI_AI_JUDGE_TIMEOUT_SECONDS='10'; $env:AGRI_AI_JUDGE_MAX_RETRIES='0'
& $py orchestrator.py --rules-only --llm-judge --json "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"
```

---

## 六、审计边界

- 未调用真实 LLM/外网；第 1 项的真实 LLM 路径证据引用历史已验证记录（`reports/phase4_judge_recovery_20261019/judge_recovery_report.md`：6/6 `judge_mode=deepseek`、零回退）与 Phase 6 baseline（72 次真实 Judge 调用）；本轮未复跑付费调用。
- Docker 不可用：容器路径仅静态核验（版本/环境变量/healthcheck/依赖透传）。
- pytest 的 44 errors / 3 failed 为**沙箱环境**（`0o700` 目录 ACL、禁止子进程管道），已用 ACL shim 隔离验证；不是代码缺陷，但说明 README 的 `pytest -q` 在受限环境脆弱。
- 评测样本小（Challenge Set n=24，Phase 6 仅 2 seeds），本报告不对"架构有效性"下统计结论；只核对其"可复现/可解释"。
- 工作树中并行会话的未提交改动（5 个文件 + 2 个未跟踪目录）未纳入审计结论，但已在 §三-G1 登记为交付风险。

---

## 七、结论与建议口径

- **可勾选**：第 1 项（核心流程）、第 6 项（演示，配合新增 `docs/DEMO_RUNBOOK.md`）。
- **有条件勾选**：第 2、3、4、5 项；建议在交付说明中同时写明限定条件（P0 整改项），不要无标注勾选。
- **不建议的口径**：①"完整架构优于裸基线"（证据不支持 C1 > C0）；②"干净环境按 README 一键复现"（依赖未锁定、凭证链不完整）；③"所有故障都可追踪"（仍有 5 条中危静默路径）；④"效果已闭环可复算"（Phase 6 关键信号在 gitignored trace 中）。
- **推荐交付叙事**：*"ACIS 是可运行、可降级、可审计的农业决策研究原型：规则主链保证离线可用与确定性回退；检索/KG 提供可核对的领域证据；多 Agent 与 LLM Judge 提供证据聚合与结构化解释；我们公开记录了置信度链路的缺陷与修复（ADR-005）、以及架构级收益尚未证明的负向结果。"*
