"""气象数据服务（模拟）"""
import random, math
from datetime import datetime, timedelta

_WEATHER_STATE = {"condition": "多云转晴", "season": "夏季", "region": "华北平原", "base_temp": 32.0, "base_humidity": 55.0}
WEATHER_WARNINGS = {"高温": {"trigger_temp": 35, "description": "日最高气温将超过35°C，注意防暑降温"}, "暴雨": {"trigger_rain": 50, "description": "预计降雨量超过50mm，注意排涝"}, "大风": {"trigger_wind": 8, "description": "阵风7级以上，注意加固设施"}}

def _simulate_weather(hours_ahead=0):
    now = datetime.now()
    target_time = now + timedelta(hours=hours_ahead)
    hour = target_time.hour
    temp_daily = _WEATHER_STATE["base_temp"] + 5 * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else _WEATHER_STATE["base_temp"] - 3
    temp = round(temp_daily + random.uniform(-2, 2), 1)
    humidity = round(max(20, min(95, _WEATHER_STATE["base_humidity"] + random.uniform(-10, 10))), 1)
    wind_speed = round(random.uniform(1, 8), 1)
    wind_dir = random.choice(["北", "东北", "东", "东南", "南", "西南", "西", "西北"])
    rain_prob = random.randint(0, 60) if "雨" in _WEATHER_STATE["condition"] else random.randint(0, 20)
    precipitation = round(random.uniform(0, 15), 1) if rain_prob > 40 else 0
    return {"time": target_time.isoformat(), "condition": _WEATHER_STATE["condition"], "temperature": temp, "humidity": humidity, "wind_speed": wind_speed, "wind_direction": wind_dir, "precipitation_mm": precipitation, "rain_probability": rain_prob, "pressure_hpa": round(1013 + random.uniform(-10, 10), 1), "uv_index": random.randint(5, 10) if 10 <= hour <= 16 else (random.randint(2, 6) if 6 <= hour <= 18 else 0), "dew_point": round(temp - (100 - humidity) / 5, 1)}

def get_current_weather():
    return {"location": _WEATHER_STATE["region"], **_simulate_weather(0)}

def get_weather_forecast(hours=48):
    return [_simulate_weather(h) for h in range(0, min(hours, 168), 3)]

def get_weather_for_irrigation():
    f24 = [_simulate_weather(h) for h in range(24)]
    rain_hours = [f for f in f24 if f["precipitation_mm"] > 0]
    total_rain = sum(f["precipitation_mm"] for f in rain_hours)
    avg_temp = sum(f["temperature"] for f in f24) / 24
    max_temp = max(f["temperature"] for f in f24)
    avg_wind = sum(f["wind_speed"] for f in f24) / 24
    should_irrigate = total_rain < 5 and avg_temp > 28
    return {"summary": {"total_rainfall_24h_mm": round(total_rain, 1), "rain_hours_count": len(rain_hours), "avg_temperature_24h": round(avg_temp, 1), "max_temperature_24h": round(max_temp, 1), "avg_wind_speed_ms": round(avg_wind, 1)}, "irrigation_advice": {"should_irrigate": should_irrigate, "reason": "未来24小时降雨不足且温度偏高，建议灌溉" if should_irrigate else "未来24小时有充足降雨或温度适中，可暂缓灌溉", "recommended_time": "清晨 5:00-7:00" if max_temp > 30 else "傍晚 18:00-20:00", "estimated_evaporation_mm": round(avg_temp * 0.4 + avg_wind * 0.3, 1)}}

def get_weather_alerts():
    current = _simulate_weather(0)
    alerts = []
    if current["temperature"] > WEATHER_WARNINGS["高温"]["trigger_temp"]:
        alerts.append({"type": "高温预警", "level": "橙色" if current["temperature"] > 37 else "黄色", "description": WEATHER_WARNINGS["高温"]["description"], "current_value": current["temperature"]})
    if current["wind_speed"] > WEATHER_WARNINGS["大风"]["trigger_wind"]:
        alerts.append({"type": "大风预警", "level": "蓝色", "description": WEATHER_WARNINGS["大风"]["description"], "current_value": current["wind_speed"]})
    if not alerts: alerts.append({"type": "无预警", "description": "当前无生效的气象预警"})
    return alerts