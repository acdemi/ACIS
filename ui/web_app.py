"""
Agri AI Web UI — Streamlit 全功能界面 v2
"""

from __future__ import annotations

import json, os, sys, tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _env import load_env
load_env()

import streamlit as st

os.environ["PYTHONIOENCODING"] = "utf-8"

st.set_page_config(page_title="Agri AI", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    :root { --primary: #2d7d46; --primary-light: #e8f5e9; --warning: #ff9800; --danger: #f44336; }
    .block-container { padding-top: 1rem; }
    .diagnosis-box { background:#e8f5e9; border-left:4px solid #2d7d46; padding:1rem; border-radius:4px; margin:1rem 0; }
    .warning-box { background:#fff3e0; border-left:4px solid #ff9800; padding:1rem; border-radius:4px; margin:0.5rem 0; }
    .error-box { background:#ffebee; border-left:4px solid #f44336; padding:1rem; border-radius:4px; margin:0.5rem 0; }
    .metric-card { text-align:center; padding:0.5rem; background:#fafafa; border-radius:8px; border:1px solid #eee; }
    .metric-value { font-size:1.5rem; font-weight:700; color:#2d7d46; }
    .metric-label { font-size:0.75rem; color:#666; }
    .chat-msg { padding:0.75rem 1rem; border-radius:12px; margin-bottom:0.5rem; }
    .user-msg { background:#e3f2fd; margin-left:auto; max-width:85%; }
    .assistant-msg { background:#f5f5f5; margin-right:auto; max-width:100%; }
    .stExpander .element-container p { margin-bottom:0.25rem; }
    .stTabs [data-baseweb="tab-list"] { gap:8px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Session state
# ============================================================
for k in ("messages", "history_count", "last_decision", "editing"):
    if k not in st.session_state:
        st.session_state[k] = None if k == "last_decision" else (0 if k == "history_count" else [])

# ============================================================
# Helpers
# ============================================================
def _cc(s):
    return "#2d7d46" if s >= 0.7 else "#ff9800" if s >= 0.4 else "#f44336"
def _ri(l):
    return {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(l, "⚪")
def _fmt_sensor(r):
    if not r: return ""
    L = {"air_temperature":"🌡️气温","air_humidity":"💧湿度","soil_moisture":"🪴土壤含水","soil_temperature":"🌡️地温","co2_concentration":"💨CO₂","light_intensity":"☀️光照","soil_ph":"🧪pH"}
    return " | ".join(f"{L.get(k,k)}: **{v}**" for k,v in r.items())
def _fmt_triples(ts):
    if not ts: return ""
    return "&nbsp;&nbsp;".join(f"`{t['subject']}` **{t['relation']}**→ `{t['object']}`" for t in ts[:6] if t.get("subject") and t.get("relation") and t.get("object"))

def _run(query, img=None, llm=False, critic=False):
    from orchestrator import AgentOrchestrator
    return AgentOrchestrator(use_llm_judge=llm, use_llm_critic=critic).run(query, img)

SCENARIOS = {
    "🍅 番茄叶霉病": "温室A番茄叶片出现黄斑，叶片背面有灰色霉层，如何处理？",
    "🥒 黄瓜霜霉病": "温室B黄瓜叶片出现多角形黄斑，叶背有灰黑色霉层，如何防治？",
    "💧 灌溉决策": "温室A番茄今天需要浇水吗？如果同时有病害风险怎么办？",
    "🌡️ 健康检查": "检查温室A所有传感器的环境状态并给出评估",
    "🛡️ 综合预警": "温室A番茄最近状态不好，帮我全面检查环境、天气和病害风险",
}

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown("""<div style="text-align:center;padding:0.5rem 0"><div style="font-size:2rem">🌱</div>
        <div style="font-size:1.1rem;font-weight:600;color:#2d7d46">Agri AI</div>
        <div style="font-size:0.75rem;color:#666">温室智能诊断系统</div></div>""", unsafe_allow_html=True)
    st.divider()
    st.markdown("**⚙️ 设置**")
    use_llm = st.checkbox("DeepSeek Judge", key="llm_judge")
    use_critic = st.checkbox("DeepSeek Critic", key="llm_critic")
    if (use_llm or use_critic) and not os.environ.get("DEEPSEEK_API_KEY"):
        st.warning("⚠️ DEEPSEEK_API_KEY 未设置，将自动回退规则模式")
    st.divider()
    st.markdown("**📡 状态**")
    try:
        from kg_adapter import kg_status as kgs
        ks = kgs()
        st.markdown(f"{'🟢' if ks['neo4j_connected'] else '🟡'} Neo4j: {'在线' if ks['neo4j_connected'] else '降级（内存）'}")
    except Exception:
        st.markdown("🔴 KG: 不可用")
    st.divider()
    st.markdown("**⚡ 快捷场景**")
    for label, q in SCENARIOS.items():
        if st.button(label, use_container_width=True, key=f"sc_{label[:4]}"):
            st.session_state.editing = q
            st.rerun()
    st.divider()
    st.caption(f"诊断次数: {st.session_state.history_count}")
    if st.button("🗑️ 清空会话", use_container_width=True):
        for k in ("messages", "history_count", "last_decision", "editing"):
            st.session_state[k] = None if k == "last_decision" else (0 if k == "history_count" else [])
        st.rerun()

# ============================================================
# Main area
# ============================================================
st.markdown("## 🧪 温室智能诊断")

query = st.text_area("描述作物问题", value=st.session_state.editing or "", placeholder="例如：温室A番茄叶片发黄、温室B黄瓜需要浇水吗？", height=60, label_visibility="collapsed")
st.session_state.editing = ""

img_col, btn_col = st.columns([1, 5])
with img_col:
    uploaded = st.file_uploader("📷 图片", type=["jpg","jpeg","png"], label_visibility="collapsed")
with btn_col:
    run_btn = st.button("🚀 运行诊断", type="primary", use_container_width=True)

image_path = None
if uploaded:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    tmp.write(uploaded.getvalue())
    image_path = tmp.name
    st.image(uploaded, width=80)

# ============================================================
# Diagnosis execution + display
# ============================================================
if run_btn and query.strip():
    st.session_state.messages.append({"role": "user", "content": query, "time": __import__("datetime").datetime.now().strftime("%H:%M:%S")})
    with st.spinner("🧠 Agent 协作诊断中..."):
        try:
            d = _run(query, image_path, use_llm, use_critic)
            st.session_state.last_decision = d
            st.session_state.history_count += 1
            st.session_state.messages.append({"role": "assistant", "content": f"诊断完成 (judge_mode={d.judge_mode})", "time": __import__("datetime").datetime.now().strftime("%H:%M:%S")})
        except Exception as e:
            st.error(f"诊断出错: {e}")
    if image_path and os.path.exists(image_path):
        try: os.unlink(image_path)
        except: pass

# ============================================================
# Decision rendering
# ============================================================
def _show_decision(d):
    traces = getattr(d, "traces", [])
    debate = getattr(d, "debate", None)
    jm = getattr(d, "judge_mode", "rules")
    st.divider()
    cols = st.columns(4)
    c = _cc(d.confidence) if hasattr(d, "confidence") else "#666"
    cols[0].markdown(f"<div class='metric-card'><div class='metric-value' style='color:{c}'>{d.confidence:.0%}</div><div class='metric-label'>置信度</div></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='metric-card'><div class='metric-value'>{_ri(d.risk_level)}</div><div class='metric-label'>风险: {d.risk_level}</div></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='metric-card'><div class='metric-value'>{len(traces)}</div><div class='metric-label'>Agent</div></div>", unsafe_allow_html=True)
    cols[3].markdown(f"<div class='metric-card'><div class='metric-value'>{jm}</div><div class='metric-label'>裁决</div></div>", unsafe_allow_html=True)

    conclusion = getattr(d, "decision", "") or getattr(d, "summary", "")
    if getattr(d, "need_human_review", False):
        st.warning("⚠️ 需要人工复核")
    st.markdown(f"<div class='diagnosis-box'>{conclusion}</div>", unsafe_allow_html=True)

    ap = getattr(d, "action_plan", [])
    if ap:
        st.markdown("**📋 建议**")
        for i, a in enumerate(ap, 1): st.markdown(f"{i}. {a}")

    if traces:
        st.markdown("**🔍 Agent 链路**")
        tabs = st.tabs([f"{getattr(t,'agent','?')[:6]}·{getattr(t,'confidence',0):.0%}" for t in traces])
        for i, t in enumerate(traces):
            with tabs[i]:
                claim = getattr(t, "claim", "")
                conf = getattr(t, "confidence", 0)
                c2 = _cc(conf)
                st.markdown(f"**{claim}**")
                st.markdown(f"<div style='height:6px;border-radius:3px;background:#e0e0e0'><div style='height:100%;border-radius:3px;width:{conf*100}%;background:{c2}'></div></div>", unsafe_allow_html=True)
                ev = getattr(t, "evidence", {}) or {}
                if ev:
                    readings = ev.get("readings") or ev.get("sensor", {})
                    if readings: st.markdown(f"**传感器**: {_fmt_sensor(readings)}")
                    triples = ev.get("triples", [])
                    if triples: st.markdown(f"**KG**: {_fmt_triples(triples)}")
                    weather = ev.get("weather", {})
                    if weather: st.markdown(f"**天气**: {weather.get('summary','')}"[:200])
                for w in (getattr(t, "warnings", []) or []):
                    st.markdown(f"<div class='warning-box'>⚠️ {w}</div>", unsafe_allow_html=True)
                for r in (getattr(t, "recommendations", []) or []):
                    st.markdown(f"- {r}")

    if debate:
        st.markdown("**⚖️ Debate**")
        cons = getattr(debate, "consensus", []) or []
        confl = getattr(debate, "conflicts", []) or []
        missing = getattr(debate, "missing_evidence", []) or []
        for c in cons: st.markdown(f"✅ {c}")
        for c in confl: st.markdown(f"<div class='error-box'>⚡ {c}</div>", unsafe_allow_html=True)
        for m in missing: st.markdown(f"⚠️ {m}")
        critic = getattr(debate, "critic", {}) or {}
        if critic:
            with st.expander("🛡️ Critic"):
                st.json(critic)
        ja = getattr(d, "judge_analysis", {})
        if ja:
            with st.expander("⚖️ Judge"):
                w = ja.get("winner",""); l = ja.get("loser","")
                if w: st.markdown(f"**胜**: {w}")
                if l: st.markdown(f"**负**: {l}")
                for k2, v2 in ja.items():
                    if k2 not in ("winner","loser"): st.markdown(f"**{k2}**: {json.dumps(v2,ensure_ascii=False)[:200]}")

    rt = getattr(d, "reasoning_trace", "")
    if rt:
        with st.expander("🧠 推理日志"): st.markdown(f"```\n{rt}\n```")

# ============================================================
# Render results
# ============================================================
last = st.session_state.last_decision
if last is None and not st.session_state.messages:
    st.info("👆 输入问题后点击「运行诊断」，系统将自动调度多 Agent 协作流程。")
    for ex in list(SCENARIOS.values())[:3]:
        st.markdown(f"- {ex}")
elif last is not None:
    _show_decision(last)

# ============================================================
# History panel
# ============================================================
st.divider()
st.markdown("## 📋 历史决策")
try:
    from storage.repository import list_decisions, get_decision, set_feedback
    rows = list_decisions(50)
    if rows:
        st.caption(f"共 {len(rows)} 条（SQLite 持久化）")
        opts = {}
        for r in rows:
            fb = r.get("feedback")
            tag = {"correct":"✅","incorrect":"❌","partial":"⚠️"}.get(fb, "⬜")
            opts[f"{tag} #{r['id']} {r['created_at']} · {r['crop']} · {str(r['decision'])[:25]}"] = r["id"]
        sel = st.selectbox("选择查看", list(opts.keys()), label_visibility="collapsed")
        did = opts[sel]
        det = get_decision(did)
        if det:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("置信度", f"{det['confidence']:.0%}")
            m2.metric("风险", det["risk_level"])
            m3.metric("裁决", det["judge_mode"])
            m4.metric("复核", det.get("feedback") or "未标记")
            st.markdown(f"**查询**: {det['query']}")
            st.markdown(f"**裁决**: {det['decision']}")
            for i, a in enumerate((det.get("action_plan") or [])[:6], 1): st.markdown(f"{i}. {a}")
            traces = det.get("traces") or []
            if traces:
                with st.expander(f"Agent Trace（{len(traces)}）"):
                    for t in traces: st.markdown(f"- [{t.get('layer')}] {t.get('agent')}: {t.get('claim')} ({t.get('confidence',0):.0%})")
            st.markdown("**人工复核**（回灌案例库，影响后续诊断）")
            b1, b2, b3 = st.columns(3)
            if b1.button("✅ 正确", key=f"ok-{did}"): set_feedback(did, "correct"); st.rerun()
            if b2.button("❌ 错误", key=f"no-{did}"): set_feedback(did, "incorrect"); st.rerun()
            if b3.button("⚠️ 部分", key=f"pa-{did}"): set_feedback(did, "partial"); st.rerun()
    else:
        st.info("暂无历史决策")
except Exception as exc:
    st.caption(f"存储不可用: {exc}")

if __name__ == "__main__":
    pass