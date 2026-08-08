# Agri AI（ACIS）

分层农业认知智能系统原型（Agricultural Cognitive Intelligence System，ACIS）。当前版本为 **ACIS 2.1E（Evidence Platform）**，
由 Planner / Tool Router / 感知 / 记忆 / 专家 / Debate / Critic / Judge 分层协作组成，默认经 LangGraph 主图执行；
LangGraph 不可用或执行失败时自动回退规则编排。

主图流程：`context → perception → memory → experts → debate → critic → judge`（含多轮辩论条件循环 `rebuttal`）。

## 当前状态（2026-08-08）

| 项目 | 状态 |
|---|---|
| 版本 | ACIS 2.1E — Evidence Platform；Sprint 01 ~ 06 已完成（Sprint 05 Experiment Manager、Sprint 06 Research Evaluation Infrastructure） |
| 模块冻结 | Planner / Judge / Debate / Critic / Tool Router / Memory / DecisionOutput / Unified Trace / Perception Agents 冻结 2.1（详见 `context/ARCHITECTURE_STATE.md`） |
| 单元测试 | `pytest`：**222 passed**（15 个测试文件 + `conftest.py`） |
| 回归 | `evals/smoke_eval.py`（3 套 × 3 场景）、`evals/fixture_eval.py`（12 场景）全绿 |
| 基准 | `benchmarks/` 9 个数据集 / **64 案例**（52 已标注能力，一致性检查 52/52）；enriched 18 例 accuracy 1.00 |
| 能力度量 | 7 种认知能力均可由 Trace 自动打分（0-1），见 `results/summary.md` 的 “Capability Performance” |
| 消融 | 7 组合消融已产出（`results/ablation/`），含能力分数消融（cap_smoke） |
| 实验管理 | `experiments/` 实验管理器：YAML 定义 / 多 seed 运行 / manifest 可复现归档 / 统计分析与论文图（见 `results/experiments/`） |
| 已知债务 | 12 个难度案例按设计未标注（待审查）；能力打分严格度问题 3 例（详见 `context/KNOWN_DEBT.md`） |

## 版本演进

### ACIS 2.1E — Evidence Platform（2026-07-28 ~ 2026-08-02）

- **Sprint 01 — Unified Trace**：`trace/` 统一追踪层（collector / exporter / types），全链路可观测。
- **Sprint 02 — Evaluation Runner**：`evals/runner.py` + `metrics.py` + `report.py` + `config.py`，9 项指标（accuracy / average_confidence / average_runtime / planner_usage / tool_usage / memory_hits / debate_rounds / counterfactual_count / collective_omission_count）。
- **Sprint 03 — Benchmark Framework**：`benchmarks/` 9 个数据集（难度分层 + 五类能力套件 + enriched 挑战集）。
- **Sprint 04 — Ablation Framework**：`evals/ablation.py`，基线（all_on）对比关闭 Planner / Debate / Memory / Counterfactual / Tool Router / Critic 的模块贡献消融。
- **Sprint 04.5A — Capability Framework**：`benchmarks/capabilities.py` 定义 7 种稳定认知能力枚举；`capability_matrix.py` 自动生成 `CAPABILITY_COVERAGE.md` 与 `CAPABILITY_ANNOTATION_SUGGESTIONS.md`。
- **Sprint 04.5B — Verifiable Capability Contract**：`observable_evidence`（`capability` / `expected_behavior` / `success_condition`）数据契约；36/36 能力案例 + 16/28 难度案例显式标注；`CAPABILITY_CONSISTENCY_REPORT.md`（52/52 一致）；enriched 新增 3 个 `information_gathering` 案例（15→18）。
- **Sprint 04.5C — Capability Evaluation Engine**：`evals/capability_metrics.py` 将能力契约接入运行时——7 种能力全部由 Trace 自动打分（0/1），写入 `CaseMetrics.capability_scores`、`metrics.csv` 能力列与 `summary.md` 的 “Capability Performance”；消融联动验证（`--planner-off` → `information_gathering`/`multi_step_planning` 归零，`--memory-off` → `knowledge_retrieval` 归零）。
- **Sprint 05 — Experiment Manager**：`experiments/`（manager / schema / catalog / archive / analysis / figures），YAML 实验定义、多 seed 运行、`config.yaml` / `manifest.json` 可复现归档、`list` / `compare` / `latest` CLI（详见 `docs/EXPERIMENT_MANAGER_SPRINT_05_REPORT.md`）。
- **Sprint 06 — Research Evaluation Infrastructure**：`experiments/analysis.py` + `figures.py` 统计检验（bootstrap 置信区间）与论文图；归档新增 `dataset_sha256` 指纹、`analysis.json`、`figures/`（详见 `docs/RESEARCH_EVAL_SPRINT_06_REPORT.md`）。

