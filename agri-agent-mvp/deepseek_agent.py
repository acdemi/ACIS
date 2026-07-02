"""
DeepSeek 驱动的 Agent Router

替代原来的规则引擎，用 DeepSeek-V3 的原生工具调用能力做意图识别和工具编排。
API 兼容 OpenAI 格式，只需改 base_url 即可切换。
"""

import json
import os
from openai import OpenAI
from typing import Any


# ============================================================
# DeepSeek 客户端配置
# ============================================================

def get_client() -> OpenAI:
    """获取 DeepSeek 客户端（OpenAI 兼容格式）"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError(
            "请设置环境变量 DEEPSEEK_API_KEY\n"
            "  获取地址: https://platform.deepseek.com/api-keys\n"
            "  设置方式: set DEEPSEEK_API_KEY=sk-xxx (Windows CMD)\n"
            "           $env:DEEPSEEK_API_KEY='sk-xxx' (PowerShell)"
        )
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


# ============================================================
# 工具定义（OpenAI function calling 格式）
# ============================================================

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_reading",
            "description": "获取指定温室的当前传感器读数，包括温度、湿度、土壤含水率、CO2浓度、光照、pH、叶面湿度等",
            "parameters": {
                "type": "object",
                "properties": {
                    "greenhouse_id": {
                        "type": "string",
                        "description": "温室ID，可选值: gh-a（番茄区）, gh-b（黄瓜区）",
                        "enum": ["gh-a", "gh-b"],
                    }
                },
                "required": ["greenhouse_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_greenhouses",
            "description": "获取所有温室的当前传感器读数快照，一次查看全部温室状态",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_for_irrigation",
            "description": "获取与灌溉决策相关的天气摘要，包括未来24小时降雨、温度、风速，以及灌溉建议",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_alerts",
            "description": "获取当前生效的气象预警信息（高温、暴雨、大风等）",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_disease",
            "description": "根据症状描述搜索可能的病害，返回匹配的病害列表、匹配度和详细信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "string",
                        "description": "症状描述，如'叶片背面有灰色霉层'、'叶片出现黄斑'",
                    },
                    "crop": {
                        "type": "string",
                        "description": "作物名称，如 tomato（番茄）、cucumber（黄瓜）",
                    },
                },
                "required": ["symptoms", "crop"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_farming_guide",
            "description": "获取作物种植管理指南，包括最佳环境条件、生长阶段管理、灌溉方案等",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {
                        "type": "string",
                        "description": "作物名称，如 tomato（番茄）、cucumber（黄瓜）",
                    }
                },
                "required": ["crop"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_optimal_conditions",
            "description": "获取作物在特定生长阶段的最佳环境条件",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "作物名称"},
                    "growth_stage": {
                        "type": "string",
                        "description": "生长阶段，如 苗期、开花期、结果期",
                    },
                },
                "required": ["crop"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_and_advise",
            "description": "综合诊断工具：结合症状、当前环境条件和知识库，给出诊断和建议。适合复杂的病虫害诊断场景",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "作物名称"},
                    "symptoms": {"type": "string", "description": "症状描述"},
                    "current_conditions": {
                        "type": "object",
                        "description": "当前环境条件，如 {temperature: 30, humidity: 90}",
                        "properties": {
                            "temperature": {"type": "number"},
                            "humidity": {"type": "number"},
                            "soil_moisture": {"type": "number"},
                        },
                    },
                },
                "required": ["crop", "symptoms"],
            },
        },
    },
]

# ============================================================
# 系统提示词
# ============================================================

SYSTEM_PROMPT = """你是一个专业的温室农业智能助手（Agent），负责管理温室环境、诊断作物病虫害、制定灌溉方案和预警风险。

## 你的能力
你可以调用以下工具来获取实时数据并做出决策：
- 传感器数据：获取温室的温度、湿度、土壤、CO2、光照等实时读数
- 气象数据：获取天气预报、灌溉建议、气象预警
- 知识库：搜索病害信息、获取种植指南、综合诊断

## 工作原则
1. **先看数据再说话**：不要凭空猜测，先调用工具获取实际数据
2. **多源交叉验证**：诊断病害时，同时查看传感器数据和气象数据，结合环境条件判断
3. **量化你的判断**：给出具体的数值依据，比如"当前温度33°C超过最佳范围22-28°C"
4. **诚实面对不确定**：如果知识库中没有匹配的病害，明确说"无法确定"而不是编造
5. **可操作的建议**：每条建议都要具体、可执行，不要泛泛而谈

