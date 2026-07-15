---
document: ACIS Constitution
project: Agricultural Cognitive Intelligence System
short_name: ACIS
version: 2.0
status: Active
priority: Highest
used_by:
  - ChatGPT
  - Codex
  - Claude Code
  - Cursor
  - Gemini CLI
  - Future AI Coding Agents
last_updated: 2026-07-11
---

# ACIS Constitution

> This document is the highest-level specification of the ACIS project.
>
> Every AI coding agent and every human contributor must follow this document before reading any implementation details.
>
> If implementation conflicts with this document, this document takes precedence.

---

# 1. Mission

ACIS (Agricultural Cognitive Intelligence System) is **not** designed to be:

- a chatbot
- a plant disease classifier
- a multi-agent demo
- a collection of AI models

ACIS is designed to become:

> **An agricultural cognitive operating system capable of continuous observation, reasoning, decision-making, execution and learning.**

The long-term objective is to build an intelligent system capable of:

Observe

↓

Understand

↓

Reason

↓

Debate

↓

Decide

↓

Execute

↓

Learn

↓

Improve

---

# 2. Core Philosophy

Every capability added to ACIS must improve at least one of the following abilities:

- Observation
- Cognition
- Decision
- Execution
- Learning

If a feature does not contribute to any of these five capabilities, it should not be added.

---

# 3. Design Principles

## Principle 1 - Evidence First

Every conclusion must be supported by evidence.

Agents are not allowed to produce unsupported conclusions.

Evidence may originate from:

- Vision
- Sensor
- Weather
- Knowledge Graph
- RAG
- Historical Cases
- Simulation

---

## Principle 2 - Explainability

Every decision must explain:

- Why this conclusion was reached.
- Which evidence was used.
- Which evidence was rejected.
- Confidence score.
- Potential risks.

Explainability is mandatory.

---

## Principle 3 - Separation of Responsibility

Each layer has exactly one responsibility.

Example:

Perception Layer

Responsible for observing.

Never makes final decisions.

Judge

Responsible only for evidence fusion.

Never creates new facts.

Memory

Responsible only for storing and retrieving knowledge.

Never performs reasoning.

---

## Principle 4 - Memory Never Rewrites History

Historical records are immutable.

Knowledge evolution is append-only.

Any modification must be represented as:

Draft

↓

Review

↓

Approved

↓

Merged

---

## Principle 5 - Debate Before Decision

Conflicting expert opinions are expected.

Debate is a feature, not a bug.

Judge must never suppress disagreement.

Instead, disagreement should become part of the reasoning process.

---

## Principle 6 - Safety Before Automation

Automatic execution must always pass:

Risk Assessment

↓

Policy Check

↓

Safety Check

↓

Execution

Human approval may override automatic execution.

---

## Principle 7 - Continuous Learning

Every execution produces feedback.

Every feedback becomes experience.

Every experience improves future decisions.

Learning never ends.

---

## Principle 8 - Human-in-the-loop

Humans remain the highest authority.

Experts may:

- approve
- reject
- modify
- annotate

AI recommendations.

Human decisions become valuable learning data.

---

## Principle 9 - Tool Isolation

Agents must never directly access:

- Database
- External APIs
- Hardware

All external interactions must pass through Tool Layer (MCP).

---

## Principle 10 - Evolution Without Destruction

ACIS evolves incrementally.

Existing capabilities must not be broken by new features.

Backward compatibility is preferred.

---

## Principle 11 - Adopt Before Build

Prefer integrating mature, well-maintained open-source projects over implementing equivalent functionality from scratch. Innovation should focus on ACIS's unique cognitive architecture rather than re-creating commodity components.

---

## Principle 12 - Dynamic Knowledge Acquisition

AI coding agents should leverage official documentation, standards, GitHub repositories, academic literature, and trusted online resources whenever network access is available. Engineering decisions should be informed by current ecosystem knowledge rather than relying solely on model memory.

---

## Principle 13 - Polyglot by Design

ACIS is language-agnostic. Each subsystem should adopt the programming language and runtime most appropriate for its requirements. System consistency is achieved through stable interfaces and protocols, not through enforcing a single implementation language.

