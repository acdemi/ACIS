"""Static labels and demo scenarios for the terminal UI."""

from __future__ import annotations

from acis.ui.demo_cases import DEMO_CASES

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
EXECUTION_STATUS = {
    "success": ("成功", "green"),
    "completed": ("已完成", "green"),
    "degraded": ("降级", "yellow"),
    "failed": ("失败", "red"),
    "error": ("失败", "red"),
    "skipped": ("跳过", "dim"),
    "pending": ("处理中", "cyan"),
    "abstained": ("弃权（证据不足）", "yellow"),
    "abstain": ("弃权（证据不足）", "yellow"),
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
