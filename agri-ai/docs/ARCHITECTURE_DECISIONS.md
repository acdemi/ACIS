---
document: Architecture Decisions
project: ACIS
phase: Architecture Freeze
version: 1.0
status: Active
based_on:
  - IMPLEMENTATION_PLAN.md
  - RFC-000 ~ RFC-010
  - ACIS.md
last_updated: 2026-07-10
---

# ACIS Architecture Decisions（ADR）

> **Architecture Freeze 阶段决策记录。**
> 本文档不修改任何 RFC 内容。所有 RFC 文本修订统一延后至 Freeze 解除后的修订轮次。
> ADR 格式：Problem / Decision / Reason / Impact。
> 状态图例：Proposed = 待确认；Accepted = 已确认/已实施。

## ADR 索引

| ADR | 处理冲突 | 主题 | 状态 |
|---|---|---|---|
| ADR-001 | C1 | RFC-001 作为唯一架构源 | Accepted（已实施） |
| ADR-002 | C2 / C3 | World Model 定位为预留接口 | Proposed |
| ADR-003 | C4 / C5 | 状态机组合规约与模块边界 | Proposed |
| ADR-004 | C6 | Executive / Execution 术语澄清 | Proposed |

---

## ADR-001: RFC-001 作为唯一架构源

- **处理冲突**：C1
- **状态**：Accepted（已实施）
- **日期**：2026-07-10
- **相关**：RFC-001、architecture.md、RFC-002/003/004/005

### Problem
RFC-001（System Architecture）为 0 字节空文件，但 RFC-002/003/004/005 均声明 `Depends On: RFC-001`。架构内容仅存于非 RFC 文档 `architecture.md`，导致依赖链根部断裂、"唯一架构源"分裂为空 RFC + 非 RFC 文档。

### Decision
将 `architecture.md` 全部内容正式纳入 RFC-001，作为权威 System Architecture RFC（Status: Accepted，version 2.0.0），并与 RFC-000（模板）、RFC-002（状态归属）、RFC-003（Agent 类别）、RFC-004（记忆类型）对齐。`architecture.md` 降级为指向 RFC-001 的说明文档（status: Superseded）。

### Reason
- 恢复依赖链完整性：RFC-002/003/004/005 已正确引用 RFC-001，仅需补全 RFC-001 本体。
- 建立 ACIS 宪法要求的单一架构真相源。
- `architecture.md` 内容成熟，纳入即可，无需重写。

### Impact
- RFC-001 成为架构唯一权威；`architecture.md` 为入口指针。
- ACIS.md 与 RFC-000 模板中对 `architecture.md` 的引用经指针解析到 RFC-001，相关措辞更新延后至后续修订轮。
- RFC-002/003/004 无需改动。
- 解决 IMPLEMENTATION_PLAN §6 C1。

---

## ADR-002: World Model 定位为预留接口（未来实现）

- **处理冲突**：C2 + C3
- **状态**：Proposed（待确认）
- **日期**：2026-07-10
- **相关**：RFC-010、RFC-008、RFC-007、RFC-004、RFC-001 §2.6、roadmap

### Problem
1. **C2**：RFC-010 §摘要/结论称 World Model 为"核心基础"，§12 称 Planner 使用 World Model；但 §19 依赖链将 World Model 置于最末（Executive Agent 之后）`RFC-004->006->007->008->009->010`，与 §12 矛盾--支持者不应位于被支持者之后。
2. **C3**：RFC-010 称"核心基础"，RFC-001 §2.6 称"预留接口/未来实现"，roadmap 将其置于 ACIS 3.0，"基础"与"3.0 远期"语义冲突。

### Decision
1. World Model 定位为**预留接口，未来实现**（ACIS 3.0），不纳入 MVP，不是当前认知闭环的必需层（以 RFC-001 §2.6 为权威）。
2. Planner 与 World Model 的关系为**可选增强**而非硬依赖：Phase 1 Planner 基于 Memory + Decision Pipeline 工作，不阻塞于 World Model；Phase 3 World Model 完成后向 Planner 提供预测/仿真能力。
3. 依赖方向以 §12 为准：World Model 支持 Planner/Learning，处其上游；RFC-010 §19 线性排序需在未来修订中更正为"World Model 上游支持 Planner"，但作为可选能力。
4. MVP 仅在 RFC-002 §10 保留 `world_model` 命名空间，不实现实体。

### Reason
- 用户指示"world model 先留下接口就行，考虑在未来实现"。
- 与 roadmap ACIS 3.0、RFC-001 §2.6"预留接口"一致。
- "可选增强"同时化解 C2（依赖方向）与 C3（实现时序）：Planner（Phase 1）不必等待 World Model（Phase 3）。
- 避免给 MVP 引入 World Model 复杂度。

### Impact
- MVP / Phase 1 / Phase 2 不含 World Model；仅保留接口与命名空间。
- Planner（Phase 1）预留 World Model 接入钩子，Phase 3 启用预测/仿真。
- RFC-010 文本（§摘要"核心基础"、§19 排序）需在未来修订轮更正；freeze 期间不改 RFC。
- 解决 IMPLEMENTATION_PLAN §6 C2、C3。

---

## ADR-003: 状态机组合规约与模块边界

- **处理冲突**：C4 + C5
- **状态**：Proposed（待确认）
- **日期**：2026-07-10
- **相关**：RFC-002、RFC-006、RFC-008、RFC-009、RFC-001

