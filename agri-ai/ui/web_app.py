"""
Agri AI Web UI — Streamlit 全功能界面
不依赖 TUI，独立可运行。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _env import load_env
load_env()  # 注入 .env（DEEPSEEK_API_KEY / NEO4J_PASSWORD），须在 import orchestrator 前

import streamlit as st

os.environ["PYTHONIOENCODING"] = "utf-8"

# ============================================================
# 页面配置（必须是第一个 streamlit 命令）
# ============================================================

st.set_page_config(
    page_title="Agri AI — 温室智能诊断",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 样式
# ============================================================

st.markdown("""
<style>
    /* 主色调 */
    :root {
        --primary: #2d7d46;
        --primary-light: #e8f5e9;
        --warning: #ff9800;
        --danger: #f44336;
        --info: #2196f3;
    }
    .block-container { padding-top: 1.5rem; }
    /* Agent 卡片 */
    .agent-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        background: white;
    }
    .agent-card .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    .agent-card .agent-name {
        font-weight: 600;
        font-size: 0.95rem;
    }
    .agent-card .layer-tag {
        font-size: 0.75rem;
        background: #e8f5e9;
        color: #2d7d46;
        padding: 2px 8px;
        border-radius: 10px;
    }
    .confidence-bar {
        height: 6px;
        border-radius: 3px;
        background: #e0e0e0;
        margin: 4px 0;
    }
    .confidence-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s;
    }
    /* 诊断结论 */
    .diagnosis-box {
        background: #e8f5e9;
        border-left: 4px solid #2d7d46;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .error-box {
        background: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .triple-tag {
        display: inline-block;
        background: #f3f4f6;
        padding: 2px 8px;
        border-radius: 4px;
        margin: 2px;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .metric-card {
        text-align: center;
        padding: 0.5rem;
        background: #fafafa;
        border-radius: 8px;
        border: 1px solid #eee;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #2d7d46;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #666;
    }
    .chat-message {
        padding: 0.75rem 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
        max-width: 85%;
    }
    .user-msg {
        background: #e3f2fd;
        margin-left: auto;
    }
    .assistant-msg {
        background: #f5f5f5;
        margin-right: auto;
    }
    /* stTabs 内边距修正 */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 16px; }
    /* 确保 expander 内 md 正常 */
    .stExpander .element-container p { margin-bottom: 0.25rem; }
    /* 发散/收敛可视化 */
    .debate-flow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .debate-node {
        padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 500;
    }
    .debate-node.agree { background: #e8f5e9; color: #2d7d46; }
    .debate-node.conflict { background: #ffebee; color: #c62828; }
    .debate-arrow { color: #999; font-size: 1.2rem; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 会话状态
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []
if "history_count" not in st.session_state:
    st.session_state.history_count = 0
if "last_decision" not in st.session_state:
    st.session_state.last_decision = None


# ============================================================
# 工具函数
# ============================================================

def _confidence_color(score: float) -> str:
    if score >= 0.7:
        return "#2d7d46"
    if score >= 0.4:
        return "#ff9800"
    return "#f44336"


def _risk_icon(level: str) -> str:
    return {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(level, "⚪")


def _format_sensor_table(readings: dict) -> str:
    if not readings:
        return "暂无传感器数据"
    lines = []
    labels = {
        "air_temperature": "🌡️ 气温", "air_humidity": "💧 湿度",
        "soil_moisture": "🪴 土壤含水", "soil_temperature": "🌡️ 地温",
        "co2_concentration": "💨 CO₂", "light_intensity": "☀️ 光照",
        "soil_ph": "🧪 pH",
    }
    for k, v in readings.items():
        label = labels.get(k, k)
        lines.append(f"{label}: **{v}**")
    return " | ".join(lines)


def _format_kg_triples(triples: list) -> str:
    if not triples:
        return ""
    parts = []
    for t in triples[:8]:
        s = t.get("subject", "")
        r = t.get("relation", "")
        o = t.get("object", "")
        if s and r and o:
            parts.append(f"`{s}` —**{r}**→ `{o}`")
    return " &nbsp;&nbsp; ".join(parts)


def _run_diagnosis(query: str, image_path: str | None,
                   use_llm: bool, use_llm_critic: bool) -> dict | None:
    """在 spinner 中执行诊断，返回 decision dict"""
    from orchestrator import AgentOrchestrator

    orch = AgentOrchestrator(
        use_llm_judge=use_llm,
        use_llm_critic=use_llm_critic,
    )
    decision = orch.run(query, image_path)
    return decision


# ============================================================
# 侧边栏
# ============================================================

with st.sidebar:
    st.markdown("""<div style="text-align:center; padding:1rem 0">
        <div style="font-size:2.5rem; margin-bottom:0.25rem">🌱</div>
        <div style="font-size:1.1rem; font-weight:600; color:#2d7d46">Agri AI</div>
        <div style="font-size:0.8rem; color:#666">温室智能诊断系统</div>
    </div>""", unsafe_allow_html=True)

    st.divider()

    # — LLM 设置 —
    st.markdown("**🤖 大模型设置**")
    use_llm_judge = st.checkbox("启用 DeepSeek Judge", value=False,
                                help="启用后使用 DeepSeek 做结构化裁决，失败自动回退规则")
    use_llm_critic = st.checkbox("启用 DeepSeek Critic 反驳", value=False,
                                 help="启用后Critic使用LLM做多轮反驳降权，失败回退规则反驳")

    key_missing = not os.environ.get("DEEPSEEK_API_KEY", "")
    if (use_llm_judge or use_llm_critic) and key_missing:
        st.warning("⚠️ 当前环境变量 DEEPSEEK_API_KEY 为空，LLM 模式将自动回退规则。")

    st.divider()

    # — 系统状态 —
    st.markdown("**📡 系统状态**")

    kg_status = "🔴 未知"
    neo4j_label = "未检测"
    try:
        from kg_adapter import kg_status as get_kg_status
        ks = get_kg_status()
        if ks.get("neo4j_connected"):
            kg_status = "🟢"
            neo4j_label = "Neo4j 在线"
        else:
            kg_status = "🟡"
            neo4j_label = "Neo4j 降级（内存模式）"
    except Exception:
        pass
    st.markdown(f"{kg_status} {neo4j_label}")

    try:
        from rule_engine.sensor_anomaly import check_anomaly
        sensor_ok = check_anomaly("gh-a")
        if sensor_ok and not sensor_ok.get("error"):
            st.markdown(f"🟢 传感器模拟器在线")
        else:
            st.markdown(f"🟡 传感器模拟器不可用")
    except Exception:
        st.markdown(f"🟡 传感器模拟器不可用")

    st.divider()

    # — 关于 —
    with st.expander("ℹ️ 关于"):
        st.markdown("""
        **版本：** v4
        **架构：** Orchestrator / Debate / Judge
        **知识库：** DISEASE_DB + AgriKG（Neo4j）
        **编排：** LangGraph 主图 + 规则回退
        **支持作物：** 番茄、甜菜、棉花
        """)

    st.divider()
    st.caption(f"会话已诊断 {st.session_state.history_count} 次")


# ============================================================
# 主界面
# ============================================================

col_title, col_clear = st.columns([6, 1])
with col_title:
    st.markdown("## 🧪 温室智能诊断")
    st.markdown("输入作物症状、环境问题或管理咨询，系统自动调度多 Agent 协作诊断并输出结构化报告。")
with col_clear:
    st.divider()
    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history_count = 0
        st.session_state.last_decision = None
        st.rerun()

st.divider()

# ============================================================
# 输入区
# ============================================================

with st.container():
    input_col, img_col = st.columns([3, 1])
    with input_col:
        query = st.text_area(
            "描述作物问题",
            value="温室A番茄叶片出现黄斑，叶片背面有灰色霉层，如何处理？",
            placeholder="例如：温室A番茄叶片发黄、温室B黄瓜需要浇水吗？",
            height=80,
            label_visibility="collapsed",
        )
    with img_col:
        st.markdown("**📷 叶片图片（可选）**")
        uploaded_file = st.file_uploader(
            "上传图片", type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
        )
        image_path = None
        if uploaded_file:
            # 保存到临时位置
            import tempfile
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.write(uploaded_file.getvalue())
            image_path = tmp.name
            st.image(uploaded_file, width=120, caption="已上传")
            st.caption(f"({len(uploaded_file.getvalue())//1024}KB)")

    run_col, _ = st.columns([1, 6])
    with run_col:
        run_btn = st.button("🚀 运行诊断", type="primary", use_container_width=True)


# ============================================================
# 诊断执行
# ============================================================

if run_btn and query.strip():
    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": query})

    with st.spinner("🧠 Agent 协作诊断中..."):
        try:
            decision = _run_diagnosis(
                query, image_path,
                use_llm=use_llm_judge,
                use_llm_critic=use_llm_critic,
            )
            st.session_state.last_decision = decision
            st.session_state.history_count += 1
        except Exception as e:
            st.error(f"诊断过程出错: {e}")
            decision = None

    if decision:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"诊断完成 (judge_mode={decision.judge_mode})",
        })

    if image_path and os.path.exists(image_path):
        try:
            os.unlink(image_path)
        except Exception:
            pass

# ============================================================
# 显示诊断结果（核心） — 定义在使用前
# ============================================================

def _show_decision(d: Any) -> None:
    """渲染 DecisionOutput 为结构化 UI"""
    traces: list = getattr(d, "traces", [])
    debate = getattr(d, "debate", None)
    judge_mode = getattr(d, "judge_mode", "rules")

    # ——— 顶层指标行 ———
    st.markdown("## 📊 诊断概览")
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        conf = getattr(d, "confidence", 0)
        c = _confidence_color(conf)
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value" style="color:{c}">{conf:.0%}</div>'
            f'<div class="metric-label">综合置信度</div></div>',
            unsafe_allow_html=True)
    with mcol2:
        risk = getattr(d, "risk_level", "low")
        icon = _risk_icon(risk)
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{icon}</div>'
            f'<div class="metric-label">风险等级: {risk}</div></div>',
            unsafe_allow_html=True)
    with mcol3:
        n_agents = len(traces)
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{n_agents}</div>'
            f'<div class="metric-label">参与 Agent</div></div>',
            unsafe_allow_html=True)
    with mcol4:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{judge_mode}</div>'
            f'<div class="metric-label">裁决模式</div></div>',
            unsafe_allow_html=True)

    # ——— 诊断结论 ———
    summary = getattr(d, "summary", "")
    decision_text = getattr(d, "decision", "")
    action_plan = getattr(d, "action_plan", [])
    need_review = getattr(d, "need_human_review", False)

    st.markdown("### 💡 诊断结论")
    conclusion = decision_text or summary

    if need_review:
        st.warning("⚠️ 该系统诊断需要人工复核确认")
    st.markdown(
        f'<div class="diagnosis-box">{conclusion}</div>',
        unsafe_allow_html=True)

    # ——— 行动方案 ———
    if action_plan:
        st.markdown("### 📋 建议措施")
        for i, action in enumerate(action_plan, 1):
            st.markdown(f"{i}. {action}")

    # ——— Agent 推理追踪 ———
    if traces:
        st.markdown("### 🔍 Agent 推理链路")
        tab_names = []
        for t in traces:
            agent_name = getattr(t, "agent", "?")
            layer = getattr(t, "layer", "?")
            tab_names.append(f"{layer}:{agent_name}")

        tabs = st.tabs(tab_names)
        for i, t in enumerate(traces):
            with tabs[i]:
                _show_agent_output(t)

    # ——— Debate & Judge ———
    if debate:
        st.markdown("### ⚖️ Debate & Judge")
        _show_debate(debate, getattr(d, "judge_analysis", {}))

    # ——— 摘要 / reasoning trace ———
    reasoning = getattr(d, "reasoning_trace", "")
    if reasoning:
        with st.expander("🧠 推理过程日志"):
            st.markdown(f"```\n{reasoning}\n```")


