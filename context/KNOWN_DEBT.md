# Known Technical Debt

- **planner.py**: mypy overload warning (accepted, low priority)
- **orchestrator.py**: E402 due to dotenv loading order (accepted)
- **agents/**, **rag/**, **rule_engine/**, **debate/**, **storage/**, **utils/**: pre-existing mypy errors (Sprint 01 legacy, frozen)
Benchmark Capability Annotation

Status:
Open

Description:

Capability Framework 已完成。

全部 61 个 Benchmark Case
目前仍依赖自动推断。

下一阶段需要：

Human-reviewed Capability Annotation

形成 Benchmark Frozen Metadata。

Priority:

High

Impact:

Benchmark Scientific Validity