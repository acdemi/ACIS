---
document: Roadmap
project: ACIS
version: 2.0
status: Archived
priority: Reference
last_updated: 2026-08-08
depends_on:
  - ACIS.md
---

# ACIS Development Roadmap

> **归档（2026-08-08）**：本文档为历史路线图，已归档。
> 当前路线以 `context/CURRENT_SPRINT.md` 为唯一事实源。

> This roadmap describes the planned evolution of ACIS.
>
> It is intentionally high-level.
>
> Detailed implementation plans belong to RFCs and Phase documents.

> **状态更新（2026-08-07）**：当前版本 **ACIS 2.1E（Evidence Platform）**，
> Sprint 01 ~ 04.5C 已完成，当前处于 **Evidence Review Gate**（等待架构师审查），
> 通过后进入 Sprint 05（Experiment Manager）。活跃的 Sprint 路线图以
> `context/ROADMAP.md` 与 `context/CURRENT_SPRINT.md` 为准；
> 本文档保留 ACIS 2.0 / 2.1 / 3.0 的版本愿景参考。

---

# Vision

The long-term goal of ACIS is to become an agricultural cognitive operating system.

Development follows incremental evolution rather than large rewrites.

---

# Current Status

| 项 | 值 |
|---|---|
| Current Version | ACIS 2.1E（Evidence Platform） |
| Status | Stable Development |
| Current Focus | Evidence Platform：评测、基准、能力覆盖与运行时能力度量（Unified Trace / Runner / Benchmark / Ablation / Capability Framework / Capability Evaluation Engine） |
| Completed | ✓ Multi-Agent Workflow ✓ Debate Engine ✓ Judge ✓ Meta-Critic ✓ Memory Layer ✓ Knowledge Evolution ✓ Outcome Replay ✓ Confidence Calibration ✓ Planner ✓ Tool Router ✓ Unified Trace ✓ Evaluation Runner ✓ Benchmark Framework ✓ Ablation Framework ✓ Capability Framework ✓ Verifiable Capability Contract ✓ Capability Evaluation Engine |

---

# Version Roadmap

# ACIS 2.1

Theme

Workflow Intelligence

Objective

Improve planning and execution.

Major Goals

✓ Planner

✓ Tool Layer Standardization (MCP)

✓ Better Workflow Scheduling

✓ More Stable State Management

Success Criteria

Workflow becomes more flexible without increasing complexity.

## ACIS 2.2

Theme

Learning System

Objective

Allow ACIS to continuously improve.

Major Goals

✓ Feedback Loop

✓ Better Procedural Memory

✓ Experience Ranking

✓ Confidence Optimization

Success Criteria

Past experience measurably improves future decisions.

# ACIS 3.0

Theme

Digital Agriculture

Objective

Expand from diagnosis to management.

Major Goals

✓ Digital Twin Interface

✓ World Model

✓ IoT Execution

✓ Decision Simulation

✓ Farm Management

Success Criteria

Support complete agricultural decision workflows.

# Out of Scope

The following capabilities are intentionally not planned in the near future.

- Training proprietary LLMs

- Building custom databases

- Replacing existing AI frameworks

- Developing hardware platforms

ACIS focuses on system integration and cognitive architecture.

# Development Principles

Development priorities:

1. Stability

2. Simplicity

3. Maintainability

4. Explainability

5. Extensibility

New features should only be introduced when they solve existing limitations.

# Release Strategy

Major Version: Architecture evolution

Minor Version: New capabilities

Patch Version: Bug fixes

Documentation updates may occur independently of software releases.

# Completion Criteria

A roadmap item is considered complete only when:

- RFC accepted
- Implementation merged
- Regression tests pass
- Documentation updated
- Interfaces remain compatible

# Future

Future directions will be evaluated according to:

- Community feedback
- Research progress
- Open-source ecosystem evolution
- Agricultural industry needs

前瞻性探索规格见 RFC-011（认知循环）/ RFC-012（自我模型与身份）/ RFC-013（目标与动机）/ RFC-014（智能体生态与市场），对应 ACIS 4.x/5.x 愿景，暂不在本 roadmap 版本计划内。

The roadmap is intentionally conservative.

Predictability is preferred over ambitious planning.
