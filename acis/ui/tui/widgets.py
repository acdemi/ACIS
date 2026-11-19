"""Small Rich text widgets shared by the TUI renderers."""

from __future__ import annotations

from rich.text import Text

from .constants import EXECUTION_STATUS


def _bar(conf: float, width: int = 16) -> Text:
    filled = max(0, min(width, int(round(conf * width))))
    color = "green" if conf >= 0.7 else "yellow" if conf >= 0.5 else "red"
    t = Text()
    t.append("█" * filled, style=color)
    t.append("░" * (width - filled), style="grey42")
    t.append(f" {conf:.0%}", style=f"bold {color}")
    return t


def _risk_badge(risk: str) -> Text:
    m = {"low": ("green", "低风险"), "medium": ("yellow", "中风险"), "high": ("red", "高风险")}
    color, label = m.get(risk, ("white", risk))
    return Text(f" {label} ", style=f"bold white on {color}")


def _status_text(status, mode: str = "") -> Text:
    normalized = str(status or "").strip().lower()
    if mode == "mock":
        return Text("降级 / Mock", style="bold yellow")
    label, style = EXECUTION_STATUS.get(normalized, (str(status or "已记录"), "dim"))
    return Text(label, style=style)
