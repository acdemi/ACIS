# agri-ai 项目审计报告 v2

> 审计日期：2026-07-11
> 代码位置：`E:\knowledge_database\agent协作模式初探\agri-ai\`

---

## 一、总体概况

| 指标 | 数值 |
|------|------|
| Python 文件数 | **51** |
| 总代码行数 | **7,578** |
| Agent 数 | 13（感知层 3 + 记忆层 4 + 专家层 5 + 裁决层 1） |
| 独立模块 | 16（orchestrator + workflow + 4 debate + 4 kg/rag + 2 storage + 2 utils + eval） |
| 评估用例 | 14（smoke 3 + fixture 11） |
| 外部依赖 | 3（FastAPI / Streamlit / langgraph 可选） |

---

## 二、架构升级回溯（本次）

### 2.1 新增模块

| 模块 | 文件 | 行数 | 功能 |
|------|------|------|------|
| 经验回放 Agent | `agents/outcome_agent.py` | 42 | 查询历史 SQLite 中 outcome=有效 的案例，提取行动建议 |
| 经济分析 Agent | `agents/economic_agent.py` | 150+ | 内置价格常量表，成本分析 + 不同措施经济收益对比 |
| 生态评估 Agent | `agents/ecology_agent.py` | 120+ | 农药-天敌对照表，化学农药生态影响评估 + 替代方案 |
| 置信度校准 | `utils/confidence_calibration.py` | 200+ | Isotonic Regression / Platt Scaling 校准各专家置信度 |
| 校准数据生成 | `utils/generate_calibration.py` | 80+ | 基于 fixture + 随机种子生成校准数据快照 |
| SQLite 持久化 | `storage/repository.py` | 80+ | 每次决策自动保存到 SQLite，带 decision_id |
| 数据库初始化 | `storage/db.py` | ~40 | 建表 DDL |
| 环境变量加载 | `_env.py` | 32 | 从 `.env` 注入密钥，取代硬编码 |

### 2.2 架构变化

**ACIS 2.0 参考架构**：
- 新增经济 + 生态 Agent，由环境变量 `AGRI_AI_EXTRA_EXPERTS` 控制开关（默认开）
- 新增经验回放 Agent，在记忆层与 RAG / KG / 历史案例并列
- 新增 `counterfactual` 字段到 `AgentOutput`，支持反事实推理
- 新增 `decision_id` 到 `DecisionOutput`，关联 SQLite 持久化

**工程约束**：
- `_env.py` 自动从 `.env` 加载密钥，`DEEPSEEK_API_KEY` / `NEO4J_PASSWORD` 移出源码
- `AGRI_AI_PERSIST=0` 可关闭 SQLite 持久化
- `AGRI_AI_CALIBRATION=0` 可关闭置信度校准
- `AGRI_AI_EXTRA_EXPERTS=0` 可关闭经济/生态 Agent

### 2.3 清理

- `orchestrator.py` 从 987 行降至 280 行（拆出 11 个 Agent 文件 + 1 个 DebateEngine）
- `debate/agents/` 下误放的 weather.py / vision.py 已复制到 `agents/` 下
- `debate/coordinator.py` 改为从 `debate/engine` 导入（不再引用 orchestrator）

---

## 三、项目水平评估

### ✅ 成熟度

| 维度 | 评估 | 依据 |
|------|------|------|
| 架构清晰度 | ★★★★☆ | 4 层（感知→记忆→专家→裁决）职责分明，每个 Agent 单一文件 |
| 可扩展性 | ★★★★☆ | 新增 Agent 只需写一个文件、在 orchestrator 注册、加入 run_rules 流程 |
| 可测试性 | ★★★★☆ | 14 个回归用例，fixture 固定随机种子，断言决策形状 |
| 可观测性 | ★★★★☆ | DecisionOutput 包含完整推理链 + KG 引用 + Critic 反驳轮次 |
| 降级鲁棒性 | ★★★★★ | 5 条自动降级链路（Neo4j→内存 / Qdrant→内存 / LangGraph→规则 / LLM→规则 / SQLite→静默） |
| 工程约束 | ★★★★☆ | 4 个环境变量开关，`.env` 自动加载，密钥脱离源码 |
| 文档完整性 | ★★★☆☆ | README 详细，但部分新模块（经济/生态/校准/存储）缺乏独立文档 |
| 领域覆盖 | ★★★☆☆ | 作物只覆盖番茄/甜菜/棉花，病害库 11 种。视觉模型未接入 |

### ✅ 自动降级链路（已验证）

| 服务 | 降级目标 | 触发条件 |
|------|---------|---------|
| Neo4j / AgriKG | DISEASE_DB 合成三元组 | 容器未启动 / 密码不对 |
| Qdrant 向量库 | 内存知识库 | 容器未启动 |
| LangGraph 主图 | `run_rules()` 规则编排 | langgraph 包未安装 / 执行异常 |
| DeepSeek Judge | `_run_rule_judge()` 规则裁决 | API Key 未设置 / 网络不可达 / 异常 |
| DeepSeek Critic | `_rules_resolve()` 规则反驳 | API Key 未设置 / 网络不可达 / 异常 |
| SQLite 持久化 | 静默跳过 | `AGRI_AI_PERSIST=0` / 异常 |
| 经济/生态 Agent | 不加入 expert_outputs | `AGRI_AI_EXTRA_EXPERTS=0` / 异常 |
| 置信度校准 | 透传原始置信度 | `AGRI_AI_CALIBRATION=0` / sklearn 不可达 |

---

## 四、目标执行情况

### 已实现

| 目标 | 状态 | 验证 |
|------|------|------|
| MCP 架构设计 | ✅ 完成 | 5 个 MCP Server 定义，kg/mcp_server.py 完整实现 |
| Agent Router 调度 | ✅ 完成 | 13 个 Agent 编排，感知→记忆→专家→裁决 4 层 |
| DeepSeek 集成 | ✅ 完成 | Judge + Critic 双模式，规则+LLM 自动切换 |
| Neo4j + AgriKG 集成 | ✅ 完成 | 导入脚本 + kg_adapter 混合查询，自动降级 |
| 三层异常检测 | ✅ 完成 | Isolation Forest + LSTM + Chronos 架构 |
| Debate & Judge | ✅ 完成 | 5 种冲突类型 + Critic 反驳降权 + KG 一致性校验 |
| Web UI | ✅ 完成 | Streamlit 全功能界面，不依赖 TUI |
| SQLite 持久化 | ✅ 完成 | 每次决策自动保存，失败静默降级 |
| 置信度校准 | ✅ 完成 | Isotonic Regression / Platt Scaling |
| 经济/生态 Agent | ✅ 完成 | ACIS 2.0 参考架构实现 |
| 环境变量约束 | ✅ 完成 | .env 加载 + 4 个开关变量 |
| 评估回归 | ✅ 完成 | 14 个用例，固定种子，expect_critic 断言 |

### 未实现

| 目标 | 状态 | 原因 |
|------|------|------|
| Swin-Tiny 视觉模型 | ❌ 未接入 | VM 无 torch，代码已就绪，conda 环境就位即生效 |
| Chronos 时序模型 | ❌ 未接入 | 当前为线性外推模拟，`pip install chronos-forecasting` 后替换 |
| 真实传感器协议 | ❌ 未开发 | 当前全模拟，无硬件/MQTT 接入 |
| 作物覆盖扩展 | ❌ 部分实现 | 仅番茄/甜菜/棉花，黄瓜残留兼容 |
| 多用户 + 鉴权 | ❌ 未开发 | Gateway 无认证 |
| 实时数据流 | ❌ 未开发 | 传感器数据为每次调用时生成 |

---

## 五、下一步建议

**P0：视觉模型接入** — conda 环境配好 torch 后，`agents/vision.py` 的 `_get_classifier()` 自动下载 Swin-Tiny 并推理，不需要改代码

**P1：Chronos 替换** — `pip install chronos-forecasting` 后，`rule_engine/sensor_anomaly.py` 的 Layer3 从线性外推替换为真实模型

**P2：作物覆盖扩展** — DISEASE_DB 当前只有 11 种病害，扩展后 RAG / KG / 病理 Agent 同时受益

**P3：经济/生态 Agent 文档** — 新增的 ACIS 2.0 模块缺乏独立文档，README 需更新