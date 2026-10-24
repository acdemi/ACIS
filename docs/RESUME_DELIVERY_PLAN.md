# ACIS 转向简历交付：只读盘点与最小交付路径

> 日期：2026-10-24　｜　分支：`work/20261024-resume-delivery-plan`（基于上一轮审计分支 `d4197f3`）
> 本轮性质：**只读盘点 + 转向方案**。未修改任何产品代码、未新增 Phase、未 push/merge。
> 依据：上一轮交付审计 `reports/delivery_audit_20261024/DELIVERY_CHECKLIST.md` + 本轮仓库复查（HEAD `6420e34`、工作树、目录、依赖、入口与测试）。
> 目标：**复用现有资产，形成一个可运行、可演示、可复现、可写进简历的农业 AI 项目**；不再以补齐 Phase/通用智能体架构为目标。

---

## 0. 结论摘要（TL;DR）

1. **现有系统已具备一个可交付的完整业务闭环**：自然语言病害咨询 → 诊断/置信度/风险/行动建议 → 证据链（Agent 轨迹 + KG 校验 + 辩论/Critic）→ SQLite 落库；CLI、TUI、FastAPI 三条入口均实测可用。**不需要重写**。
2. **最值得投入的交付场景是"温室番茄病害诊断与处置建议"**（辅以"灌溉与病害冲突"演示 Critic）。理由：知识库覆盖最好（番茄 2 病）、测试与 demo 覆盖最多、TUI 场景 1/2 已打磨。
3. **真正阻塞交付的不是功能，而是"可复现的工程外壳"**：README 过期、依赖未锁定、无 `.env.example`、`pytest -q` 脆弱、Trace 无出口、5 处静默失败、工作树有未提交 WIP、证据（agreement/traces/分析脚本）未入库。
4. **建议的最小交付路径约 2.5–3.5 个工作日**：M0 冻结基线（0.5d）→ M1 修 5+2 个核心缺陷（1d）→ M2 一键可复现评测（0.5d）→ M3 演示与简历材料（0.5–1d）→ M4 可选环境加固（0.5d）。
5. **必须停止扩张**：Phase 5/6、新 Agent/记忆/校准、World Model、RFC/ADR 治理、AG-DISTILL 小麦知识蒸馏支线、真实 AgriKG/Qdrant/视觉升级、Web 前端扩展。

---

## 1. 仓库现状快照（本轮复查）

| 项 | 现状 | 备注/证据 |
|---|---|---|
| 代码 HEAD | `main` = `6420e34`（2026-10-24 13:11） | 上一轮审计在该基线上完成 |
| 当前分支 | `work/20261024-delivery-audit`（审计提交 `750886c`/`d4197f3`）→ 本轮新建 `work/20261024-resume-delivery-plan` | 审计分支未合并；本轮基于它以保证审计报告在树内 |
| 工作树 | 5 个被跟踪文件未提交 + `tests/fixtures/`、`reports/phase6_ablation_20261024/` 未跟踪 | 来自并行会话；测试 `test_challenge_evaluation.py:633` **依赖** `tests/fixtures/` |
| 代码规模 | 125 个 Python 文件 / 25,486 行（不含 `.venv`/缓存/本地数据） | 组件不算少，但可运行核心约 15 个模块 |
| 测试 | 23 个 `test_*.py` / 331 用例；上轮实测 328 passed，3 个失败均因沙箱禁止子进程管道 | 无 `pytest.ini`；根目录遗留 `pytest-of-lkl/` 会让 `pytest -q` 收集中断 |
| 依赖/解释器 | `.venv` Python 3.13.3；135 个包；`requirements.txt` 全为 `>=` 下界、无 lock | 见 `reports/delivery_audit_20261024/evidence/env_A_env_reproducibility.md` |
| 本地数据 | `data/` 264MB（含 `Agriculture_KnowledgeGraph-master` 245MB）、`logs/` 76MB、`results/` 57MB | 全部 gitignored，不随仓库交付 |
| 文档 | `docs/` 33 个 md（Sprint 报告占多数）、`reports/` 109 个文件、`context/` 31 个文件 | README 状态停留在 2026-09-20，Phase 6 未反映 |
| 分支 | 17 条历史 `work/*` 未清理 | 合并/删除需用户授权 |