def _show_agent_output(t: Any) -> None:
    layer = getattr(t, "layer", "?")
    agent = getattr(t, "agent", "?")
    claim = getattr(t, "claim", "")
    confidence = getattr(t, "confidence", 0.0)
    evidence = getattr(t, "evidence", {}) or {}
    warnings = getattr(t, "warnings", []) or []
    recommendations = getattr(t, "recommendations", []) or []

    conf_color = _confidence_color(confidence)

    # 头部：声明 + 置信度
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown(f"**{claim}**" if claim else "_无输出_")
    with cols[1]:
        st.markdown(
            f'<div style="text-align:right">'
            f'<span style="font-size:1.2rem;font-weight:700;color:{conf_color}">{confidence:.0%}</span>'
            f'</div>',
            unsafe_allow_html=True)
    st.markdown(
        f'<div class="confidence-bar">'
        f'<div class="confidence-fill" style="width:{confidence*100}%;background:{conf_color}"></div>'
        f'</div>',
        unsafe_allow_html=True)

    # 证据
    if evidence:
        with st.expander("📎 证据", expanded=False):
            # 传感器读数
            readings = evidence.get("readings") or evidence.get("sensor", {})
            if isinstance(readings, dict) and readings:
                st.markdown(f"**传感器读数**：{_format_sensor_table(readings)}")

            # 天气
            weather = evidence.get("weather", {})
            if isinstance(weather, str):
                st.markdown(f"**天气**：{weather}")
            elif isinstance(weather, dict) and weather:
                st.markdown(f"**天气**：{weather.get('summary', json.dumps(weather, ensure_ascii=False)[:100])}")

            # KG 三元组
            triples = evidence.get("triples", [])
            if triples:
                st.markdown("**知识图谱三元组**：")
                html = _format_kg_triples(triples)
                if html:
                    st.markdown(f'<div>{html}</div>', unsafe_allow_html=True)

            # 其他证据
            for k, v in evidence.items():
                if k in ("readings", "sensor", "weather", "triples"):
                    continue
                if v:
                    text = json.dumps(v, ensure_ascii=False)[:200] if not isinstance(v, str) else v
                    st.markdown(f"**{k}**：{text}")

    # 告警
    if warnings:
        for w in warnings:
            st.markdown(f'<div class="warning-box">⚠️ {w}</div>', unsafe_allow_html=True)

    # 建议
    if recommendations:
        st.markdown("**建议：**")
        for r in recommendations:
            st.markdown(f"- {r}")


