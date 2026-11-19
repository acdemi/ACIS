from __future__ import annotations

import importlib
import os
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def delivery_eval():
    module_name = "scripts.run_delivery_eval"
    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    yield module
    sys.modules.pop(module_name, None)


def test_diagnosis_scoring_uses_final_decision_and_separates_top_three(delivery_eval):
    score = delivery_eval._score_diagnosis(
        expected="叶霉病",
        intent="diagnose",
        decision="病理判断首选：番茄早疫病",
        candidate_names=["叶霉病", "早疫病"],
        crop="tomato",
    )

    assert score == {
        "scored": True,
        "matches_expected": False,
        "top3_scored": True,
        "top3_matches_expected": True,
    }


def test_diagnosis_labels_use_exact_normalized_matches(delivery_eval):
    score = delivery_eval._score_diagnosis(
        expected="黄萎病",
        intent="diagnose",
        decision="病理判断首选：棉花萎病",
        candidate_names=["棉花萎病"],
        crop="cotton",
    )

    assert score["matches_expected"] is False
    assert score["top3_matches_expected"] is False


def test_empty_candidate_list_counts_as_top_three_miss(delivery_eval):
    score = delivery_eval._score_diagnosis(
        expected="大斑病",
        intent="diagnose",
        decision="病理判断首选：玉米大斑病",
        candidate_names=[],
        crop="maize",
    )

    assert score["scored"] is True
    assert score["matches_expected"] is True
    assert score["top3_scored"] is True
    assert score["top3_matches_expected"] is False


def test_non_diagnosis_and_missing_reference_are_not_scored(delivery_eval):
    assert delivery_eval._score_diagnosis(
        expected=None,
        intent="diagnose",
        decision="anything",
        candidate_names=[],
        crop="maize",
    ) == {
        "scored": False,
        "matches_expected": None,
        "top3_scored": False,
        "top3_matches_expected": None,
    }
    assert delivery_eval._score_diagnosis(
        expected="叶霉病",
        intent="irrigate",
        decision="气象条件支持灌溉",
        candidate_names=["叶霉病"],
        crop="tomato",
    )["scored"] is False


def test_insufficient_evidence_score_requires_explicit_abstention(delivery_eval):
    abstained = delivery_eval._score_diagnosis(
        expected="证据不足",
        intent="diagnose",
        decision="证据不足，暂不能确认病害",
        candidate_names=[],
        crop="maize",
    )
    guessed = delivery_eval._score_diagnosis(
        expected="证据不足",
        intent="diagnose",
        decision="病理判断首选：叶霉病，建议人工复核",
        candidate_names=["叶霉病"],
        crop="maize",
    )

    assert abstained["matches_expected"] is True
    assert guessed["matches_expected"] is False


def test_latency_percentile_uses_linear_interpolation(delivery_eval):
    assert delivery_eval._percentile([4.0, 1.0, 3.0, 2.0], 0.5) == 2.5
    assert delivery_eval._percentile([4.0, 1.0, 3.0, 2.0], 0.95) == 3.85


