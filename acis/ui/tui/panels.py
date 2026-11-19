"""Secondary TUI panels (help and system status)."""

from __future__ import annotations

import os

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def render_system_detail(
    console: Console, last_decision: object, deepseek_configured: bool
) -> None:
    try:
        from acis.knowledge.kg.adapter import kg_status

        kg = kg_status()
        neo4j_state = "已连接" if kg.get("neo4j_connected") else "未连接 / 回退可用"
    except Exception as exc:
        neo4j_state = f"状态不可用（{type(exc).__name__}）"
    report = getattr(last_decision, "report", {}) or {}
    sources = report.get("knowledge_sources", {}) if isinstance(report, dict) else {}
    rag_state = sources.get("rag_status", "尚无诊断记录")
    rag_hits = sources.get("rag", []) or []
    rag_backend = rag_hits[0].get("backend", "未提供") if rag_hits else "未提供来源"
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("项目", style="cyan")
    table.add_column("状态")
    table.add_row("API Key", "已配置" if os.environ.get("ACIS_API_KEY", "").strip() else "未配置")
    table.add_row("DeepSeek Key", "已配置" if deepseek_configured else "未配置")
    table.add_row("Neo4j", neo4j_state)
    table.add_row("最近 RAG 结果", f"{rag_state} · backend={rag_backend}")
    console.print(Panel(table, title="系统状态（连接状态与配置状态分开显示）", border_style="cyan"))


def render_help(console: Console) -> None:
    help_text = (
        "输入 1–9：运行对应演示场景（固定案例会标明 DEMO / FIXTURE MODE）\n"
        "x：输入自定义农业问题，可选填写本地叶片图片路径\n"
        "h：查看 SQLite 历史记录并打开详情\n"
        "t：查看最近一次运行的真实 Trace\n"
        "s：查看模型配置、KG 连接和最近 RAG 状态\n"
        "j / c：切换已配置的 LLM Judge / Critic\n"
        "a：查看架构；q：退出"
    )
    console.print(Panel(help_text, title="帮助 · 键盘快捷键", border_style="green"))
