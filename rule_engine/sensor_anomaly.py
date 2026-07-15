"""Sensor MCP Server v2 - Three-Layer Anomaly Detection

L1: Isolation Forest (sklearn) — sklearn 缺失时降级为区间阈值检查
L3: Chronos-T5-Small (chronos-forecasting + torch) — 依赖缺失时降级为线性回归
L2: 规则引擎（LSTM-Autoencoder 占位，待后续接入）
依赖缺失时模块仍可导入与运行（降级为启发式），仅当对应库已安装才启用真模型。
"""

import random
import math
import time
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

# ============================================================
# L1 / L3 真模型支撑（懒加载，依赖缺失自动降级）
# ============================================================

_FEATURES = ["air_temperature", "air_humidity", "soil_moisture",
             "soil_temperature", "co2_concentration", "light_intensity", "soil_ph"]
_IF_CACHE = {}
_IF_TRIED = set()
_IF_STATUS = {}
_CHRONOS = None
_CHRONOS_TRIED = False
_CHRONOS_STATUS = "not_loaded"


def _feat_vec(rd):
    return [float(rd.get(f, 0.0)) for f in _FEATURES]


def _gen_normal_history(gh_id, n=240):
    """生成 n 个无注入异常的正常读数，用于拟合 Isolation Forest。"""
    saved = ANOMALIES.pop(gh_id, None)
    try:
        now = datetime.now()
        iv = timedelta(minutes=30)
        return [_gen(gh_id, now - iv * i)["readings"] for i in range(n, 0, -1)]
    finally:
        if saved is not None:
            ANOMALIES[gh_id] = saved


def _fit_isolation_forest(gh_id):
    """懒加载并按温室拟合 Isolation Forest；失败返回 None（调用方降级）。"""
    if gh_id in _IF_TRIED:
        return _IF_CACHE.get(gh_id)
    _IF_TRIED.add(gh_id)
    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest
        X = [_feat_vec(r) for r in _gen_normal_history(gh_id, 240)]
        model = IsolationForest(n_estimators=100, contamination=0.02, random_state=42)
        model.fit(X)
        # 以训练分布的 1% 分位为阈值：新点比 99% 正常样本更异常才计分
        thr = float(np.percentile(model.decision_function(X), 1))
        _IF_CACHE[gh_id] = {"model": model, "thr": thr}
        _IF_STATUS[gh_id] = "isolation_forest"
    except Exception as e:
        _IF_STATUS[gh_id] = f"range_check_fallback ({type(e).__name__})"
    return _IF_CACHE.get(gh_id)


def _get_chronos():
    """懒加载 Chronos-T5-Small；失败返回 None（调用方降级为线性回归）。"""
    global _CHRONOS, _CHRONOS_TRIED, _CHRONOS_STATUS
    if _CHRONOS_TRIED:
        return _CHRONOS
    _CHRONOS_TRIED = True
    try:
        import os
        import torch
        import huggingface_hub.constants as _hfc
        from chronos import ChronosPipeline
        # 强制离线：命中本地缓存即秒载；HF 不可达时不会挂起在 etag 检查上。
        # 注意 env 在 huggingface_hub 已导入后设置不生效，必须直接改 constants。
        _prev_off = _hfc.HF_HUB_OFFLINE
        _prev_env = os.environ.get("HF_HUB_OFFLINE")
        _hfc.HF_HUB_OFFLINE = True
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            _CHRONOS = ChronosPipeline.from_pretrained(
                "amazon/chronos-t5-small", device_map="cpu", torch_dtype=torch.float32)
        finally:
            _hfc.HF_HUB_OFFLINE = _prev_off
            if _prev_env is None:
                os.environ.pop("HF_HUB_OFFLINE", None)
            else:
                os.environ["HF_HUB_OFFLINE"] = _prev_env
        _CHRONOS_STATUS = "chronos-t5-small"
    except Exception as e:
        _CHRONOS = None
        _CHRONOS_STATUS = f"linear_regression_fallback ({type(e).__name__})"
    return _CHRONOS