def test_run_forces_and_restores_offline_configuration_and_sensor_state(
    delivery_eval, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    import acis.knowledge.storage.db as database

    sentinel_db = tmp_path / "existing.sqlite3"
    sentinel_db.write_bytes(b"preserve this file")
    original_db_path = database._DB_PATH
    database._DB_PATH = sentinel_db

    previous_environment = {
        "AGRI_AI_RAG_BACKEND": "qdrant",
        "AGRI_AI_KG_BACKEND": "neo4j",
        "AGRI_AI_PERSIST": "1",
        "HF_HUB_OFFLINE": "0",
        "TRANSFORMERS_OFFLINE": "0",
        "AGRI_AI_DB_PATH": str(sentinel_db),
        "AGRI_AI_EXTRA_EXPERTS": "0",
        "AGRI_AI_MULTI_ROUND_DEBATE": "0",
        "AGRI_AI_RAG_TOP_K": "99",
        "AGRI_AI_CALIBRATION": "0",
    }
    for name, value in previous_environment.items():
        monkeypatch.setenv(name, value)

    from datetime import datetime

    sensor_anomaly = SimpleNamespace(
        ANOMALIES={"gh-a": {"preexisting": True}}, datetime=datetime
    )
    weather_module = SimpleNamespace(
        datetime=datetime,
        _WEATHER_STATE={
            "condition": "多云转晴",
            "season": "夏季",
            "region": "华北平原",
            "base_temp": 32.0,
            "base_humidity": 55.0,
        },
    )
    seen_sensor_states: list[dict | None] = []
    observed_clocks: list[str] = []
    fixtures = [
        {
            "id": "maize_case",
            "query": "玉米叶片病斑",
            "crop": "maize",
            "intent": "diagnose",
            "disease": "大斑病",
            "sensor_override": {"humidity_offset": -20.0},
        },
        {
            "id": "maize_case_without_override",
            "query": "玉米叶片病斑",
            "crop": "maize",
            "intent": "diagnose",
            "disease": "大斑病",
        },
    ]

    class FakeOrchestrator:
        last_trace = SimpleNamespace(stages_present=["request", "judge"], events=[1, 2])

        def __init__(self, **_kwargs):
            assert os.environ["AGRI_AI_RAG_BACKEND"] == "memory"
            assert os.environ["AGRI_AI_KG_BACKEND"] == "memory"
            assert os.environ["AGRI_AI_PERSIST"] == "0"
            assert os.environ["HF_HUB_OFFLINE"] == "1"
            assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
            assert os.environ["AGRI_AI_EXTRA_EXPERTS"] == "1"
            assert os.environ["AGRI_AI_MULTI_ROUND_DEBATE"] == "1"
            assert os.environ["AGRI_AI_RAG_TOP_K"] == "3"
            assert os.environ["AGRI_AI_CALIBRATION"] == "1"
            assert Path(os.environ["AGRI_AI_DB_PATH"]) != sentinel_db

        def run(self, _query):
            seen_sensor_states.append(sensor_anomaly.ANOMALIES.get("gh-a"))
            observed_clocks.append(sensor_anomaly.datetime.now().isoformat())
            return SimpleNamespace(
                traces=[
                    SimpleNamespace(
                        agent="病理Agent",
                        claim="病理判断首选：玉米大斑病",
                        execution={"status": "success", "mode": "rules"},
                    )
                ],
                decision="病理判断首选：玉米大斑病",
                confidence=0.8,
                risk_level="low",
                judge_mode="rules",
                need_human_review=False,
                debate=SimpleNamespace(critic={"triggered": False}),
                report={"candidates": [{"name": "玉米大斑病"}]},
                token_usage=None,
            )

    monkeypatch.setattr(
        delivery_eval,
        "_load_runtime",
        lambda: (
            fixtures,
            FakeOrchestrator,
            lambda _query: SimpleNamespace(crop="maize", intent="irrigate"),
            sensor_anomaly,
            database,
            weather_module,
        ),
    )
    random_state = random.getstate()

    try:
        summary = delivery_eval.run()
        assert database._DB_PATH == sentinel_db
    finally:
        database._DB_PATH = original_db_path

    assert summary["aggregate"]["diagnosis_accuracy"] == {
        "correct": 2,
        "scored": 2,
        "rate": 1.0,
    }
    assert summary["aggregate"]["top3_accuracy"] == {
        "correct": 2,
        "scored": 2,
        "rate": 1.0,
    }
    assert summary["aggregate"]["intent_accuracy"] == {
        "correct": 0,
        "scored": 2,
        "rate": 0.0,
    }
    assert seen_sensor_states == [
        {"humidity_offset": -20.0},
        None,
    ]
    assert observed_clocks == ["2026-06-15T10:00:00", "2026-06-15T10:00:00"]
    assert sensor_anomaly.ANOMALIES["gh-a"] == {"preexisting": True}
    assert random.getstate() == random_state
    assert sensor_anomaly.datetime is datetime
    assert weather_module.datetime is datetime
    assert weather_module._WEATHER_STATE == {
        "condition": "多云转晴",
        "season": "夏季",
        "region": "华北平原",
        "base_temp": 32.0,
        "base_humidity": 55.0,
    }
    assert sentinel_db.read_bytes() == b"preserve this file"
    assert {name: os.environ[name] for name in previous_environment} == previous_environment
