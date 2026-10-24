# A 项 — 环境可复现性审计（ACIS @ work/20261024-delivery-audit）

> 审计员：env-auditor（task-3）｜时间：2026-10-24 14:07–14:25 (+08:00)
> HEAD：`6420e34`（Sat Oct 24 13:08:28 2026 +0800，`docs: archive 20261024 merge round`）
> 解释器：`.venv\Scripts\python.exe` = **Python 3.13.3**（`pip check` 无破损）
> 约束：只读源码；未联网、未 pip install、未改被跟踪文件；证据全部写入 `logs/delivery_audit_20261024/env/`

## 证据文件索引

| 文件 | 内容 |
|---|---|
| `acis_head.tar` | `git archive HEAD` 干净副本（4.6 MB） |
| `clean/` | 解压后的干净副本（无 `.env` / `data/` / `results/` / `logs/`） |
| `env_baseline.json` | 当前解释器 135 个包的实测版本（事实基线） |
| `requirements_vs_installed.json` | requirements 声明 vs 实际安装版本对照 |
| `clean_run_probe.json` | 干净副本 rules-only + LangGraph 两路径实测结果 |
| `probe_clean_run.py` / `baseline_env.py` / `summarize_requirements.py` | 复跑脚本 |

---

## A1 依赖与凭证声明 — **PARTIAL**

