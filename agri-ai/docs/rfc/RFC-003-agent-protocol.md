# RFC-003: Agent Protocol Specification

**Status:** Draft
**Version:** 1.0.0
**Author:** Chief Architect
**Maintainer:** Chief Maintainer
**Depends On:** RFC-001 System Architecture, RFC-002 Workflow State
**Priority:** ★★★★★

---

# Abstract

This RFC defines the standard protocol for all ACIS Agents.

Every cognitive component participating in the ACIS workflow must implement this protocol.

The protocol standardizes:

* Agent lifecycle
* Input and output schema
* Capability declaration
* Tool usage
* Confidence reporting
* Error handling
* State interaction

This specification ensures that all agents remain interchangeable, composable, and independently evolvable.

---

# 1. Motivation

ACIS contains multiple categories of agents:

* Perception Agents
* Expert Agents
* Memory Agents
* Debate Agents
* Critic Agents
* Judge Agents
* Execution Agents
* Future Planner Agents

Without a common protocol:

* Agent interfaces become inconsistent.
* New agents require custom integration.
* AI coding agents cannot automatically generate compatible implementations.
* Workflow complexity increases over time.

This RFC defines one unified protocol.

---

# 2. Goals

The protocol aims to:

* Standardize every Agent interface.
* Enable plug-and-play agent replacement.
* Separate cognition from implementation.
* Support multiple programming languages.
* Support local and remote agents.
* Maintain compatibility with Workflow State.

---

# 3. Non-Goals

This RFC does not define:

* Prompt engineering
* Internal reasoning
* LLM providers
* Model selection
* Memory algorithms
* Debate logic

These are specified elsewhere.

---

# 4. Agent Categories

ACIS currently defines the following agent classes.

## Perception Agent

Responsible for environmental observation.

Examples:

* Vision
* Sensor
* Weather
* Spectrum
* Drone

---

## Expert Agent

Responsible for domain reasoning.

Examples:

* Pathology
* Cultivation
* Meteorology
* Economic
* Ecology

---

## Memory Agent

Responsible for knowledge retrieval.

Examples:

* RAG
* Knowledge Graph
* Case Memory
* Procedural Memory

---

## Cognitive Agent

Responsible for higher-order reasoning.

Examples:

* Debate
* Critic
* Meta-Critic
* Judge

---

## Execution Agent

Responsible for action execution.

Examples:

* IoT
* Work Order
* Notification

---

# 5. Agent Lifecycle

Every Agent follows the same lifecycle.

```text
Initialized
      ↓
Ready
      ↓
Invoked
      ↓
Reasoning
      ↓
Completed
      ↓
Archived
```

If execution fails:

```text
Reasoning
      ↓
Error
      ↓
Retry
      ↓
Completed
```

---

# 6. Agent Capability Declaration

Each Agent must declare its capabilities.

Example

```yaml
name: PathologyAgent

category: expert

version: 1.0

inputs:
  - observation
  - weather

outputs:
  - diagnosis

tools:
  - knowledge_graph
  - rag

supports_counterfactual: true

supports_streaming: false

supports_async: true
```

This declaration enables automatic orchestration.

---

# 7. Standard Input

Every Agent receives a unified request object.

Required fields:

* request_id
* workflow_state
* context
* inputs
* memory
* configuration

Agents may ignore fields that are not relevant.

---

# 8. Standard Output

Every Agent returns an AgentOutput object.

Required fields:

* agent_name
* category
* result
* evidence
* confidence
* reasoning_summary
* execution_time
* version

Optional fields:

* counterfactual
* citations
* warnings
* telemetry

Outputs must be deterministic in structure.

---

# 9. Confidence

Every reasoning Agent must estimate confidence.

Range

0.0 ~ 1.0

Confidence should represent:

* Evidence quality
* Data completeness
* Model certainty

Confidence must not represent:

* Model preference
* Randomness
* Prompt verbosity

Judge performs final calibration.

---

# 10. Evidence Requirements

Every conclusion must include evidence.

Evidence may originate from:

* Sensor data
* Images
* Knowledge Graph
* RAG
* Historical cases
* Weather
* Rules

Conclusions without evidence should be marked low confidence.

---

# 11. Tool Protocol

Agents access external capabilities through the Tool Layer.

Examples:

* MCP
* Knowledge Graph
* RAG
* Weather API
* Sensor API

Agents should avoid directly importing infrastructure modules.

Tool invocation should occur through standardized interfaces.

---

# 12. State Interaction

Agents must follow RFC-002.

Rules:

* Read only permitted state.
* Modify only owned state.
* Never overwrite another agent's output.
* Append instead of replace.

---

# 13. Error Handling

Agents should return structured errors.

Example:

```json
{
  "status": "failed",
  "error_type": "ToolUnavailable",
  "message": "Knowledge Graph timeout."
}
```

Errors should never crash the workflow.

---

# 14. Language Independence

Agent implementation language is unrestricted.

Examples include:

* Python
* Rust
* Go
* TypeScript
* C++

Interoperability is achieved through protocol compliance rather than language consistency.

---

# 15. Extensibility

Future Agent types may include:

* Planner Agent
* Executive Agent
* Simulation Agent
* Learning Agent
* Digital Twin Agent

No changes to existing interfaces should be required.

---

# 16. Compatibility

New Agents must:

* Implement this protocol.
* Remain compatible with RFC-002.
* Preserve Workflow State.
* Provide capability declarations.

---

# 17. AI Context

Load this RFC when working on:

* New Agent development
* Agent refactoring
* Workflow integration
* MCP tools
* Multi-Agent orchestration

Priority: ★★★★★

---

# 18. Audit Checklist

* [ ] Agent follows lifecycle.
* [ ] Capability declaration complete.
* [ ] Standard input implemented.
* [ ] Standard output implemented.
* [ ] Evidence included.
* [ ] Confidence reported.
* [ ] RFC-002 compliance verified.
* [ ] Tool Layer used where applicable.
* [ ] No cross-layer state modification.