def _sklearn_available():
    try:
        import sklearn  # noqa: F401
        return True
    except Exception:
        return False


def _chronos_available():
    try:
        import chronos  # noqa: F401
        import torch  # noqa: F401
    except Exception:
        return False
    # import 成功不代表权重已下载；确认本地缓存含模型权重文件
    try:
        import os
        import glob
        base = os.path.expanduser(
            "~/.cache/huggingface/hub/models--amazon--chronos-t5-small/snapshots")
        for snap in glob.glob(os.path.join(base, "*")):
            if any(f.endswith(".safetensors") or f.endswith(".bin")
                   for f in os.listdir(snap)):
                return True
    except Exception:
        return False
    return False


def _torch_available():
    try:
        import torch  # noqa: F401
        return True
    except Exception:
        return False


# ---- L2 LSTM-Autoencoder（懒训练，torch 缺失降级为规则引擎）----
_LSTM_CACHE = {}
_LSTM_TRIED = set()
_LSTM_STATUS = {}
_LSTM_WINDOW = 12
_LSTM_HIDDEN = 16
_LSTM_EPOCHS = 30


def _train_lstm_ae(gh_id):
    """按温室在正常时序上训练 LSTM-Autoencoder；失败返回 None（调用方降级）。"""
    if gh_id in _LSTM_TRIED:
        return _LSTM_CACHE.get(gh_id)
    _LSTM_TRIED.add(gh_id)
    try:
        import numpy as np
        import torch
        from torch import nn

        class _LSTMAE(nn.Module):
            def __init__(self, n_feat, hidden):
                super().__init__()
                self.enc = nn.LSTM(n_feat, hidden, batch_first=True)
                self.to_z = nn.Linear(hidden, hidden)
                self.from_z = nn.Linear(hidden, hidden)
                self.dec = nn.LSTM(hidden, n_feat, batch_first=True)

            def forward(self, x):
                _, (h, _) = self.enc(x)
                z = self.from_z(self.to_z(h.squeeze(0)))
                z = z.unsqueeze(1).repeat(1, x.size(1), 1)
                out, _ = self.dec(z)
                return out

        hist = _gen_normal_history(gh_id, 400)
        arr = np.array([_feat_vec(r) for r in hist], dtype=np.float32)
        mean = arr.mean(axis=0, keepdims=True)
        std = arr.std(axis=0, keepdims=True) + 1e-6
        arr_n = (arr - mean) / std
        W = _LSTM_WINDOW
        if len(arr_n) <= W:
            raise RuntimeError("insufficient normal history for LSTM-AE")
        wins = np.stack([arr_n[i:i + W] for i in range(len(arr_n) - W + 1)], axis=0)
        X = torch.tensor(wins, dtype=torch.float32)
        model = _LSTMAE(arr.shape[1], _LSTM_HIDDEN)
        opt = torch.optim.Adam(model.parameters(), lr=1e-3)
        lossf = nn.MSELoss()
        model.train()
        for _ in range(_LSTM_EPOCHS):
            opt.zero_grad()
            loss = lossf(model(X), X)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            recon = model(X)
            errs = torch.mean((recon - X) ** 2, dim=(1, 2)).numpy()
        err_thr = float(np.percentile(errs, 99))
        _LSTM_CACHE[gh_id] = {"model": model, "mean": mean, "std": std, "thr": err_thr}
        _LSTM_STATUS[gh_id] = "lstm_autoencoder"
    except Exception as e:
        _LSTM_STATUS[gh_id] = f"rule_based_fallback ({type(e).__name__})"
    return _LSTM_CACHE.get(gh_id)


