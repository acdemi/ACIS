---
rfc: 002
title: Workflow State Specification
status: Accepted
version: 2.0.0
author: Chief Architect
maintainer: Chief Maintainer
reviewers: []
created: 2026-07
last_updated: 2026-07-11
depends_on:
  - ACIS.md
  - RFC-001
supersedes: []
related_rfcs:
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

# RFC-002: Workflow State Specification

> Workflow State is the single source of truth shared by every workflow node, agent, memory module, tool, planner, judge, and execution component.
> Any implementation that reads or modifies workflow state MUST conform to this RFC.
> This RFC defines the state model, ownership, contracts, schema, transitions, validation, and failure handling. It cross-references RFC-001 for architecture and does not repeat it.

---

# Abstract

This RFC defines the Workflow State Specification for ACIS. Workflow State is the single source of truth shared by every layer and component in the cognitive workflow. This specification standardizes the state model, field-level ownership, producer and consumer contracts, the immutable and mutable schema, the workflow lifecycle and state transitions (including how subsystem sub-lifecycles compose), validation rules, runtime metrics, and failure handling. Agent, memory, tool, decision, planner, and execution internals are defined by RFC-003 through RFC-010; this RFC defines only the shared state they read and write.

---

# Motivation

As ACIS evolves, more components participate in the cognitive workflow: Planner, Perception Agents, Expert Agents, Memory, Debate, Critic, Meta-Critic, Judge, Execution, and Learning. Without a unified state specification:
- Different nodes introduce inconsistent fields.
- State ownership becomes ambiguous.
- Workflow becomes difficult to maintain and observe.
- AI coding agents cannot safely extend the system.
- Subsystem lifecycles (RFC-006, RFC-008, RFC-009) cannot be composed unambiguously.

This RFC establishes a stable, extensible state model as the single source of truth.

---

# Goals

- Standardize Workflow State as the single source of truth.
- Define ownership of every state field.
- Define producer, consumer, and validator contracts for every node.
- Separate immutable and mutable state.
- Define validation rules per workflow phase.
- Define state transitions and sub-lifecycle composition.
- Prevent hidden workflow state.
- Preserve backward compatibility.
- Enable deterministic, observable workflow execution.

---

# Non Goals

This RFC does NOT define:
- Agent implementation or prompt engineering (RFC-003).
- Memory retrieval algorithms or storage layout (RFC-004).
- Tool implementation or MCP adapters (RFC-005).
- Decision, planner, or execution internals (RFC-006, RFC-008, RFC-009).
- Business logic or domain knowledge.
- Serialization format (implementation choice; the logical schema is canonical).
- Roadmap timing (see ROADMAP).

---

# Architecture

ACIS is a layered cognitive architecture defined by RFC-001. Each layer (L1 through L10) participates in the workflow by reading and writing the state segments it owns. RFC-001 defines the layers, core components, and the architectural state-segment-to-layer mapping; this RFC defines the state itself: its structure, ownership contracts, schema, transitions, and validation. The cognitive loop (Observe -> Understand -> Reason -> Debate -> Decide -> Execute -> Learn -> Improve) and the ten layers are defined in RFC-001 and are not repeated here. Cross-references to RFC-001 use the L1 through L10 layer names.

---

# State Model

Workflow State is a single object composed of independent segments. Each segment has exactly one owner (see State Ownership). Segments are logical; the physical representation is implementation-defined provided the logical schema is preserved.

## Workflow State Structure

```
WorkflowState
  +- Metadata        (phase, timestamps, workflow_version)
  +- Request         (request_id, session_id, user_input, created_at)
  +- Context         (goal, decomposed tasks, plan)
  +- Observation     (raw + structured observations)
  +- Evidence        (expert outputs, evidence items)
  +- Memory          (retrievals, fusion results)
  +- Debate          (debate rounds, positions)
  +- Critic          (critiques, rebuttals)
  +- MetaCritic      (meta-review, uncertainty)
  +- Decision        (decision, confidence, risk, explanation)
  +- Execution       (actions, execution logs)
  +- Outcome         (results, feedback)
  +- Learning        (experience, calibration)
  +- Telemetry       (metrics, traces)
```

## Workflow Lifecycle