**已实测可用的运行基线（上一轮，零真实 API）**
- 规则路径 8.55s / LangGraph 9.06s（冷启动），预热后 1.4–1.7s；统一 Trace 10/10 阶段；SQLite `decision_id` 落库。
- `evals/smoke_eval.py`（3 套×3 场景）与 `evals/fixture_eval.py`（12 场景）通过；`evals/runner.py --rules-only` 离线跑 18 例 40s。
- TUI 6 场景，非交互回放场景 1 用时 12.2s，输出完整（Agent 轨迹→裁决→辩论→KG 分析→行动建议）。
- FastAPI `GET /health` / `POST /diagnose` 200；`/decisions`、`/feedback`、`/outcome` 已实现（`gateway/app.py:45-88`）。
- 故障注入：8 类 Judge 失败均有 reason_code/trace/日志/脱敏，进程正常回退规则。

---

## 2. 业务场景盘点

### 2.1 系统实际支持的能力

| 维度 | 现状 |
|---|---|
| 作物/病害知识 | **4 作物 / 7 病害**：番茄（叶霉病、早疫病）、黄瓜（霜霉病）、甜菜（褐斑病、根腐病）、棉花（黄萎病、枯萎病），`rag/knowledge_base.py:34` |
| 意图 | `diagnose` / `irrigate` / `alert` / `monitor` / `consult`（`orchestrator.py:64-73`） |
| 输入 | 中文自然语言（症状/环境/管理问题）+ 可选图片路径（视觉为 mock/可选真实模型）+ 模拟传感器/天气数据 |
| 输出 | 首选结论、置信度、风险等级、是否需人工复核、行动计划、辩论共识/冲突、KG 校验、`reasoning_trace`、决策 ID |
| 入口 | CLI（`orchestrator.py`）、TUI（`ui/tui.py`，6 场景）、FastAPI（`gateway/app.py`）、Streamlit Web UI（`ui/web_app.py`，未文档化/未验证） |
| 外部依赖 | 无 Neo4j/Qdrant/API key 均可降级运行；真实 LLM Judge 为可选增强（有 key 时启用） |

### 2.2 建议的 MVP 业务场景（唯一验收场景）

> **"温室番茄病害诊断与处置建议"**
> 输入示例：`温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？`
> 输出：首选病害（叶霉病）+ 鉴别/排除依据 + 置信度 + 风险等级 + 是否需人工复核 + 6 条处置建议 + 证据链（Agent 轨迹、KG 一致性、辩论/Critic 结果）+ 决策落库 ID。
>
> 辅助演示场景（不新增代码）：`温室A番茄叶背灰色霉层，今天需要浇水吗？要兼顾病害风险` → 展示 Debate/Critic 冲突与降权。

**选它的理由**：知识库/测试/demo 覆盖最高；输出结构化、可讲清楚；离线可跑、无需真实 LLM；与"农业 AI 工程"简历叙事匹配。

**MVP 明确不做**：黄瓜/甜菜/棉花的专项验收（代码保留兼容）；图片真实识别；真实传感器接入；真实 LLM 作为必选路径；多轮对话/长期学习；Web 前端作为交付必需项。

---

## 3. 组件五级分类与处置

> 分类依据：上一轮实测 + 本轮代码/测试/文档引用检查。"保留"= 纳入交付并冻结；"修复"= 必须处理；"暂缓"= 保留代码但不投入；"停止"= 不再扩展；"清理"= 可删除/归档（需授权）。

### A. 已实现且实际可运行（**保留**）

