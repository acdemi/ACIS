"""Debate coordination facade — delegates to debate/engine.py."""
from debate.engine import DebateEngine
from agents.types import DebateResult


__all__ = ["DebateEngine", "DebateResult"]
