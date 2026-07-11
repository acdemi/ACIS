---
rfc: 001
title: System Architecture Specification
status: Accepted
version: 2.1.0
author: Chief Architect
maintainer: Chief Maintainer
reviewers: []
created: 2026-07
last_updated: 2026-07-11
depends_on:
  - ACIS.md
supersedes:
  - architecture.md
related_rfcs:
  - RFC-002
  - RFC-003
  - RFC-004
  - RFC-005
  - RFC-006
  - RFC-007
  - RFC-008
  - RFC-009
  - RFC-010
priority: ★★★★★
---

# RFC-001: System Architecture Specification

> This RFC is the authoritative definition of the ACIS system architecture.
> It describes WHAT the architecture is, not how modules are implemented.
> It formally supersedes architecture.md, whose content is incorporated here.
> Every later RFC depends on this document. Any implementation must conform to this architecture unless an ADR explicitly changes it.

---

# Abstract

ACIS (Agricultural Cognitive Intelligence System) is a layered cognitive architecture. Each layer has a single responsibility and is independently replaceable. This RFC defines the system layers, their responsibilities and boundaries, the cognitive loop, core components, state ownership, architectural constraints, and extension principles.

Workflow State (RFC-002), Agent Protocol (RFC-003), Memory System (RFC-004), Tool Protocol (RFC-005), Decision Pipeline (RFC-006), Learning (RFC-007), Planner (RFC-008), Executive Agent (RFC-009), and World Model (RFC-010) are specified by their own RFCs. This RFC provides their architectural placement and mutual relationships only. The World Model is a reserved interface and is not part of the current cognitive loop.

---

# Motivation

ACIS is designed to become an agricultural cognitive operating system capable of continuous observation, reasoning, decision-making, execution, and learning. Unlike traditional agricultural expert systems that treat a task as rule matching, ACIS treats every task as a cognitive process. This requires a stable, evolvable, replaceable layered architecture as the common foundation for all modules.

This RFC exists because RFC-002 through RFC-010 all declare Depends On: RFC-001. Previously the architecture lived only in the non-RFC document architecture.md, leaving the dependency root split and fragile. This RFC consolidates the architecture into a single authoritative specification and resolves the recorded audit conflicts C1 through C9 where they belong to the architecture layer (see Audit Checklist).

Rejected alternatives:
- Monolithic application: rejected, because not replaceable, not independently testable, and hard to evolve.
- Pure rule engine: rejected, because it cannot support evidence-driven, debate-based cognition.
- Single agent: rejected, because it cannot express collective intelligence and multi-expert debate.

---

# Goals

- G1 Modularity: every component is replaceable.
- G2 Explainability: every decision is traceable.
- G3 Evidence-driven reasoning: evidence precedes conclusion.
- G4 Human-in-the-loop: human experts remain involved.
- G5 Continuous evolution: knowledge grows over time.
- G6 Fault tolerance: a single module failure must not collapse the workflow.

---

# Non Goals

This RFC does NOT specify:
- Implementation details or coding style (see IMPLEMENTATION_ARCHITECTURE).
- Database schema or storage layout (see RFC-004, RFC-002).
- Deployment, prompt engineering, or model selection (out of scope).
- Roadmap timing (see ROADMAP).
- Per-subsystem protocols, schemas, or state contracts (see RFC-002 through RFC-010).

ACIS is intentionally NOT: a large language model, a database, a monolithic application, a rule engine, or an autonomous AGI. Those responsibilities belong to external systems.

---

# Architecture Overview

ACIS is a layered cognitive architecture. The high-level cognitive loop is:

```
Observe -> Understand -> Reason -> Debate -> Decide -> Execute -> Learn -> Improve
```

Workflow State is the single source of truth shared by every layer. It is defined by RFC-002. Each layer participates in the workflow by reading and writing the state segments it owns (see State Ownership). Layers are composed top-down; no layer bypasses another to reach infrastructure (see Architectural Constraints).

