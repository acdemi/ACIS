# Known Technical Debt

- **planner.py**: mypy overload warning (accepted, low priority)
- **orchestrator.py**: E402 due to dotenv loading order (accepted)
- **agents/**, **rag/**, **rule_engine/**, **debate/**, **storage/**, **utils/**: pre-existing mypy errors (Sprint 01 legacy, frozen)