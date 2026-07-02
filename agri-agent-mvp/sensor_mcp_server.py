"""
传感器 MCP Server — 温室传感器数据模拟器
"""

import random
import math
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("greenhouse-sensors")

GREENHOUSES = {
    "gh-a": {
        "name": "温室A（番茄区）", "crop": "番茄", "growth_stage": "开花期",
        "area_m2": 2000, "base_temp": 26.0, "base_humidity": 65.0,
        "base_soil_moisture": 45.0, "base_ph": 6.5, "base_co2": 800.0, "base_light": 25000.0,
    },
    "gh-b": {
        "name": "温室B（黄瓜区）", "crop": "黄瓜", "growth_stage": "结果期",
        "area_m2": 1500, "base_temp": 24.0, "base_humidity": 70.0,
        "base_soil_moisture": 50.0, "base_ph": 6.8, "base_co2": 750.0, "base_light": 22000.0,
    },
}

ANOMALIES = {
    "gh-a": {"temp_offset": 5.0, "humidity_offset": -10.0, "leaf_wetness": True}
}


def _time_of_day_factor(hour: int) -> dict:
    temp_factor = 3.0 * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else -2.0
    light_factor = math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 0.0
    co2_factor = 100.0 if hour < 6 or hour > 20 else -50.0
    return {"temp": temp_factor, "light": light_factor, "co2": co2_factor}


def _add_noise(value: float, noise_pct: float = 0.02) -> float:
    return value * (1 + random.uniform(-noise_pct, noise_pct))


def _generate_reading(gh_id: str, timestamp: datetime = None) -> dict:
    if timestamp is None:
        timestamp = datetime.now()
    gh = GREENHOUSES.get(gh_id)
    if not gh:
        return {"error": f"未知温室 ID: {gh_id}"}

    anomaly = ANOMALIES.get(gh_id, {})
    tod = _time_of_day_factor(timestamp.hour)

    air_temp = gh["base_temp"] + tod["temp"] + anomaly.get("temp_offset", 0)
    air_temp = _add_noise(air_temp, 0.03)

    air_humidity = gh["base_humidity"] + anomaly.get("humidity_offset", 0)
    air_humidity -= (air_temp - gh["base_temp"]) * 1.5
    air_humidity = max(30, min(95, _add_noise(air_humidity, 0.05)))

    soil_moisture = max(20, min(80, _add_noise(gh["base_soil_moisture"], 0.04)))
    soil_temp = air_temp - 3 + _add_noise(0, 0.02)
    light = max(0, _add_noise(gh["base_light"] * tod["light"], 0.1))
    co2 = max(300, min(1500, _add_noise(gh["base_co2"] + tod["co2"], 0.05)))
    ph = _add_noise(gh["base_ph"], 0.02)
    leaf_wetness = anomaly.get("leaf_wetness", False)

    return {
        "greenhouse_id": gh_id,
        "greenhouse_name": gh["name"],
        "crop": gh["crop"],
        "growth_stage": gh["growth_stage"],
        "timestamp": timestamp.isoformat(),
        "sensors": {
            "air_temperature": {"value": round(air_temp, 1), "unit": "°C", "status": "warning" if air_temp > 32 else "normal"},
            "air_humidity": {"value": round(air_humidity, 1), "unit": "%", "status": "warning" if air_humidity < 40 else "normal"},
            "soil_moisture": {"value": round(soil_moisture, 1), "unit": "%", "status": "normal"},
            "soil_temperature": {"value": round(soil_temp, 1), "unit": "°C", "status": "normal"},
            "light_intensity": {"value": round(light, 0), "unit": "lux", "status": "normal"},
            "co2_concentration": {"value": round(co2, 0), "unit": "ppm", "status": "warning" if co2 > 1200 else "normal"},
            "soil_ph": {"value": round(ph, 2), "unit": "pH", "status": "normal"},
            "leaf_wetness": {"value": leaf_wetness, "unit": "boolean", "status": "warning" if leaf_wetness else "normal"},
        },
    }


@mcp.tool()
def get_current_reading(greenhouse_id: str) -> dict:
    """获取指定温室的当前传感器读数。"""
    return _generate_reading(greenhouse_id)


@mcp.tool()
def get_all_greenhouses() -> list[dict]:
    """获取所有温室的当前传感器读数快照。"""
    return [_generate_reading(gh_id) for gh_id in GREENHOUSES]


@mcp.tool()
def get_sensor_history(greenhouse_id: str, hours: int = 24) -> list[dict]:
    """获取指定温室最近 N 小时的传感器历史数据。"""
    now = datetime.now()
    interval = timedelta(minutes=30)
    return [_generate_reading(greenhouse_id, now - (interval * i)) for i in range(hours * 2, 0, -1)]


@mcp.tool()
def inject_anomaly(greenhouse_id: str, anomaly_type: str, severity: float = 1.0) -> dict:
    """向指定温室注入模拟异常。"""
    global ANOMALIES
    anomaly_map = {
        "high_temp": {"temp_offset": 8.0 * severity},
        "low_humidity": {"humidity_offset": -20.0 * severity},
        "sensor_failure": {"temp_offset": 999},
        "pest_risk": {"humidity_offset": 15.0 * severity, "leaf_wetness": True},
    }
    if anomaly_type not in anomaly_map:
        return {"error": f"未知异常类型: {anomaly_type}，可选: {list(anomaly_map.keys())}"}
    ANOMALIES[greenhouse_id] = anomaly_map[anomaly_type]
    return {"status": "ok", "message": f"已向 {GREENHOUSES[greenhouse_id]['name']} 注入 {anomaly_type} 异常（严重度: {severity}）"}


@mcp.tool()
def clear_anomaly(greenhouse_id: str) -> dict:
    """清除指定温室的模拟异常。"""
    global ANOMALIES
    ANOMALIES.pop(greenhouse_id, None)
    return {"status": "ok", "message": f"已清除 {greenhouse_id} 的异常"}


@mcp.tool()
def get_greenhouse_info(greenhouse_id: str) -> dict:
    """获取温室的基本配置信息。"""
    gh = GREENHOUSES.get(greenhouse_id)
    if not gh:
        return {"error": f"未知温室 ID: {greenhouse_id}"}
    return {"id": greenhouse_id, **gh, "has_anomaly": greenhouse_id in ANOMALIES, "anomaly": ANOMALIES.get(gh_id, None)}


@mcp.resource("greenhouse://status")
def greenhouse_status_summary() -> str:
    """所有温室的状态概览"""
    lines = ["=== 温室状态概览 ===\n"]
    for gh_id, gh in GREENHOUSES.items():
        reading = _generate_reading(gh_id)
        sensors = reading["sensors"]
        warnings = [k for k, v in sensors.items() if v.get("status") == "warning"]
        anomaly = "⚠️ 有异常" if gh_id in ANOMALIES else "✅ 正常"
        lines.append(f"【{gh['name']}】{anomaly}")
        lines.append(f"  作物: {gh['crop']} | 阶段: {gh['growth_stage']}")
        lines.append(f"  温度: {sensors['air_temperature']['value']}°C | 湿度: {sensors['air_humidity']['value']}%")
        if warnings:
            lines.append(f"  ⚠️  异常指标: {', '.join(warnings)}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