Generational evolution (1.x single agent -> 2.x multi-agent cognitive -> 3.x executive intelligence -> 4.x autonomous agricultural -> 5.x agricultural cognitive OS) is sequenced in the ROADMAP. The current generation is ACIS 2.0 (multi-agent cognitive decision-making). This RFC is generation-stable: the layer model is preserved across generations, with capabilities added incrementally rather than by rewrite.

---

# System Layers

ACIS comprises ten layers. Each has exactly one responsibility and owns specific Workflow State segments. Subsystem detail belongs to the referenced RFC; this section defines placement and boundaries only.

## L1 Executive Intelligence Layer
- Responsibility: coordinate the cognitive workflow - planning, scheduling, resource allocation, workflow generation, safety gating.
- Components: Orchestrator (owns Metadata), Gateway (owns Request), Planner (owns Context, see RFC-008).
- Forbidden: diagnosing disease, storing knowledge, operating hardware directly.

## L2 Tool Layer
- Responsibility: unified interface to every external capability.
- Examples: Neo4j, Qdrant, Weather API, MCP Server, YOLO, PLC.
- Rule: agents never access infrastructure directly; all external interaction passes through the Tool Layer (MCP), see RFC-005.

## L3 Perception Layer
- Responsibility: convert raw observations into structured evidence.
- Agents (RFC-003 Perception Agents): Vision, Sensor, Weather, Spectral, Drone. Future: Satellite, Robot.
- Owns the Observation state segment.

## L4 Cognition Layer
- Responsibility: produce domain interpretations.
- Experts (RFC-003 Expert Agents): Pathology, Cultivation, Meteorology, Economic, Ecology. Future: Fertilization, Pest, Supply Chain, Carbon.
- Experts never produce the final decision. Owns the Evidence state segment.

## L5 Memory Layer
- Responsibility: store and retrieve knowledge only; never reason.
- Types (RFC-004): Semantic (RAG / vector), Episodic (case repository), Procedural (outcome repository), Knowledge Graph, Outcome Replay, Memory Evolution (append-only, auditable).
- Memory Fusion does not make final decisions; final decisions belong to the Judge. Owns the Memory state segment.

## L6 Collective Intelligence
- Responsibility: produce intelligence through collaboration rather than a single expert.
- Pipeline: Experts -> Debate -> Critic -> Meta-Critic -> Consensus -> Judge.
- Each stage reduces uncertainty. Corresponds to RFC-003 Cognitive Agents. Owns Debate / Critic / MetaCritic state segments.

## L7 Decision Layer
- Responsibility: fuse evidence into an actionable, explainable decision.
- Judge: evidence fusion, risk assessment, confidence calibration, policy check. Outputs Decision, Confidence, Evidence, Explanation.
- Judge never creates facts. Owns the Decision state segment (RFC-002). A decision is immutable once produced; revision creates a new version.
- Boundary (C5): the Decision Pipeline (RFC-006) orchestrates the decision phase (context build -> reasoning -> decision maker (Judge) -> action planning). Judge is the decision-fusion component within it; the Pipeline operates within this layer and does not exceed it.

## L8 Execution Layer
- Responsibility: turn decisions into action.
- Targets: IoT, Drone, PLC, work orders, notifications, human approval.
- Four phases: Action Planning -> Safety Verification -> Execution -> Outcome Collection.
- Owns the Execution state segment; Outcome is collected by the Feedback component (owns Outcome, RFC-002).
- High-risk actions require human approval (Human-in-the-loop).

## L9 Learning Layer
- Responsibility: turn outcomes into improved future decisions.
- Loop: Outcome -> Evaluation -> Experience Replay -> Memory Update -> Knowledge Evolution -> Confidence Calibration -> Future Decisions.
- Learning never edits history directly; it only proposes improvements (RFC-007). Owns the Learning state segment.

## L10 World Model (reserved)
- Responsibility: maintain an internal representation of the agricultural world (crop growth, disease spread, weather evolution, market change, resource dynamics).
- Status: RESERVED INTERFACE, not implemented in the current generation. Full Entity / Relationship / State / Causal / Prediction / Simulation capability is deferred to ACIS 3.0 per ROADMAP (RFC-010).
- The current cognitive loop does NOT depend on the World Model. Planner (RFC-008) and Learning (RFC-007) operate without it in ACIS 2.x.

