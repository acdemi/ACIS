"""TUI 演示界面 — 农业 Agent v4 多智能体决策系统

交互式终端界面，用于演示完整诊断流程，基于 rich。
单文件、零额外配置：自动加载 DeepSeek Key 与 Neo4j 连接，离线可跑。

启动：
    python -m ui.tui
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
import random
import time

from _env import load_env

load_env()  # 注入 .env（DEEPSEEK_API_KEY / NEO4J_PASSWORD），须在 import orchestrator 前

# 离线/编码兜底；Neo4j 密码必须由 .env 或进程环境显式提供。
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

_DEEPSEEK_CONFIGURED = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
_NEO4J_CONFIGURED = bool(os.environ.get("NEO4J_PASSWORD", "").strip())

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich import box

from orchestrator import AgentOrchestrator, build_context
from rule_engine import sensor_anomaly
from ui.demo_cases import DEMO_CASES

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
CROP_CN = {
    "tomato": "🍅 番茄",
    "cucumber": "🥒 黄瓜",
    "maize": "🌽 玉米",
    "wheat": "🌾 小麦",
    "sugar_beet": "🥬 甜菜",
    "cotton": "🌱 棉花",
}
INTENT_CN = {
    "diagnose": "病害诊断",
    "irrigate": "灌溉决策",
    "alert": "风险预警",
    "monitor": "状态监测",
    "consult": "综合咨询",
}
LAYER_STYLE = {"感知层": "cyan", "记忆层": "magenta", "专家层": "yellow"}
KG_MATCH_STYLE = {
    "完全匹配": "bold green",
    "部分匹配": "yellow",
    "冲突": "bold red",
    "无KG数据": "grey42",
}

DEMO_SCENARIOS = [
    {
        "title": "番茄叶霉病诊断",
        "crop": "tomato",
        "intent": "diagnose",
        "query": "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？",
        "highlight": "RAG 命中 + KG 一致性校验 + 病理 Agent 高置信",
        "sensor_override": None,
    },
    {
        "title": "灌溉与病害冲突（Critic 反驳）",
        "crop": "tomato",
        "intent": "irrigate",
        "query": "温室A番茄叶背出现灰色霉层，今天需要浇水吗？要兼顾病害风险",
        "highlight": "高湿环境 · 灌溉 vs 病害风险 → Critic 多轮反驳降权",
        "sensor_override": {"humidity_offset": 22.0},
    },
    {
        "title": "甜菜褐斑病诊断",
        "crop": "sugar_beet",
        "intent": "diagnose",
        "query": "甜菜叶片出现褐色圆形病斑，病斑中心灰白，怎么防治？",
        "highlight": "跨作物知识库 + KG 参照",
        "sensor_override": None,
    },
    {
        "title": "棉花枯萎病诊断",
        "crop": "cotton",
        "intent": "diagnose",
        "query": "棉花出现半边黄化萎蔫，剖开茎秆维管束变褐，是什么病？",
        "highlight": "维管束病害鉴别 + KG 三元组",
        "sensor_override": None,
    },
    {
        "title": "番茄环境风险预警",
        "crop": "tomato",
        "intent": "alert",
        "query": "温室A番茄当前环境是否有病害预警风险？需要注意什么？",
        "highlight": "传感器 + 天气综合预警",
        "sensor_override": None,
    },
    {
        "title": "高湿病害 vs 低湿环境（诊断存疑）",
        "crop": "tomato",
        "intent": "diagnose",
        "query": "温室A番茄叶背出现灰色霉层，环境是否适合发病？",
        "highlight": "诊断高湿型叶霉病但环境偏干 -> Critic 降权病理诊断",
        "sensor_override": {"humidity_offset": -25.0},
    },
    {
        "title": "玉米大斑病（明确症状）",
        "crop": "maize",
        "intent": "diagnose",
        "query": "玉米下部叶片出现长梭形灰绿色至灰褐色病斑，湿度高时病斑快速扩大，请诊断。",
        "highlight": "症状证据、RAG 来源与诊断 Trace",
        "sensor_override": None,
        "fixture_mode": True,
    },
    *[
        {
            "title": case["title"],
            "crop": case["crop_code"],
            "intent": "diagnose",
            "query": case["query"],
            "highlight": case["focus"],
            "sensor_override": None,
            "fixture_mode": True,
        }
        for case in DEMO_CASES[1:]
    ],
]

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


_ARCH_LINES = [
    ("        ┌──────────────────────────────┐", "white"),
    ("        │   用户层  CLI / Web / 小程序   │", "bold"),
    ("        └──────────────┬───────────────┘", "white"),
    ("                       │", "white"),
    ("        ┌──────────────▼───────────────┐", "white"),
    ("        │    Agent Orchestrator (主图)   │", "bold cyan"),
    ("        └──────────────┬───────────────┘", "white"),
    ("       ┌──────────────┼──────────────┐", "white"),
    ("       ▼              ▼              ▼", "white"),
    ("   感知层           专家层          记忆层", "bold"),
    ("   视觉Agent       病理Agent        RAG", "cyan"),
    ("   传感器Agent     气象Agent       知识图谱", "yellow"),
    ("   天气Agent       栽培Agent       历史案例库", "magenta"),
    ("       └──────────────┼──────────────┘", "white"),
    ("                      ▼", "white"),
    ("               Debate & Critic", "bold yellow"),
    ("                      ▼", "white"),
    ("               Judge 裁决输出", "bold green"),
]


def _render_architecture() -> None:
    diag = Text()
    for text, style in _ARCH_LINES:
        diag.append(text + "\n", style=style)
    console.print(Panel(diag, title="[bold]系统架构[/]", border_style="cyan", padding=(1, 2)))


def _render_status(use_llm_judge: bool, use_llm_critic: bool) -> None:
    t = Table.grid(expand=True, padding=(0, 2))
    t.add_column(justify="left")
    t.add_column(justify="left")
    t.add_column(justify="left")
    t.add_column(justify="right")
    if _DEEPSEEK_CONFIGURED:
        ds = Text(" DeepSeek: ✓ 已配置 ", style="green")
    else:
        ds = Text(" DeepSeek: ✗ 未配置 ", style="red")
    if os.environ.get("NEO4J_PASSWORD"):
        neo = Text(" Neo4j: 已配置 ", style="magenta")
    else:
        neo = Text(" Neo4j: ✗ 未配置 ", style="red")
    rag = Text(f" RAG: auto · KG后端:{_last_backend} ", style="cyan")
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
    t.add_column("序", width=3)
    t.add_column("场景", ratio=2)
    t.add_column("作物 / 意图", ratio=2)
    t.add_column("演示亮点", ratio=4)
    for i, s in enumerate(DEMO_SCENARIOS, 1):
        title = Text(s["title"], style="bold")
        if s.get("fixture_mode"):
            title.append(" · DEMO / FIXTURE MODE", style="bold yellow")
        t.add_row(
            Text(str(i), style="bold cyan"),
            title,
            Text(f"{CROP_CN.get(s['crop'], '')} · {INTENT_CN.get(s['intent'], '')}", style="dim"),
            Text(s["highlight"], style="dim"),
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
def _animate_trace(decision) -> None:
    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold",
        expand=True,
        title="[dim]Agent 执行轨迹[/]",
    )
    table.add_column("层", width=6, no_wrap=True)
    table.add_column("Agent", width=12, no_wrap=True)
    table.add_column("诊断 / 结论", ratio=3)
    table.add_column("置信度", justify="right", width=20, no_wrap=True)
    with Live(table, console=console, refresh_per_second=20):
        for out in decision.traces:
            time.sleep(0.07)
            claim = out.claim
            if out.warnings:
                claim += "\n" + "\n".join(f"⚠ {w}" for w in out.warnings[:2])
            table.add_row(
                Text(out.layer, style=LAYER_STYLE.get(out.layer, "white")),
                Text(out.agent, style="bold"),
                Text(claim),
                _bar(out.confidence, 12),
            )
    console.print()


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
    lines = [
        Text(f"作物：{crop.get('label', '未识别')} · 状态：{report.get('status', 'unknown')}"),
        Text(f"置信度：{confidence.get('band', 'unknown')} ({confidence.get('score', 0):.0%})"),
        Text(str(confidence.get("meaning", "")), style="dim"),
    ]
    if report.get("growth_stage"):
        lines.append(Text(f"生育期：{report['growth_stage']}"))
    if report.get("environment"):
        lines.append(Text("环境数据：" + json.dumps(report["environment"], ensure_ascii=False, default=str)))
    if report.get("candidates"):
        lines.append(Text("候选诊断：" + "；".join(item["name"] for item in report["candidates"])))
    differential = report.get("differential_analysis", {})
    if differential:
        lines.append(Text(f"鉴别分析：{differential.get('alternative', '')}；{differential.get('rejection_reason', '')}"))
    rag_sources = sources.get("rag", [])
    lines.append(Text(f"RAG：{sources.get('rag_status', 'unavailable')}，来源 {len(rag_sources)} 条"))
    for source in rag_sources:
        lines.append(Text(f"  · {source.get('title') or source.get('source') or source.get('id')} [{source.get('backend')}]"))
    if report.get("follow_up_questions"):
        lines.append(Text("补充信息：" + "；".join(report["follow_up_questions"])))
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
                    str(execution.get("status", payload.get("status", ""))),
                    str(execution.get("mode", "")),
                    str(execution.get("duration_ms", payload.get("duration_ms", ""))),
                )
        lines.append(trace_table)
    console.print(Panel(Group(*lines), title="完整诊断报告与执行 Trace", border_style="cyan"))


def _render_result(decision, ctx, query, label, trace=None) -> None:
    crop_cn = CROP_CN.get(ctx.crop, ctx.crop)
    intent_cn = INTENT_CN.get(ctx.intent, ctx.intent)
    judge_tag = "DeepSeek AI 裁判" if decision.judge_mode == "deepseek" else "规则裁决"
    hdr = Table.grid(expand=True)
    hdr.add_column(justify="left", ratio=1)
    hdr.add_column(justify="right")
    left = Text.assemble(crop_cn, "  ", (intent_cn, "cyan"), "  ", (label, "bold"))
    hdr.add_row(left, Text(f" {judge_tag} ", style="black on cyan"))
    console.print(Panel(Group(hdr, Text(query, style="dim italic")), border_style="blue", padding=(1, 2)))
    _animate_trace(decision)
    _render_verdict(decision)
    _render_debate_critic(decision)
    _render_judge_analysis(decision)
    _render_action_plan(decision)
    _render_diagnosis_report(decision, trace)


def _render_trace(trace) -> None:
    if trace is None or not trace.events:
        console.print(Panel("尚无可查看的诊断 Trace。", title="执行追溯", border_style="yellow"))
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
            str(execution.get("status", payload.get("status", "已记录"))),
            str(execution.get("mode", "")),
            str(execution.get("duration_ms", payload.get("duration_ms", ""))),
        )
    console.print(Panel(table, title=f"执行 Trace · {trace.trace_id}", border_style="cyan"))


def _render_history() -> None:
    try:
        from storage.repository import get_decision, list_decisions

        rows = list_decisions(10)
    except Exception as exc:
        console.print(Panel(f"历史记录暂不可用（{type(exc).__name__}）。", title="历史记录", border_style="red"))
        return

    if not rows:
        console.print(Panel("暂无历史诊断。完成一次诊断后，记录会保存在本地 SQLite。", title="历史记录", border_style="yellow"))
        return

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
    if not decision_id.isdigit():
        return
    try:
        detail = get_decision(int(decision_id))
    except Exception as exc:
        console.print(Panel(f"读取记录失败（{type(exc).__name__}）。", title="历史详情", border_style="red"))
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
        trace_table = Table(box=box.SIMPLE, expand=True)
        trace_table.add_column("阶段", style="cyan")
        trace_table.add_column("记录时间")
        trace_table.add_column("执行单元")
        for event in events:
            payload = event.get("payload", {})
            trace_table.add_row(
                str(event.get("stage", "")),
                str(event.get("timestamp", "")),
                str(payload.get("agent", "")),
            )
        console.print(Panel(trace_table, title=f"历史 Trace · {detail.get('trace_id') or trace.get('trace_id', '')}", border_style="cyan"))


def _render_system_detail() -> None:
    try:
        from kg_adapter import kg_status

        kg = kg_status()
        neo4j_state = "已连接" if kg.get("neo4j_connected") else "未连接 / 回退可用"
    except Exception as exc:
        neo4j_state = f"状态不可用（{type(exc).__name__}）"
    report = getattr(_last_decision, "report", {}) or {}
    sources = report.get("knowledge_sources", {}) if isinstance(report, dict) else {}
    rag_state = sources.get("rag_status", "尚无诊断记录")
    rag_hits = sources.get("rag", []) or []
    rag_backend = rag_hits[0].get("backend", "未提供") if rag_hits else "未提供来源"
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("项目", style="cyan")
    table.add_column("状态")
    table.add_row("API Key", "已配置" if os.environ.get("ACIS_API_KEY", "").strip() else "未配置")
    table.add_row("DeepSeek Key", "已配置" if _DEEPSEEK_CONFIGURED else "未配置")
    table.add_row("Neo4j", neo4j_state)
    table.add_row("最近 RAG 结果", f"{rag_state} · backend={rag_backend}")
    console.print(Panel(table, title="系统状态（连接状态与配置状态分开显示）", border_style="cyan"))


def _render_help() -> None:
    help_text = (
        "输入 1–9：运行对应演示场景（固定案例会标明 DEMO / FIXTURE MODE）\n"
        "x：输入自定义农业问题\n"
        "h：查看 SQLite 历史记录并打开详情\n"
        "t：查看最近一次运行的真实 Trace\n"
        "s：查看模型配置、KG 连接和最近 RAG 状态\n"
        "j / c：切换已配置的 LLM Judge / Critic\n"
        "a：查看架构；q：退出"
    )
    console.print(Panel(help_text, title="帮助 · 键盘快捷键", border_style="green"))


# ---------------------------------------------------------------------------
# 运行
# ---------------------------------------------------------------------------
def _run_scenario(query, use_llm_judge, use_llm_critic, sensor_override, label, fixture_mode=False) -> None:
    global _last_backend, _last_decision, _last_trace
    ctx = build_context(query)
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
    try:
        with console.status(f"[bold green]调度多智能体（{mode}）…[/]", spinner="dots"):
            decision = orch.run(query)
    except Exception as exc:
        sensor_anomaly.ANOMALIES.pop("gh-a", None)
        console.print(Panel(f"[red]执行失败：{exc}[/]", title="错误"))
        return
    sensor_anomaly.ANOMALIES.pop("gh-a", None)
    try:
        _last_backend = (decision.judge_analysis or {}).get("kg", {}).get("backend", _last_backend)
    except Exception:
        pass
    _last_decision = decision
    _last_trace = orch.last_trace
    display_label = f"{label} · DEMO / FIXTURE MODE" if fixture_mode else label
    _render_result(decision, ctx, query, display_label, orch.last_trace)


def main() -> None:
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
            q = Prompt.ask("[bold]输入农业问题（作物与症状尽量描述具体）[/]")
            if q.strip():
                _run_scenario(q.strip(), use_llm_judge, use_llm_critic, None, "自定义查询")
                Prompt.ask("[dim]按回车返回菜单[/]", default="")
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


if __name__ == "__main__":
    main()