## 输出格式
用中文回答。结构清晰，重点突出。如果涉及数值，带单位。"""


# ============================================================
# 工具执行器（桥接到现有的 MCP Server 函数）
# ============================================================

class ToolExecutor:
    """将 DeepSeek 的工具调用桥接到本地 MCP Server 函数"""

    def __init__(self):
        self._tools: dict[str, Any] = {}

    def register(self, name: str, func: Any):
        self._tools[name] = func

    def execute(self, name: str, args: dict) -> str:
        func = self._tools.get(name)
        if not func:
            return json.dumps({"error": f"工具 {name} 未注册"}, ensure_ascii=False)
        try:
            result = func(**args)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)


def build_executor() -> ToolExecutor:
    """构建并注册所有工具"""
    from sensor_mcp_server import (
        get_current_reading, get_all_greenhouses,
        inject_anomaly, clear_anomaly,
    )
    from weather_mcp_server import (
        get_weather_for_irrigation, get_weather_alerts,
    )
    from knowledge_mcp_server import (
        search_disease, get_farming_guide,
        get_optimal_conditions, diagnose_and_advise,
    )

    executor = ToolExecutor()
    executor.register("get_current_reading", get_current_reading)
    executor.register("get_all_greenhouses", get_all_greenhouses)
    executor.register("get_weather_for_irrigation", get_weather_for_irrigation)
    executor.register("get_weather_alerts", get_weather_alerts)
    executor.register("search_disease", search_disease)
    executor.register("get_farming_guide", get_farming_guide)
    executor.register("get_optimal_conditions", get_optimal_conditions)
    executor.register("diagnose_and_advise", diagnose_and_advise)
    return executor


# ============================================================
# Agent 主循环
# ============================================================

def run_agent(user_query: str, verbose: bool = True) -> str:
    """
    DeepSeek 驱动的 Agent 主循环

    流程：
    1. 用户输入 → DeepSeek 分析意图
    2. DeepSeek 决定调用哪些工具 → 执行工具 → 返回结果
    3. DeepSeek 根据工具结果生成最终回答
    4. 如果 DeepSeek 还需要更多数据，循环继续
    """
    client = get_client()
    executor = build_executor()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    max_iterations = 10  # 防止无限循环
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        if verbose:
            print(f"\n  [Agent 循环 #{iteration}] 调用 DeepSeek...")

        response = client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            tools=AGENT_TOOLS,
            tool_choice="auto",
            temperature=0.1,  # 低温度，保证农业建议的稳定性
        )

        message = response.choices[0].message
        messages.append(message)

        # 检查是否有工具调用
        if not message.tool_calls:
            # 没有工具调用，DeepSeek 已经给出最终回答
            final_answer = message.content
            if verbose:
                print(f"  [Agent 完成] 共 {iteration} 轮，无更多工具调用")
            return final_answer

        # 执行所有工具调用
        if verbose:
            print(f"  [工具调用] DeepSeek 请求调用 {len(message.tool_calls)} 个工具:")

        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            if verbose:
                print(f"    → {fn_name}({json.dumps(fn_args, ensure_ascii=False)})")

            # 执行工具
            result = executor.execute(fn_name, fn_args)

            if verbose:
                # 截断显示，避免刷屏
                display_result = result[:200] + "..." if len(result) > 200 else result
                print(f"    ← 结果: {display_result}")

            # 将结果返回给 DeepSeek
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    return "Agent 达到最大迭代次数，未能完成任务。"


# ============================================================
# 演示
# ============================================================

async def run_demo():
    """运行演示场景"""
    print("=" * 60)
    print("  农业 Agent MVP — DeepSeek 驱动版")
    print("=" * 60)
    print()
    print("注意：需要设置 DEEPSEEK_API_KEY 环境变量")
    print("获取地址: https://platform.deepseek.com/api-keys")
    print()

    scenarios = [
        ("场景 1: 病虫害诊断", "温室A的番茄叶片出现黄斑，叶片背面有灰色霉层，可能是什么病？怎么治？"),
        ("场景 2: 环境监控", "帮我看看所有温室的环境状态，有没有需要关注的异常？"),
        ("场景 3: 灌溉决策", "温室A番茄现在需要浇水吗？帮我分析一下。"),
        ("场景 4: 综合诊断", "温室A番茄最近状态不太好，帮我全面检查一下环境、天气和可能的病害风险。"),
    ]

    for title, query in scenarios:
        print("━" * 60)
        print(title)
        print("━" * 60)
        print(f"用户: {query}\n")

        try:
            answer = run_agent(query, verbose=True)
            print(f"\n🤖 Agent 回答:\n{answer}")
        except ValueError as e:
            print(f"❌ {e}")
            break
        except Exception as e:
            print(f"❌ 调用出错: {e}")

        print()


async def run_interactive():
    """交互模式"""
    print("=" * 60)
    print("  农业 Agent — DeepSeek 交互模式 (输入 quit 退出)")
    print("=" * 60)

    while True:
        try:
            query = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query or query.lower() in ("quit", "exit", "q"):
            break
        try:
            answer = run_agent(query, verbose=False)
            print(f"\n🤖 {answer}")
        except Exception as e:
            print(f"❌ 出错: {e}")


if __name__ == "__main__":
    import asyncio
    import sys

    if "--interactive" in sys.argv or "-i" in sys.argv:
        asyncio.run(run_interactive())
    else:
        asyncio.run(run_demo())