Terminology (C6): "Executive Intelligence Layer" (L1, planning and coordination) and "Execution Layer" (L8, action) are distinct layers with similar names. RFC-009 "Executive Agent" belongs to the Execution Layer (L8) despite its name; it performs runtime execution loops and recovery, not strategic planning. RFC-009 should reflect this mapping in its own document.

---

# Core Components

Core components are the primary replaceable objects. Each implements an interface defined by its owning RFC.

| Component | Layer | Owns (State) | Defined By |
|---|---|---|---|
| Gateway | L1 Executive Intelligence | Request | RFC-003 |
| Orchestrator | L1 Executive Intelligence | Metadata | RFC-002, RFC-003 |
| Planner | L1 Executive Intelligence | Context | RFC-008 |
| Tool Registry / Router / MCP Adapter | L2 Tool | - | RFC-005 |
| Perception Agents | L3 Perception | Observation | RFC-003 |
| Expert Agents | L4 Cognition | Evidence | RFC-003 |
| Memory Store / Fusion | L5 Memory | Memory | RFC-004 |
| Debate / Critic / Meta-Critic | L6 Collective Intelligence | Debate / Critic / MetaCritic | RFC-003 |
| Judge | L7 Decision | Decision | RFC-002, RFC-006 |
| Execution / Feedback | L8 Execution | Execution / Outcome | RFC-002, RFC-009 |
| Learning Pipeline | L9 Learning | Learning | RFC-007 |
| World Model | L10 World Model | (reserved) | RFC-010 |

---

# State Ownership

Workflow State (RFC-002) is the single source of truth. This section states architectural ownership only; the state contract, lifecycle, and mutation rules are defined by RFC-002.

| State Segment | Owner | Layer |
|---|---|---|
| Metadata | Orchestrator | L1 |
| Request | Gateway | L1 |
| Context | Planner | L1 |
| Observation | Perception Layer | L3 |
| Evidence | Expert Agents | L4 |
| Memory | Memory Layer | L5 |
| Debate | Debate Engine | L6 |
| Critic | Critic Agent | L6 |
| MetaCritic | Meta-Critic | L6 |
| Decision | Judge | L7 |
| Execution | Execution Layer | L8 |
| Outcome | Feedback | L8 |
| Learning | Learning Layer | L9 |
| Telemetry | Infrastructure | cross-cutting |

State machine composition (C4): the Workflow lifecycle (RFC-002: Created -> Observed -> Perceived -> Reasoned -> Debated -> Reviewed -> Judged -> Executed -> Evaluated -> Archived) is the CANONICAL lifecycle. The Decision lifecycle (RFC-006), the Planner lifecycle (RFC-008, including dynamic replanning), and the Executive state machine (RFC-009) are SUB-LIFECYCLES that operate WITHIN specific workflow phases. They do not replace the workflow lifecycle. Replanning (RFC-008) and execution recovery (RFC-009) occur as transitions within workflow phases, not as bypasses of the canonical lifecycle. The detailed phase-to-sub-lifecycle mapping is specified by RFC-002; this RFC fixes only the composition principle.

Immutable fields (architectural): request_id, session_id, created_at, user_input, workflow_version. Mutable state follows append-first; history is immutable; knowledge evolution is append-only (Draft -> Review -> Approved -> Merged). Object models for memory and agent I/O are defined by RFC-004 and RFC-003 respectively.

---

# Architectural Constraints

These constraints are mandatory. Each mitigates a specific architectural risk.

