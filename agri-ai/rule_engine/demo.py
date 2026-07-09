"""
农业 Agent MVP — 主入口
"""

import asyncio
import sys
from rule_engine.router import AgentRouter

from rule_engine.sensor_simulator import (
    get_current_reading, get_all_greenhouses, get_sensor_history,
    get_greenhouse_info, inject_anomaly, clear_anomaly,
)
from agents.weather import (
    get_current_weather, get_weather_forecast,
    get_weather_for_irrigation, get_weather_alerts,
)
from rag.knowledge_base import (
    search_disease, get_disease_info, get_farming_guide,
    get_optimal_conditions, diagnose_and_advise,
)


def build_router() -> AgentRouter:
    router = AgentRouter()
    # 传感器
    router.register_tool("sensors", "get_current_reading", get_current_reading)
    router.register_tool("sensors", "get_all_greenhouses", get_all_greenhouses)
    router.register_tool("sensors", "get_sensor_history", get_sensor_history)
    router.register_tool("sensors", "get_greenhouse_info", get_greenhouse_info)
    router.register_tool("sensors", "inject_anomaly", inject_anomaly)
    router.register_tool("sensors", "clear_anomaly", clear_anomaly)
    # 气象
    router.register_tool("weather", "get_current_weather", get_current_weather)
    router.register_tool("weather", "get_weather_forecast", get_weather_forecast)
    router.register_tool("weather", "get_weather_for_irrigation", get_weather_for_irrigation)
    router.register_tool("weather", "get_weather_alerts", get_weather_alerts)
    # 知识库
    router.register_tool("knowledge", "search_disease", search_disease)
    router.register_tool("knowledge", "get_disease_info", get_disease_info)
    router.register_tool("knowledge", "get_farming_guide", get_farming_guide)
    router.register_tool("knowledge", "get_optimal_conditions", get_optimal_conditions)
    router.register_tool("knowledge", "diagnose_and_advise", diagnose_and_advise)
    return router


async def run_demo():
    router = build_router()

    print("=" * 60)
    print("  农业 Agent MVP — 端到端演示")
    print("=" * 60)
    print()

    # 场景 1: 诊断
    print("━" * 60)
    print("场景 1: 病虫害诊断")
    print("━" * 60)
    query = "温室A的番茄叶片出现黄斑，叶片背面有灰色霉层，可能是什么病？"
    print(f"用户: {query}\n")
    trace = await router.route(query)
    print(router.format_trace(trace))
    print()

    # 场景 2: 监控
    print("━" * 60)
    print("场景 2: 环境监控")
    print("━" * 60)
    query = "查看温室B黄瓜的当前状态"
    print(f"用户: {query}\n")
    trace = await router.route(query)
    print(router.format_trace(trace))
    print()

    # 场景 3: 灌溉
    print("━" * 60)
    print("场景 3: 灌溉决策")
    print("━" * 60)
    query = "温室A番茄需要浇水吗？"
    print(f"用户: {query}\n")
    trace = await router.route(query)
    print(router.format_trace(trace))
    print()

    # 场景 4: 预警
    print("━" * 60)
    print("场景 4: 预警查询")
    print("━" * 60)
    query = "温室A有什么需要特别注意的风险？"
    print(f"用户: {query}\n")
    trace = await router.route(query)
    print(router.format_trace(trace))
    print()

    # 场景 5: 注入异常后诊断
    print("━" * 60)
    print("场景 5: 注入异常 → 诊断（数字孪生测试）")
    print("━" * 60)
    print("系统: 向温室A注入 'pest_risk' 异常（模拟高温高湿环境）")
    inject_anomaly("gh-a", "pest_risk", severity=1.5)
    query = "温室A番茄叶片出现异常，帮我诊断一下"
    print(f"用户: {query}\n")
    trace = await router.route(query)
    print(router.format_trace(trace))
    print("\n系统: 清除温室A的异常")
    clear_anomaly("gh-a")

    print("\n" + "=" * 60)
    print("  演示完成")
    print("=" * 60)


async def run_interactive():
    router = build_router()
    print("=" * 60)
    print("  农业 Agent MVP — 交互模式 (输入 quit 退出)")
    print("=" * 60)
    print("示例: 温室A番茄叶片有黄斑怎么办 | 查看温室B黄瓜状态 | 需要浇水吗\n")

    while True:
        try:
            query = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query or query.lower() in ("quit", "exit", "q"):
            break
        trace = await router.route(query)
        print()
        print(router.format_trace(trace))
        print()


if __name__ == "__main__":
    if "--interactive" in sys.argv or "-i" in sys.argv:
        asyncio.run(run_interactive())
    else:
        asyncio.run(run_demo())

