# 项目审计报告 v4

> 审计日期：2026-08-01 | 代码根：`E:\knowledge_database\ACIS`（原 `agent协作模式初探` 目录已更名/迁移至此）

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
├── evals/         (9 文件)  ← smoke / fixture / runner / ablation
├── benchmarks/    (7 文件 + 9 数据集)  ← 61 案例 + 能力框架
├── tests/        (11 文件, 167 用例)
├── utils/         (4 文件)  ← 置信度校准 + 集体遗漏（活代码）
├── context/                ← Sprint 状态（实现入口）
├── docs/                   ← 宪法 / RFC / ADR / Sprint 报告
├── results/                ← 评测产物（summary / suites / ablation / traces）
├── data/                   ← 运行时数据库与数据集（gitignored）
└── agri-ai/.venv           ← Python 3.13 虚拟环境
```

**代码量：83 个 Python 文件，11,378 行**（不含 venv / neo4j / data / 缓存）。单元测试 167 个。

---

## 二、活代码 vs 死代码

### 状态更新（相对 v3 审计）

- v3 列出的死代码**已全部清理**：`debate/coordinator.py`、`agents/vision_test.py`、`rule_engine/demo.py`、`ui/app.py` 已删除；README 曾引用的 `orchestrator_v3.py` 已移除。
- `utils/` **已复活为活代码**：`confidence_calibration.py`（Judge 融合前置信度校准）与 `omission.py`（集体遗漏分析）均被 `agents/judge_agent.py` 引用；v3 中“可删”结论已失效。
- 当前无已知死代码；`src/` 为空目录（占位，待使用或移除）。

### 核心链路（活代码）

感知层（视觉/传感器/天气）→ 记忆层（RAG/KG/历史案例/经验回放）→ 专家层（病理/气象/栽培/经济/生态）→ Debate → Critic → Judge，前置 Planner 与 Tool Router，全程 Unified Trace 采集。

---

## 三、数据流

```text
用户输入 → orchestrator.run()
              ├─ Planner（任务分解）→ Tool Router（工具路由）
              ├─ LangGraph 主图（失败降级规则编排）
              │     context → perception → memory → experts → debate → critic → judge
              │     └─ 多轮辩论条件循环（rebuttal，AGRI_AI_MULTI_ROUND_DEBATE=0 关闭）
              ├─ Unified Trace（trace/）全程采集
              └─ SQLite 持久化 + 反馈/结果回灌（feedback / outcome）
```

---

## 四、验证现状（2026-08-01 实测）

| 检查项 | 结果 |
|---|---|
| `python -m pytest -q` | **167 passed**（11 个测试文件） |
| `evals/smoke_eval.py` | 3 套（rules / langgraph / langgraph+llm-judge）× 3 场景 passed |
| `evals/fixture_eval.py` | 12 场景 passed |
| enriched 基准（`results/summary.md`） | accuracy 1.00（15/15），planner/tool 使用率 1.00 |
| 消融（`results/ablation/`） | 7 组合，模块贡献可测量（memory_hits / debate_rounds / counterfactual_count / runtime） |
| 外部依赖 | Qdrant / Neo4j / DeepSeek 均未连接时自动回退，离线可跑 |

---

## 五、待办清单

1. **61 个 benchmark case 能力标注人工审查**（High）：自动推断建议已生成于 `benchmarks/CAPABILITY_ANNOTATION_SUGGESTIONS.md`，需 Chief Architect 审查后形成冻结元数据。
2. **venv 开发依赖**：pytest 已补装（9.1.1）；`ruff`、`mypy` 未安装，无法本地复跑静态检查（Sprint 报告记录 ruff/mypy 0 错误）。
3. **mypy 遗留错误**：冻结模块（agents/rag/rule_engine/debate/storage/utils）pre-existing 错误 + `planner.py` overload 警告（accepted，低优先）。
4. **`src/` 空目录**：占位未使用，建议使用或移除。
5. **运行环境**：当前 shell 默认 `python` 为 hermes-agent venv（无项目依赖）；应使用 `agri-ai\.venv`（Python 3.13）。

---

## 六、项目画像

| 维度 | 评估 |
|---|---|
| 代码健康度 | 83 文件 / 11,378 行，无已知死代码 |
| 架构层次 | 规划（Planner/Tool Router）→ 感知 → 记忆 → 专家 → 裁决 + 统一追踪 |
| 自动降级 | 6 条链路（Neo4j / Qdrant / LangGraph / Judge / Critic / SQLite） |
| 评估覆盖 | 167 单测 + 12 fixture + 61 benchmark 案例 + 7 组合消融 |
| 作物覆盖 | 番茄 / 甜菜 / 棉花（黄瓜保留兼容） |
| 版本 | ACIS 2.1E；Sprint 04.5A 完成，等待 Evidence Review Gate |
| Git | `main` HEAD `d74bc63`（database updated），工作树干净 |
