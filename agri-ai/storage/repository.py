"""Repository: save / list / get decisions."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

from agents.types import DecisionOutput, RequestContext
from storage.db import get_connection

_JSON_FIELDS = ("action_plan", "traces", "debate", "judge_analysis")


def save_decision(decision: DecisionOutput, context: RequestContext, query: str) -> int:
    """Persist a decision and stamp its ``decision_id``. Returns the new row id."""
    traces_json = json.dumps([asdict(t) for t in decision.traces], ensure_ascii=False, default=str)
    debate_json = json.dumps(asdict(decision.debate), ensure_ascii=False, default=str)
    analysis_json = json.dumps(decision.judge_analysis, ensure_ascii=False, default=str)
    actions_json = json.dumps(decision.action_plan, ensure_ascii=False)
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO decisions
           (created_at, greenhouse_id, crop, intent, query, decision, confidence,
            risk_level, judge_mode, need_human_review, action_plan, traces, debate, judge_analysis)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            datetime.now().isoformat(timespec="seconds"),
            context.greenhouse_id, context.crop, context.intent, query,
            decision.decision, decision.confidence, decision.risk_level,
            decision.judge_mode, int(decision.need_human_review),
            actions_json, traces_json, debate_json, analysis_json,
        ),
    )
    conn.commit()
    did = cur.lastrowid
    conn.close()
    decision.decision_id = did
    return did


def list_decisions(limit: int = 50) -> list[dict]:
    """Return recent decisions (summary fields, newest first)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, created_at, greenhouse_id, crop, intent, decision,
                  confidence, risk_level, judge_mode, need_human_review,
                  feedback, feedback_note
           FROM decisions ORDER BY id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_decision(decision_id: int) -> dict | None:
    """Return a full decision by id, with JSON fields parsed."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    for k in _JSON_FIELDS:
        v = d.get(k)
        if v:
            try:
                d[k] = json.loads(v)
            except (ValueError, TypeError):
                pass
    return d


def set_feedback(decision_id: int, feedback: str, note: str = "") -> dict | None:
    """Record human-review feedback on a decision (correct/incorrect/partial)."""
    conn = get_connection()
    conn.execute(
        "UPDATE decisions SET feedback=?, feedback_note=?, feedback_at=? WHERE id=?",
        (feedback, note, datetime.now().isoformat(timespec="seconds"), decision_id),
    )
    conn.commit()
    conn.close()
    return get_decision(decision_id)


def search_confirmed_cases(crop: str, query: str, limit: int = 3) -> list[dict]:
    """Return human-confirmed decisions for the same crop (case-memory recall)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, created_at, crop, intent, query, decision, confidence,
                  risk_level, feedback_note
           FROM decisions
           WHERE feedback='correct' AND crop=?
           ORDER BY id DESC LIMIT ?""",
        (crop, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
