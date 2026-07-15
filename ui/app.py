"""Minimal Streamlit UI for the agriculture Agent."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _env import load_env
load_env()  # 注入 .env（DEEPSEEK_API_KEY / NEO4J_PASSWORD），须在 import orchestrator 前

from orchestrator import AgentOrchestrator, format_decision


def main() -> None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise SystemExit("请先安装 streamlit，或使用 CLI: python orchestrator.py") from exc

    st.set_page_config(page_title="Agri AI", page_icon="🌱")
    st.title("🌱 Agri AI Agent")
    query = st.text_area("问题", "温室A的番茄叶片出现黄斑，叶片背面有灰色霉层")
    image_path = st.text_input("叶片图片路径（可选）", "")
    use_llm_judge = st.checkbox("启用 DeepSeek Judge（失败自动回退规则）", value=False)

    if st.button("运行诊断"):
        decision = AgentOrchestrator(use_llm_judge=use_llm_judge).run(query, image_path or None)
        st.markdown(format_decision(decision).replace("\n", "  \n"))


if __name__ == "__main__":
    main()
