"""Unit tests for the AgentOutput schema, including the ACIS cognitive-upgrade
``counterfactual_observations`` field.

These tests pin down:
- the new optional ``counterfactual_observations: list[str]`` field defaults to
  an empty list when an agent does not provide it;
- the pre-existing ``counterfactual`` dict field (rejected alternative
  diagnosis, consumed by the Judge consistency review) is preserved unchanged so
  existing agent implementations keep working;
- runtime serialization (``dataclasses.asdict``) and JSON export include the new
  field, yielding ``counterfactual_observations: []`` when omitted.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, fields

# Make the repo root importable when running ``pytest tests/test_agent_output.py``
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.types import AgentOutput  # noqa: E402


def test_counterfactual_observations_field_exists():
    names = {f.name for f in fields(AgentOutput)}
    assert "counterfactual_observations" in names


def test_counterfactual_observations_defaults_to_empty_list():
    out = AgentOutput(layer="专家层", agent="病理Agent", claim="x", confidence=0.5)
    assert out.counterfactual_observations == []
    assert isinstance(out.counterfactual_observations, list)


def test_counterfactual_dict_field_still_defaults_to_empty_dict():
    # Backward compatibility: the existing dict-based counterfactual keeps its
    # original default so existing agents / Judge consumers are unaffected.
    out = AgentOutput(layer="L", agent="A", claim="c", confidence=0.5)
    assert out.counterfactual == {}


def test_agent_can_populate_counterfactual_observations():
    observations = [
        "If leaf lesions had concentric rings, Alternaria would become the preferred diagnosis.",
        "If humidity had stayed below 70%, fungal pressure would drop sharply.",
    ]
    out = AgentOutput(
        layer="专家层", agent="病理Agent", claim="番茄灰霉病", confidence=0.78,
        counterfactual_observations=observations,
    )
    assert out.counterfactual_observations == observations
    assert all(isinstance(x, str) for x in out.counterfactual_observations)


def test_asdict_includes_counterfactual_observations_default_empty():
    out = AgentOutput(layer="L", agent="A", claim="c", confidence=0.5)
    d = asdict(out)
    assert "counterfactual_observations" in d
    assert d["counterfactual_observations"] == []


def test_json_serialization_has_empty_list_when_omitted():
    out = AgentOutput(layer="L", agent="A", claim="c", confidence=0.5)
    payload = json.dumps(asdict(out), ensure_ascii=False)
    assert '"counterfactual_observations": []' in payload


def test_json_serialization_roundtrips_populated_observations():
    observations = ["If symptom X appeared, diagnosis Y would be preferred."]
    out = AgentOutput(
        layer="L", agent="A", claim="c", confidence=0.5,
        counterfactual_observations=observations,
    )
    payload = json.loads(json.dumps(asdict(out), ensure_ascii=False))
    assert payload["counterfactual_observations"] == observations


def test_existing_agent_dict_counterfactual_pattern_still_works():
    # Mirrors how PathologyAgent / CultivationAgent / EconomicAgent /
    # EcologyAgent / MeteorologyAgent currently build an AgentOutput: they pass
    # the dict-based ``counterfactual``. This must keep working, and the new
    # list field must default to [] alongside it.
    legacy_counterfactual = {
        "alternative": "Alternaria leaf spot",
        "rejection_reason": "match score lower than the primary diagnosis",
    }
    out = AgentOutput(
        layer="专家层", agent="病理Agent", claim="番茄灰霉病", confidence=0.7,
        evidence={"possible_diseases": []}, warnings=[], recommendations=[],
        counterfactual=legacy_counterfactual,
    )
    assert out.counterfactual == legacy_counterfactual
    assert out.counterfactual_observations == []


def test_two_counterfactual_concepts_are_independent():
    # The dict field (rejected alternative) and the list field (hypothetical
    # observations that would change the conclusion) are distinct and must not
    # interfere with each other.
    out = AgentOutput(
        layer="L", agent="A", claim="c", confidence=0.5,
        counterfactual={"alternative": "X", "rejection_reason": "Y"},
        counterfactual_observations=["If Z were observed, X would be preferred."],
    )
    assert out.counterfactual == {"alternative": "X", "rejection_reason": "Y"}
    assert out.counterfactual_observations == ["If Z were observed, X would be preferred."]