Every workflow follows one canonical lifecycle. No node may skip a mandatory stage without an explicit RFC exception.

```
Created -> Observed -> Perceived -> Reasoned -> Debated -> Reviewed -> Judged -> Executed -> Evaluated -> Archived
```

## State Transitions

- Transitions are forward-only along the canonical lifecycle, except for explicit replanning and recovery (see Sub-lifecycle Composition).
- A transition commits only after validation passes for the target phase (see Validation Rules).
- Every transition is observable (recorded in Telemetry).
- Archiving freezes the workflow; no further mutation is permitted.

## Sub-lifecycle Composition

Resolves audit conflict C4 (deferred from RFC-001). The workflow lifecycle above is canonical. The Decision lifecycle (RFC-006), the Planner lifecycle (RFC-008, including dynamic replanning), and the Executive state machine (RFC-009) are sub-lifecycles that operate WITHIN specific workflow phases. They compose within, never bypass, the canonical lifecycle.

| Workflow Phase | Sub-system (RFC) | Sub-lifecycle activity | Segments written |
|---|---|---|---|
| Created | Gateway (RFC-003) | request intake | Request, Metadata |
| Observed | Perception (RFC-003) | perception agents produce raw observation | Observation |
| Perceived | Perception (RFC-003) | observation structured into evidence-ready form | Observation |
| Reasoned | Experts (RFC-003) + Planner (RFC-008) | expert interpretation; Planner goal and decomposition; replanning loops here | Evidence, Context |
| Debated | Debate + Critic (RFC-003) | debate rounds and critic rebuttals | Debate, Critic |
| Reviewed | Meta-Critic (RFC-003) | meta-review and uncertainty reduction | MetaCritic |
| Judged | Judge / Decision Pipeline (RFC-006) | decision lifecycle: Analyzing -> Evaluated -> Approved | Decision |
| Executed | Executive Agent (RFC-009) | execution state machine: Ready -> Executing -> Completed (-> Failed -> Recovery) | Execution |
| Evaluated | Feedback + Learning (RFC-007) | outcome evaluation and learning loop | Outcome, Learning |
| Archived | Orchestrator (RFC-001) | immutable archive | all (frozen) |

Replanning (RFC-008) re-enters the Reasoned phase without leaving the workflow; it does not rewind the canonical lifecycle. Execution recovery (RFC-009) remains within the Executed phase. The detailed per-subsystem state machines are defined by RFC-006, RFC-008, and RFC-009; this RFC fixes only their composition points.

---

# State Ownership

Each state segment has exactly one owner. The owner owns all fields within its segment; field-level ownership is implied by segment ownership. Only the owner may write its segment; all other modules read only. Ownership is architectural (RFC-001) and contractual (this RFC).

| Segment | Owner | Layer (RFC-001) | Produces | Consumes (reads) |
|---|---|---|---|---|
| Metadata | Orchestrator | L1 | phase, timestamps | all segments (read) |
| Request | Gateway | L1 | request fields | - |
| Context | Planner | L1 | goal, tasks, plan | Request, Observation, Evidence |
| Observation | Perception Layer | L3 | observations | Request |
| Evidence | Expert Agents | L4 | expert outputs, evidence | Observation, Memory |
| Memory | Memory Layer | L5 | retrievals, fusion | Request, Observation, Evidence |
| Debate | Debate Engine | L6 | debate rounds, positions | Evidence |
| Critic | Critic Agent | L6 | critiques, rebuttals | Evidence, Debate |
| MetaCritic | Meta-Critic | L6 | meta-review | Debate, Critic |
| Decision | Judge | L7 | decision, confidence, risk | Evidence, Memory, Debate, Critic, MetaCritic |
| Execution | Execution Layer | L8 | actions, execution logs | Decision |
| Outcome | Feedback | L8 | results, feedback | Execution |
| Learning | Learning Layer | L9 | experience, calibration | Outcome, Decision, Memory |
| Telemetry | Infrastructure | cross-cutting | metrics, traces | all segments (read) |

Ownership guarantees:
- Only the owner may modify its segment.
- Other modules may only read it.
- Cross-layer writes are prohibited.
- A component that does not own a segment must not mutate it.

---

# State Contract