class Layer1:
    RANGES = {"air_temperature": (18.0, 30.0), "air_humidity": (45.0, 85.0),
              "soil_moisture": (30.0, 70.0), "soil_temperature": (15.0, 28.0),
              "co2_concentration": (400.0, 1100.0), "light_intensity": (0.0, 45000.0),
              "soil_ph": (5.8, 7.2)}

    def _range_check(self, rd):
        anoms = []
        for s, v in rd.items():
            if s not in self.RANGES:
                continue
            lo, hi = self.RANGES[s]
            if v < lo or v > hi:
                sev = "critical" if (v < lo * 0.8 or v > hi * 1.2) else "warning"
                anoms.append({"sensor": s, "value": v, "range": [lo, hi], "severity": sev})
        return anoms

    def detect(self, rd, gh_id="gh-a"):
        start = time.perf_counter()
        anoms = self._range_check(rd)
        info = _fit_isolation_forest(gh_id)
        if info is not None:
            raw = float(info["model"].decision_function([_feat_vec(rd)])[0])
            score = max(0.0, min(1.0, (info["thr"] - raw) / 0.2))
            engine = "isolation_forest"
        else:
            score = min(1.0, len(anoms) * 0.3)
            engine = "range_check_fallback"
        latency = (time.perf_counter() - start) * 1000
        return {"layer": "L1_isolation_forest", "engine": engine,
                "score": round(score, 3), "anomalous": score > 0.3,
                "anomalies": anoms, "latency_ms": round(latency, 2)}


class Layer2:
    RULES = [
        {"n": "temp_humid_coupling", "c": lambda r: r.get("air_temperature",25)>28 and r.get("air_humidity",60)>80, "d": "temp>28+humid>80=disease risk", "s": 0.5},
        {"n": "temp_soil_gap", "c": lambda r: abs(r.get("air_temperature",25)-r.get("soil_temperature",22))>8, "d": "air-soil temp gap >8C", "s": 0.3},
        {"n": "high_humidity", "c": lambda r: r.get("air_humidity",60)>80, "d": "humidity>80% fungal risk", "s": 0.4},
    ]

    def _rule_based(self, rd, hist):
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
        return min(1.0, total), viols

    def detect(self, rd, hist, gh_id="gh-a"):
        start = time.perf_counter()
        info = _train_lstm_ae(gh_id)
        if info is not None:
            import numpy as np
            import torch
            W = _LSTM_WINDOW
            recent = hist[-W:] if len(hist) >= W else hist
            arr = np.array([_feat_vec(p["readings"]) for p in recent], dtype=np.float32)
            if len(arr) < W:
                pad = np.repeat(arr[-1:], W - len(arr), axis=0)
                arr = np.vstack([pad, arr])[-W:]
            arr_n = (arr - info["mean"]) / info["std"]
            x = torch.tensor(arr_n, dtype=torch.float32).unsqueeze(0)
            info["model"].eval()
            with torch.no_grad():
                recon = info["model"](x)
                err = float(torch.mean((recon - x) ** 2).item())
                feat_err = torch.mean((recon - x) ** 2, dim=(0, 1)).numpy()
            thr = info["thr"]
            score = max(0.0, min(1.0, (err - thr) / (thr * 2 + 1e-6)))
            top = sorted(zip(_FEATURES, feat_err.tolist()), key=lambda t: t[1], reverse=True)[:3]
            viols = [{"feature": f, "recon_error": round(float(e), 4)} for f, e in top]
            engine = "lstm_autoencoder"
            extra = {"recon_error": round(err, 4)}
        else:
            score, viols = self._rule_based(rd, hist)
            engine = "rule_based_fallback"
            extra = {}
        latency = (time.perf_counter() - start) * 1000
        result = {"layer": "L2_lstm_ae", "engine": engine,
                  "score": round(score, 3), "anomalous": score > 0.3,
                  "violations": viols, "latency_ms": round(latency, 2)}
        result.update(extra)
        return result