---

## Principle 14 - Evolve with the Ecosystem

ACIS should continuously align with the evolution of the open-source AI ecosystem. When widely adopted standards, protocols, or frameworks emerge (such as MCP, A2A, OpenTelemetry, or future interoperable agent protocols), the project should prefer adaptation over maintaining incompatible proprietary solutions. Novelty is valuable only when it delivers clear architectural or domain-specific advantages.

---

# 4. Engineering Rules

All contributors must follow these rules.

## Never

Never remove regression tests.

Never bypass workflow.

Never hardcode business logic into prompts.

Never allow Judge to invent facts.

Never allow Memory to overwrite history.

Never duplicate tool implementations.

Never couple Agent logic with infrastructure.

---

## Always

Always write tests.

Always keep modules loosely coupled.

Always provide fallback implementations.

Always document architectural changes.

Always explain breaking changes.

Always keep workflow observable.

---

# 5. Documentation Authority

This section defines how ACIS documentation is organized and which document wins when they conflict. It is binding on all contributors and AI coding agents.

## 5.1 Documentation Hierarchy

Documents are read top-down. Each document may reference, but must not duplicate, content owned by a higher document.

ACIS.md - philosophy, mission, principles, documentation governance

↓

README.md - project entry point and quick start

↓

ARCHITECTURE - why the system is structured this way (see RFC-001)

↓

ROADMAP - when capabilities are delivered

↓

IMPLEMENTATION_PLAN - how the system is built, phased

↓

IMPLEMENTATION_ARCHITECTURE - how modules are realized in code

↓

RFC/ - what each subsystem specifies (contracts, schemas, interfaces)

↓

ADR/ - immutable records of significant decisions and rationale

↓

Tasks - actionable, sprint-scoped work items

## 5.2 Documentation Priority

When two documents conflict, the higher-priority document wins.

Priority 1 - ACIS.md - philosophy and governance
Priority 2 - RFC - subsystem specifications (WHAT)
Priority 3 - ARCHITECTURE - system structure (WHY)
Priority 4 - IMPLEMENTATION - realization (HOW)
Priority 5 - README - entry point and quick start
Priority 6 - Comments - inline clarification

If documentation conflicts internally, stop and resolve the conflict before writing code. Documentation is the single source of truth; implementation never silently overrides it.

## 5.3 Document Responsibilities

Each document category answers exactly one question. Content is cross-referenced, never duplicated.

ARCHITECTURE answers WHY.
RFC answers WHAT.
IMPLEMENTATION answers HOW.
ROADMAP answers WHEN.

## 5.4 Read-Before-Implement Protocol

Before implementing any feature, AI coding agents and contributors must read, in order:

1. ACIS.md (this document)
2. ARCHITECTURE (RFC-001)
3. ROADMAP
4. The RFC that owns the touched subsystem
5. The current phase or sprint task

Only then may implementation begin. If a required document is missing or internally inconsistent, raise the conflict instead of proceeding.

---

# 6. Long-term Vision

ACIS evolves through five generations. This section states the philosophical trajectory; version sequencing and acceptance criteria live in the ROADMAP.

ACIS 1.x - Single Agent

↓

ACIS 2.x - Multi-Agent Cognitive System

↓

ACIS 3.x - Executive Intelligence

↓

ACIS 4.x - Autonomous Agricultural Intelligence

↓

ACIS 5.x - Agricultural Cognitive Operating System

See ROADMAP for version sequencing and completion criteria.

---

# 7. Success Criteria

A successful ACIS system should:

- produce reliable decisions
- explain every decision
- learn from experience
- improve over time
- safely execute actions
- cooperate with humans
- remain modular
- remain extensible

---

# 8. Final Statement

Every line of code should move ACIS closer to becoming an agricultural cognitive intelligence system.

Architecture is more important than implementation.

Correctness is more important than complexity.

Maintainability is more important than cleverness.

Long-term evolution is more important than short-term functionality.


# ACIS Philosophy

Complexity is acceptable only when it increases cognitive capability.

Every new module must eliminate an old limitation.

Architecture evolves slower than implementation.

Decisions are evidence-driven, not prompt-driven.