| 组件 | 证据 | 处置 |
|---|---|---|
| `orchestrator.py` + `workflow.py`（LangGraph 主图 + 规则回退） | 双路径 e2e 实测；10/10 Trace 阶段 | 保留，冻结接口 |
| `agents/` 感知（视觉 mock/传感器/天气）、记忆（RAG/KG/案例/经验回放）、专家（病理/气象/栽培/经济/生态） | 单次 12–15 条 Agent 轨迹 | 保留，不加新 Agent |
| `debate/` + `agents/judge_agent.py`（规则 Judge；LLM Judge 可选） | Critic 在 2 个 fixture 场景触发；8 类故障回退实测 | 保留 |
| `trace/`（10 阶段统一 Trace、`export_trace_json`） | 实测 19/22 事件、阶段齐全 | 保留；补出口（M1） |
| `storage/` + `gateway/app.py`（SQLite 决策审计 + 反馈/结果回灌） | `/diagnose` 200、`decision_id` 落库 | 保留 |
| `ui/tui.py`（6 场景演示） | 非交互回放完整通过 | 保留；小修显示项（M1） |
| `evals/smoke_eval.py`、`evals/fixture_eval.py` | 均 exit 0；确定性 12 场景 | 保留，作为 MVP 回归基线 |
| `benchmarks/` + `evals/runner.py`（64 案例、能力打分） | 离线 18 例 40s；测试覆盖 | 保留，不扩数据集 |
| `rag/knowledge_base.py` + `rag/retriever.py`（7 病/4 作物、内存回退、Qdrant 可选） | 离线可用；`backend=fallback` 可审计 | 保留 |
| `kg_adapter.py`（Neo4j 优先 + DISEASE_DB 兜底） | 本地 Neo4j 实测 `kg_backend=neo4j`；无服务时 memory | 保留 |
| `rule_engine/sensor_anomaly.py`（规则 + IF/LSTM/Chronos 降级） | 降级链完整 | 保留 |
| `planner/` + `tool_router/`（默认关闭，`ACIS_ENABLE_PLANNER=1` 开启） | 单测通过；开启后离线可跑 | 保留但**不作为 MVP 必需项** |
| `utils/judge_runtime.py`、`decision_semantics.py` | 8 类失败码 + 脱敏；语义判分契约 | 保留 |
| `experiments/`（实验管理/指纹/统计） | 单测通过 | 保留，不投入扩展 |

### B. 已实现但缺乏验证（**暂缓，按需修复**）

| 组件 | 问题 | 处置 |
|---|---|---|
| LLM Judge / Critic 真实路径 | 10-19 历史验证 6/6 zero fallback，但无当前自动化测试；需 key/网络 | 保留为可选增强；MVP 不依赖 |
| `ui/web_app.py`（Streamlit，276 行） | README 未提、无测试、未实测启动 | 暂缓；不纳入 MVP（TUI 足够） |
| `kg/mcp_server.py`（独立 MCP Server） | 无测试、需单独进程启动；主链走 `kg_adapter` | 暂缓 |
| 视觉真实推理（`agents/vision.py`） | 默认 mock；`VisionAgent` 读错字段（`vision_agent.py:20` vs `vision.py:155-165`） | 若 MVP 含图片则必修；否则 M1 顺手修字段+warning |
| Qdrant 后端 | 可选服务；本地实测可用但无回归测试 | 暂缓（内存回退已够） |
| Docker 部署路径 | 仅静态核验；`Dockerfile` 3.11 vs 本地 3.13；compose 未透传 `AGRI_AI_JUDGE_*`/`NO_PROXY` | M4 可选修复 |
| `gateway`/`storage` 直接单测 | 只有 e2e 探针，无单测 | 可接受；M2 加最小 API 冒烟测试 |
| Phase 6 自一致性/校准 | 仅 2 seeds；指标不可由 committed raw 复算 | 保留为"研究记录"，**不写进简历核心指标** |

### C. 部分实现（**暂缓/不扩展**）

- `OPENCODE_*` 配置：`.env` 有但代码不读取（死配置）；真实网关只能经 `AGRI_AI_JUDGE_*` 配置。
- 真实 AgriKG 导入：`scripts/import_agrikg.py` + 本地 245MB 数据存在，但 clean clone 无数据。
- Chronos/LSTM/IsolationForest 预测：仅降级占位，无真实模型。
- 置信度校准生产路径：样本 <50 时禁用（`DecisionCalibrator`）。
- 多作物知识：`CROP_MAP` 有 7 种，但 DISEASE_DB 仅 4 种。
- Web UI：有页面骨架，未验证/未文档化。

### D. 只有接口或设计（**停止扩张**）

- RFC-011~014（认知环/自我模型/目标动机/Agent 生态）：已归档，不实现。
- World Model（ADR-002 预留接口，ACIS 3.0）：不实现。
- RFC-003 Agent 协议（生命周期/能力声明）：未实现，不实现。
- Phase 5 扩展评测 / Phase 6 进一步架构重设计：暂停。
- 预测增强（Chronos/statsmodels/传感器第三层/`prediction_uncertainty`）：不实现。

### E. 已无实际使用价值 / 应清理（**需授权后处理**）