### ACIS 2.1（2026-07-25）

- Planner（`planner/`：任务分解、工具调用规划）
- Tool Router（`tool_router/`：Agent → 工具统一路由与权限）
- Meta-Critic（级联错误检测）
- Procedural Memory（经验回放）
- LangGraph 工作流扩展

### ACIS 2.0 认知进化版（2026-07）

- 反事实推理 + Judge 集体忽略检测（争议分 +0.2、置信度下调）
- 多轮辩论：`workflow.py` 主图 `rebuttal` 条件循环，`AGRI_AI_MULTI_ROUND_DEBATE=0` 可关闭
- 经济 Agent / 生态 Agent（成本-收益、农药-天敌冲突检测）
- 置信度校准（`utils/confidence_calibration.py`，Isotonic Regression / Platt Scaling，`AGRI_AI_CALIBRATION=0` 可关闭）
- KG 进化（`propose_triple()` 幂等写入 `data/kg_drafts.json`）+ 经验回放闭环（`POST /decisions/{id}/outcome`）
- 阶段三（P2，远期）预测增强未实施：Chronos/statsmodels 时序预测、传感器异常第三层、`prediction_uncertainty` 字段

## 目录

- `orchestrator.py`：主编排入口（默认 LangGraph 主图，失败回退规则编排）
- `workflow.py`：LangGraph 主图节点定义（含多轮辩论条件循环）
- `planner/`：Planner（任务分解、工具编排）
- `tool_router/`：Tool Router（工具注册与路由）
- `trace/`：Unified Trace（统一追踪采集与导出）
- `agents/`：感知（视觉/传感器/天气）、记忆（RAG/KG/案例/经验回放）、专家（病理/气象/栽培/经济/生态）、Judge
- `debate/`：Debate 协调器 + Critic 反驳轮次
- `rag/`：知识库（Qdrant 可选，默认内存回退）
- `kg_adapter.py` + `kg/`：知识图谱适配器 + AgriKG MCP Server
- `rule_engine/`：传感器异常检测（sensor_anomaly MCP）
- `storage/`：SQLite 持久化（决策审计 + 反馈/结果回灌）
- `gateway/`：FastAPI 路由入口
- `ui/`：TUI + Web UI
- `evals/`：smoke_eval / fixture_eval / runner / ablation / capability_metrics / report
- `experiments/`：实验管理器（Sprint 05/06：YAML 定义、多 seed 运行、统计分析与论文图）
- `benchmarks/`：基准数据集（64 案例）、能力枚举、覆盖/一致性报告（自动生成）
- `context/`：Sprint 状态、路线图、架构状态、已知债务（实现入口，先读 `CURRENT_SPRINT.md`）
- `docs/`：宪法（`ACIS.md`）、RFC、ADR、Sprint 报告
- `results/`：评测产物（summary / suites / ablation / traces / experiments，gitignored）
- `utils/`：置信度校准、集体遗漏分析
- `.venv`：项目 Python 3.13 虚拟环境（运行时 + 开发依赖已装）

## 环境准备

```powershell
# 推荐使用仓库自带 venv
.\.venv\Scripts\Activate.ps1
# 或直接指定解释器
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='.'
$py = 'E:\knowledge_database\ACIS\.venv\Scripts\python.exe'

# 首次安装依赖（含开发工具）
pip install -r requirements.txt pytest ruff mypy
```

