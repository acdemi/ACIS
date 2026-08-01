# ACIS System Architecture

## 分层架构
- 用户层 (UI/TUI/API)
- 编排层 (Orchestrator + LangGraph Workflow)
- 感知层 (视觉、传感器、天气)
- 认知层 (病理、栽培、经济、生态 Agent)
- 记忆层 (RAG + KG + 案例库)
- 辩论与裁决层 (Debate/Critic/Meta-Critic/Judge)
- 决策输出与持久化

## 通信协议
所有 Agent 通过 Orchestrator 的全局 State 通信，禁止 Agent 间直接调用。

## 冻结模块
参见 context/ARCHITECTURE_STATE.md