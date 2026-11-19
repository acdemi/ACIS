"""TUI 演示界面 — 农业 Agent v4 多智能体决策系统

交互式终端界面，用于演示完整诊断流程，基于 rich。
单文件、零额外配置：自动加载 DeepSeek Key 与 Neo4j 连接，离线可跑。

启动：
    python -m acis tui        （旧入口 python -m ui.tui 仍保留弃用 shim）
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import os
import random


# 离线/编码兜底
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

_DEEPSEEK_CONFIGURED = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
_NEO4J_CONFIGURED = bool(os.environ.get("NEO4J_PASSWORD", "").strip())
logger = logging.getLogger(__name__)

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from acis.core.orchestrator import AgentOrchestrator, build_context
from acis.reasoning.rule_engine import sensor_anomaly

from .constants import (
    CROP_CN,
    DEMO_SCENARIOS,
    INTENT_CN,
    KG_MATCH_STYLE,
    LAYER_STYLE,
    _ARCH_LINES,
)
console = Console()
_orch_cache: dict[tuple[bool, bool], AgentOrchestrator] = {}
_last_backend = "未运行"
_last_decision = None
_last_trace = None


def _get_orchestrator(use_llm_judge: bool, use_llm_critic: bool) -> AgentOrchestrator:
    key = (use_llm_judge, use_llm_critic)
    if key not in _orch_cache:
        _orch_cache[key] = AgentOrchestrator(
            use_langgraph=True,
            use_llm_judge=use_llm_judge,
            use_llm_critic=use_llm_critic,
        )
    return _orch_cache[key]


def _warmup() -> None:
    """预热传感器异常检测模型（IsolationForest + LSTM），首次约 10s。"""
    try:
        sensor_anomaly.check_anomaly("gh-a")
    except Exception:
        pass


from .panels import render_help, render_system_detail
from .widgets import _bar, _risk_badge, _status_text


# ---------------------------------------------------------------------------
# 渲染：横幅 / 架构 / 状态
# ---------------------------------------------------------------------------
def _render_banner() -> None:
    console.print(
        Panel(
            Align.center(
                Group(
                    Text("🌱 农业 Agent v4 — 多智能体决策系统", style="bold green"),
                    Text("ACIS 演示 · 感知 → 记忆 → 专家 → 辩论 → Critic → Judge", style="cyan"),
                )
            ),
            border_style="green",
            padding=(1, 2),
        )
    )





def _render_architecture() -> None:
    diag = Text()
    for text, style in _ARCH_LINES:
        diag.append(text + "\n", style=style)
    console.print(Panel(diag, title="[bold]系统架构[/]", border_style="cyan", padding=(1, 2)))


def _render_status(use_llm_judge: bool, use_llm_critic: bool) -> None:
    if console.size.width < 92:
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column()
        table.add_column()
        table.add_row(
            Text(f"DeepSeek: {'已配置' if _DEEPSEEK_CONFIGURED else '未配置'}", style="green" if _DEEPSEEK_CONFIGURED else "yellow"),
            Text(f"Neo4j: {'已配置' if _NEO4J_CONFIGURED else '未配置'}", style="magenta" if _NEO4J_CONFIGURED else "dim"),
        )
        table.add_row(Text(f"最近 KG 后端: {_last_backend}", style="cyan"), Text(f"Judge {'开' if use_llm_judge else '关'} · Critic {'开' if use_llm_critic else '关'}", style="dim"))
        console.print(Panel(table, title="系统状态", border_style="dim", padding=(0, 1)))
        return

    t = Table.grid(expand=True, padding=(0, 2))
    t.add_column(justify="left")
    t.add_column(justify="left")
    t.add_column(justify="left")
    t.add_column(justify="right")
    if _DEEPSEEK_CONFIGURED:
        ds = Text(" DeepSeek: ✓ 已配置 ", style="green")
    else:
        ds = Text(" DeepSeek: ✗ 未配置 ", style="red")
    neo = Text(
        " Neo4j: ✓ 已配置 " if _NEO4J_CONFIGURED else " Neo4j: 未配置 ",
        style="magenta",
    )
    rag = Text(f" 最近 KG 后端:{_last_backend} ", style="cyan")
    j = Text(" Judge:开 ", style="black on green") if use_llm_judge else Text(" Judge:关 ", style="dim")
    c = Text(" Critic:开 ", style="black on green") if use_llm_critic else Text(" Critic:关 ", style="dim")
    t.add_row(ds, neo, rag, Text.assemble(j, c))
    console.print(Panel(t, title="[bold]系统状态[/]", border_style="dim", padding=(0, 2)))


# ---------------------------------------------------------------------------
# 渲染：菜单
# ---------------------------------------------------------------------------
def _menu(use_llm_judge: bool, use_llm_critic: bool) -> str:
    if any(s.get("fixture_mode") for s in DEMO_SCENARIOS):
        console.print(Text("DEMO / FIXTURE MODE · 固定案例输入由当前诊断服务实时处理", style="bold yellow"))
    t = Table(box=None, show_header=False, expand=True, padding=(0, 1))
    if console.size.width < 100:
        t.add_column("场景")
        for i, scenario in enumerate(DEMO_SCENARIOS, 1):
            entry = Text(f"{i}. {scenario['title']}", style="bold")
            if scenario.get("fixture_mode"):
                entry.append(" · DEMO / FIXTURE MODE", style="bold yellow")
            entry.append(f"\n{CROP_CN.get(scenario['crop'], '')} · {INTENT_CN.get(scenario['intent'], '')} · {scenario['highlight']}", style="dim")
            t.add_row(entry)
    else:
        t.add_column("序", width=3)
        t.add_column("场景", ratio=2)
        t.add_column("作物 / 意图", ratio=2)
        t.add_column("演示亮点", ratio=4)
        for i, scenario in enumerate(DEMO_SCENARIOS, 1):
            title = Text(scenario["title"], style="bold")
            if scenario.get("fixture_mode"):
                title.append(" · DEMO / FIXTURE MODE", style="bold yellow")
            t.add_row(
                Text(str(i), style="bold cyan"),
                title,
                Text(f"{CROP_CN.get(scenario['crop'], '')} · {INTENT_CN.get(scenario['intent'], '')}", style="dim"),
                Text(scenario["highlight"], style="dim"),
            )
    console.print(Panel(t, title="[bold]演示场景（输入序号运行）[/]", border_style="blue"))

    j_state = Text(" 开 ", style="black on green") if use_llm_judge else Text(" 关 ", style="white on red")
    c_state = Text(" 开 ", style="black on green") if use_llm_critic else Text(" 关 ", style="white on red")
    console.print(Text("[x] 自定义  [h] 历史  [t] Trace  [s] 状态", style="bold"))
    console.print(Text("[?] 帮助  [a] 架构  [q] 退出", style="dim"))
    console.print(Text.assemble("[j] DeepSeek Judge ", j_state, "    [c] Critic 反驳 ", c_state))
    console.print()
    return Prompt.ask("[bold green]请选择[/]", default="1")


# ---------------------------------------------------------------------------
# 渲染：结果
# ---------------------------------------------------------------------------
def _render_agent_trace(decision) -> None:
    outputs = getattr(decision, "traces", []) or []
    if not outputs:
        return
    if console.size.width < 100:
        for index, output in enumerate(outputs, 1):
            execution = output.execution or {}
            claim = Text(output.claim or "未提供结论")
            if output.warnings:
                claim.append("\n" + "\n".join(f"⚠ {warning}" for warning in output.warnings[:2]), style="yellow")
            details = Text.assemble(
                _status_text(execution.get("status"), execution.get("mode")),
                f" · 模式：{execution.get('mode') or '未记录'} · 置信度：{output.confidence:.0%}",
            )
            console.print(
                Panel(
                    Group(Text(f"{output.layer} · {output.agent}", style="bold"), claim, details),
                    title=f"Agent {index}",
                    border_style=LAYER_STYLE.get(output.layer, "dim"),
                    padding=(0, 1),
                )
            )
        return

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold", expand=True)
    table.add_column("层")
    table.add_column("Agent")
    table.add_column("诊断 / 结论", ratio=3)
    table.add_column("状态 / 模式")
    table.add_column("置信度", justify="right")
    for output in outputs:
        execution = output.execution or {}
        claim = output.claim or "未提供结论"
        if output.warnings:
            claim += "\n" + "\n".join(f"⚠ {warning}" for warning in output.warnings[:2])
        table.add_row(
            Text(output.layer, style=LAYER_STYLE.get(output.layer, "white")),
            Text(output.agent, style="bold"),
            Text(claim),
            Text.assemble(_status_text(execution.get("status"), execution.get("mode")), f" · {execution.get('mode') or '未记录'}"),
            _bar(output.confidence, 12),
        )
    console.print(Panel(table, title="Agent 执行记录（诊断服务已返回）", border_style="cyan", padding=(0, 1)))


def _render_verdict(decision) -> None:
    kg_backend = (decision.judge_analysis or {}).get("kg", {}).get("backend", "")
    review = (
        Text(" 需人工复核 ", style="bold white on red")
        if decision.need_human_review
        else Text(" 无需复核 ", style="green")
    )
    kg = Text(f" KG:{kg_backend} ", style="magenta") if kg_backend else Text("")
    row = Table.grid(expand=True)
    row.add_column(justify="left", ratio=1)
    row.add_column(justify="left")
    row.add_column(justify="left")
    row.add_column(justify="right")
    row.add_row(_risk_badge(decision.risk_level), review, Text(f" {decision.judge_mode} ", style="dim"), kg)

    body = Group(
        Text("最终诊断 / 决策", style="dim"),
        Text(decision.decision, style="bold white"),
        Text(""),
        _bar(decision.confidence, 26),
        Text(""),
        row,
        Text(""),
        Text(decision.summary, style="italic dim"),
    )
    border = "green" if decision.confidence >= 0.6 else "yellow" if decision.confidence >= 0.4 else "red"
    console.print(Panel(body, title="[bold]★ 最终裁决[/]", border_style=border, padding=(1, 2)))


def _render_critic_block(critic) -> Group:
    mode = critic.get("mode", "?")
    rounds = critic.get("rounds", "?")
    lines: list = [Text(f"Critic 反驳（{mode} 模式 · {rounds} 轮）", style="bold yellow")]
    if critic.get("winner"):
        lines.append(Text(f"  胜方：{critic['winner']}", style="green"))
    if critic.get("loser"):
        lines.append(Text(f"  败方：{critic['loser']}", style="red"))
    if critic.get("resolution"):
        lines.append(Text(f"  裁定：{critic['resolution']}", style="white"))
    dw = critic.get("down_weighted") or []
    if dw:
        t = Table(box=box.SIMPLE, show_header=True, header_style="dim", expand=False)
        t.add_column("Agent")
        t.add_column("原置信度", justify="right")
        t.add_column("→", justify="center")
        t.add_column("降权后", justify="right")
        for item in dw:
            t.add_row(
                item.get("agent", ""),
                f"{item.get('from', 0):.0%}",
                "→",
                f"{item.get('to', 0):.0%}",
            )
        lines.append(t)
    if critic.get("escalate"):
        lines.append(Text("  ⚠ 仍需人工复核（escalate）", style="bold red"))
    for r in critic.get("rounds_log") or []:
        lines.append(
            Text(
                f"  · 第{r.get('round')}轮：{r.get('winner', '')} 胜 {r.get('loser', '')} — {r.get('resolution', '')}",
                style="dim",
            )
        )
    return Group(*lines)


def _render_debate_critic(decision) -> None:
    d = decision.debate
    parts: list = []
    if d.consensus:
        t = Text("共识\n", style="bold green")
        for c in d.consensus:
            t.append(f"  ✓ {c}\n", style="green")
        parts.append(t)
    if d.conflicts:
        t = Text("冲突\n", style="bold red")
        for c in d.conflicts:
            t.append(f"  ✗ {c}\n", style="red")
        parts.append(t)
    if d.missing_evidence:
        t = Text("缺失证据\n", style="dim")
        for m in d.missing_evidence:
            t.append(f"  • {m}\n", style="dim")
        parts.append(t)
    if d.critic.get("triggered"):
        parts.append(_render_critic_block(d.critic))
    else:
        parts.append(Text("  Critic：无冲突，未触发反驳轮次", style="dim"))
    console.print(
        Panel(
            Group(*parts) if parts else Text("（无）"),
            title="[bold]辩论与反驳 (Debate & Critic)[/]",
            border_style="yellow",
            padding=(1, 2),
        )
    )


def _render_judge_analysis(decision) -> None:
    ja = decision.judge_analysis or {}
    kg = ja.get("kg", {})
    parts: list = []
    kg_line = Text()
    kg_line.append(f"知识图谱后端：{kg.get('backend', '?')}    ", style="magenta")
    diseases = kg.get("diseases") or []
    if diseases:
        kg_line.append("参照疾病：" + "、".join(diseases), style="white")
    parts.append(kg_line)

    if decision.judge_mode == "deepseek":
        ca = ja.get("consistency_analysis", {})
        adiag = ca.get("agent_diagnoses") or []
        if adiag:
            t = Table(box=box.SIMPLE, show_header=True, header_style="dim", expand=True)
            t.add_column("Agent")
            t.add_column("诊断")
            t.add_column("KG 一致性", justify="center")
            t.add_column("冲突原因")
            for a in adiag:
                km = a.get("kg_match", "")
                t.add_row(
                    a.get("agent", ""),
                    a.get("claim", ""),
                    Text(km, style=KG_MATCH_STYLE.get(km, "white")),
                    a.get("conflict_reason", ""),
                )
            parts.append(t)
        es = ja.get("evidence_scores") or {}
        if es:
            esc = Text("证据权重：", style="bold")
            for agent, score in es.items():
                esc.append(f"{agent}={score}  ", style="cyan")
            parts.append(esc)
        kgc = ja.get("kg_contribution")
        if kgc:
            parts.append(Text(f"KG 贡献度：{kgc}", style="yellow"))
    else:
        consistency = ja.get("consistency", {})
        rv = consistency.get("rule_violations") or []
        if rv:
            for v in rv:
                parts.append(Text(f"  ✗ 硬约束违反：{v}", style="red"))
        else:
            parts.append(Text("  ✓ 未触发 KG 硬约束否决", style="green"))
        sr = ja.get("sensor_readings") or {}
        if sr:
            srline = Text("传感器读数：", style="dim")
            for k, v in sr.items():
                srline.append(f"{k}={v}  ")
            parts.append(srline)

    if decision.reasoning_trace:
        parts.append(Text(""))
        parts.append(Text("裁决推理：", style="bold"))
        parts.append(Text(decision.reasoning_trace, style="white"))
    console.print(
        Panel(
            Group(*parts),
            title="[bold]KG 锚定裁决分析 (Judge Analysis)[/]",
            border_style="magenta",
            padding=(1, 2),
        )
    )


def _render_action_plan(decision) -> None:
    if not decision.action_plan:
        return
    t = Text()
    for i, step in enumerate(decision.action_plan, 1):
        t.append(f"  {i}. ", style="bold green")
        t.append(step + "\n", style="white")
    console.print(Panel(t, title="[bold]行动建议 (Action Plan)[/]", border_style="green", padding=(1, 2)))


def _render_diagnosis_report(decision, trace) -> None:
    report = getattr(decision, "report", {}) or {}
    if not report:
        return
    crop = report.get("crop", {})
    confidence = report.get("confidence", {})
    sources = report.get("knowledge_sources", {})
    score = confidence.get("score")
    score_label = f"{score:.0%}" if isinstance(score, (int, float)) else "未提供"
    lines = [
        Text(f"作物：{crop.get('label', '未识别')}"),
        Text.assemble("诊断状态：", _status_text(report.get("status"))),
        Text(f"置信度：{confidence.get('band', 'unknown')} ({score_label})"),
        Text(str(confidence.get("meaning", "")), style="dim"),
    ]
    if report.get("growth_stage"):
        lines.append(Text(f"生育期：{report['growth_stage']}"))
    if report.get("environment"):
        lines.append(Text("环境数据：" + json.dumps(report["environment"], ensure_ascii=False, default=str)))
    if report.get("candidates"):
        lines.append(Text("候选诊断：" + "；".join(item.get("name", "未命名候选") for item in report["candidates"])))
    differential = report.get("differential_analysis", {})
    if differential:
        lines.append(Text(f"鉴别分析：{differential.get('alternative', '')}；{differential.get('rejection_reason', '')}"))
    rag_sources = sources.get("rag", [])
    lines.append(Text(f"RAG：{sources.get('rag_status', 'unavailable')}，来源 {len(rag_sources)} 条"))
    for source in rag_sources:
        lines.append(Text(f"  · {source.get('title') or source.get('source') or source.get('id')} [{source.get('backend')}]"))
    if report.get("follow_up_questions"):
        lines.append(Text("补充信息：" + "；".join(report["follow_up_questions"])))
    if report.get("recommendations"):
        lines.append(Text("建议措施：" + "；".join(report["recommendations"])))
    if report.get("risk"):
        lines.append(Text(f"风险等级：{report['risk']}"))
    if trace is not None:
        lines.append(Text(f"Trace ID：{trace.trace_id} · 阶段：{', '.join(trace.stages_present)}"))
        trace_table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
        trace_table.add_column("阶段")
        trace_table.add_column("Agent")
        trace_table.add_column("状态")
        trace_table.add_column("模式")
        trace_table.add_column("耗时 ms", justify="right")
        for event in trace.events:
            payload = event.payload
            execution = payload.get("execution", {})
            if payload.get("agent") or event.stage in {"request", "judge", "metrics"}:
                trace_table.add_row(
                    event.stage,
                    str(payload.get("agent", "")),
                    _status_text(execution.get("status", payload.get("status", "")), execution.get("mode", "")),
                    str(execution.get("mode", "")),
                    str(execution.get("duration_ms", payload.get("duration_ms", ""))),
                )
        lines.append(trace_table)
    console.print(Panel(Group(*lines), title="完整诊断报告与执行 Trace", border_style="cyan"))


def _render_vision_status(decision, image_path: str | None) -> None:
    if not image_path:
        console.print(Panel("未提供图片；视觉识别未执行，本次诊断依据文本和其他可用证据。", title="图片输入", border_style="dim", padding=(0, 1)))
        return

    vision = next(
        (output for output in getattr(decision, "traces", []) or [] if output.agent == "视觉Agent"),
        None,
    )
    filename = Path(image_path).name
    if vision is None:
        message = f"图片路径已提供：{filename}。Trace 未记录视觉 Agent 状态，请结合诊断依据复核。"
        style = "yellow"
    else:
        execution = vision.execution or {}
        mode = execution.get("mode", "")
        status = execution.get("status", "")
        if mode == "mock":
            message = f"图片路径已提供：{filename}。视觉识别返回 Mock 模拟结果，并非真实模型推理。"
            style = "yellow"
        elif status == "success" and mode:
            message = f"图片路径已提供：{filename}。视觉模型推理已完成（{mode}）。"
            style = "green"
        elif status == "failed":
            error_type = execution.get("error_type")
            detail = f"（{error_type}）" if error_type else ""
            message = f"图片路径已提供：{filename}。视觉识别失败{detail}；请检查图片与模型配置。"
            style = "red"
        else:
            message = f"图片路径已提供：{filename}。视觉识别状态：{_status_text(status, mode)}。"
            style = "yellow"
    console.print(Panel(Text(message, style=style), title="图片输入与视觉状态", border_style=style, padding=(0, 1)))


def _render_result(decision, ctx, query, label, trace=None, image_path: str | None = None) -> None:
    crop_cn = CROP_CN.get(ctx.crop, ctx.crop)
    intent_cn = INTENT_CN.get(ctx.intent, ctx.intent)
    judge_tag = "DeepSeek AI 裁判" if decision.judge_mode == "deepseek" else "规则裁决"
    hdr = Table.grid(expand=True)
    hdr.add_column(justify="left", ratio=1)
    hdr.add_column(justify="right")
    left = Text.assemble(crop_cn, "  ", (intent_cn, "cyan"), "  ", (label, "bold"))
    hdr.add_row(left, Text(f" {judge_tag} ", style="black on cyan"))
    console.print(Panel(Group(hdr, Text(query, style="dim italic")), border_style="blue", padding=(1, 2)))
    _render_vision_status(decision, image_path)
    _render_agent_trace(decision)
    _render_verdict(decision)
    _render_debate_critic(decision)
    _render_judge_analysis(decision)
    _render_action_plan(decision)
    _render_diagnosis_report(decision, trace)


def _render_trace(trace) -> None:
    if trace is None or not trace.events:
        console.print(Panel("尚无可查看的诊断 Trace。", title="执行追溯", border_style="yellow"))
        return

    if console.size.width < 100:
        console.print(Panel(f"Trace ID：{trace.trace_id} · 记录时间：{trace.timestamp}", title="执行追溯", border_style="cyan", padding=(0, 1)))
        for index, event in enumerate(trace.events, 1):
            payload = event.payload or {}
            execution = payload.get("execution", {}) or {}
            status = execution.get("status", payload.get("status", "已记录"))
            mode = execution.get("mode", "")
            detail = Text.assemble(
                _status_text(status, mode),
                f" · {mode or '模式未记录'} · {execution.get('duration_ms', payload.get('duration_ms', '—'))} ms",
            )
            agent = str(payload.get("agent") or "系统阶段")
            error_type = execution.get("error_type")
            if error_type:
                detail.append(f"\n错误类型：{error_type}", style="red")
            console.print(
                Panel(
                    Group(Text(f"{event.stage} · {agent}", style="bold cyan"), detail),
                    title=f"步骤 {index}",
                    box=box.SIMPLE,
                    padding=(0, 1),
                )
            )
        return

    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("序号", justify="right", style="dim")
    table.add_column("阶段", style="cyan")
    table.add_column("执行单元")
    table.add_column("状态")
    table.add_column("模式")
    table.add_column("耗时 ms", justify="right")
    for index, event in enumerate(trace.events, 1):
        payload = event.payload or {}
        execution = payload.get("execution", {})
        table.add_row(
            str(index),
            event.stage,
            str(payload.get("agent", "")),
            _status_text(execution.get("status", payload.get("status", "已记录")), execution.get("mode", "")),
            str(execution.get("mode", "")),
            str(execution.get("duration_ms", payload.get("duration_ms", ""))),
        )
    console.print(Panel(table, title=f"执行 Trace · {trace.trace_id}", border_style="cyan"))


def _render_history() -> None:
    try:
        from acis.knowledge.storage.repository import get_decision, list_decisions

        rows = list_decisions(10)
    except Exception as exc:
        console.print(Panel(f"历史记录暂不可用（{type(exc).__name__}）。请确认本地 SQLite 可访问后重试。", title="历史记录", border_style="red"))
        return

    if not rows:
        console.print(Panel("暂无历史诊断。完成一次诊断后，记录会保存在本地 SQLite。", title="历史记录", border_style="yellow"))
        return

    if console.size.width < 92:
        for row in rows:
            confidence = float(row.get("confidence") or 0)
            body = Text(f"{row.get('created_at', '时间未知')} · 置信度 {confidence:.0%}\n{row.get('decision', '')}")
            console.print(
                Panel(
                    body,
                    title=f"记录 #{row.get('id', '?')} · {CROP_CN.get(row.get('crop', ''), row.get('crop', '未知作物'))}",
                    border_style="yellow" if confidence < 0.5 else "blue",
                    box=box.SIMPLE,
                    padding=(0, 1),
                )
            )
    else:
        table = Table(box=box.SIMPLE_HEAVY, expand=True)
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("时间")
        table.add_column("作物")
        table.add_column("置信度", justify="right")
        table.add_column("结论", overflow="ellipsis")
        for row in rows:
            table.add_row(
                str(row["id"]),
                str(row.get("created_at", "")),
                CROP_CN.get(row.get("crop", ""), row.get("crop", "")),
                f"{float(row.get('confidence') or 0):.0%}",
                str(row.get("decision", "")),
            )
        console.print(Panel(table, title="最近 10 条本地决策记录", border_style="blue"))
    decision_id = Prompt.ask("输入记录 ID 查看报告，直接回车返回", default="").strip()
    if not decision_id:
        return
    if not decision_id.isdigit():
        console.print("[yellow]请输入数字记录 ID；历史内容未修改，可以重新打开查询。[/]")
        return
    try:
        detail = get_decision(int(decision_id))
    except Exception as exc:
        console.print(Panel(f"读取记录失败（{type(exc).__name__}）。请检查记录 ID 和本地数据库状态。", title="历史详情", border_style="red"))
        return
    if detail is None:
        console.print("[yellow]没有找到该记录 ID。[/]")
        return
    console.print(Panel(str(detail.get("decision", "")), title=f"诊断记录 #{decision_id}"))
    report = detail.get("report_json")
    if report:
        console.print(Panel(json.dumps(report, ensure_ascii=False, indent=2), title="诊断报告", border_style="green"))
    trace = detail.get("trace_json")
    if trace:
        events = trace.get("events", []) if isinstance(trace, dict) else []
        trace_id = detail.get("trace_id") or (trace.get("trace_id", "") if isinstance(trace, dict) else "")
        if console.size.width < 100:
            console.print(Panel(f"历史 Trace · {trace_id or 'ID 未记录'}", border_style="cyan", padding=(0, 1)))
            for event in events:
                payload = event.get("payload") or {}
                execution = payload.get("execution", {}) or {}
                console.print(Panel(
                    Group(
                        Text(f"{event.get('stage', '')} · {payload.get('agent') or '系统阶段'}", style="cyan"),
                        Text.assemble(
                            _status_text(execution.get("status", payload.get("status", "已记录")), execution.get("mode", "")),
                            f" · {execution.get('mode') or '模式未记录'} · {execution.get('duration_ms', '—')} ms",
                        ),
                    ),
                    title=str(event.get("timestamp", "")),
                    box=box.SIMPLE,
                    padding=(0, 1),
                ))
        else:
            trace_table = Table(box=box.SIMPLE, expand=True)
            trace_table.add_column("阶段", style="cyan")
            trace_table.add_column("记录时间")
            trace_table.add_column("执行单元")
            trace_table.add_column("状态 / 模式")
            trace_table.add_column("耗时 ms", justify="right")
            for event in events:
                payload = event.get("payload") or {}
                execution = payload.get("execution", {}) or {}
                trace_table.add_row(
                    str(event.get("stage", "")),
                    str(event.get("timestamp", "")),
                    str(payload.get("agent", "")),
                    Text.assemble(_status_text(execution.get("status", payload.get("status", "已记录")), execution.get("mode", "")), f" · {execution.get('mode', '')}"),
                    str(execution.get("duration_ms", payload.get("duration_ms", ""))),
                )
            console.print(Panel(trace_table, title=f"历史 Trace · {trace_id}", border_style="cyan"))





def _render_system_detail() -> None:
    render_system_detail(console, _last_decision, _DEEPSEEK_CONFIGURED)


def _render_help() -> None:
    render_help(console)


# ---------------------------------------------------------------------------
# 运行
# ---------------------------------------------------------------------------
def _prompt_image_path() -> str | None:
    while True:
        raw_path = Prompt.ask("本地图片路径（可选，直接回车跳过）", default="").strip()
        if not raw_path:
            return None
        if len(raw_path) >= 2 and raw_path[0] == raw_path[-1] and raw_path[0] in {"'", '"'}:
            raw_path = raw_path[1:-1]
        image_path = Path(raw_path).expanduser()
        if image_path.is_file():
            return str(image_path.resolve())
        console.print(Panel(
            f"找不到该文件或路径不是文件：{image_path}\n检查路径后重新输入，或直接回车继续文本诊断。",
            title="图片路径无效",
            border_style="yellow",
            padding=(0, 1),
        ))


def _run_scenario(query, use_llm_judge, use_llm_critic, sensor_override, label, fixture_mode=False, image_path=None) -> None:
    global _last_backend, _last_decision, _last_trace
    try:
        ctx = build_context(query, image_path=image_path)
        if sensor_override:
            sensor_anomaly.ANOMALIES["gh-a"] = sensor_override
        random.seed(7)
        orch = _get_orchestrator(use_llm_judge, use_llm_critic)
        tag = []
        if use_llm_judge:
            tag.append("DeepSeek Judge")
        if use_llm_critic:
            tag.append("Critic")
        mode = " + ".join(tag) if tag else "规则编排"
        with console.status(f"[bold green]调度多智能体（{mode}）…[/]", spinner="dots"):
            decision = orch.run(query, image_path=image_path)
    except Exception as exc:
        logger.error("TUI diagnosis failed (type=%s, scenario=%s)", type(exc).__name__, label)
        console.print(Panel(
            f"诊断执行失败（{type(exc).__name__}），本次未生成新的诊断结论。请检查输入、图片路径和系统连接状态后重试。",
            title="诊断未完成",
            border_style="red",
            padding=(0, 1),
        ))
        return
    finally:
        sensor_anomaly.ANOMALIES.pop("gh-a", None)
    try:
        _last_backend = (decision.judge_analysis or {}).get("kg", {}).get("backend", _last_backend)
    except Exception:
        pass
    _last_decision = decision
    _last_trace = orch.last_trace
    display_label = f"{label} · DEMO / FIXTURE MODE" if fixture_mode else label
    _render_result(decision, ctx, query, display_label, orch.last_trace, image_path=image_path)


def _run_main() -> None:
    _render_banner()
    with console.status("[bold green]正在加载系统（传感器模型首次约 10s）…[/]", spinner="dots"):
        _warmup()
    _render_architecture()
    use_llm_judge = False
    use_llm_critic = False
    while True:
        console.rule(style="dim")
        _render_status(use_llm_judge, use_llm_critic)
        choice = _menu(use_llm_judge, use_llm_critic).strip().lower()
        if choice in ("q", "quit", "exit"):
            console.print("[bold green]再见！🌱[/]")
            break
        elif choice == "a":
            _render_architecture()
        elif choice == "s":
            _render_system_detail()
        elif choice == "h":
            _render_history()
        elif choice == "t":
            _render_trace(_last_trace)
        elif choice in ("?", "help"):
            _render_help()
        elif choice == "j":
            if not _DEEPSEEK_CONFIGURED:
                console.print("[red]未检测到 DeepSeek API Key，无法开启 AI 裁判。[/]")
            else:
                use_llm_judge = not use_llm_judge
                console.print(f"[green]DeepSeek Judge：{'开' if use_llm_judge else '关'}[/]")
        elif choice == "c":
            if not _DEEPSEEK_CONFIGURED:
                console.print("[red]未检测到 DeepSeek API Key，无法开启 Critic 反驳。[/]")
            else:
                use_llm_critic = not use_llm_critic
                console.print(f"[green]Critic 反驳：{'开' if use_llm_critic else '关'}[/]")
        elif choice == "x":
            q = Prompt.ask("[bold]输入农业问题（作物与症状尽量描述具体）[/]", default="").strip()
            if q.strip():
                image_path = _prompt_image_path()
                _run_scenario(q, use_llm_judge, use_llm_critic, None, "自定义查询", image_path=image_path)
                Prompt.ask("[dim]按回车返回菜单[/]", default="")
            else:
                console.print("[yellow]问题不能为空；可重新选择自定义诊断。[/]")
        elif choice.isdigit() and 1 <= int(choice) <= len(DEMO_SCENARIOS):
            s = DEMO_SCENARIOS[int(choice) - 1]
            _run_scenario(
                s["query"],
                use_llm_judge,
                use_llm_critic,
                s["sensor_override"],
                s["title"],
                fixture_mode=s.get("fixture_mode", False),
            )
            Prompt.ask("[dim]按回车返回菜单[/]", default="")
        else:
            console.print("[yellow]无效选择[/]")


def main() -> None:
    try:
        _run_main()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]终端输入已取消，安全退出；未完成的诊断不会显示为成功。[/]")