### Problem
1. **C4**：RFC-002 工作流生命周期为线性（Created->...->Archived，无重规划），与 RFC-008 Planner（含 Replanning）、RFC-009 Executive（含 Failed->Recovery）无法直接组合；五套生命周期/状态机（RFC-002/006/008/009 + 认知环）嵌套关系未定义。
2. **C5**：RFC-002 将 Decision 归 Judge、Execution 归 Execution Layer；但 RFC-006 Decision Pipeline（Context Builder/Reasoning Core/Decision Maker/Action Planner）超出"Judge"，RFC-009 Executive Agent 超出"Execution Layer"；且 RFC-006 "Action Planner"、RFC-008 "Plan Generator"、RFC-009 "Task Controller" 职责重叠。

### Decision

**A. 状态机组合（C4）**
- RFC-002 工作流生命周期为**外层规范状态机**（canonical）；RFC-008/006/009 为运行于其特定阶段的**内层循环**。
- 阶段映射：
  - Planner（RFC-008）运行于 Created->Perceived 过渡（Context 阶段，owner=Planner）。
  - Decision Pipeline（RFC-006）运行于 Reasoned->Judged（产出候选，Judge 终止裁决）。
  - Executive Agent（RFC-009）运行于 Judged->Executed（Action Loop）。
  - Learning（RFC-007）运行于 Executed->Evaluated->Archived。
- 向 RFC-002 增加**向后兼容的附加转移**：失败时 `Executed -> Recovery -> (Perceived|Planned)` 支持重规划；为 Planner 增加 "Planned" 子状态（归于 Context/Planner）。此为扩展而非重写。

**B. 模块边界（C5）**
- RFC-006 Decision Pipeline ⊃ Judge：Context Building/Reasoning/Evaluation 产出候选，Judge 为其**终止裁决阶段**；RFC-002 "Decision" 状态 = Judge 输出的不可变 Decision 对象。
- 行动规划按层级分工（消除重叠）：
  - RFC-008 Plan Generator = **任务级**（目标->任务图），决策前，Context/Planner 阶段。
  - RFC-006 Action Planner = **决策级**（选定方案->行动计划），裁决时。
  - RFC-009 Task Controller = **执行级**（逐步执行行动计划），Execution 阶段。
- RFC-009 Executive Agent 即 Execution Layer 的执行代理，拥有 Execution 阶段；Outcome 仍归 Feedback Layer。

### Reason
- 单一外层状态机（RFC-002）保留为真相源，内层循环按阶段归属，避免多套并行生命周期冲突。
- 附加 Recovery 转移以兼容重规划，且为向后兼容扩展（符合 RFC-002 §13 版本语义：Minor 级新增）。
- 按"任务级/决策级/执行级"切分行动规划，消除三者重叠，同时不改 RFC-002 归属（Judge 仍拥有最终 Decision）。

### Impact
- Orchestrator 实现外层生命周期；Planner/Decision/Executive 作内层循环。
- RFC-002 需在后续修订轮增补：(a) Planned 子状态，(b) Recovery/Replan 转移（向后兼容扩展）。
- RFC-006/008/009 需在后续修订轮按上述边界互引用澄清；freeze 期间不改 RFC 文本。
- 解决 IMPLEMENTATION_PLAN §6 C4、C5。

---

## ADR-004: Executive / Execution 术语澄清

- **处理冲突**：C6
- **状态**：Proposed（待确认）
- **日期**：2026-07-10
- **相关**：RFC-001 §2.1/§2.9、RFC-009

### Problem
RFC-001 同时存在"Executive Intelligence Layer"（规划/协调）与"Execution Layer"（行动）。RFC-009 标题"Executive Agent"近似"Executive Intelligence"，但其内容（Tool Executor/Action Loop/Recovery）实为 Execution Layer，易被误归入 Executive Intelligence Layer。

### Decision
1. "Executive Intelligence Layer" = 协调/规划层（Orchestrator、Gateway、Planner），依据 RFC-001 §2.1。
2. "Execution Layer" = 行动层；**RFC-009 Executive Agent 归属 Execution Layer**，其语义为"执行行动的代理"，非 Executive Intelligence。
3. freeze 期间保留 RFC-009 标题原文不改；本 ADR 为权威解释。后续修订轮可考虑将 RFC-009 标题改为"Execution Agent Architecture"以彻底消除歧义。

### Reason
- 消除 Executive/Execution 混淆，使 RFC-009 内容与其所属层一致。
- 保留 RFC 文本以遵守 freeze；以 ADR 治理解释权。
- 与 ADR-003 的"RFC-009 = Execution 阶段执行代理"一致。

### Impact
- 实现者将 RFC-009 视为 Execution Layer 组件，不与 Planner/Orchestrator（Executive Intelligence）混淆。
- 文档交叉引用按此解释澄清。
- RFC-009 可能的改名延后至 freeze 解除后。
- 解决 IMPLEMENTATION_PLAN §6 C6。

---

# 决策生效与后续

- **ADR-001** 已实施（RFC-001 已填充、`architecture.md` 已降级为指针）。
- **ADR-002 ~ ADR-004** 为 Proposed，经确认后生效。
- 所有 ADR 涉及的 RFC 文本修订统一延后至 Architecture Freeze 解除后的修订轮，包括：
  - RFC-002：Planned 子状态 + Recovery/Replan 转移（ADR-003）。
  - RFC-006/008/009：按层级边界互引用澄清（ADR-003）。
  - RFC-009：可选改名"Execution Agent Architecture"（ADR-004）。
  - RFC-010：World Model 依赖方向更正与"核心基础"措辞软化（ADR-002）。
- **freeze 期间不修改任何 RFC 内容。**
