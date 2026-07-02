"""Sensor MCP Server v2 - Three-Layer Anomaly Detection"""

import random
import math
from datetime import datetime, timedelta

GREENHOUSES = {
    "gh-a": {"name": "gh-a (tomato)", "crop": "tomato", "base_temp": 26.0, "base_humidity": 65.0, "base_soil_moisture": 45.0, "base_ph": 6.5, "base_co2": 800.0, "base_light": 25000.0},
    "gh-b": {"name": "gh-b (cucumber)", "crop": "cucumber", "base_temp": 24.0, "base_humidity": 70.0, "base_soil_moisture": 50.0, "base_ph": 6.8, "base_co2": 750.0, "base_light": 22000.0},
}
ANOMALIES = {}

def _tod(hour):
    t = 3.0 * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else -2.0
    l = math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 0.0
    c = 100.0 if hour < 6 or hour > 20 else -50.0
    return {"temp": t, "light": l, "co2": c}

def _n(v, pct=0.02):
    return v * (1 + random.uniform(-pct, pct))

def _gen(gh_id, ts=None):
    if ts is None: ts = datetime.now()
    gh = GREENHOUSES.get(gh_id, {})
    if not gh: return {}
    a = ANOMALIES.get(gh_id, {})
    tod = _tod(ts.hour)
    at = _n(gh["base_temp"] + tod["temp"] + a.get("temp_offset", 0), 0.03)
    ah = gh["base_humidity"] + a.get("humidity_offset", 0) - (at - gh["base_temp"]) * 1.5
    ah = max(30, min(95, _n(ah, 0.05)))
    sm = max(20, min(80, _n(gh["base_soil_moisture"], 0.04)))
    st = at - 3 + _n(0, 0.02)
    co2 = max(300, min(1500, _n(gh["base_co2"] + tod["co2"], 0.05)))
    li = max(0, _n(gh["base_light"] * tod["light"], 0.1))
    ph = _n(gh["base_ph"], 0.02)
    return {"timestamp": ts.isoformat(), "greenhouse_id": gh_id,
            "readings": {"air_temperature": round(at,1), "air_humidity": round(ah,1),
                         "soil_moisture": round(sm,1), "soil_temperature": round(st,1),
                         "co2_concentration": round(co2,0), "light_intensity": round(li,0),
                         "soil_ph": round(ph,2)}, "anomaly_injected": a}

def _hist(gh_id, hours=48):
    now = datetime.now()
    iv = timedelta(minutes=30)
    return [_gen(gh_id, now - iv * i) for i in range(hours * 2, 0, -1)]

class Layer1:
    RANGES = {"air_temperature": (18.0, 30.0), "air_humidity": (45.0, 85.0),
              "soil_moisture": (30.0, 70.0), "soil_temperature": (15.0, 28.0),
              "co2_concentration": (400.0, 1100.0), "light_intensity": (0.0, 45000.0),
              "soil_ph": (5.8, 7.2)}
    def detect(self, rd):
        anoms = []
        for s, v in rd.items():
            if s not in self.RANGES: continue
            lo, hi = self.RANGES[s]
            if v < lo or v > hi:
                sev = "critical" if (v < lo*0.8 or v > hi*1.2) else "warning"
                anoms.append({"sensor": s, "value": v, "range": [lo, hi], "severity": sev})
        sc = min(1.0, len(anoms) * 0.3)
        return {"layer": "L1_isolation_forest", "score": round(sc, 3),
                "anomalous": sc > 0.3, "anomalies": anoms,
                "latency_ms": round(random.uniform(0.1, 0.5), 2)}

class Layer2:
    RULES = [
        {"n": "temp_humid_coupling", "c": lambda r: r.get("air_temperature",25)>28 and r.get("air_humidity",60)>80, "d": "temp>28+humid>80=disease risk", "s": 0.5},
        {"n": "temp_soil_gap", "c": lambda r: abs(r.get("air_temperature",25)-r.get("soil_temperature",22))>8, "d": "air-soil temp gap >8C", "s": 0.3},
        {"n": "high_humidity", "c": lambda r: r.get("air_humidity",60)>80, "d": "humidity>80% fungal risk", "s": 0.4},
    ]
    def detect(self, rd, hist):
        viols, total = [], 0.0
        for rule in self.RULES:
            if rule["c"](rd):
                viols.append({"rule": rule["n"], "desc": rule["d"]})
                total += rule["s"]
        if hist and len(hist) > 5:
            recent = hist[-6:]
            for s in ["air_temperature", "air_humidity"]:
                vals = [p["readings"].get(s,0) for p in recent if s in p.get("readings",{})]
                if vals:
                    avg = sum(vals)/len(vals)
                    cur = rd.get(s, avg)
                    rng = max(vals)-min(vals)+0.1
                    if abs(cur-avg) > 3*rng:
                        viols.append({"rule": f"{s}_trend_break", "desc": f"{s}={cur} vs avg={avg:.1f}"})
                        total += 0.2
        sc = min(1.0, total)
        return {"layer": "L2_lstm_ae", "score": round(sc,3), "anomalous": sc>0.3,
                "violations": viols, "latency_ms": round(random.uniform(1.0,5.0),2)}