| 对象 | 说明 | 建议 |
|---|---|---|
| `codex/`（5 文件，2 个 0 字节） | AI 会话残留 | 归档/删除（需授权） |
| 根目录 `phase4_2_*.txt`（12 个）、`phase4_1_pilot_results.json` | 旧运行状态快照，与 `reports/` 重复 | 归档/删除（需授权） |
| `scripts/phase0_check.py` | 一次性旧脚本，无人引用 | 删除（需授权） |
| `pytest-of-lkl/`、`torchinductor_lkl/`、`data/.fuse_hidden*` | 本地缓存/挂载残留 | 清理（安全，需授权） |
| `IMPLEMENTATION_AUDIT.md`、`REVIEW_REPORT.md` | 2026-08 历史审阅，数字已过期 | 移至 `docs/archive/`（需授权） |
| 17 条历史 `work/*` 分支 | 已合并/未合并混杂 | 需用户决定 |
| AG-DISTILL 支线（`scripts/*t2*.py`、`reports/ag-distill-*`、`docs/knowledge/…`） | 小麦赤霉病知识蒸馏，独立课题 | **移出本交付范围**（不删除） |

---

## 4. 保留成果清单（简历可直接使用）

1. **端到端多智能体决策链**：Perception → Memory → Experts → Debate → Critic → Judge，LangGraph 主图 + 规则回退。
2. **农业领域知识资产**：4 作物/7 病害知识库（症状/病原/环境条件/防治）、KG 三元组与硬约束、案例/经验回放。
3. **可解释决策输出**：置信度、风险、人工复核、行动建议、辩论冲突、KG 一致性、`reasoning_trace`。
4. **统一 Trace（10 阶段）+ SQLite 决策审计**：每个结论可回溯。
5. **可靠性工程**：8 类 LLM 故障分类、密钥脱敏、自动回退、降级链（Neo4j/Qdrant/视觉/校准）。
6. **评测基础设施**：64 案例 benchmark、24 案例 Challenge Set、7 组合消融、7 能力打分、多 seed 实验管理。
7. **三入口交付形态**：CLI、TUI（6 场景）、FastAPI（诊断/历史/反馈/结果回灌）。
8. **演示材料**：`docs/DEMO_RUNBOOK.md`（3–5 分钟脚本）、上一轮交付审计报告（可证明工程严谨性）。
9. **真实实验结论（含负向）**：完整架构未优于规则基线（C1 0.792 vs C0 0.833）、记忆注入有害、置信度校准失败模式——面试中可作为"如何做实验/如何诚实报告"的素材。

---

## 5. 必须修复的问题（按优先级）

### P0 — 不修则 MVP 不成立（约 1.5 天）

| # | 问题 | 位置/证据 | 修复内容 | 验收 |
|---|---|---|---|---|
| P0-1 | **工作树未冻结**：5 个被跟踪文件未提交 + `tests/fixtures/` 未跟踪，而新测试依赖 fixtures | `git status`；`tests/test_challenge_evaluation.py:633` | 审查 WIP（confidence 契约校验 + fixtures），确认后提交为冻结基线；若不要则回退并删除依赖测试 | `git status` 干净；`pytest -q` 可复现 |
| P0-2 | **README 不可按图施工**：状态/数字过期，缺环境变量与 `.env` 说明 | `README.md:9,15,92-104,159,161,180-189,194` | 重写"状态/快速开始/环境变量/评估"四节；补 `.env.example`；修正 267→331、5→6、`<1s`→1.4–2.7s、Phase 6 状态 | 新环境按 README ≤10 分钟跑通 |
| P0-3 | **依赖不可锁定** | `requirements.txt`、`requirements.docker.txt` | 生成 `requirements.lock`（`pip freeze` 子集或 `pip-compile`）；README 增加锁文件用法 | 新 venv 安装后关键包版本与当前一致 |
| P0-4 | **`pytest -q` 不可一键执行** | 无 `pytest.ini`；根目录 `pytest-of-lkl/` 权限不可读 | 加 `pytest.ini`（`testpaths=tests`、`norecursedirs`）；清理根目录残留 | `python -m pytest -q` 从仓库根一次通过 |
| P0-5 | **证据不可追溯（演示卖点缺失）** | Trace 仅在 `orchestrator.last_trace`；CLI/HTTP/TUI 无出口（`trace/exporter.py:17-53`） | CLI 增加 `--trace-out`（或 `--json` 输出 trace_id/stages）；TUI 显示 `judge_runtime.outcome/fallback_reason_code` | 一条命令输出 trace_id + 10 阶段 + judge 元数据；演示可现场追溯 |
| P0-6 | **故障可解释有静默路径** | `orchestrator.py:157-162`（持久化）、`:140-149`（LangGraph 回退）、`judge_agent.py:486-517`（采样失败） | 加 `logger.warning` + 结构化字段（`fallback_reason_code`）；不改变主逻辑 | 故障注入命令输出可见原因；日志可读 |
| P0-7 | **可复现实验缺失** | `evals/` 有脚本但无"一条命令 + committed 结果" | 新增 `scripts/run_delivery_eval.py`：跑 smoke(3×3)+fixture(12)+固定 CLI 场景，写 `reports/delivery_eval/{summary.json,summary.md}` 并提交 | 重跑结果与 committed 完全一致；README 一条命令可复现 |