Every workflow node declares four contracts: Consumes (required input), Produces (new outputs), Modifies (owned state that may change), and Forbidden (state that must never be modified). This is the producer, consumer, and validator contract framework.

| Node | Consumes | Produces / Modifies | Forbidden |
|---|---|---|---|
| Gateway | - | Request | all other segments |
| Orchestrator | all (read) | Metadata | domain segments |
| Planner | Request, Observation, Evidence | Context | Observation, Evidence, Decision, Execution |
| Perception Agents | Request | Observation | Evidence, Decision, Execution |
| Expert Agents | Observation, Memory | Evidence | Decision, Execution, Observation |
| Memory | Request, Observation, Evidence | Memory | Decision, Evidence (Memory never creates facts) |
| Debate | Evidence | Debate | Decision, Observation |
| Critic | Evidence, Debate | Critic | Decision, Observation |
| Meta-Critic | Debate, Critic | MetaCritic | Decision, Observation |
| Judge | Evidence, Memory, Debate, Critic, MetaCritic | Decision | Observation, Request, Memory, Evidence (Judge never creates facts) |
| Execution | Decision | Execution | Decision, Evidence, Observation |
| Feedback | Execution | Outcome | Decision, Evidence |
| Learning | Outcome, Decision, Memory | Learning | Decision (history), Observation |

A node that cannot satisfy its Consumes contract must not advance the workflow; it must raise a validation failure (see Failure Handling).

---

# Schema

## Immutable Fields

Immutable after workflow creation. These must never change.

| Field | Segment | Type |
|---|---|---|
| request_id | Request | id |
| session_id | Request | id |
| user_input | Request | text |
| created_at | Request | timestamp |
| workflow_version | Metadata | semver |

## Mutable State

Mutable state follows append-first principles. Mutable segments may grow but not rewrite history.

Allowed:
- Append evidence, expert outputs, memory retrievals, execution logs, debate rounds.
- Add a new decision version (revision appends a new entry; the previous is retained).

Not allowed:
- Delete evidence or history.
- Rewrite or replace previous decisions.
- Mutate immutable fields.
- Cross-owner writes.

Per-segment mutability:
- Metadata: mutable (phase and timestamps advance).
- Decision: immutable once a version is produced; revision appends a new version.
- All other segments: append-only.

## Reserved Namespaces

Future capabilities reserve these namespaces. They must not be reused for unrelated purposes.

```
planner
world_model
simulation
digital_twin
learning
telemetry
governance
policy
```

## Schema Versioning

Workflow State follows semantic versioning (recorded in workflow_version).
- Major: breaking structural changes.
- Minor: backward-compatible additions.
- Patch: documentation or validation updates.
Deprecated fields remain readable for at least one major version. Structural changes require migration documentation and an ADR.

---

# Interfaces

Workflow State exposes a stable access interface. Implementation is free; the contract is fixed.
- Read(segment): returns the current value of a segment. Available to any component.
- Write(segment, delta): appends to an owned segment. Available only to the owner; non-owners raise an ownership violation.
- Transition(target_phase): requests a lifecycle transition. Validates before committing.
- Validate(phase): runs validation rules for a phase. Returns pass or fail with reasons.
- Snapshot(): returns an immutable point-in-time copy for archive and replay.

Agent, memory, and tool input/output object models are defined by RFC-003, RFC-004, and RFC-005 respectively; this RFC defines only the state container and access contract.

---

# Protocols

## Mutation Protocol
- Ownership-first: every write is checked against the owner map; non-owner writes are rejected.
- Append-first: mutable segments grow only; history is never deleted or rewritten.
- Validate-before-transition: a phase transition commits only after validation passes.
- Decision immutability: a produced decision version is final; revision appends a new version.
- Observability: every write and transition is recorded in Telemetry.

## Compatibility Protocol
- New modules must preserve existing fields and avoid renaming established fields.
- New namespaces are introduced only when necessary, with migration documentation.
- Backward compatibility is required unless an ADR explicitly breaks it.

## Serialization
Workflow State is serialization-independent. The logical schema is canonical; any serialization format may be used provided the logical schema is preserved. Specific formats are an implementation choice, not specified here.

---

# Runtime Metrics

