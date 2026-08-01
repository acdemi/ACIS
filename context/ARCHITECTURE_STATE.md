# ACIS Architecture State

> Last updated: 2026-08-01
> This file is the single source of truth for module stability.

## Module Status

| Module | Status | Version | Notes |
|--------|--------|---------|-------|
| Planner | Frozen | 2.1 | |
| Judge | Frozen | 2.1 | |
| Debate | Frozen | 2.1 | |
| Critic | Frozen | 2.1 | |
| Tool Router | Frozen | 2.1 | |
| Memory (RAG/KG/Case) | Frozen | 2.1 | |
| DecisionOutput | Frozen | 2.1 | |
| Unified Trace | Frozen | 2.1E | Sprint 01 complete |
| Perception Agents | Frozen | 2.1 | |
| Orchestrator | Stable | 2.1 | Allowed limited changes for integration |
| Evals/Runner | Active | 2.1E | Sprint 02 complete |
| Ablation Framework | Active | 2.1E | Sprint 04 complete |
| Benchmark Framework | Frozen | 2.1E | Sprint 03-04 complete（9 datasets / 61 cases） |
| Capability Framework | Active | 2.1E | Sprint 04.5A complete；61 cases 标注待审查 |
| Executor | Not Started | 2.2 | |
| Learning Runtime | Not Started | 2.2 | |

## Frozen Definition

- No new public methods
- No signature changes
- No new dependencies
- Bug fixes must be approved by Chief Architect