class Layer3:
    SENSORS = ["air_temperature", "air_humidity", "soil_moisture"]
    CONTEXT = 48

    def _linear_forecast(self, rd, hist):
        preds, devs = {}, {}
        for s in self.SENSORS:
            vals = [p["readings"].get(s, 0.0) for p in hist[-12:]]
            if not vals:
                continue
            n = len(vals); xm = (n - 1) / 2; ym = sum(vals) / n
            slope = sum((i - xm) * (v - ym) for i, v in enumerate(vals)) / max(sum((i - xm) ** 2 for i in range(n)), 0.001)
            pred = ym + slope * (n - xm); act = rd.get(s, pred)
            dev = abs(act - pred) / max(abs(pred), 0.001)
            preds[s] = round(pred, 2); devs[s] = round(dev, 4)
        return preds, devs, "linear_regression_fallback"

    def _chronos_forecast(self, rd, hist, pipe):
        import numpy as np
        import torch
        ctx_len = min(self.CONTEXT, len(hist))
        series = [[p["readings"].get(s, 0.0) for p in hist[-ctx_len:]] for s in self.SENSORS]
        context = torch.tensor(series, dtype=torch.float32)
        forecast = pipe.predict(context, prediction_length=1)
        fa = forecast.numpy() if hasattr(forecast, "numpy") else np.asarray(forecast)
        preds, devs = {}, {}
        for i, s in enumerate(self.SENSORS):
            pred = float(np.median(fa[i, :, 0]))
            act = rd.get(s, pred)
            dev = abs(act - pred) / max(abs(pred), 0.001)
            preds[s] = round(pred, 2); devs[s] = round(dev, 4)
        return preds, devs, "chronos-t5-small"

    def detect(self, rd, hist):
        start = time.perf_counter()
        if not hist or len(hist) < 10:
            return {"layer": "L3_chronos", "engine": "none", "score": 0.0,
                    "anomalous": False, "note": "insufficient history",
                    "latency_ms": 0.0}
        pipe = _get_chronos()
        if pipe is not None:
            preds, devs, engine = self._chronos_forecast(rd, hist, pipe)
        else:
            preds, devs, engine = self._linear_forecast(rd, hist)
        avg_d = sum(devs.values()) / max(len(devs), 1)
        max_d = max(devs.values()) if devs else 0
        sc = min(1.0, avg_d * 5 + max_d * 2)
        latency = (time.perf_counter() - start) * 1000
        return {"layer": "L3_chronos", "engine": engine, "score": round(sc, 3),
                "anomalous": sc > 0.4, "predictions": preds, "deviations": devs,
                "latency_ms": round(latency, 2)}


class Detector:
    def __init__(self): self.l1, self.l2, self.l3 = Layer1(), Layer2(), Layer3()
    def detect(self, gh_id):
        cur = _gen(gh_id); hist = _hist(gh_id, 24); rd = cur["readings"]
        r1 = self.l1.detect(rd, gh_id); r2 = self.l2.detect(rd, hist, gh_id); r3 = self.l3.detect(rd, hist)
        combined = r1["score"]*0.3 + r2["score"]*0.4 + r3["score"]*0.3
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
    l1_ok = _sklearn_available()
    l2_ok = _torch_available()
    l3_ok = _chronos_available()
    return {"architecture": "three-layer defense",
            "layers": [
                {"layer": 1, "name": "Isolation Forest", "latency": "<1ms",
                 "real_model": l1_ok,
                 "engine": "isolation_forest" if l1_ok else "range_check_fallback"},
                {"layer": 2, "name": "LSTM-Autoencoder", "latency": "<5ms",
                 "real_model": l2_ok,
                 "engine": "lstm_autoencoder" if l2_ok else "rule_based_fallback"},
                {"layer": 3, "name": "Chronos-T5-Small", "latency": "~50ms",
                 "real_model": l3_ok,
                 "engine": "chronos-t5-small" if l3_ok else "linear_regression_fallback"},
            ],
            "weights": {"L1": 0.3, "L2": 0.4, "L3": 0.3},
            "thresholds": {"warning": 0.3, "critical": 0.7}}