def _show_debate(debate: Any, judge_analysis: dict) -> None:
    consensus = getattr(debate, "consensus", []) or []
    conflicts = getattr(debate, "conflicts", []) or []
    missing = getattr(debate, "missing_evidence", []) or []
    risk_level = getattr(debate, "risk_level", "low")
    critic = getattr(debate, "critic", {}) or {}

    # — Consensus 共识
    if consensus:
        st.markdown("**✅ 共识**")
        for c in consensus:
            st.markdown(f"- {c}")

    # — Conflicts 冲突
    if conflicts:
        st.markdown("**❌ 冲突**")
        for c in conflicts:
            st.markdown(
                f'<div class="error-box">⚡ {c}</div>',
                unsafe_allow_html=True)

    # — Missing evidence
    if missing:
        st.markdown("**⚠️ 证据不足**")
        for m in missing:
            st.markdown(f"- {m}")

    # — Critic
    if critic:
        with st.expander("🛡️ Critic 反驳详情", expanded=False):
            _show_agent_output(critic) if hasattr(critic, "agent") else \
                st.json(critic)

    # — Judge 分析
    if judge_analysis:
        with st.expander("⚖️ Judge 裁决分析", expanded=False):
            # 显示结构化裁决
            st.markdown("**裁决理由**")
            st.markdown(judge_analysis.get("reasoning", ""))

            # 扇形图：哪个 Agent 赢了
            winner = judge_analysis.get("winner", "")
            loser = judge_analysis.get("loser", "")
            vote = judge_analysis.get("vote", "")
            if winner:
                st.markdown(f"**裁决结果**：{vote} — **{winner}** → {judge_analysis.get('vote', '')}")
                if loser:
                    st.markdown(f"**被驳回**：{loser}")

            # judge_analysis 中其他字段
            for k, v in judge_analysis.items():
                if k in ("reasoning", "winner", "loser", "vote", "judge_mode"):
                    continue
                if v:
                    text = json.dumps(v, ensure_ascii=False)[:200] if not isinstance(v, str) else str(v)
                    st.markdown(f"**{k}**：{text}")