Every Workflow State must be observable. Minimum metrics:
- state_size: total size of the workflow state.
- segment_coverage: which segments are populated.
- transition_count: number of lifecycle transitions.
- validation_failures: count and reasons per phase.
- ownership_violations: count of rejected non-owner writes.
- immutability_violations: count of attempts to mutate immutable fields.
- phase_latency: time spent in each phase.

Metrics are written to the Telemetry segment and are read-only for non-infrastructure components.

---

# Validation Rules

Validation runs before each transition commits.

## Pre-Judge (entering Judged)
- At least one Expert Output present in Evidence.
- Evidence is non-empty.
- Memory Retrieval present.
- Debate Result present.
- MetaCritic Result present.

## Pre-Execute (entering Executed)
- Decision present.
- Confidence recorded.
- Risk assessment recorded.
- Safety check passed (Human-in-the-loop for high-risk actions, per RFC-001 L8).

## Pre-Evaluate (entering Evaluated)
- Execution log present.
- Outcome collected.

## Pre-Archive (entering Archived)
- Outcome present.
- Learning recorded.
- No pending ownership or immutability violations.

## Invariants (always)
- Every write is by the segment owner.
- Immutable fields are unchanged since creation.
- Mutable segments are append-only.
- Every transition is recorded in Telemetry.

If validation fails, the workflow enters the Error state (see Failure Handling).

---

# Failure Handling

Workflow State corruption results in immediate workflow termination.

Detectable errors:
- Missing mandatory fields for a phase.
- Invalid ownership (non-owner write).
- Immutable field mutation.
- Schema violation.
- Circular reference.
- Validation failure.

Recovery strategy:
- Preserve the original Request (immutable).
- Log the validation error to Telemetry.
- Return a structured failure response (error code, phase, reason, segment).
- Do not mutate state on failure; the last valid state is retained for diagnosis.

Execution-level recovery (retry, alternative action, replanning) is governed by RFC-009 and occurs within the Executed phase; it does not bypass the canonical lifecycle.

---

# Reference Implementation

Reference package layout only. No implementation code is specified here.

```
workflow/
  state.py        # WorkflowState container + segments
  lifecycle.py    # phases, transitions, sub-lifecycle composition
  ownership.py    # owner map + access guard
  validation.py   # per-phase validation rules + invariants
  schema.py       # field definitions, immutable/mutable, reserved namespaces
  telemetry.py    # runtime metrics
```

Reference tests (mandatory invariants):
- Ownership: only the owner can write a segment; non-owner writes are rejected.
- Transition legality: forward-only; mandatory stages not skipped; replanning and recovery stay within phase.
- Validation: pre-Judge, pre-Execute, pre-Evaluate, pre-Archive rules enforced.
- Immutability: immutable fields unchanged across the workflow.
- Append-first: mutable segments grow only; history is never deleted or rewritten.
- Decision versioning: revision appends a new version; previous version retained.

Validation points: every phase transition is gated by validation; every write is ownership-checked; every decision carries confidence, risk, and explanation; the archived state is a frozen, reproducible snapshot.

---

# AI Context

Load this RFC when working on:
- Workflow State, workflow lifecycle, or LangGraph integration.
- Orchestrator, Planner, Judge, or any node that reads or writes state.
- State ownership, validation, or transition logic.
- Memory, Debate, Critic, Meta-Critic, Execution, or Learning state segments.
- Debugging who owns a field or why validation failed.

Priority: ★★★★★

---

# Audit Checklist

- [x] Consistent with ACIS.md.
- [x] Compatible with RFC-001; architecture cross-referenced, not repeated.
- [x] State ownership defined for every field and segment.
- [x] No hidden state introduced.
- [x] Workflow lifecycle preserved; sub-lifecycle composition defined (C4 resolved).
- [x] Immutable and mutable state separated.
- [x] Producer, consumer, and validator contracts defined for every node.
- [x] Validation rules documented per phase.
- [x] Backward compatibility evaluated; schema versioning defined.
- [x] Reference implementation and reference tests identified.
- [x] Status synced to Accepted (C8 resolved for RFC-002).
- [x] Normalized to RFC-000 template: YAML frontmatter, English (C9 resolved for RFC-002).
