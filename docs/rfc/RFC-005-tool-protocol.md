# RFC-005: Tool Protocol Specification

**Status:** Draft
**Version:** 1.0.0
**Author:** Chief Architect
**Maintainer:** Chief Maintainer
**Depends On:** RFC-001 System Architecture, RFC-002 Workflow State, RFC-003 Agent Protocol
**Related:** MCP Protocol
**Priority:** ★★★★★

---

# Abstract

This RFC defines the Tool Protocol for ACIS.

Tools provide external capabilities that Agents can invoke during reasoning and execution.

Examples include:

* Knowledge Graph queries
* RAG retrieval
* Weather services
* Sensor data access
* Simulation engines
* IoT control

This specification defines:

* Tool lifecycle
* Tool registration
* Tool invocation
* Input/output contracts
* Permission boundaries
* MCP compatibility

The goal is to enable agents to use capabilities through stable interfaces rather than direct implementation dependencies.

---

# 1. Motivation

ACIS contains many external capabilities.

Examples:

Current:

* RAG Retriever
* Knowledge Graph
* Sensor Simulator
* Weather API

Future:

* Digital Twin
* Farm IoT
* Crop Simulation
* Remote Sensing

Without a unified Tool Protocol:

* Agents directly import modules.
* Infrastructure changes affect reasoning logic.
* Tool replacement becomes difficult.
* Multi-language extension becomes impossible.

Therefore ACIS separates:

```
Agent

↓

Tool Protocol

↓

Tool Implementation
```

---

# 2. Goals

This RFC aims to:

* Provide a unified tool interface.
* Decouple Agents from infrastructure.
* Support MCP-compatible tools.
* Enable local and remote tools.
* Support future multi-language implementation.
* Maintain explainable tool usage.

---

# 3. Non-Goals

This RFC does not define:

* Specific MCP server implementation.
* Database design.
* API gateway design.
* Tool business logic.
* Cloud deployment.

---

# 4. Architecture

The Tool Layer follows this structure:

```
Agent

↓

Tool Registry

↓

Tool Router

↓

Tool Interface

↓

Implementation

↓

External System
```

Examples:

```
Pathology Agent

↓

query_knowledge_graph

↓

Neo4j

```

```
Meteorology Agent

↓

get_weather

↓

Weather API

```

---

# 5. Tool Definition

Every tool must declare metadata.

Example:

```yaml
name: query_knowledge_graph

version: 1.0

category: knowledge

description:
  Query agricultural knowledge relationships.

input_schema:
  type: object

output_schema:
  type: object

requires_permission:
  - knowledge_read
```

---

# 6. Tool Categories

ACIS defines the following categories.

## Knowledge Tools

Examples:

* RAG Search
* Knowledge Graph Query

Purpose:

Provide verified information.

---

## Data Tools

Examples:

* Weather API
* Sensor Query
* Remote Sensing Data

Purpose:

Provide environmental observations.

---

## Simulation Tools

Examples:

* Crop Simulation
* What-if Analysis

Purpose:

Predict possible outcomes.

---

## Execution Tools

Examples:

* IoT Control
* Farm Work Order

Purpose:

Perform external actions.

---

# 7. Tool Lifecycle

Tools follow:

```
Registered

↓

Available

↓

Invoked

↓

Executed

↓

Returned

↓

Logged
```

Failure:

```
Invoked

↓

Error

↓

Fallback

↓

Retry / Abort
```

---

# 8. Tool Invocation

Agents must not directly import tool implementations.

Forbidden:

```python
from weather_api import get_weather
```

Recommended:

```python
result = tool.call(
    name="get_weather",
    parameters={}
)
```

---

# 9. Tool Request Schema

Standard request:

```json
{
  "tool_name": "get_weather",
  "request_id": "xxx",
  "parameters": {},
  "caller": "MeteorologyAgent",
  "timeout": 10
}
```

Required fields:

* tool_name
* request_id
* caller
* parameters

---

# 10. Tool Response Schema

Standard response:

```json
{
  "status": "success",
  "tool_name": "get_weather",
  "data": {},
  "metadata": {
    "source": "weather_api",
    "timestamp": ""
  }
}
```

Required:

* status
* tool_name
* data

---

# 11. Evidence Requirements

Tools providing knowledge or data must return provenance.

Example:

```json
{
 "source":
 "National Agricultural Database",

 "timestamp":
 "2026-07-10",

 "confidence":
 0.92
}
```

A tool result without provenance should be considered low reliability.

---

# 12. MCP Compatibility

ACIS Tool Protocol is compatible with Model Context Protocol (MCP).

MCP may be used as:

* Tool discovery mechanism.
* Tool communication layer.
* Remote execution protocol.

However:

ACIS agents should depend on the ACIS Tool abstraction, not directly depend on MCP.

Architecture:

```
Agent

↓

ACIS Tool Interface

↓

MCP Adapter

↓

MCP Server
```

This allows future protocol replacement.

---

# 13. Tool Security

Tools should define access permissions.

Examples:

Read:

* query_weather
* search_rag

Write:

* create_work_order
* control_device

High-risk tools require confirmation.

Examples:

* pesticide recommendation execution
* irrigation control
* hardware operation

---

# 14. Tool Logging

Every invocation should record:

* Tool name
* Caller
* Timestamp
* Parameters
* Result status
* Execution time

Logs are used for:

* Debugging
* Evaluation
* Learning
* Audit

---

# 15. Error Handling

Tools must return structured errors.

Example:

```json
{
 "status":"failed",
 "error_type":"Timeout",
 "message":"Weather service unavailable"
}
```

Agents should handle:

* Retry
* Alternative tools
* Reduced confidence
* Workflow interruption

---

# 16. Tool Evolution

Adding a new tool requires:

1. Tool specification
2. Schema definition
3. Permission definition
4. Test cases
5. Documentation update

Existing agents should not break.

---

# 17. Future Extensions

Possible future improvements:

* Dynamic tool discovery
* Tool ranking
* Tool marketplace
* Multi-agent tool sharing
* Cost-aware tool selection

These require additional RFCs.

---

# 18. AI Context

Load this RFC when modifying:

* MCP
* External APIs
* Knowledge Graph
* RAG
* Sensor System
* Weather System
* IoT Execution
* Agent Tool Calls

Priority:

★★★★★

---

# 19. Audit Checklist

* [ ] Tool follows standard schema.
* [ ] Agent does not directly depend on implementation.
* [ ] Input/output contract defined.
* [ ] Provenance included.
* [ ] Permission considered.
* [ ] Error handling implemented.
* [ ] MCP compatibility maintained.
* [ ] Workflow State impact reviewed.
* [ ] Documentation updated.