# ============================================================
# 结果显示（在函数定义之后）
# ============================================================

last = st.session_state.last_decision
if last is None:
    # 未运行过，显示欢迎/引导
    st.info("👆 输入问题后点击「运行诊断」，系统将自动调度多 Agent 协作流程。")
    st.markdown("""
    **🌱 示例问题：**
    - "温室A番茄叶片出现黄斑，叶片背面有灰色霉层，如何处理？"
    - "温室B黄瓜今天需要浇水吗？有哪些风险要考虑？"
    - "温室A甜菜叶片圆形褐色病斑，帮我诊断一下"
    - "检查所有温室的环境状态和预警信息"
    """)
elif isinstance(last, dict):
    # 兼容 dict 格式
    pass
else:
    _show_decision(last)


def _show_history_panel() -> None:
    # 历史决策记录：SQLite 持久化 + 详情查看 + 人工复核反馈回灌
    st.markdown("## 📋 历史决策记录")
    try:
        from storage.repository import list_decisions, get_decision, set_feedback
    except Exception as exc:
        st.warning(f"存储层不可用：{exc}")
        return
    rows = list_decisions(50)
    if not rows:
        st.info("暂无历史决策。运行一次诊断后会自动保存到 SQLite。")
        return
    st.caption(f"共 {len(rows)} 条决策（SQLite 持久化，按时间倒序）")
    options = {}
    for r in rows:
        fb = r.get("feedback")
        tag = {"correct": "✅", "incorrect": "❌", "partial": "⚠️"}.get(fb, "⬜")
        label = f"{tag} #{r['id']} {r['created_at']} · {r['crop']} · {r['decision'][:20]}"
        options[label] = r["id"]
    sel = st.selectbox("选择决策查看详情", list(options.keys()))
    did = options[sel]
    detail = get_decision(did)
    if not detail:
        st.warning("该决策不存在")
        return
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("置信度", f"{detail['confidence']:.0%}")
    m2.metric("风险", detail["risk_level"])
    m3.metric("裁决模式", detail["judge_mode"])
    m4.metric("人工复核", detail.get("feedback") or "未标记")
    st.markdown(f"**查询：** {detail['query']}")
    st.markdown(f"**裁决：** {detail['decision']}")
    actions = detail.get("action_plan") or []
    if actions:
        st.markdown("**行动建议：**")
        for i, a in enumerate(actions, 1):
            st.markdown(f"{i}. {a}")
    traces = detail.get("traces") or []
    if traces:
        with st.expander(f"Agent Trace（{len(traces)} 个 Agent）"):
            for t in traces:
                conf = t.get("confidence", 0)
                st.markdown(f"- **[{t.get('layer')}] {t.get('agent')}** · {t.get('claim')}（{conf:.0%}）")
    debate = detail.get("debate") or {}
    if debate.get("conflicts"):
        with st.expander("Debate 冲突"):
            for c in debate["conflicts"]:
                st.markdown(f"- {c}")
    st.markdown("**人工复核反馈**（标记后回灌案例库，影响后续诊断）")
    b1, b2, b3, _ = st.columns([1, 1, 1, 4])
    if b1.button("✅ 正确", key=f"ok-{did}"):
        set_feedback(did, "correct")
        st.success("已标记正确，将作为确认案例回灌案例库")
        st.rerun()
    if b2.button("❌ 错误", key=f"no-{did}"):
        set_feedback(did, "incorrect")
        st.success("已标记错误")
        st.rerun()
    if b3.button("⚠️ 部分", key=f"po-{did}"):
        set_feedback(did, "partial")
        st.success("已标记部分正确")
        st.rerun()


# ============================================================
# 历史决策面板
# ============================================================

st.divider()
_show_history_panel()


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    pass  # streamlit run 启动