### P1 — 明显提升交付质量（约 0.5–1 天，可与 P0 合并）

| # | 问题 | 位置 | 修复 |
|---|---|---|---|
| P1-1 | `experiments/archive.py:66` 只兜 `FileNotFoundError/TimeoutExpired`，子进程管道失败会抛错 | `experiments/archive.py:58-66` | 兜 `OSError` 并返回空串，与 docstring 一致 |
| P1-2 | `challenge_scorer.py:154` 浮点分箱 bug；全仓无 corr 实现 | `src/openmetaphysics/evaluation/challenge_scorer.py:154` | 改为 `min(bins-1, int(conf*bins))` 或显式区间；决定是否补 corr（若不用于简历可只修 bug） |
| P1-3 | VisionAgent 字段名错误 | `agents/vision_agent.py:20` | 改为读 `diagnosis`；无图/失败加 warning |
| P1-4 | Docker 不一致 | `Dockerfile:2`、`docker-compose.yml:19-26,59` | 3.13 基础镜像；透传 `AGRI_AI_JUDGE_*`/`NO_PROXY`；固定镜像 tag；README 注明 APOC 需联网 |
| P1-5 | 演示材料不完整 | — | TUI 截图/GIF；`docs/RESUME_PROJECT.md`；README 首屏"项目一句话 + 3 条命令" |

---

## 6. 可暂缓 / 应停止扩张

**暂缓（保留代码，不投入）**：真实 LLM Judge 作为必选路径、Streamlit Web UI、`kg/mcp_server.py`、Qdrant 真实向量检索、真实 AgriKG 导入、真实视觉模型、Docker 部署（除非面试要求）、多作物扩写。

**停止扩张（不再新增/重构）**：
- Phase 5 扩展评测 / Phase 6 架构重设计 / 任何新 Phase；
- 新增 Agent、专家、记忆、校准、治理、审批层；
- 为文档一致性批量改写 RFC/ADR/Sprint 报告；
- AG-DISTILL 小麦知识蒸馏支线（`scripts/*t2*`、`reports/ag-distill-*`）；
- 新增 benchmark 数据集/挑战集/消融组合；
- 以"组件数量/测试数量/代码行数"作为交付目标。

**判断标准**：任何新工作必须能回答"它是否让 MVP 的 4 条叙事（能跑/能复现/能演示/能讲清楚）更强？"答否即不做。

---

## 7. 最小交付路径（M0–M4）

> 总计约 **2.5–3.5 个工作日**；M0–M3 为必须，M4 可选。每个任务结束按用户要求报告：修改文件 / 实现功能 / 测试真实结果 / 未完成项 / 下一项。

### M0 冻结基线（0.5 天）

- 任务：P0-1（WIP 审查与提交）、P0-3（锁依赖）、P0-4（pytest.ini）、P0-2 的 README 事实校正、`.env.example`。
- 交付：干净工作树 + 可从 clone 启动的 README + 锁文件 + `pytest.ini`。
- 验收：`git status` 干净；`pytest -q` 一次通过；`orchestrator.py --rules-only` 出决策。

### M1 核心缺陷修复（1 天）

- 任务：P0-5（Trace 出口/TUI 展示）、P0-6（3 处静默失败）、P1-1/P1-3；为每项补最小测试。
- 交付：可演示的"证据追溯"与"故障可解释"。
- 验收：`--trace-out` 产出 trace 文件；故障注入命令输出 reason_code + missing_evidence；新增测试通过。

### M2 可复现实验（0.5 天）

