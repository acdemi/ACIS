"""FastAPI gateway for the agriculture Agent orchestrator."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _env import load_env
load_env()  # 注入 .env（DEEPSEEK_API_KEY / NEO4J_PASSWORD），须在 import orchestrator 前

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from orchestrator import AgentOrchestrator

app = FastAPI(title="Agri AI Gateway", version="0.2.0")


class DiagnoseRequest(BaseModel):
    query: str
    image_path: str | None = None
    use_llm_judge: bool = False
    use_llm_critic: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/diagnose")
def diagnose(request: DiagnoseRequest) -> dict:
    orchestrator = AgentOrchestrator(
        use_llm_judge=request.use_llm_judge, use_llm_critic=request.use_llm_critic
    )
    decision = orchestrator.run(request.query, request.image_path)
    return asdict(decision)


@app.get("/decisions")
def list_decisions(limit: int = 50) -> list[dict]:
    from storage.repository import list_decisions as _list
    return _list(limit)


@app.get("/decisions/{decision_id}")
def get_decision(decision_id: int) -> dict:
    from storage.repository import get_decision as _get
    d = _get(decision_id)
    if d is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return d

class FeedbackRequest(BaseModel):
    feedback: str  # correct | incorrect | partial
    note: str = ""


@app.post("/decisions/{decision_id}/feedback")
def set_feedback(decision_id: int, request: FeedbackRequest) -> dict:
    """人工复核反馈：标记决策正确/错误，回灌案例库。"""
    from storage.repository import set_feedback as _set
    d = _set(decision_id, request.feedback, request.note)
    if d is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return d


class OutcomeRequest(BaseModel):
    outcome: str  # 有效 | 无效 | 部分有效
    note: str = ""


@app.post("/decisions/{decision_id}/outcome")
def set_outcome(decision_id: int, request: OutcomeRequest) -> dict:
    """ACIS 2.0: 记录决策实际结果（有效/无效/部分有效），供经验回放 Agent 召回。"""
    if request.outcome not in {"有效", "无效", "部分有效"}:
        raise HTTPException(status_code=400, detail="outcome 必须为 有效/无效/部分有效")
    from storage.repository import set_outcome as _set
    d = _set(decision_id, request.outcome, request.note)
    if d is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return d
