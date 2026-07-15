"""Generate ``utils/calibration_data.json`` from the fixed fixtures.

对每个 fixture 运行完整管线（固定随机种子，可复现），收集各专家 Agent 的最终
置信度 + 是否正确(1/0)。病理 Agent 额外把"次选诊断(反事实)"作为负样本，使校准
数据同时包含正负两类，IsotonicRegression 才能学到有意义的映射。

Run from agri-ai/:
    python utils/generate_calibration.py
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("AGRI_AI_DB_PATH", str(ROOT / "data" / "calib.db"))
os.environ.setdefault("AGRI_AI_CALIBRATION", "0")  # 生成期间关闭校准，收集原始置信度

from orchestrator import AgentOrchestrator
from rule_engine import sensor_anomaly
from evals.fixtures import FIXTURES
from utils.confidence_calibration import Calibrator


def _pathology_correct(trace, ground_truth) -> int:
    if not ground_truth or ground_truth == "证据不足":
        return 1 if "病理证据不足" in trace.claim else 0
    return 1 if ground_truth in trace.claim else 0


def _collect_counterfactual(cal: Calibrator, trace, ground_truth) -> None:
    """把病理次选诊断(反事实)作为负样本：次选不是真值 -> correct=0。"""
    diseases = (trace.evidence or {}).get("possible_diseases", [])
    if len(diseases) < 2:
        return
    alt = diseases[1]
    alt_name = alt.get("name", "")
    alt_conf = min(0.9, 0.45 + alt.get("match_score", 0) * 0.08)
    correct = 1 if (ground_truth and ground_truth in alt_name) else 0
    cal.collect("病理Agent", round(alt_conf, 3), correct)


def main() -> None:
    cal = Calibrator(enabled=False)
    cal._training.clear()  # 每次从零生成，避免叠加历史快照
    orch = AgentOrchestrator(use_langgraph=True)
    for fx in FIXTURES:
        if fx.get("sensor_override"):
            sensor_anomaly.ANOMALIES["gh-a"] = fx["sensor_override"]
        try:
            random.seed(7)
            decision = orch.run(fx["query"])
        finally:
            sensor_anomaly.ANOMALIES.pop("gh-a", None)

        ground_truth = fx.get("ground_truth")
        pathology = next((t for t in decision.traces if t.agent == "病理Agent"), None)
        global_correct = _pathology_correct(pathology, ground_truth) if pathology else 0

        is_disease_case = bool(ground_truth and ground_truth != "证据不足")
        for trace in decision.traces:
            if trace.layer != "专家层":
                continue
            if trace.agent == "病理Agent":
                # 仅对真实病害诊断场景收集病理样本（证据不足属于不同regime，
                # 低置信度是恰当的，纳入会污染单调校准）
                if is_disease_case:
                    cal.collect(trace.agent, trace.confidence, _pathology_correct(trace, ground_truth))
                    _collect_counterfactual(cal, trace, ground_truth)
            else:
                # 非病理专家以"最终决策是否正确"作为标签
                cal.collect(trace.agent, trace.confidence, global_correct)

    cal.save()
    print(f"calibration data saved -> {cal.data_path}")
    for agent, samples in cal._training.items():
        print(f"  {agent}: {len(samples)} samples, positives={sum(c for _, c in samples)}")


if __name__ == "__main__":
    main()