- 任务：P0-7（`scripts/run_delivery_eval.py` + committed 结果）、README 评估章节、固定测试口径（12 fixture + 3×3 smoke + 2 条端到端）。
- 交付：一条命令复现的 `reports/delivery_eval/summary.{json,md}`。
- 验收：连续两次运行输出一致；新环境可复现；文档写明"不包含真实 LLM/外部服务"。

### M3 演示与简历材料（0.5–1 天）

- 任务：TUI 演示彩排 + 截图/GIF；更新 `docs/DEMO_RUNBOOK.md`；写 `docs/RESUME_PROJECT.md`（场景/架构/选型/实测/限制/复现命令）；README 首屏精简。
- 交付：3–5 分钟可稳定演示 + 一份诚实、可核对的简历项目说明。
- 验收：按 runbook 完整彩排 2 次通过；简历每条声称都能对应到命令或报告。

### M4 可选环境加固（0.5 天）

- 任务：P1-4 Docker、干净 clone 自动验证脚本、清理 E 类垃圾（需授权）。
- 仅在 M0–M3 完成后有余力时做；不做不影响 MVP。

---

## 8. MVP 验收条件（可执行）

| # | 验收项 | 命令 | 通过标准 |
|---|---|---|---|
| AC-1 | 规则路径端到端 | `python orchestrator.py --rules-only "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"` | exit 0；输出诊断/置信度/风险/6 条建议；SQLite 有 `decision_id` |
| AC-2 | LangGraph 默认路径 | `python orchestrator.py "同上"` | exit 0；同诊断；Trace 10/10 阶段 |
| AC-3 | TUI 演示 | `python -m ui.tui` → 场景 1、2 | 30s 内完成；显示 Agent 轨迹、裁决、Critic/证据、回退信息（若触发） |
| AC-4 | API | `uvicorn gateway.app:app` + `POST /diagnose` | 200；返回 decision/confidence/traces/judge_analysis |
| AC-5 | 测试 | `python -m pytest -q` | 0 failed / 0 errors（普通 Windows 环境；沙箱限制单独记录） |
| AC-6 | 回归 | `python evals/smoke_eval.py`、`python evals/fixture_eval.py` | 均 exit 0；12/12 fixture 通过 |
| AC-7 | 可复现实验 | `python scripts/run_delivery_eval.py` | 输出与 committed `reports/delivery_eval/` 完全一致 |
| AC-8 | 故障可解释 | 按 runbook 的故障注入命令 | exit 0；`fallback_reason_code`/`missing_evidence`/日志齐全；密钥不泄漏 |
| AC-9 | 环境 | 按 README 从干净副本启动 | ≤10 分钟完成；仅需 `.env`（可选 key）；无需 Neo4j/Qdrant |
| AC-10 | 文档 | README + `docs/RESUME_PROJECT.md` + `docs/DEMO_RUNBOOK.md` | 声称与实测一致；无"accuracy 1.00/架构优于基线/<1s"等表述 |
| AC-11 | 演示 | 按 runbook 3–5 分钟 | 正常任务 + 证据追溯 + 异常处理三要素齐全 |

---

## 9. 简历材料与口径

### 9.1 建议的项目一句话

> 面向温室作物病害诊断的多智能体决策支持原型：以规则主链保证离线可用，以多专家辩论与知识图谱约束提升可解释性，配套统一追踪、故障回退与可复现评测。

### 9.2 可写进简历的要点（均已实测或可复现）

- 设计并实现 **LangGraph 多智能体决策流水线**（感知/记忆/专家/辩论/Critic/Judge），规则回退保证离线可用；单次决策预热后 1.4–2.7s。
- 构建 **4 作物/7 病害知识库 + KG 硬约束校验**，输出诊断/置信度/风险/行动建议与完整证据链。
- 实现 **统一 Trace（10 阶段）+ SQLite 决策审计 + FastAPI 服务**，支持反馈与结果回灌。
- 实现 **8 类 LLM 故障分类、脱敏与自动回退**，故障注入验证服务不中断。
- 搭建 **64 案例 benchmark + 24 案例 Challenge Set + 7 组合消融 + 能力打分**；如实记录完整架构未优于规则基线（C1 0.792 vs C0 0.833）并定位置信度校准失效模式。
- 交付 **TUI 演示、3–5 分钟演示脚本、12 场景固定回归与一键复现实验**。

### 9.3 明确不要写