**事实**
- `requirements.txt`（36 行）与 `requirements.docker.txt`（20 行）全部为 `>=` 下界，仅 `mcp` 有上界 `>=1.0.0,<2.0.0`（requirements.txt:5 / requirements.docker.txt:11）；无任何 lock 文件。
- 仓库根无 `pyproject.toml` / `setup.py` / `setup.cfg` / `Pipfile` / `poetry.lock` / `uv.lock` / `environment.yml` / `.env.example`（`git ls-tree HEAD` 根目录清单已核对）。
- 无 `.env` 模板：`.env` 被 `.gitignore:2` 忽略；`_env.py:16-32` 找不到文件时静默返回（不报错、不提示）。
- README「环境准备」只有 4 行（README.md:92-104）：假定仓库自带 `.venv`，`pip install -r requirements.txt pytest ruff mypy`，无版本、无 venv 创建步骤、无 `.env` 创建步骤。
- 实测基线（`requirements_vs_installed.json`）：openai 2.45.0、langgraph 1.2.9、fastapi 0.139.0、pydantic 2.13.4、mcp 1.28.1、httpx 0.28.1、qdrant-client 1.18.0、neo4j 6.2.0、rich 15.0.0、transformers 5.13.1、torch 2.13.0、scikit-learn 1.9.0、numpy 2.5.1、pillow 12.3.0、streamlit 1.59.2；pytest 9.1.1 / ruff 0.16.2 / mypy 2.3.0 也已安装。
- **等价重建不可保证**：所有主依赖只有下界，`pip install -r requirements.txt` 今天会拉到（或更新到）任意未来大版本（openai 2.x / langgraph 1.x / transformers 5.x 已在本机出现），无法重建出与当前等价的环境。mcp 是唯一有上界的包。
- **torch / transformers / scikit-learn 非核心必需**（静态）：全仓库无顶层 `import torch/transformers/sklearn`；均为懒加载且失败降级——`agents/vision.py:103`（transformers→mock）、`rule_engine/sensor_anomaly.py:91,112,114,190`（IF/LSTM/Chronos→规则/线性回归）、`utils/confidence_calibration.py:74`（isotonic→手写 Platt）。rules-only 主链路（orchestrator→agents→judge）不需要它们。
- **凭证文档缺口（关键）**：README 只写了 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` / `AGRI_AI_JUDGE_MODEL`（README.md:144,180-189），**完全没有** `AGRI_AI_JUDGE_API_KEY` / `_BASE_URL` / `_PROVIDER` / `_TIMEOUT_SECONDS` / `_MAX_RETRIES` / `_SELF_CONSISTENCY_K`（`utils/judge_runtime.py:67-114`、`agents/judge_agent.py:462-467`）、`AGRI_AI_MEMORY_GATE(_MIN_CONF)`（judge_agent.py:528-533）、`AGRI_AI_ABSTAIN_MIN_SUFFICIENCY`（judge_agent.py:582）、`AGRI_AI_DB_PATH`（storage/db.py:13）、`AGRI_AI_JUDGE_SESSION_ID`（judge_runtime.py:166）。
- **OPENCODE_* 是死配置**：仓库 `.env` 有 `OPENCODE_BASE_URL` / `OPENCODE_API_KEY`，但全仓库 Python 代码**没有任何地方读取 `OPENCODE_*`**（grep 仅命中 `utils/judge_runtime.py:150-151,159-186` 的 provider 推断与 `x-opencode-session` 头；`scripts/emit_t2b_audit.py:139` 是文案）。opencode 网关只能通过 `AGRI_AI_JUDGE_BASE_URL`/`AGRI_AI_JUDGE_API_KEY` 或 `DEEPSEEK_*` 配置，README 未说明该映射 → 新环境按 README 无法复现 Phase 6 的真实 Judge 通道。

**结论**：能在本机跑，但"干净环境按 README 重建出等价环境"= 不成立（无锁、无 .env 模板、Judge/opencode 凭证链未文档化）。严重度：**高**（交付项 2 的核心判据）。

## A2 干净副本自包含性 — **PASS（核心链路）/ PARTIAL（完整能力）**

**做法**：`git -c safe.directory=... archive --format=tar -o acis_head.tar HEAD` → `tar -xf` 到 `clean/`；用**原 `.venv` 解释器**、`PYTHONPATH=clean 根`、工作目录=clean 根，运行探针（不联网、不装包）。

**结果**（`clean_run_probe.json`）
- `clean/` 内 `.env`、`data/`、`results/`、`logs/` 全部不存在（符合 `.gitignore:2,20,37,40`）；`benchmarks/**`、`tests/`、`reports/` 均在（已入库）。
- rules-only：**OK**，3.78s，`judge_mode=rules`，决策"病理判断首选：番茄叶霉病"（confidence 0.72），trace 10 个 stage / 19 事件；`judge_runtime.outcome=rules`、`fallback_reason_code=disabled_by_configuration`、`config_sources` 全为 `default`。
- 默认 LangGraph：**OK**，2.05s，编译图成功（`compiled_graph=true`），`judge_mode=rules`（无 key）。
- 运行后自动创建 `clean/data/agri.db`（`storage/db.py:13,50` 会 `mkdir(parents=True)`）；`results/`、`logs/` 始终不需要。
- 运行中 Qdrant `localhost:6333` 返回 **502**（本机系统代理劫持，正是 README.md:240-242 描述的现象）→ RAG 静默回退内存后端；Neo4j 未连 → KG 回退 memory 后端；两者都不影响启动。
- 代码对 `data/` 的硬依赖只有：`storage/db.py:13`（自动创建）、`kg_adapter.py:449`（`data/kg_drafts.json`，`propose_triple` 会 `mkdir`，kg_adapter.py:461）、`scripts/run_challenge_evaluation.py:7`（`data/evaluation/challenge_raw`，仅评测脚本）。

**要跑起来需要的额外步骤（按目标分层）**
1. 仅 rules-only / LangGraph 主图：**零额外步骤**（实测）。
2. 真实 LLM Judge：创建 `.env`（格式 `KEY=VALUE`，`_env.py` 解析）或设 `DEEPSEEK_API_KEY`（或 `AGRI_AI_JUDGE_API_KEY`）；如用 opencode 网关还需设 `AGRI_AI_JUDGE_BASE_URL`/`_MODEL`（README 未写）。
3. 本机 CLI 访问 localhost 服务：`$env:NO_PROXY='localhost,127.0.0.1'`（README 已写，但见 A3 的脚本误解）。
4. Qdrant/Neo4j：`docker compose up -d qdrant neo4j` 或允许内存回退。
5. 视觉真实推理：需 torch/transformers + HF 模型缓存（或先设 `HF_HUB_OFFLINE=1` 接受 mock）；README 未提。

## A3 Docker / 启动脚本与 README 一致性 — **PARTIAL**

**一致的声称**
- API 端口 8000：`docker-compose.yml:13` ↔ README.md:143；`GET /health` / `POST /diagnose` 存在（`gateway/app.py:31-42`）。
- Neo4j 控制台 17474：compose:50 ↔ README:143；Neo4j 密码 `agriai2026`：compose:23,58 ↔ README:143,260。
- `DEEPSEEK_API_KEY` 透传：compose:19 `${DEEPSEEK_API_KEY:-}` ↔ README:144。
- 健康检查存在：compose:30-35（`python -c urllib.urlopen('/health')`），start 脚本另等 `http://localhost:8000/health`（start.ps1:30-46 / start.sh:27-38）。
- 轻量镜像不含 ML 依赖：requirements.docker.txt:1-20 ↔ README:145；`data/Agriculture_KnowledgeGraph-master` 导入前置检查（start.ps1:73 / start.sh:64）↔ README:146；`scripts/import_agrikg.py` 存在。

**不一致 / 缺口**
1. **Python 版本漂移**：`Dockerfile:2` `FROM python:3.11-slim`，而 README.md:90 与本地 `.venv` 为 **Python 3.13.3**。静态扫描未发现 3.12+ 语法（无 PEP 695 `type X=`、无 `except*`、无 `itertools.batched`），因此 3.11 大概率可运行，但"镜像=本地"的等价性未验证（本沙箱 docker 不可用）。
2. **NO_PROXY 处理名不副实**：`start.ps1:19-20` / `start.sh:15-16` 只设置**宿主机当前 shell** 的环境变量，且 compose 的 api 服务 `environment:`（compose:14-26）**没有** `NO_PROXY`；它既不会进入容器，也不会影响用户随后另开的 CLI/TUI 进程。README.md:242 "（`start.ps1` / `start.sh` 已自动处理）"对 CLI 场景是**误导**。
3. **Judge/opencode 配置在 Docker 下不可达**：compose 只透传 `DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL`（compose:19-20），未透传 `AGRI_AI_JUDGE_*`、`OPENCODE_*`、`NO_PROXY`；而 `.:/app` 绑定挂载（compose:10）虽让容器能读到宿主机 `.env`（尽管 `.dockerignore:5` 排除了它，bind mount 会重新暴露），干净 clone 无 `.env` → Docker 用户无法通过宿主环境变量配置 opencode 网关 Judge（README:144 只提 DEEPSEEK_API_KEY）。
4. **Neo4j APOC 需联网**：compose:59 `NEO4J_PLUGINS=["apoc"]` 首次启动会下载 APOC；离线/内网环境 Neo4j 可能无法 healthy，而 api `depends_on: neo4j: condition: service_healthy`（compose:27-29）→ `start` 在 60s 后失败。README 未提示该前置条件。
5. **健康检查能力有限**：`/health` 是静态 `{"status":"ok"}`（gateway/app.py:31-33），不检查 Judge 凭证、Neo4j/Qdrant 连接；一键启动"健康"不代表能力可用（与 A5 的降级设计配套，但 README 未声明）。
6. **镜像 tag 未锁定**：`neo4j:community`（compose:46）、`qdrant/qdrant:latest`（compose:38）、`python:3.11-slim`（Dockerfile:2）均为浮动 tag → 构建不可复现。
7. **未验证项**：Neo4j healthcheck 依赖 `wget`（compose:65）是否存在于 `neo4j:community` 镜像；Dockerfile 无 `HEALTHCHECK`（由 compose 提供，可接受）；`.:/app` 绑定挂载使镜像内代码被宿主代码覆盖（构建产物与实际运行不一致）。

## A4 README / 审计文档过期声称 — **FAIL**

| 文档:行 | 声称 | 实际（证据） |
|---|---|---|
| README.md:9 | 「当前状态（2026-09-20）」 | HEAD 2026-10-24；Phase 6 进行中（context/CURRENT_SPRINT.md:4；docs/ARCHITECTURE_DECISIONS.md:160-224 ADR-005 2026-10-24） |
| README.md:13 | 处于 Phase 4.2-R，等待 Phase 5/6 决策 | 已进入 Phase 6 架构重设计并实施 ADR-005 |
| README.md:15 | pytest **267 passed**（2026-09-20） | 实际 23 个测试文件、静态 ≥300 个 `def test_`（含 parametrize 更多）；仓库自己的审计报告已写 **307 passed**（reports/phase4_evaluation_metric_contract_audit.md:267，2026-10-17） |
| README.md:194 | 「267 个，18 个测试文件 + conftest.py」 | 实际 23 个 `tests/test_*.py`（多出 test_challenge_scorer / test_challenge_evaluation / test_decision_confidence / test_metrics / test_stability_metric_contract 等） |
| README.md:22-23 | 已知债务含「judge 端点/连接性」 | 2026-10-19 已 RECOVERED：6/6 deepseek 零回退（reports/phase4_judge_recovery_20261019/judge_recovery_report.md:1-6,60） |
| README.md:180-189 | 可选环境变量清单 | 缺 `AGRI_AI_JUDGE_*`（6 个）、`AGRI_AI_MEMORY_GATE*`、`AGRI_AI_ABSTAIN_MIN_SUFFICIENCY`、`AGRI_AI_DB_PATH`、`AGRI_AI_JUDGE_SESSION_ID`；`OPENCODE_*` 全文未提 |
| IMPLEMENTATION_AUDIT.md:7,12 | 222 passed / 267 passed（15 个测试文件） | 同上，已过期；正文为 2026-08-07 快照（189 passed / 12 文件 / 85 文件 12,373 行） |
| IMPLEMENTATION_AUDIT.md:108 | 「ruff、mypy 未安装，本地无法复跑静态检查」 | 当前已装 ruff 0.16.2 / mypy 2.3.0（requirements_vs_installed.json） |
| IMPLEMENTATION_AUDIT.md:63,110 | `src/` 为空目录 | `src/openmetaphysics/evaluation/` 已有实质代码（challenge_report / challenge_scorer 等） |
| README.md:3 | 版本 ACIS 2.1E | 未反映 Phase 6 / ADR-005（置信度链路、judge_runtime、自一致性采样） |

说明：README 的「9 个数据集 / 64 案例 / enriched 18 例」与当前 `benchmarks/datasets/*.json`（9 个）一致，不算过期；测试数量/状态/凭证债务是主要过期项。

## A5 无 Neo4j / Qdrant / API key 时的降级 — **PARTIAL**

| 能力 | 无后端/无 key 时的行为 | 是否有明确记录 | 证据 |
|---|---|---|---|
| LLM Judge | `use_llm=True` 但无 key → `JudgeConfigurationError` → 规则裁决 | ✅ `judge_runtime.outcome=fallback` + `fallback_reason_code=missing_credentials` + `debate.missing_evidence` + WARNING 日志 | judge_agent.py:119-166, 342-343；实测见 B 项 probe |
| 显式 rules-only | 规则裁决 | ✅ `outcome=rules` + `fallback_reason_code=disabled_by_configuration` | judge_agent.py:156-166；clean 实测 |
| RAG/Qdrant | 回退内存 DISEASE_DB | ◐ `retrieve_with_backend` 返回 `backend=fallback`+`error`，写进 RagMemoryAgent evidence；**无日志**；`retrieve()`（retriever.py:252-267）完全静默 | rag/retriever.py:252-295；agents/rag_memory_agent.py:9-13 |
| KG/Neo4j | 回退 DISEASE_DB 三元组 | ◐ `query_kg` 有 `backend`/`neo4j_connected`/`error`，但 Judge 只保留 `backend`，error 被丢弃；**无日志** | kg_adapter.py:396-442；judge_agent.py:338,450 |
| 传感器 ML（sklearn/torch/chronos） | IF→range check、LSTM→规则、Chronos→线性回归 | ✅ `layer_details` 里 engine 字段随 trace 记录 | sensor_anomaly.py:84-134, 388-405；sensor_agent.py:11-19 |
| 视觉（transformers） | mock 分类 + `note` 提示 | ◐ 有 note，但 VisionAgent 读错字段（见 B4-5）→ 实际表现为"未知类别"且无 warning | vision.py:102-108,195-200；vision_agent.py:20 |
| SQLite | 自动创建 `data/agri.db` | ◐ 创建成功可观测；**失败被 `except: pass` 吞掉** | storage/db.py:50；orchestrator.py:157-162 |
| LangGraph | ImportError → 规则路径 | ◐ ImportError 无记录；执行异常 → `missing_evidence`（有文字、无 reason_code） | orchestrator.py:140-149,196-201 |
| 置信度校准器 | sklearn 缺失→Platt；校准器不可用→passthrough | ✅ `calibration.status()` 写入 judge_analysis | utils/confidence_calibration.py:60-80；judge_agent.py:92-117 |

**用户按 README 能否离线启动**：**能**（已实测 clean 副本，无 key、无 Qdrant、无 Neo4j 均正常出决策）；但"离线可用"的边界（哪些能力被降级、降级后置信度/证据如何解读）README 未系统说明，且 Judge 真实通道的凭证要求不完整。

---

## A 项总判定：**PARTIAL**

- 可运行、可离线、干净副本自包含（PASS）；但"可复现"依赖未锁定、`.env` 无模板、Judge/opencode 凭证链未文档化、Docker 与本地版本/环境变量透传不一致、README 状态与测试数字过期（FAIL 项）。交付项 2「环境可复现」判 **PARTIAL**。