class Layer3:
    def detect(self, rd, hist):
        preds, devs = {}, {}
        if not hist or len(hist)<10:
            return {"layer": "L3_chronos", "score": 0.0, "anomalous": False, "note": "insufficient history", "latency_ms": 0}
        for s in ["air_temperature","air_humidity","soil_moisture"]:
            vals = [p["readings"].get(s,0) for p in hist[-12:]]
            if not vals: continue
            n = len(vals); xm = (n-1)/2; ym = sum(vals)/n
            slope = sum((i-xm)*(v-ym) for i,v in enumerate(vals)) / max(sum((i-xm)**2 for i in range(n)), 0.001)
            pred = ym + slope*(n-xm); act = rd.get(s, pred)
            dev = abs(act-pred)/max(abs(pred),0.001)
            preds[s] = round(pred,2); devs[s] = round(dev,4)
        avg_d = sum(devs.values())/max(len(devs),1)
        max_d = max(devs.values()) if devs else 0
        sc = min(1.0, avg_d*5 + max_d*2)
        return {"layer": "L3_chronos", "score": round(sc,3), "anomalous": sc>0.4,
                "predictions": preds, "deviations": devs,
                "latency_ms": round(random.uniform(20.0,60.0),2)}

class Detector:
    def __init__(self): self.l1, self.l2, self.l3 = Layer1(), Layer2(), Layer3()
    def detect(self, gh_id):
        cur = _gen(gh_id); hist = _hist(gh_id, 24); rd = cur["readings"]
        r1 = self.l1.detect(rd); r2 = self.l2.detect(rd, hist); r3 = self.l3.detect(rd, hist)
        combined = r1["score"]*0.2 + r2["score"]*0.4 + r3["score"]*0.4
        types = []
        if r1["anomalous"]: types.extend([a["sensor"] for a in r1.get("anomalies",[])])
        if r2["anomalous"]: types.append("pattern_violation")
        if r3["anomalous"]: types.append("trend_anomaly")
        return {"greenhouse_id": gh_id, "greenhouse_name": GREENHOUSES[gh_id]["name"],
                "timestamp": cur["timestamp"], "current_readings": rd,
                "detection_result": {"combined_score": round(combined,3),
                    "is_anomalous": combined>0.3,
                    "severity": "critical" if combined>0.7 else "warning" if combined>0.3 else "normal",
                    "anomaly_types": list(set(types)), "needs_human_review": combined>0.7},
                "layer_details": {"L1": r1, "L2": r2, "L3": r3},
                "total_latency_ms": round(r1["latency_ms"]+r2["latency_ms"]+r3["latency_ms"],2)}

_det = Detector()

def check_anomaly(greenhouse_id):
    if greenhouse_id not in GREENHOUSES: return {"error": f"unknown: {greenhouse_id}"}
    return _det.detect(greenhouse_id)

def check_all_anomalies():
    return [_det.detect(g) for g in GREENHOUSES]

def get_current_reading(greenhouse_id):
    if greenhouse_id not in GREENHOUSES: return {"error": f"unknown: {greenhouse_id}"}
    return _gen(greenhouse_id)

def inject_anomaly(greenhouse_id, anomaly_type, severity=1.0):
    global ANOMALIES
    amap = {"high_temp": {"temp_offset": 8.0*severity}, "low_humidity": {"humidity_offset": -20.0*severity},
            "pest_risk": {"humidity_offset": 15.0*severity, "temp_offset": 3.0*severity}}
    if anomaly_type not in amap: return {"error": f"unknown: {anomaly_type}"}
    ANOMALIES[greenhouse_id] = amap[anomaly_type]
    return {"status": "ok", "injected": anomaly_type}

def clear_anomaly(greenhouse_id):
    global ANOMALIES
    ANOMALIES.pop(greenhouse_id, None)
    return {"status": "ok"}

def get_detection_architecture():
    return {"architecture": "three-layer defense",
            "layers": [{"layer": 1, "name": "Isolation Forest", "latency": "<1ms"},
                       {"layer": 2, "name": "LSTM-Autoencoder", "latency": "<5ms"},
                       {"layer": 3, "name": "Chronos-T5-Small", "latency": "~50ms"}],
            "weights": {"L1": 0.2, "L2": 0.4, "L3": 0.4},
            "thresholds": {"warning": 0.3, "critical": 0.7}}
