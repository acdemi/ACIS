# Constraints - <Sprint Name>

> Hard rules. A violation blocks the sprint.

## Workflow Step 4 Rules
- Do NOT change public APIs.
- Do NOT rename existing dataclasses.
- Do NOT rewrite architecture.
- Do NOT replace working modules.
- Reuse existing implementations whenever possible.
- Prefer extension over modification.
- Keep backward compatibility.
- Do not implement additional features.

## Project Constraints
- Architecture Freeze: do not modify RFC text in `docs/rfc/`.
- ADR-002 / ADR-003 / ADR-004 are Proposed; follow their guidance, do not assume Accepted.
- Agents never touch infrastructure directly; they go through the Tool Layer.
- Memory never reasons; Judge never invents facts.
- History is append-only and immutable.
- Regression assets (`tests/`, `evals/`) must stay green; never delete them.

## Environment and Compatibility
- Python: <version>
- Optional dependencies degrade gracefully: Neo4j, Qdrant, LangGraph, DeepSeek, sklearn.

## Dependencies
- <Prior sprint, ADR, or RFC this sprint depends on>