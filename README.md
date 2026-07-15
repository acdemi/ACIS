# ACIS · 农业多智能体认知决策系统

> Agricultural Cognitive Intelligence System（ACIS）—— 面向农业场景的多智能体认知决策原型。
> 个人学习向项目，探索 Agent 协作 / 辩论 / 裁决 / 记忆 / 知识进化的工程化落地。

主实现位于 [`agri-ai/`](agri-ai/)，旧版单体 MVP（`agri-agent-mvp/`）已归档移除。

## 项目简介

ACIS 不是一个聊天机器人或病害分类器，而是一个具备 **观察 → 理解 → 推理 → 辩论 → 裁决 → 执行 → 学习** 闭环的农业认知决策系统原型。多个领域专家 Agent（病理 / 栽培 / 气象 / 经济 / 生态）并行推理，经 Debate 协调器与 Critic 反驳后，由 Judge 基于 RAG 记忆与知识图谱（KG）硬约束给出结构化裁决。

当前版本：**ACIS 2.0 认知进化版（2026-07）**，回归测试（`smoke_eval` + 12 场景 `fixture_eval`）保持全绿。

## 核心特性

- **多专家并行 + 多轮辩论**：专家 Agent 反事实推理；置信度落在 0.6~0.85 且存在冲突时进入 rebuttal 第二轮辩论
- **Judge 裁决**：融合 KG 硬约束与 RAG 记忆；检测集体忽略（KG 存在但专家均未提及则争议分 +0.2 并下调置信度）
- **记忆层**：RAG（内存 / Qdrant）+ 知识图谱（Neo4j / 内置 DISEASE_DB）+ 案例记忆
- **知识进化**：Judge 发现证据充分但 KG 缺失关系时自动提议三元组（草稿审核闭环）
- **经验回放**：`decisions` 表记录 outcome，OutcomeAgent 召回同作物有效历史案例
- **置信度校准**：IsotonicRegression / Platt Scaling 在 Judge 融合前校准各专家置信度
- **优雅降级**：LangGraph 不可用回退规则编排；Neo4j / Qdrant / DeepSeek 不可用时自动回退离线模式

## 系统架构

```
context -> perception -> memory -> experts(并行) -> debate -> critic -> judge
                                ↑___________ rebuttal(条件循环) ___________|
```

| 目录 | 说明 |
| --- | --- |
| `agri-ai/gateway/` | FastAPI 路由入口 |
| `agri-ai/agents/` | 领域专家 Agent（病理 / 栽培 / 气象 / 经济 / 生态 / Judge / Outcome） |
| `agri-ai/debate/` | Debate 协调器 + Critic 反驳轮次 |
| `agri-ai/kg_adapter.py` | 知识图谱适配器（三元组 + 硬约束 + 草稿提议） |
| `agri-ai/orchestrator.py` `workflow.py` | 主编排入口（LangGraph 主图 + 规则回退） |
| `agri-ai/rag/` | 知识检索（内存 / Qdrant） |
| `agri-ai/rule_engine/` | 传感器模拟 / 异常检测 / 规则版 Router |
| `agri-ai/storage/` | SQLite 持久化（decisions + outcome 反馈闭环） |
| `agri-ai/evals/` | 回归评估脚本 |
| `agri-ai/ui/` | Streamlit UI + TUI 演示界面 |

## 快速开始

```powershell
cd agri-ai
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='.'

# 运行主编排（默认 LangGraph 主图，离线可跑）
python orchestrator.py "温室A番茄叶片黄斑，叶背有灰色霉层，如何处理？"

# TUI 交互演示（内置 5 个演示场景）
python -m ui.tui

# API 服务
uvicorn gateway.app:app --reload
```

可选依赖：DeepSeek（结构化 Judge / Critic）、Neo4j（知识图谱）、Qdrant（向量检索）。未配置时均自动回退离线模式。详见 [`agri-ai/README.md`](agri-ai/README.md)。

## 回归测试

```powershell
cd agri-ai
$env:PYTHONPATH='.'
python evals/smoke_eval.py      # 轻量冒烟
python evals/fixture_eval.py    # 12 个确定性场景断言
```

## 文档

- [`agri-ai/docs/ACIS.md`](agri-ai/docs/ACIS.md) — ACIS 宪法（最高级规范）
- [`agri-ai/docs/architecture.md`](agri-ai/docs/architecture.md) — 系统架构
- [`agri-ai/docs/roadmap.md`](agri-ai/docs/roadmap.md) — 版本路线图
- [`agri-ai/docs/rfc/`](agri-ai/docs/rfc/) — RFC 设计规范集
- [`agri-ai/README.md`](agri-ai/README.md) — 详细运行说明与环境变量

## 技术栈

Python · LangGraph · FastAPI · SQLite · Neo4j · Qdrant · DeepSeek · Streamlit / Rich TUI

## License

[MIT](LICENSE)