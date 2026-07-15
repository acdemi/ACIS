"""Confidence calibration for expert agents (ACIS 2.0).

收集各专家 Agent 在 fixture 上的原始置信度 + 是否正确(1/0)，使用
``sklearn.isotonic.IsotonicRegression`` 训练校准函数；sklearn 不可用时回退到
手写 Platt Scaling（sigmoid 拟合，TODO: 迁移到 sklearn LogisticRegression）。

校准器在 Judge 融合置信度前对各专家置信度做映射，默认开启，可用环境变量
``AGRI_AI_CALIBRATION=0`` 关闭。校准数据快照见 ``utils/calibration_data.json``
（由 ``utils/generate_calibration.py`` 基于固定 fixture + 随机种子生成）。
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

DEFAULT_DATA_PATH = Path(__file__).parent / "calibration_data.json"


class Calibrator:
    """Per-agent confidence calibrator (Isotonic / Platt / passthrough)."""

    def __init__(self, data_path: str | Path | None = None, enabled: bool | None = None):
        self.data_path = Path(data_path) if data_path else DEFAULT_DATA_PATH
        if enabled is None:
            enabled = os.environ.get("AGRI_AI_CALIBRATION", "1") not in {"0", "false", "False"}
        self.enabled = enabled
        self._training: dict[str, list[tuple[float, int]]] = {}
        self._models: dict[str, tuple[str, Any]] = {}
        self._load()
        if self.enabled:
            self.fit()

    # ------------------------------------------------------------------
    # data collection / persistence
    # ------------------------------------------------------------------
    def collect(self, agent: str, raw_confidence: float, correct: int) -> None:
        self._training.setdefault(agent, []).append((float(raw_confidence), int(bool(correct))))

    def _load(self) -> None:
        if not self.data_path.exists():
            return
        try:
            data = json.loads(self.data_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return
        for agent, samples in data.items():
            self._training[agent] = [(float(r), int(c)) for r, c in samples]

    def save(self, path: str | Path | None = None) -> None:
        out = Path(path) if path else self.data_path
        data = {a: [[r, c] for r, c in s] for a, s in self._training.items()}
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # fitting
    # ------------------------------------------------------------------
    def fit(self) -> None:
        for agent, samples in self._training.items():
            self._models[agent] = self._fit_one(samples)

    def _fit_one(self, samples: list[tuple[float, int]]) -> tuple[str, Any] | None:
        if len(samples) < 2 or len({r for r, _ in samples}) < 2:
            return None  # 置信度无变化，无法校准
        X = [r for r, _ in samples]
        y = [c for _, c in samples]
        if len(set(y)) < 2:
            # 退化：只有一类标签，无校准信号，原值透传。
            return None
        try:
            from sklearn.isotonic import IsotonicRegression
            ir = IsotonicRegression(out_of_bounds="clip", y_min=0.05, y_max=0.95)
            ir.fit(X, y)
            return ("isotonic", ir)
        except Exception:
            # TODO: 迁移到 sklearn LogisticRegression；当前手写 Platt Scaling。
            return ("platt", self._platt_fit(X, y))

    @staticmethod
    def _platt_fit(X: list[float], y: list[int]) -> tuple[float, float]:
        a, b, lr = 0.0, 0.0, 0.1
        for _ in range(800):
            for xi, yi in zip(X, y):
                p = 1.0 / (1.0 + math.exp(-(a * xi + b)))
                err = p - yi
                a -= lr * err * xi
                b -= lr * err
        return (a, b)

    # ------------------------------------------------------------------
    # inference
    # ------------------------------------------------------------------
    def calibrate(self, agent: str, raw_confidence: float) -> float:
        if not self.enabled:
            return float(raw_confidence)
        raw = float(raw_confidence)
        model = self._models.get(agent)
        if model is None:
            return raw  # 该 Agent 无校准数据，原值透传
        kind, payload = model
        if kind == "isotonic":
            pred = float(payload.predict([raw])[0])
        elif kind == "platt":
            a, b = payload
            pred = 1.0 / (1.0 + math.exp(-(a * raw + b)))
        else:
            return raw
        # 与原始置信度混合，保证稳定性（alpha 可调）
        alpha = float(os.environ.get("AGRI_AI_CALIB_ALPHA", "0.5"))
        calibrated = alpha * pred + (1.0 - alpha) * raw
        return round(max(0.1, min(0.95, calibrated)), 3)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "agents": {
                a: {"kind": m[0], "samples": len(self._training.get(a, []))} if m else {"kind": "passthrough", "samples": len(self._training.get(a, []))}
                for a, m in self._models.items()
            },
        }
