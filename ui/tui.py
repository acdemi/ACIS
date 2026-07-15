"""TUI 演示界面 — 农业 Agent v4 多智能体决策系统

面试演示用交互式终端界面，基于 rich。
单文件、零额外配置：自动加载 DeepSeek Key 与 Neo4j 连接，离线可跑。

启动：
    python -m ui.tui
"""

from __future__ import annotations

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

# 离线/编码兜底（.env 未覆盖时用默认值）
os.environ.setdefault("NEO4J_PASSWORD", "agriai2026")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

_DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip() or None

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

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
CROP_CN = {
    "tomato": "🍅 番茄",
    "cucumber": "🥒 黄瓜",
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
]

console = Console()
_orch_cache: dict[tuple[bool, bool], AgentOrchestrator] = {}
_last_backend = "未运行"


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
                    Text("面试演示 · 感知 → 记忆 → 专家 → 辩论 → Critic → Judge", style="cyan"),
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
    if _DEEPSEEK_KEY:
        ds = Text(f" DeepSeek: ✓ …{_DEEPSEEK_KEY[-4:]} ", style="green")
    else:
        ds = Text(" DeepSeek: ✗ 未配置 ", style="red")
    neo = Text(" Neo4j: agriai2026 ", style="magenta")
    rag = Text(f" RAG: auto · KG后端:{_last_backend} ", style="cyan")
    j = Text(" Judge:开 ", style="black on green") if use_llm_judge else Text(" Judge:关 ", style="dim")
    c = Text(" Critic:开 ", style="black on green") if use_llm_critic else Text(" Critic:关 ", style="dim")
    t.add_row(ds, neo, rag, Text.assemble(j, c))
    console.print(Panel(t, title="[bold]系统状态[/]", border_style="dim", padding=(0, 2)))


# ---------------------------------------------------------------------------
# 渲染：菜单
# ---------------------------------------------------------------------------
def _menu(use_llm_judge: bool, use_llm_critic: bool) -> str:
    t = Table(box=None, show_header=False, expand=True, padding=(0, 1))
    t.add_column("序", width=3)
    t.add_column("场景", ratio=2)
    t.add_column("作物 / 意图", ratio=2)
    t.add_column("演示亮点", ratio=4)
    for i, s in enumerate(DEMO_SCENARIOS, 1):
        t.add_row(
            Text(str(i), style="bold cyan"),
            Text(s["title"], style="bold"),
            Text(f"{CROP_CN.get(s['crop'], '')} · {INTENT_CN.get(s['intent'], '')}", style="dim"),
            Text(s["highlight"], style="dim"),
        )
    console.print(Panel(t, title="[bold]演示场景（输入序号运行）[/]", border_style="blue"))

    j_state = Text(" 开 ", style="black on green") if use_llm_judge else Text(" 关 ", style="white on red")
    c_state = Text(" 开 ", style="black on green") if use_llm_critic else Text(" 关 ", style="white on red")
    ctrl = Table.grid(expand=True, padding=(0, 2))
    ctrl.add_column(justify="left", ratio=1)
    ctrl.add_column(justify="left", ratio=1)
    ctrl.add_column(justify="left", ratio=1)
    ctrl.add_column(justify="right", ratio=1)
    ctrl.add_row(
        Text("[6] ✍  自定义输入", style="bold"),
        Text.assemble("[j] DeepSeek Judge ", j_state),
        Text.assemble("[c] Critic 反驳 ", c_state),
        Text("[a] 架构  [q] 退出", style="dim"),
    )
    console.print(ctrl)
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


def _render_result(decision, ctx, query, label) -> None:
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


# ---------------------------------------------------------------------------
# 运行
# ---------------------------------------------------------------------------
def _run_scenario(query, use_llm_judge, use_llm_critic, sensor_override, label) -> None:
    global _last_backend
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
    _render_result(decision, ctx, query, label)


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
        elif choice == "j":
            if not _DEEPSEEK_KEY:
                console.print("[red]未检测到 DeepSeek API Key，无法开启 AI 裁判。[/]")
            else:
                use_llm_judge = not use_llm_judge
                console.print(f"[green]DeepSeek Judge：{'开' if use_llm_judge else '关'}[/]")
        elif choice == "c":
            if not _DEEPSEEK_KEY:
                console.print("[red]未检测到 DeepSeek API Key，无法开启 Critic 反驳。[/]")
            else:
                use_llm_critic = not use_llm_critic
                console.print(f"[green]Critic 反驳：{'开' if use_llm_critic else '关'}[/]")
        elif choice == "6":
            q = Prompt.ask("[bold]输入农业问题[/]")
            if q.strip():
                _run_scenario(q.strip(), use_llm_judge, use_llm_critic, None, "自定义查询")
                Prompt.ask("[dim]按回车返回菜单[/]", default="")
        elif choice.isdigit() and 1 <= int(choice) <= len(DEMO_SCENARIOS):
            s = DEMO_SCENARIOS[int(choice) - 1]
            _run_scenario(s["query"], use_llm_judge, use_llm_critic, s["sensor_override"], s["title"])
            Prompt.ask("[dim]按回车返回菜单[/]", default="")
        else:
            console.print("[yellow]无效选择[/]")


if __name__ == "__main__":
    main()