## 运行

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='.'
python orchestrator.py
```

自定义问题：

```powershell
python orchestrator.py "温室A番茄叶片黄斑，叶背有灰色霉层，如何处理？"
```

仅使用规则编排 fallback：

```powershell
python orchestrator.py --rules-only
```

## Docker 快速部署（一键启动）

需要 Docker Desktop（Windows / macOS）或 Docker Engine（Linux），首次构建约 2~5 分钟（轻量镜像，不含 ML 可选依赖）。

```powershell
# Windows
.\start.ps1            # 构建 + 启动 api/qdrant/neo4j + 等待健康检查
.\start.ps1 status     # 查看服务状态
.\start.ps1 logs       # 跟踪 API 日志
.\start.ps1 stop       # 停止（保留数据卷）

# Linux / macOS
./start.sh start
./start.sh import      # 可选: 导入真实 AgriKG 图谱到 Neo4j
./start.sh stop
```

- 启动后 API 位于 `http://localhost:8000`（`GET /health`、`POST /diagnose`），Neo4j 控制台 `http://localhost:17474`（`neo4j / agriai2026`）。
- 启用 LLM Judge / Critic：启动前设置 `$env:DEEPSEEK_API_KEY='sk-...'`（或 `export`），compose 自动透传。
- 镜像基于 `requirements.docker.txt` 的**轻量核心依赖**：torch / transformers / scikit-learn 未打包（视觉推理、Isolation-Forest 异常检测自动降级为模拟/阈值模式）。需要完整能力时改用 `requirements.txt` 构建。
- 真实 AgriKG 导入：将 `Agriculture_KnowledgeGraph-master` 解压到 `data/` 后运行 `.\start.ps1 import`；未导入时 Judge 自动使用内置 DISEASE_DB，离线可跑。
- 常用 docker 命令：`docker compose ps` / `docker compose down -v`（清空数据卷）。

## TUI 演示界面（面试演示）

交互式终端界面（基于 rich），自动加载 DeepSeek Key 与 Neo4j 连接，离线可跑：

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='.'
python -m ui.tui
```

- 内置 5 个演示场景（番茄 / 甜菜 / 棉花 × 诊断 / 灌溉 / 预警），覆盖 RAG 命中、KG 一致性校验、Critic 多轮反驳降权。
- `[j]` 切换 DeepSeek Judge（KG 锚定结构化裁决），`[c]` 切换 Critic LLM 反驳；`[6]` 自定义输入。无 Key 或网络失败时自动回退规则模式。
- 首次启动预热传感器异常检测模型约 10s，之后每次决策 <1s。
- 未启动 Neo4j / Qdrant 时自动回退内存知识库，TUI 自动设置 `NEO4J_PASSWORD=agriai2026` 与 `HF_HUB_OFFLINE=1`（避免 Chronos 联网下载超时）。

当前支持作物：番茄 / 甜菜 / 棉花（病害与农事指南已内置；黄瓜保留兼容）。

启用 DeepSeek 结构化 Judge（无 Key 或调用失败时自动回退规则裁决）：

```powershell
$env:DEEPSEEK_API_KEY='你的 key'
python orchestrator.py --llm-judge "温室A番茄叶片黄斑，叶背有灰色霉层，如何处理？"
```

启用 DeepSeek 结构化 Critic 反驳（冲突时用 LLM 裁决降权，无 key 或失败时回退规则反驳）：

```powershell
python orchestrator.py --llm-critic "温室A番茄今天需要浇水吗？如果有病害风险要一起考虑"
python orchestrator.py --llm-judge --llm-critic "温室A甜菜叶片圆形褐色病斑，如何处理？"
```

可选环境变量：

- `DEEPSEEK_BASE_URL`：默认 `https://api.deepseek.com`
- `DEEPSEEK_MODEL` / `AGRI_AI_JUDGE_MODEL`：默认 `deepseek-chat`
- `AGRI_AI_CRITIC_MODEL`：Critic 反驳所用模型，默认同上
- `AGRI_AI_MULTI_ROUND_DEBATE`：多轮辩论开关（默认 1）
- `AGRI_AI_EXTRA_EXPERTS`：经济/生态 Agent 开关（默认 1）
- `AGRI_AI_CALIBRATION` / `AGRI_AI_CALIB_ALPHA`：置信度校准开关与参数
- `AGRI_AI_KG_DRAFTS_PROPOSE` / `AGRI_AI_KG_DRAFTS_LOAD` / `AGRI_AI_KG_DRAFTS_PATH`：KG 草稿三元组提议/加载
- `AGRI_AI_PERSIST`：SQLite 持久化开关（默认 1）

