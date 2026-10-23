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

    @staticmethod
    def _fit_one(samples: list[tuple[float, int]]) -> tuple[str, Any] | None:
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


# ---------------------------------------------------------------------------
# Decision-level confidence (ADR-005)
# ---------------------------------------------------------------------------
DECISION_DATA_PATH = Path(__file__).parent / 'decision_calibration_data.json'


def parse_signed_delta(value: Any) -> float:
    """Parse +0.15 / -0.10 / 15% / 0.15 into a bounded float delta."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return max(-0.2, min(0.2, float(value)))
    text = str(value or '').strip()
    if not text:
        return 0.0
    percent = '%' in text
    text = text.replace('%', '').strip()
    try:
        delta = float(text)
    except ValueError:
        return 0.0
    if percent:
        delta = delta / 100.0
    return max(-0.2, min(0.2, delta))


def compute_decision_signals(
    llm: dict[str, Any],
    fallback_analysis: dict[str, Any] | None = None,
    debate: Any = None,
    self_consistency: float | None = None,
) -> dict[str, Any]:
    """Collect structural evidence signals around a Judge decision.

    The model's own number is only one input, so a confident-sounding answer
    cannot dominate the score when KG support, expert evidence, conflicts and
    collective omissions disagree with it.
    """
    fallback_analysis = fallback_analysis or {}
    consistency = llm.get("consistency_analysis") or {}
    diagnoses = consistency.get("agent_diagnoses") or []
    full = partial = conflict = 0
    for item in diagnoses:
        match = str((item or {}).get("kg_match", "")) if isinstance(item, dict) else ""
        if "完全匹配" in match:
            full += 1
        elif "部分匹配" in match:
            partial += 1
        elif "冲突" in match:
            conflict += 1
    total = len(diagnoses) or 1

    scores = llm.get("evidence_scores") or {}
    numeric = [
        float(v)
        for v in scores.values()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    ]
    evidence_strength = (
        min(1.0, max(0.0, sum(numeric) / len(numeric) / 10.0)) if numeric else 0.5
    )

    omission = fallback_analysis.get("collective_omission") or {}
    omitted = omission.get("omitted_diseases") if isinstance(omission, dict) else None
    omission_count = len(omitted) if isinstance(omitted, list) else 0

    critic = fallback_analysis.get("critic") or {}
    critic_escalate = bool(critic.get("escalate")) if isinstance(critic, dict) else False

    try:
        debate_conflicts = int(getattr(debate, "conflicts", 0) or 0)
    except (TypeError, ValueError):
        debate_conflicts = 0

    self_report = llm.get("final_confidence", llm.get("confidence"))
    try:
        self_report = float(self_report)
    except (TypeError, ValueError):
        self_report = 0.5

    return {
        'self_report': round(max(0.0, min(1.0, self_report)), 4),
        'kg_support': round((full + 0.5 * partial) / total, 4),
        'kg_conflict_ratio': round(conflict / total, 4),
        'evidence_strength': round(evidence_strength, 4),
        "conflict_count": len(consistency.get("critical_conflicts") or []) + debate_conflicts,
        "omission_count": omission_count,
        "critic_escalate": critic_escalate,
        "kg_contribution": parse_signed_delta(llm.get("kg_contribution")),
        "diagnoses": len(diagnoses),
        "self_consistency": None if self_consistency is None else round(float(self_consistency), 4),
    }


def combine_decision_score(signals: dict[str, Any]) -> float:
    """Deterministic structural score before calibration (documented weights)."""
    consistency = signals.get("self_consistency")
    if consistency is None:
        # No agreement signal: the remaining features were measured to carry
        # almost no information, so degrade instead of pretending confidence.
        score = (
            0.40 * float(signals.get("self_report", 0.5))
            + 0.35 * float(signals.get("evidence_strength", 0.5))
            + 0.25 * float(signals.get("kg_support", 0.0))
        )
        degradation = 0.65
    else:
        # Agreement is the only signal shown to separate correct from wrong
        # decisions (corr 0.78 on the 2026-10-24 probe), so it dominates.
        score = (
            0.65 * float(consistency)
            + 0.20 * float(signals.get("self_report", 0.5))
            + 0.15 * float(signals.get("evidence_strength", 0.5))
        )
        degradation = 1.0
    score += float(signals.get("kg_contribution", 0.0))
    score -= 0.02 * min(int(signals.get("conflict_count", 0)), 3)
    score -= 0.05 * min(int(signals.get("omission_count", 0)), 2)
    if signals.get("critic_escalate"):
        score -= 0.05
    score -= 0.05 * float(signals.get("kg_conflict_ratio", 0.0))
    upper = 0.95 * degradation if degradation < 1.0 else 0.95
    return round(max(0.05, min(upper, score)), 4)


class DecisionCalibrator:
    """Calibrate the derived decision score against observed correctness.

    Training samples are (structural_score, correct) pairs generated by
    scripts/fit_decision_calibration.py from a real-Judge run.  Fit on one
    seed and evaluate on another; never fit and evaluate on the same cases.
    """

    def __init__(
        self,
        data_path: str | Path | None = None,
        enabled: bool | None = None,
    ):
        self.data_path = Path(data_path) if data_path else DECISION_DATA_PATH
        if enabled is None:
            enabled = os.environ.get(
                "AGRI_AI_DECISION_CALIBRATION", "1"
            ) not in {"0", "false", "False"}
        self.enabled = enabled
        self._samples: list[tuple[float, int]] = []
        self._model: tuple[str, Any] | None = None
        self._load()
        if self.enabled and self._samples:
            self._model = Calibrator._fit_one(self._samples)
            if self._model is None and len({c for _, c in self._samples}) == 1:
                self._model = ("constant", float(self._samples[0][1]))

    def _load(self) -> None:
        if not self.data_path.exists():
            return
        try:
            data = json.loads(self.data_path.read_text(encoding=
                "utf-8"
            ))
        except (ValueError, OSError):
            return
        pairs = data.get(
            "samples"
        ) if isinstance(data, dict) else data
        for item in pairs or []:
            try:
                self._samples.append((float(item[0]), int(bool(item[1]))))
            except (TypeError, ValueError, IndexError):
                continue

    def calibrate(self, score: float) -> float:
        raw = float(score)
        if not self.enabled or self._model is None:
            return round(raw, 4)
        kind, payload = self._model
        if kind == "constant":
            pred = float(payload)
        elif kind == "isotonic":
            pred = float(payload.predict([raw])[0])
        elif kind == "platt":
            a, b = payload
            pred = 1.0 / (1.0 + math.exp(-(a * raw + b)))
        else:
            return round(raw, 4)
        return round(max(0.05, min(0.95, pred)), 4)

    def status(self) -> dict[str, Any]:
        return {
            'enabled': self.enabled,
            'samples': len(self._samples),
            'model': self._model[0] if self._model else 'identity',
            'data_path': self.data_path.name,
        }