- Agents never access infrastructure directly; the Tool Layer is the only gateway. (mitigates coupling)
- Memory never reasons; it only retrieves and stores. (mitigates scope creep)
- Judge never creates facts; it only fuses evidence. (mitigates hallucination)
- The Tool Layer is the sole gateway to external systems. (mitigates uncontrolled I/O)
- Historical records are immutable; knowledge evolution is append-only. (mitigates history rewrite)
- Every Workflow State must be observable. (mitigates opacity)
- Every decision must be explainable. (mitigates unaccountable automation)
- Every module must be independently testable. (mitigates regression)
- Every architectural change must have an ADR. (mitigates architecture drift)
- Backward compatibility is required unless an ADR explicitly breaks it. (mitigates evolution breakage)
- The workflow lifecycle (RFC-002) is canonical; sub-lifecycles compose within it, never bypass it. (mitigates orchestration ambiguity, C4)
- A single module failure must not collapse the workflow; failures return structured errors. (mitigates cascade failure, G6)

---

# Extension Principles

- Every component is replaceable; a new module must satisfy its owning RFC interface.
- New agents must implement the Agent interface and produce AgentOutput (RFC-003).
- New memory backends must implement the Memory interface (RFC-004).
- New tools must implement the Tool interface and support MCP (RFC-005).
- New workflows must remain Workflow State compatible (RFC-002).
- New decision engines must preserve the Decision schema (RFC-006).
- Prefer integrating mature open-source components over building commodities (ACIS Principle 11).
- The system is polyglot; consistency comes from stable interfaces, not a single language (ACIS Principle 13).
- Evolution is incremental: existing capabilities must not be broken by new features (ACIS Principle 10).
- Future extensions (Digital Twin, multi-farm coordination, embodied intelligence, agricultural foundation models) are accommodated by reserved interfaces; the World Model slot (L10) is the primary reserved extension point.

---

# Module Responsibilities

This section fixes the boundary between overlapping subsystems (C5). Action-planning responsibilities are separated by layer.

| Subsystem | RFC | Layer | Scope |
|---|---|---|---|
| Planner | RFC-008 | L1 | Strategic: goal -> task decomposition -> plan. Owns Context. |
| Decision Pipeline | RFC-006 | L7 | Tactical: context -> options -> evaluation -> decision (Judge) -> action plan. Owns Decision. |
| Executive Agent | RFC-009 | L8 | Runtime: plan -> action execution -> tool invocation -> observation -> recovery. Owns Execution / Outcome. |

Action-planning separation:
- RFC-008 Plan Generation: strategic plan (which goals and tasks, in what order).
- RFC-006 Action Planner: tactical action sequence within a single decision.
- RFC-009 Task Controller: runtime task execution control.
These are distinct scopes at different layers; they do not duplicate responsibility.

Judge versus Decision Pipeline (C5): Judge is the decision-fusion component that owns the Decision state segment (RFC-002). The Decision Pipeline (RFC-006) is the broader subsystem that orchestrates the decision phase and contains Judge as its decision maker. The Pipeline operates within the Decision Layer (L7); it does not exceed it.

Execution Layer versus Executive Agent (C5, C6): the Execution Layer (L8) owns Execution / Outcome state (RFC-002). The Executive Agent (RFC-009) is the execution subsystem within L8. Despite the name "Executive", it belongs to the Execution Layer, not the Executive Intelligence Layer.

---

# Cross RFC References

This RFC defines placement only. Each subsystem protocol, schema, and contract lives in its own RFC.

| RFC | Title | Owns |
|---|---|---|
| RFC-002 | Workflow State Specification | Workflow lifecycle, state ownership, state contract, mutation rules |
| RFC-003 | Agent Protocol Specification | Agent I/O, capability declaration, agent lifecycle, perception / expert / cognitive agents |
| RFC-004 | Memory System Specification | Memory types, retrieval pipeline, fusion, storage interface |
| RFC-005 | Tool Protocol Specification | Tool registry, router, MCP adapter |
| RFC-006 | Decision Pipeline Specification | Decision phase, decision lifecycle, action planning within a decision |
| RFC-007 | Learning Pipeline Specification | Outcome -> evaluation -> replay -> memory update -> calibration |
| RFC-008 | Planner Architecture Specification | Goal understanding, decomposition, plan generation, dynamic replanning |
| RFC-009 | Executive Agent Architecture Specification | Action execution, tool invocation, execution loop, error recovery |
| RFC-010 | World Model Architecture Specification | Entity / relationship / state / causal / prediction / simulation (reserved, ACIS 3.0) |