❌ "准确率 1.00 / SOTA / 生产级"；❌ "完整架构优于基线"；❌ "真实田间数据验证"；❌ "自主进化/持续学习"；❌ "LLM Judge 始终可用"；❌ "每次决策 <1s"。

### 9.4 面试问答准备（建议写入 `docs/RESUME_PROJECT.md`）

| 问题 | 要点 |
|---|---|
| 为什么规则 + Agent 混合，而不是端到端 LLM？ | 成本/时延/可解释/离线可用；规则是可回退底座；LLM 只在需要结构化融合时可选启用。 |
| 多 Agent 真的更好吗？ | 不声称更好；定位为可解释的证据聚合。Challenge Set 上 C1 未优于 C0，已如实记录。 |
| 效果怎么验证？ | 固定 12 场景 fixture + 24 案例挑战集 + 64 案例 benchmark；区分"离线可复现"与"真实 LLM 条件"。 |
| 怎么保证可靠性？ | 8 类故障分类 + 自动回退 + 脱敏 + 决策审计；已知静默路径在审计报告中列出。 |
| 你个人做了什么？ | 按交付清单逐项自证：入口/评测/可观测性/故障处理/文档；避免"团队项目"式空话。 |

---

## 10. 需要用户确认的决策点

1. **WIP 处理**：是否把 5 个未提交修改 + `tests/fixtures/` 纳入冻结基线？（建议：纳入；测试依赖 fixtures，且是 confidence 契约校验改进）
2. **AG-DISTILL 支线**：是否移出交付范围（保留在仓库、不投入、不进简历）？（建议：是）
3. **MVP 场景**：是否确认"温室番茄病害诊断 + 灌溉冲突演示"，其余作物仅保留兼容？（建议：是）
4. **清理授权**：是否允许删除/归档 E 类对象（`codex/`、根目录旧 `phase4_2_*.txt`、`scripts/phase0_check.py`、本地缓存）？不可逆操作，需明确授权。
5. **Docker/部署**：是否纳入 MVP？（建议：暂缓，除非面试明确要求"可部署"）
6. **真实 LLM 演示**：是否要求现场有 key 演示 LLM Judge？（建议：不要求；作为可选加演，默认离线规则版）
7. **分支**：本轮方案分支是否在确认后合并/推送？（按约定由用户决定）

---

## 11. 下一步建议（单一任务）

> **任务 A（M0，0.5 天）：冻结基线并让 `pytest -q` / README 快速开始可用。**
> 具体：① 审查并提交 WIP（5 文件 + `tests/fixtures/`）；② 新增 `pytest.ini`（`testpaths=tests`）并清理根目录 `pytest-of-lkl/`；③ README 事实校正 + 快速开始 + `.env.example`；④ 生成 `requirements.lock`；⑤ 实跑 `pytest -q`、`orchestrator.py --rules-only`、`smoke_eval`，记录真实结果。
> 完成后按约定报告并停止，等待下一条指令。

---

## 附录 A：本轮回溯的检查项（只读）

- 目录/代码量：125 py / 25,486 行（不含缓存/本地数据）；23 测试文件；33 docs；109 reports。
- 入口阅读：`orchestrator.py`、`workflow.py`、`gateway/app.py`、`ui/tui.py`、`ui/web_app.py`、`rag/retriever.py`、`kg_adapter.py`、`rag/knowledge_base.py`、`tests/conftest.py`。
- 引用检查：`ui/web_app.py` 仅自身引用；`kg/mcp_server.py` 仅 `kg/__init__.py`/文档引用；`tests/` 无 `rag|storage|gateway|kg` 直接 import；`tests/fixtures` 被 `test_challenge_evaluation.py` 使用。
- 数据：`data/` 264MB（AgriKG 245MB，gitignored）；`logs/` 76MB；`results/` 57MB。
- 分支：17 条历史 `work/*`（未清理）。
- 未执行：任何代码修改、安装、push、merge、删除。

## 附录 B：与上一轮审计的关系

上一轮 `reports/delivery_audit_20261024/DELIVERY_CHECKLIST.md` 已给出 6 项交付判定（2 PASS / 4 PARTIAL）。本方案**不重复审计**，只回答"转向简历交付后，保留什么、修什么、停什么、怎样算完成"。上轮证据（`evidence/` 18 个文件、`logs/delivery_audit_20261024/`）仍是本方案的事实基础。