## 测试与评估

```powershell
# 单元测试（222 个，15 个测试文件 + conftest.py）
python -m pytest -q

# 轻量回归：主图 / 规则 / LLM Judge 回退（3 套 × 3 场景）
python evals/smoke_eval.py

# 固定场景回归（12 个确定性 crop/intent/病害 断言）
python evals/fixture_eval.py

# Benchmark 评测（64 案例；输出含 capability_scores 与 Capability Performance）
python evals/runner.py --dataset benchmarks.datasets.enriched
python evals/runner.py --suite all

# 消融（7 组合，输出 results/ablation/；能力分数随模块开关联动）
python evals/ablation.py --dataset benchmarks.datasets.enriched

# 能力覆盖/一致性/标注建议（自动生成 benchmarks/*.md，勿手写）
python -m benchmarks.capability_matrix

# 实验管理（Sprint 05/06；YAML 定义见 experiments/definitions/）
python -m experiments.manager list --output-root results/experiments
python -m experiments.manager run experiments/definitions/phase2_multiseed.yaml
```

## RAG/Qdrant 记忆层

Qdrant 不可用时自动回退内存知识库：

```powershell
# 可选：启动 Qdrant
docker compose up -d qdrant

# 可选：索引内置病害知识
python -m rag.retriever --index

# 检索冒烟测试
python -m rag.retriever --query "番茄叶背灰色霉层" --crop tomato
```

RAG 环境变量：

- `AGRI_AI_RAG_BACKEND`：默认 `auto`，可选 `auto|qdrant|memory`
- `QDRANT_URL`：默认 `http://localhost:6333`
- `QDRANT_COLLECTION`：默认 `agri_knowledge_v1`
- `AGRI_AI_RAG_TOP_K`：默认 `3`

## KG/Neo4j 知识图谱

Neo4j 不可用时自动回退内置病害库 DISEASE_DB：

```powershell
# 查看 KG 后端状态
python kg_adapter.py --status

# 检索冒烟测试
python kg_adapter.py --crop tomato --query "叶片黄斑，叶背灰色霉层"
```

KG 环境变量：

- `AGRI_AI_KG_BACKEND`：默认 `auto`，可选 `auto|neo4j|memory`
- `NEO4J_URI`：默认 `bolt://localhost:7687`
- `NEO4J_USER` / `NEO4J_PASSWORD`：默认 `neo4j` / `neo4j`；本项目 docker-compose 的 Neo4j 密码为 `agriai2026`（CLI 运行需 `$env:NEO4J_PASSWORD='agriai2026'`）

> 真实 AgriKG 数据需先用 `scripts/import_agrikg.py` 导入 Neo4j；未导入或未启动时 Judge 自动使用 DISEASE_DB 合成的三元组与硬约束，离线可跑。

## API

```powershell
uvicorn gateway.app:app --reload
```

- `GET /health`
- `POST /diagnose`
- `GET /decisions` / `GET /decisions/{id}`
- `POST /decisions/{id}/feedback`（人工复核标记）
- `POST /decisions/{id}/outcome`（ACIS 2.0 经验回放：有效 / 无效 / 部分有效）

## 相关文档

- `context/ARCHITECTURE_STATE.md`：模块冻结状态（单一真相源）
- `context/ROADMAP.md` / `context/CURRENT_SPRINT.md`：Sprint 路线图与当前 Sprint
- `context/KNOWN_DEBT.md`：已知技术债务
- `docs/ACIS.md`：项目宪法
- `docs/rfc/RFC001-System Architecture.md`：架构权威文档（RFC-001）
- `docs/architecture/architecture.md`：分层架构入口（权威见 RFC-001）
- `benchmarks/README.md`：基准框架说明
