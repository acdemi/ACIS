# Agri AI

分层农业智能 Agent 原型，当前由 v3 多模型能力和 v4 Orchestrator / Debate / Judge 架构组成。
`orchestrator.py` 默认使用 LangGraph 主图执行，LangGraph 不可用或执行失败时自动回退到规则编排。
主图流程：context → perception → memory → experts → debate → critic → judge。

## 目录

- `gateway/`：FastAPI 路由入口
- `agents/`：视觉、气象、病理、栽培、Judge Agent
- `kg_adapter.py`：知识图谱适配器，为 Judge 提供 KG 三元组与硬约束
- `debate/`：Debate 协调器 + Critic 反驳轮次
- `kg/`：AgriKG 知识图谱 MCP Server
- `scripts/`：AgriKG 导入脚本与集成指南
- `rag/`：当前内存知识库，预留 Qdrant 检索接口
- `rule_engine/`：传感器模拟、异常检测、规则版 Router
- `orchestrator.py`：当前主编排入口，默认 LangGraph 主图
- `orchestrator_v3.py`：DeepSeek 工具调用版 v3
- `workflow.py`：LangGraph 主图节点定义
- `MODEL_AGENT_ORCHESTRATION.md`：小模型与 Agent 编排方案
- `evals/`：回归评估脚本（smoke_eval + fixture_eval）
- `ui/`：Streamlit UI + TUI 演示界面（`ui/tui.py`，面试演示）

## 运行

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='.'
python orchestrator.py
```

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

仅使用规则编排 fallback：

```powershell
python orchestrator.py --rules-only
```

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

运行轻量回归：

```powershell
python evals/smoke_eval.py
```

固定场景回归（12 个确定性 crop/intent/病害 断言）：

```powershell
python evals/fixture_eval.py
```

RAG/Qdrant 记忆层（Qdrant 不可用时自动回退内存知识库）：

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

KG/Neo4j 知识图谱（Neo4j 不可用时自动回退内置病害库 DISEASE_DB）：

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

自定义问题：

```powershell
python orchestrator.py "温室A番茄叶片黄斑，叶背有灰色霉层，如何处理？"
```

API：

```powershell
uvicorn gateway.app:app --reload
```