Higher authority: ACIS.md (constitution, priority 1). This RFC depends on ACIS.md and is the dependency root for RFC-002 through RFC-010. Future RFCs (RFC-011 Cognitive Loop, RFC-012 Self-Model, RFC-013 Goal / Motivation) extend this architecture and must conform to it.

---

# Reference Implementation

Reference package layout only. No implementation code is specified here.

```
workflow/      # Workflow State, lifecycle (RFC-002)
agents/        # Perception, Expert, Cognitive agents (RFC-003)
memory/        # Memory store, fusion (RFC-004)
tools/         # Tool registry, router, MCP adapter (RFC-005)
judge/         # Decision fusion (RFC-002, RFC-006)
planner/       # Strategic planning (RFC-008)
execution/     # Action execution, feedback (RFC-009)
learning/      # Learning pipeline (RFC-007)
worldmodel/    # Reserved interface (RFC-010, ACIS 3.0)
gateway/       # Request entry (RFC-003)
```

Validation points: each layer must be independently testable; each state transition must be observable; each decision must carry evidence, confidence, and explanation; each architectural change must be recorded in an ADR.

---

# AI Context

Load this RFC when:
- Adding or modifying any system layer.
- Adding an agent, tool, memory, workflow, planner, or decision module.
- Evaluating architectural compatibility or backward compatibility.
- Writing or reviewing an ADR.
- Resolving a boundary or terminology dispute between subsystems.

Priority: ★★★★★

---

# Audit Checklist

Conflicts C1 through C9 from the implementation audit, resolved where they belong to RFC-001:

- [x] C1 - RFC-001 is the single architecture source; architecture.md is superseded (frontmatter supersedes field). Resolved.
- [x] C2 - World Model is a reserved interface; the current cognitive loop does not depend on it, so its dependency ordering does not block Planner (RFC-008) or Learning (RFC-007). Resolved at architecture level. RFC-010 dependency wording remains for RFC-010 normalization.
- [x] C3 - World Model positioning fixed: reserved architectural slot (L10), full capability deferred to ACIS 3.0 per ROADMAP. Resolved. RFC-010 "core foundation" wording remains for RFC-010 normalization.
- [x] C4 - State machine composition defined: RFC-002 workflow lifecycle is canonical; RFC-006 / RFC-008 / RFC-009 sub-lifecycles compose within workflow phases. Resolved at architecture level. Detailed phase mapping remains for RFC-002.
- [x] C5 - Module boundaries fixed: Judge is a component of the Decision Pipeline (L7); Executive Agent is a subsystem of the Execution Layer (L8); action planning is separated by layer. Resolved at architecture level. Per-subsystem wording remains for RFC-006 / RFC-008 / RFC-009.
- [x] C6 - "Executive" terminology disambiguated: L1 Executive Intelligence (planning) versus L8 Execution (action); RFC-009 Executive Agent mapped to L8. Resolved at architecture level. RFC-009 name clarification remains for RFC-009.
- [x] C7 - No duplicate layer definitions; RFC-001 layers are single-authority. Resolved.
- [ ] C8 - RFC status versus roadmap status: RFC-001 is Accepted; RFC-002 through RFC-010 remain Draft. Remaining; resolved per-RFC when those RFCs are normalized.
- [x] C9 - RFC-001 normalized to the RFC-000 template (YAML frontmatter, English, standard sections). Resolved for RFC-001. RFC-006 through RFC-010 style remains for their normalization.

Consistency:
- [x] Consistent with ACIS.md.
- [x] Single responsibility maintained per layer.
- [x] No unnecessary complexity; no new subsystems introduced.
- [x] Interfaces referenced, not duplicated (RFC-002 / RFC-003 / RFC-004 / RFC-005).
- [x] Backward compatibility required; changes require ADR.
- [x] Architecture internally consistent; cross references valid.
