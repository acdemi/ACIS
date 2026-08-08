# 项目审计报告 v5

> 审计日期：2026-08-07 | 代码根：`E:\knowledge_database\ACIS`（原 `agent协作模式初探` 目录已更名/迁移至此）

---

## 一、全景

```text
ACIS/
├── orchestrator.py       ← 主编排入口（默认 LangGraph 主图）
├── workflow.py           ← LangGraph 图（含多轮辩论循环）
├── kg_adapter.py         ← KG 适配器
├── _env.py               ← 环境变量加载
├── requirements.txt / docker-compose.yml
│
├── planner/       (4 文件)  ← Planner 2.1（冻结）
├── tool_router/   (3 文件)  ← Tool Router 2.1（冻结）
├── trace/         (4 文件)  ← Unified Trace 2.1E（冻结）
├── agents/       (16 文件)  ← 感知 + 记忆 + 专家 + 裁决 Agent
├── debate/        (3 文件)  ← DebateEngine + Critic
├── rag/           (3 文件)  ← 知识库 + RAG 检索
├── kg/            (2 文件)  ← Neo4j MCP Server
├── rule_engine/   (4 文件)  ← 传感器模拟 + 异常检测
├── storage/       (3 文件)  ← SQLite 持久化
├── gateway/       (2 文件)  ← FastAPI
├── ui/            (3 文件)  ← TUI + Web UI
├── evals/        (10 文件)  ← smoke / fixture / runner / ablation / capability_metrics
├── benchmarks/    (7 文件 + 9 数据集)  ← 64 案例 + 能力框架（52 标注）
├── tests/        (12 文件, 189 用例)
├── utils/         (4 文件)  ← 置信度校准 + 集体遗漏（活代码）
├── context/                ← Sprint 状态（实现入口）
├── docs/                   ← 宪法 / RFC / ADR / Sprint 报告
├── results/                ← 评测产物（summary / suites / ablation / traces）
├── data/                   ← 运行时数据库与数据集（gitignored）
└── agri-ai/.venv           ← Python 3.13 虚拟环境
```

**代码量：85 个 Python 文件，12,373 行**（不含 venv / neo4j / data / 缓存）。单元测试 189 个。

---

## 二、活代码 vs 死代码

### 状态更新（相对 v4 审计）

- v3 列出的死代码已全部清理（`debate/coordinator.py`、`agents/vision_test.py`、`rule_engine/demo.py`、`ui/app.py`、`orchestrator_v3.py`）。
- `utils/` 为活代码：`confidence_calibration.py`（Judge 融合前校准）与 `omission.py`（集体遗漏分析）均被 `agents/judge_agent.py` 引用。
- 新增活代码：`evals/capability_metrics.py`（7 种能力 Trace 打分）、`benchmarks/metadata.py` 的 `ObservableEvidence` 契约、`benchmarks/capability_matrix.py` 一致性检查。
- 当前无已知死代码；`src/` 为空目录（占位，待使用或移除）。

### 核心链路（活代码）

规划（Planner → Tool Router）→ 感知（视觉/传感器/天气）→ 记忆（RAG/KG/案例/经验回放）→ 专家（病理/气象/栽培/经济/生态）→ Debate → Critic → Judge；全程 Unified Trace 采集，评测阶段由 capability_metrics 自动打分。

---

## 三、数据流

```text
用户输入 → orchestrator.run()
              ├─ Planner（任务分解）→ Tool Router（工具路由）
              ├─ LangGraph 主图（失败降级规则编排）
              │     context → perception → memory → experts → debate → critic → judge
              │     └─ 多轮辩论条件循环（rebuttal，AGRI_AI_MULTI_ROUND_DEBATE=0 关闭）
              ├─ Unified Trace（trace/）全程采集
              ├─ 评测：runner → capability_metrics（7 能力分数）→ report（metrics.csv / summary.md）
              └─ SQLite 持久化 + 反馈/结果回灌（feedback / outcome）
```

---

## 四、验证现状（2026-08-07 实测）

| 检查项 | 结果 |
|---|---|
| `python -m pytest -q` | **189 passed**（12 个测试文件） |
| `evals/smoke_eval.py` | 3 套（rules / langgraph / langgraph+llm-judge）× 3 场景 passed |
| `evals/fixture_eval.py` | 12 场景 passed |
| enriched 基准（`results/summary.md`） | accuracy 1.00（18/18），planner/tool 使用率 1.00 |
| 能力一致性（`CAPABILITY_CONSISTENCY_REPORT.md`） | 52 标注 / 52 一致 / 0 不一致 |
| 能力打分（Sprint 04.5C） | 7 能力全部 Trace 打分；消融联动验证（planner/memory 关闭对应分数归零） |
| 外部依赖 | Qdrant / Neo4j / DeepSeek 均未连接时自动回退，离线可跑 |

---

## 五、待办清单

1. **Evidence Review Gate**：Sprint 04.5A~04.5C 产物等待架构师审查；通过后才进入 Sprint 05（Experiment Manager），**不自动进入**。
2. **能力标注审查**（High）：52/64 已标注，12 个难度案例按设计未标注；待 Chief Maintainer 审查形成冻结元数据。
3. **能力打分严格度（Sprint 04.5C）**：
   - `conflict_resolution` 依赖 critic triggered：3 个环境矛盾案例得分为 0，需决定改标注还是改管线；
   - `information_gathering` 依赖关键词启发式，提示词变更后需重新校准；
   - `sensor_cross_validation` 要求真实异常或 `sensor_verify` 请求，仅存在传感器数据不得分。
4. **venv 开发依赖**：pytest 已装（9.1.1）；`ruff`、`mypy` 未安装，本地无法复跑静态检查（Sprint 报告记录新增文件 0 错误）。
5. **mypy 遗留错误**：冻结模块 pre-existing 错误 + `planner.py` overload 警告（accepted）。
6. **`src/` 空目录**：占位未使用，建议使用或移除。
7. **运行环境**：当前 shell 默认 `python` 为 hermes-agent venv（无项目依赖）；应使用 `agri-ai\.venv`（Python 3.13）。

---

## 六、项目画像

| 维度 | 评估 |
|---|---|
| 代码健康度 | 85 文件 / 12,373 行，无已知死代码 |
| 架构层次 | 规划 → 感知 → 记忆 → 专家 → 裁决 + 统一追踪 + 能力度量 |
| 自动降级 | 6 条链路（Neo4j / Qdrant / LangGraph / Judge / Critic / SQLite） |
| 评估覆盖 | 189 单测 + 12 fixture + 64 benchmark 案例（52 标注）+ 7 组合消融 + 7 能力打分 |
| 作物覆盖 | 番茄 / 甜菜 / 棉花（黄瓜保留兼容） |
| 版本 | ACIS 2.1E；Sprint 01~04.5C 完成，处于 Evidence Review Gate |
| Git | `main` HEAD `ff825c9`（0.45C），工作树干净 |
