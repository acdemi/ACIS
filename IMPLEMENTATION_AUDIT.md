# 项目审计报告 v3

> 审计日期：2026-07-16 | 代码根：`E:\knowledge_database\agent协作模式初探\`

---

## 一、全景

```
agent协作模式初探/
├── orchestrator.py       ← 主编排入口
├── _env.py               ← 环境变量加载
├── kg_adapter.py         ← KG 适配器
├── workflow.py           ← LangGraph 图
├── requirements.txt
├── docker-compose.yml
│
├── agents/          (18 文件)  ← 感知+记忆+专家+裁决 Agent
├── debate/           (4 文件)  ← DebateEngine + Critic
├── rag/              (3 文件)  ← 知识库 + RAG 检索
├── kg/               (2 文件)  ← Neo4j MCP Server
├── rule_engine/      (5 文件)  ← 传感器模拟 + 异常检测
├── storage/          (3 文件)  ← SQLite 持久化
├── ui/               (4 文件)  ← TUI + Web UI
├── gateway/          (2 文件)  ← FastAPI
├── evals/            (3 文件)  ← 回归测试
├── utils/            (4 文件)  ← 置信度校准（已废弃）
├── scripts/          (1 文件)  ← AgriKG 导入
├── neo4j/            (Docker 数据)
├── docs/             (架构文档)
│
├── agri-ai/          (已空，仅剩 .venv)
└── 5 个 .md 文档
```

**代码量：53 个 Python 文件，7,577 行。** 全部 git 跟踪（部分 untracked 文件是本地新增未提交）。

---

## 二、活代码 vs 死代码

### 活代码（44 个文件）

**核心链路**（orchestrator.py 直接 import，15 个）：
`types / sensor_agent / weather_agent / vision_agent / rag_memory_agent / kg_agent / case_memory_agent / outcome_agent / pathology_agent / meteorology_agent / cultivation_agent / economic_agent / ecology_agent / judge_agent / debate.engine`

**基础设施**（15 个）：
`orchestrator.py / workflow.py / kg_adapter.py / _env.py / agents/weather.py / agents/vision.py / rag/knowledge_base.py / rag/retriever.py / kg/mcp_server.py / rule_engine/sensor_anomaly.py / rule_engine/sensor_simulator.py / rule_engine/router.py / scripts/import_agrikg.py / storage/db.py / storage/repository.py`

**界面层**（3 个）：
`ui/tui.py / ui/web_app.py / gateway/app.py`

**评估**（3 个）：
`evals/smoke_eval.py / evals/fixture_eval.py / evals/fixtures.py`

**包声明**（5 个 __init__.py，建议保留）：
`debate/ / gateway/ / rag/ / rule_engine/ / ui/`

### 死代码（8 个文件，可删）

| 文件 | 行数 | 死因 |
|------|------|------|
| `debate/coordinator.py` | 6 | re-export，零引用 |
| `agents/vision_test.py` | 204 | 零引用 |
| `rule_engine/demo.py` | 137 | 零引用 |
| `ui/app.py` | 36 | 被 web_app.py 取代 |
| `utils/confidence_calibration.py` | 122 | 零引用，untracked |
| `utils/generate_calibration.py` | 86 | 零引用，untracked |
| `utils/calibration_data.json` | — | 零引用，untracked |
| `utils/__init__.py` | 1 | 零引用，untracked |

---

## 三、数据流

```
用户输入 → orchestrator.run()
              ├─ _run_core()
              │     ├─ LangGraph 主图（失败降级）
              │     └─ run_rules()（规则编排）
              │           ├─ 感知层: vision / sensor / weather
              │           ├─ 记忆层: RAG / KG / 历史案例 / 经验回放
              │           ├─ 专家层: 病理 / 气象 / 栽培 / 经济 / 生态
              │           ├─ Debate → Critic → Judge
              │           └─ DecisionOutput
              └─ _persist() → SQLite
```

13 个 Agent 依次调用，数据经 `AgentOutput` 传递，最终 `JudgeAgent` 汇聚为 `DecisionOutput`。全链路已验证通过。

---

## 四、待清理清单

```powershell
cd E:\knowledge_database\agent协作模式初探

# 死代码（git 跟踪）
git rm debate/coordinator.py
git rm agents/vision_test.py
git rm rule_engine/demo.py
git rm ui/app.py

# 废弃目录（untracked）
Remove-Item -Recurse -Force utils
Remove-Item -Recurse -Force data

git commit -m "cleanup: 移除死代码和废弃目录"
```

---

## 五、项目画像

| 维度 | 评估 |
|------|------|
| 代码健康度 | 53 活 / 8 死，死代码率 13% |
| 架构层次 | 4 层（感知→记忆→专家→裁决），Agent 单一文件 |
| 自动降级 | 6 条链路（Neo4j / Qdrant / LangGraph / Judge / Critic / SQLite） |
| 评估覆盖 | 14 个回归用例，固定种子，断言决策形状 |
| 作物覆盖 | 4 种（番茄/黄瓜/甜菜/棉花），病害库 11 种 |
| 工程约束 | _env.py 管理密钥，4 个 AGRI_AI_* 开关变量 |
| Git 状态 | 44 文件跟踪，8 文件 untracked，index 干净 |