"""
气象 MCP Server — 天气数据服务（模拟）
"""

import random
import math
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-service")

_WEATHER_STATE = {
    "condition": "多云转晴", "season": "夏季", "region": "华北平原",
    "base_temp": 32.0, "base_humidity": 55.0,
}

WEATHER_WARNINGS = {
    "高温": {"trigger_temp": 35, "description": "日最高气温将超过35°C，注意防暑降温"},
    "暴雨": {"trigger_rain": 50, "description": "预计降雨量超过50mm，注意排涝"},
    "大风": {"trigger_wind": 8, "description": "阵风7级以上，注意加固设施"},
}


def _simulate_weather(hours_ahead: int = 0) -> dict:
    now = datetime.now()
    target_time = now + timedelta(hours=hours_ahead)
    hour = target_time.hour

    temp_daily = _WEATHER_STATE["base_temp"] + 5 * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else \
        _WEATHER_STATE["base_temp"] - 3
    temp = round(temp_daily + random.uniform(-2, 2), 1)
    humidity = round(max(20, min(95, _WEATHER_STATE["base_humidity"] + random.uniform(-10, 10))), 1)
    wind_speed = round(random.uniform(1, 8), 1)
    wind_dir = random.choice(["北", "东北", "东", "东南", "南", "西南", "西", "西北"])
    rain_prob = random.randint(0, 60) if "雨" in _WEATHER_STATE["condition"] else random.randint(0, 20)
    precipitation = round(random.uniform(0, 15), 1) if rain_prob > 40 else 0
    pressure = round(1013 + random.uniform(-10, 10), 1)
    uv_index = random.randint(5, 10) if 10 <= hour <= 16 else (random.randint(2, 6) if 6 <= hour <= 18 else 0)

    return {
        "time": target_time.isoformat(), "condition": _WEATHER_STATE["condition"],
        "temperature": temp, "humidity": humidity, "wind_speed": wind_speed,
        "wind_direction": wind_dir, "precipitation_mm": precipitation,
        "rain_probability": rain_prob, "pressure_hpa": pressure,
        "uv_index": uv_index, "visibility_km": round(random.uniform(5, 30), 1),
        "dew_point": round(temp - (100 - humidity) / 5, 1),
    }


@mcp.tool()
def get_current_weather() -> dict:
    """获取当前天气状况。"""
    return {"location": _WEATHER_STATE["region"], **_simulate_weather(0)}


@mcp.tool()
def get_weather_forecast(hours: int = 48) -> list[dict]:
    """获取未来 N 小时的逐时天气预报。"""
    return [_simulate_weather(h) for h in range(0, min(hours, 168), 3)]


@mcp.tool()
def get_weather_for_irrigation() -> dict:
    """获取与灌溉决策相关的天气摘要。"""
    forecast_24h = [_simulate_weather(h) for h in range(24)]
    rain_hours = [f for f in forecast_24h if f["precipitation_mm"] > 0]
    total_rain = sum(f["precipitation_mm"] for f in rain_hours)
    avg_temp = sum(f["temperature"] for f in forecast_24h) / len(forecast_24h)
    max_temp = max(f["temperature"] for f in forecast_24h)
    avg_wind = sum(f["wind_speed"] for f in forecast_24h) / len(forecast_24h)

    should_irrigate = total_rain < 5 and avg_temp > 28
    best_time = "清晨 5:00-7:00" if max_temp > 30 else "傍晚 18:00-20:00"

    return {
        "summary": {
            "total_rainfall_24h_mm": round(total_rain, 1), "rain_hours_count": len(rain_hours),
            "avg_temperature_24h": round(avg_temp, 1), "max_temperature_24h": round(max_temp, 1),
            "avg_wind_speed_ms": round(avg_wind, 1),
        },
        "irrigation_advice": {
            "should_irrigate": should_irrigate,
            "reason": "未来24小时降雨不足且温度偏高，建议灌溉" if should_irrigate else "未来24小时有充足降雨或温度适中，可暂缓灌溉",
            "recommended_time": best_time,
            "estimated_evaporation_mm": round(avg_temp * 0.4 + avg_wind * 0.3, 1),
        },
    }


@mcp.tool()
def get_weather_alerts() -> list[dict]:
    """获取当前生效的气象预警信息。"""
    alerts = []
    current = _simulate_weather(0)
    if current["temperature"] > WEATHER_WARNINGS["高温"]["trigger_temp"]:
        alerts.append({"type": "高温预警", "level": "橙色" if current["temperature"] > 37 else "黄色", "description": WEATHER_WARNINGS["高温"]["description"], "current_value": current["temperature"]})
    if current["wind_speed"] > WEATHER_WARNINGS["大风"]["trigger_wind"]:
        alerts.append({"type": "大风预警", "level": "蓝色", "description": WEATHER_WARNINGS["大风"]["description"], "current_value": current["wind_speed"]})
    if not alerts:
        alerts.append({"type": "无预警", "description": "当前无生效的气象预警"})
    return alerts


@mcp.resource("weather://summary")
def weather_summary() -> str:
    """天气概览文本"""
    w = _simulate_weather(0)
    return f"【{_WEATHER_STATE['region']}天气】\n天气: {w['condition']}\n温度: {w['temperature']}°C | 湿度: {w['humidity']}%\n风向: {w['wind_direction']}风 {w['wind_speed']}m/s\n降雨概率: {w['rain_probability']}%\nUV指数: {w['uv_index']}"


if __name__ == "__main__":
    mcp.run()
