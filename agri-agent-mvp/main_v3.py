"""
农业 Agent MVP v3 — 多模型协作架构

集成：
- DeepSeek-V4-Pro（中央决策）
- Swin-Tiny（视觉感知）
- 三层异常检测（Isolation Forest + LSTM + Chronos）
- 气象服务
- 农业知识库
"""

import asyncio
import json
import sys
from openai import OpenAI
import os


# ============================================================
# DeepSeek 客户端
# ============================================================

def get_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError(
            "请设置 DEEPSEEK_API_KEY\n"
            "  获取地址: https://platform.deepseek.com/api-keys"
        )
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


# ============================================================
# 工具定义（全部 MCP Server 的工具）
# ============================================================

def build_tools() -> list[dict]:
    """构建所有可用工具的定义"""
    return [
        # === 视觉模块 ===
        {
            "type": "function",
            "function": {
                "name": "diagnose_image",
                "description": "对植物叶片图像进行病害识别，返回病害类别和置信度",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "图像文件路径"},
                    },
                    "required": ["image_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_vision_models",
                "description": "列出所有可用的视觉识别模型",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        # === 异常检测模块 ===
        {
            "type": "function",
            "function": {
                "name": "check_anomaly",
                "description": "对指定温室执行三层异常检测（Isolation Forest + LSTM + Chronos），返回异常分数和详情",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "greenhouse_id": {
                            "type": "string",
                            "description": "温室ID",
                            "enum": ["gh-a", "gh-b"],
                        },
                    },
                    "required": ["greenhouse_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_all_anomalies",
                "description": "对所有温室执行异常检测",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_current_reading",
                "description": "获取指定温室的当前传感器读数",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "greenhouse_id": {"type": "string", "enum": ["gh-a", "gh-b"]},
                    },
                    "required": ["greenhouse_id"],
                },
            },
        },
        # === 气象模块 ===
        {
            "type": "function",
            "function": {
                "name": "get_weather_for_irrigation",
                "description": "获取灌溉相关的天气摘要和建议",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_weather_alerts",
                "description": "获取当前气象预警",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        # === 知识库模块 ===
        {
            "type": "function",
            "function": {
                "name": "search_disease",
                "description": "根据症状搜索可能的病害",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symptoms": {"type": "string", "description": "症状描述"},
                        "crop": {"type": "string", "description": "作物名称"},
                    },
                    "required": ["symptoms", "crop"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "diagnose_and_advise",
                "description": "综合诊断：结合症状、环境和知识库给出诊断和建议",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "crop": {"type": "string"},
                        "symptoms": {"type": "string"},
                        "current_conditions": {"type": "object"},
                    },
                    "required": ["crop", "symptoms"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_farming_guide",
                "description": "获取作物种植管理指南",
                "parameters": {
                    "type": "object",
                    "properties": {"crop": {"type": "string"}},
                    "required": ["crop"],
                },
            },
        },
    ]


# ============================================================
# 工具执行器
# ============================================================

class ToolExecutor:
    def __init__(self):
        self._tools = {}
        self._load_modules()

    def _load_modules(self):
        """加载所有 MCP Server 模块"""
        # 视觉模块
        try:
            from vision_mcp_server import diagnose_image, list_models
            self._tools["diagnose_image"] = diagnose_image
            self._tools["list_vision_models"] = list_models
        except ImportError:
            self._tools["diagnose_image"] = lambda image_path: {"error": "vision_mcp_server 未安装"}
            self._tools["list_vision_models"] = lambda: {"error": "vision_mcp_server 未安装"}

        # 传感器异常检测模块（v2 三层架构）
        try:
            from sensor_mcp_server_v2 import (
                check_anomaly, check_all_anomalies, get_current_reading,
                get_sensor_history, inject_anomaly, clear_anomaly,
                get_detection_architecture,
            )
            self._tools["check_anomaly"] = check_anomaly
            self._tools["check_all_anomalies"] = check_all_anomalies
            self._tools["get_current_reading"] = get_current_reading
            self._tools["get_sensor_history"] = get_sensor_history
            self._tools["inject_anomaly"] = inject_anomaly
            self._tools["clear_anomaly"] = clear_anomaly
            self._tools["get_detection_architecture"] = get_detection_architecture
        except ImportError:
            pass

        # 气象模块
        try:
            from weather_mcp_server import get_weather_for_irrigation, get_weather_alerts
            self._tools["get_weather_for_irrigation"] = get_weather_for_irrigation
            self._tools["get_weather_alerts"] = get_weather_alerts
        except ImportError:
            pass

        # 知识库模块
        try:
            from knowledge_mcp_server import (
                search_disease, diagnose_and_advise, get_farming_guide,
            )
            self._tools["search_disease"] = search_disease
            self._tools["diagnose_and_advise"] = diagnose_and_advise
            self._tools["get_farming_guide"] = get_farming_guide
        except ImportError:
            pass

    def execute(self, name: str, args: dict) -> str:
        func = self._tools.get(name)
        if not func:
            return json.dumps({"error": f"工具 {name} 未注册"}, ensure_ascii=False)
        try:
            result = func(**args)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================
# Agent 主循环
# ============================================================

SYSTEM_PROMPT = """你是温室农业智能 Agent，负责管理温室环境、诊断病虫害、检测异常、制定灌溉方案。

你可以调用以下模块的工具：
- 视觉感知：对植物叶片图像做病害识别
- 异常检测：三层检测（Isolation Forest + LSTM + Chronos）发现传感器数据异常
- 气象服务：获取天气预报和灌溉建议
- 知识库：搜索病害信息、获取种植指南

工作原则：
1. 先调工具获取数据，再做判断
2. 多源交叉验证：视觉诊断 + 传感器异常 + 知识库三者对照
3. 量化判断：带具体数值和单位
4. 诚实面对不确定：知识库没有的就说不确定
5. 可操作的建议：每条建议具体、可执行

用中文回答，结构清晰。"""


def run_agent(user_query: str, verbose: bool = True) -> str:
    client = get_client()
    executor = ToolExecutor()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    tools = build_tools()
    max_iter = 10

    for iteration in range(1, max_iter + 1):
        if verbose:
            print(f"\n  [循环 #{iteration}] 调用 DeepSeek-V4-Pro...")

        response = client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1,
        )

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            if verbose:
                print(f"  [完成] 共 {iteration} 轮")
            return message.content

        if verbose:
            print(f"  [调用 {len(message.tool_calls)} 个工具]")

        for tc in message.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)

            if verbose:
                print(f"    → {fn_name}({json.dumps(fn_args, ensure_ascii=False)[:80]})")

            result = executor.execute(fn_name, fn_args)

            if verbose:
                preview = result[:150] + "..." if len(result) > 150 else result
                print(f"    ← {preview}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return "达到最大迭代次数"


# ============================================================
# 演示
# ============================================================

async def run_demo():
    print("=" * 60)
    print("  农业 Agent v3 — 多模型协作架构")
    print("  视觉: Swin-Tiny | 异常: 3层检测 | 决策: DeepSeek-V4-Pro")
    print("=" * 60)
    print()

    scenarios = [
        ("场景 1: 全面健康检查", "帮我全面检查所有温室的状态，包括传感器异常检测和环境评估。"),
        ("场景 2: 异常诊断", "温室A番茄叶片出现黄斑，帮我综合分析一下——先检查传感器有没有异常，再查知识库看看可能是什么病。"),
        ("场景 3: 灌溉决策", "温室B黄瓜现在需要浇水吗？帮我看看土壤湿度、天气预报和灌溉指南。"),
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
            print(f"❌ 出错: {e}")

        print()


async def run_interactive():
    print("=" * 60)
    print("  农业 Agent v3 — 交互模式 (quit 退出)")
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
            print(f"❌ {e}")


if __name__ == "__main__":
    if "--interactive" in sys.argv or "-i" in sys.argv:
        asyncio.run(run_interactive())
    else:
        asyncio.run(run_demo())
