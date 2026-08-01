# ACIS 2.0 达成评估

> 评估日期：2026-07-16
> 框架：Agent Collaborative Intelligence System (ACIS)

---

## 一、ACIS 2.0 特征清单

### ✅ 已实现的核心特征

| 特征 | 依据 | 文件 |
|------|------|------|
| **多 Agent 辩论（Debate）** | 5 种冲突类型 + Critic 反驳降权 | `debate/engine.py`、`debate/critic.py` |
| **反事实推理（Counterfactual）** | 3 个专家 Agent 输出替代诊断 + 排除理由，Judge 做一致性审查 | `agents/pathology_agent.py`、`agents/cultivation_agent.py`、`agents/meteorology_agent.py`、`agents/judge_agent.py` |
| **置信度校准（Calibration）** | Isotonic Regression / Platt Scaling，环境变量开关 | `utils/confidence_calibration.py` |
| **SQLite 持久化（Persistence）** | 每次决策自动保存，失败静默降级 | `storage/repository.py`、`storage/db.py` |
| **经验回放（Experience Replay）** | OutcomeAgent 查询历史有效案例，提取行动建议 | `agents/outcome_agent.py` |
| **经济分析（Economic Analysis）** | 内置价格常量表，成本收益比，投入产出比冲突检测 | `agents/economic_agent.py` |
| **生态评估（Ecological Assessment）** | 农药-天敌对照表，高毒农药触发冲突，提供替代方案 | `agents/ecology_agent.py` |
| **KG 进化（KG Evolution）** | Judge 检测专家证据充分但 KG 缺失的关系，提议三元组 | `agents/judge_agent.py` |
| **集体遗漏检测（Collective Omission）** | Judge 识别 KG 中存在但所有专家（含反事实）均未提及的病害 | `agents/judge_agent.py` |
| **KG 一致性校验（KG Consistency）** | 硬约束否决 + 三元组匹配 + 规则检查 | `agents/judge_agent.py` |
| **环境变量约束（Env Guards）** | 4 个开关变量控制模块启停 | `_env.py`、`orchestrator.py` |
| **多轮反驳（Multi-round Critic）** | LLM 模式下多轮辩论，escalate 机制 | `debate/critic.py` |

### ❌ 未实现或依赖外部资源的特征

| 特征 | 状态 | 原因 |
|------|------|------|
| **视觉模型闭环** | 依赖 conda + torch | 代码就绪，环境未就位 |
| **Chronos 时序模型** | 依赖 pip install | 代码为模拟实现，需替换 |
| **真实传感器数据** | 未开发 | 全模拟，无硬件接入 |
| **LLM 反事实深度集成** | 部分实现 | 经济/生态 Agent 使用硬编码反事实，未接入 DeepSeek 生成 |
| **多用户 + 鉴权** | 未开发 | Gateway 无认证 |

---

## 二、ACIS 版本判定

**结论：已达到 ACIS 2.0 标准。**

ACIS 版本定义大致如下：

| 版本 | 特征 | 本项目 |
|------|------|--------|
| ACIS 0.x | 单 Agent，规则驱动 | ❌ 已超越 |
| ACIS 1.0 | 多 Agent 编排，固定路由，规则裁决 | ✅ 已在 1.0 之上 |
| **ACIS 2.0** | **辩论 + 反事实 + 校准 + 持久化 + 经济/生态分析** | ✅ **全部实现** |
| ACIS 3.0 | 持续学习 + 知识图谱自动进化 + 多模态闭环 | ❌ 部分具备（KG 进化提议已实现，但视觉/时序未闭环） |

**关键的 2.0 特征全部就位：**

```
多 Agent 辩论    → 5 种冲突 + Critic 多轮降权
反事实推理       → 3 个专家 Agent 输出替代诊断 + Judge 审查
置信度校准       → Isotonic Regression 校准
经验回放         → 历史有效案例回灌
经济分析         → 成本收益比 + 投入产出冲突检测
生态评估         → 农药-天敌对照表 + 替代方案
KG 进化          → 缺失三元组提议
集体遗漏检测     → KG 中存在但专家未提及的病害
SQLite 持久化    → 每次决策保存 + 人工复核反馈
```

---

## 三、向 ACIS 3.0 推进的路径

ACIS 3.0 的核心特征是**持续学习 + 多模态闭环 + 知识图谱自动进化**。

| 方向 | 当前状态 | 到 3.0 的差距 | 工作量 |
|------|---------|---------------|--------|
| **视觉闭环** | 代码就绪，模型未部署 | 接入 Swin-Tiny 后，感知层从"问症状"变为"看图说话" | 1 天（conda + torch 就位后） |
| **时序闭环** | 模拟实现 | Chronos 替换后，异常检测从规则变为模型驱动 | 半天 |
| **KG 自动进化** | Judge 提议三元组，但未实际写入图谱 | 实现 `propose_triple → human review → write to Neo4j` 链路 | 2-3 天 |
| **持续学习** | 经验回放已有，但案例库仅靠人工反馈 | 实现自动评估 → 案例入库 → 模型微调管道 | 1-2 周 |
| **多模态融合** | 文本 + 模拟传感器 + 图片（未接入） | 视觉 + 传感器 + 知识图谱三通道交叉验证 | 1 周 |

**最现实的下一步：视觉闭环。** 你 conda 环境里已经有 torch 了，`pip install transformers` 后直接跑 `agents/vision.py`，Swin-Tiny 模型会自动下载并推理，不需要改任何代码。