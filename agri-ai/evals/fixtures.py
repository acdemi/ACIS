"""Fixed greenhouse scenarios for architecture regression checks.

覆盖当前三种重点作物：番茄 / 甜菜 / 棉花。crop / intent / disease 期望是确定性的
（关键词抽取 + DISEASE_DB 匹配，与随机传感器无关）。risk_level 不断言单一值——
传感器模拟器返回随机读数，仅在 fixture_eval 中校验其属于 {low, medium, high}。
"""

from __future__ import annotations

from typing import Any

FIXTURES: list[dict[str, Any]] = [
    dict(id="tomato_leaf_mold", query="温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？", crop="tomato", intent="diagnose", disease="叶霉病"),
    dict(id="tomato_early_blight", query="温室A番茄叶片同心轮纹状病斑，褐色边缘，怎么治？", crop="tomato", intent="diagnose", disease="早疫病"),
    dict(id="tomato_irrigate_with_risk", query="温室A番茄今天需要浇水吗？如果有病害风险要一起考虑", crop="tomato", intent="irrigate", disease=None),
    dict(id="tomato_monitor_no_disease", query="温室A番茄今天状态怎么样", crop="tomato", intent="monitor", disease="证据不足"),
    dict(id="sugar_beet_leaf_spot", query="温室A甜菜叶片圆形褐色病斑，中央灰白，如何处理", crop="sugar_beet", intent="diagnose", disease="褐斑病"),
    dict(id="sugar_beet_root_rot", query="温室A甜菜植株萎蔫黄化，根部腐烂，疑似根部病害如何处理", crop="sugar_beet", intent="diagnose", disease="根腐病"),
    dict(id="sugar_beet_alert", query="温室A甜菜当前有什么风险，需要优先处理", crop="sugar_beet", intent="alert", disease="证据不足"),
    dict(id="cotton_verticillium_wilt", query="温室A棉花叶片黄绿斑驳，维管束变褐，如何处理", crop="cotton", intent="diagnose", disease="黄萎病"),
    dict(id="cotton_fusarium_wilt", query="温室A棉花植株萎蔫，半边叶片发黄，如何诊断", crop="cotton", intent="diagnose", disease="枯萎病"),
    dict(id="cotton_irrigate", query="温室A棉花花铃期需要浇水吗", crop="cotton", intent="irrigate", disease="证据不足"),
    # 灌溉意图 + 已诊断真菌病害 → DebateEngine 触发"灌溉 vs 病害"冲突，Critic 必然反驳降权
    dict(id="tomato_irrigate_with_disease", query="温室A番茄叶背有灰色霉层，今天需要浇水吗，要兼顾病害风险", crop="tomato", intent="irrigate", disease="叶霉病", expect_critic=True),
    # 高湿型病害 vs 低湿环境：诊断与环境矛盾，Critic 降权病理诊断
    dict(id="tomato_mold_low_humidity", query="温室A番茄叶背有灰色霉层，环境是否适合发病", crop="tomato", intent="diagnose", disease="叶霉病", expect_critic=True, sensor_override={"humidity_offset": -25.0}),
]
