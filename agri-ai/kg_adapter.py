"""Knowledge graph adapter for the Judge Agent.

Hybrid KG: prefers a real Neo4j + AgriKG graph when available, then falls back
to the structured ``DISEASE_DB`` synthesis so the MVP stays runnable offline.
This mirrors the RAG retriever's "real-backend-first, memory-fallback" pattern.

The public contract ``query_kg(crop, query, top_k)`` is unchanged: it always
returns ``diseases`` / ``triples`` / ``triple_strings`` / ``rules`` /
``hard_constraints`` plus a ``backend`` marker (``neo4j`` | ``memory`` |
``fallback``) so the Judge can record which knowledge source backed its
consistency check.

AgriKG schema (imported by ``scripts/import_agrikg.py``):
  节点 :HudongItem / :NewNode，部分按标题关键词追加 :Disease / :Pest 标签
  关系 (:HudongItem|:NewNode)-[:RELATION {type}]->(:HudongItem|:NewNode)
  病害的 detail / baseInfoKeyList / baseInfoValueList 为自然语言文本。

Env:
  AGRI_AI_KG_BACKEND=auto|neo4j|memory  (default auto)
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=agriai2026
"""

from __future__ import annotations

import os
import re
from typing import Any

from rag.knowledge_base import CROP_MAP, DISEASE_DB, _DISEASE_KEYWORDS

# ============================================================
# 作物归一化
# ============================================================


def _normalize_crop(crop: str = "") -> str:
    if not crop:
        return ""
    return CROP_MAP.get(crop.lower(), crop)


# ============================================================
# 条件阈值解析（供硬约束使用）
# ============================================================


def _parse_threshold(value: str) -> tuple[str | None, float | None]:
    """Parse a condition string like '>85%' or '20-25°C' into (operator, number)."""
    if not isinstance(value, str):
        return None, None
    match = re.search(r"(>=|<=|>|<)\s*([0-9]+(?:\.[0-9]+)?)", value)
    if match:
        return match.group(1), float(match.group(2))
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*[-~]\s*([0-9]+(?:\.[0-9]+)?)", value)
    if match:
        return "range", float(match.group(2))
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    if match:
        return None, float(match.group(1))
    return None, None


_CONDITION_LABELS = {"temperature": "温度", "humidity": "湿度", "co2": "CO2", "ventilation": "通风"}


def _condition_label(key: str) -> str:
    return _CONDITION_LABELS.get(key, key)


def _metric_key(label: str) -> str | None:
    label = label.lower()
    if "湿度" in label or "humid" in label:
        return "humidity"
    if "温度" in label or "temp" in label:
        return "temperature"
    if "co2" in label or "二氧化碳" in label:
        return "co2"
    return None


# ============================================================
# 记忆后端：基于 DISEASE_DB 的结构化合成（离线可用，硬约束来源）
# ============================================================


def _relevant_diseases(crop: str, query: str, top_k: int = 3) -> list[tuple[str, dict[str, Any], float]]:
    crop_zh = _normalize_crop(crop)
    scored = []
    for disease_id, disease in DISEASE_DB.items():
        if crop_zh and crop_zh not in disease.get("crop", ""):
            continue
        score = 0.0
        for kw in _DISEASE_KEYWORDS.get(disease_id, []):
            if kw in query:
                score += 1.0
        for symptom in disease.get("symptoms", []):
            for char in query:
                if char in symptom and "\u4e00" <= char <= "\u9fff":
                    score += 0.3
                    break
        scored.append((disease_id, disease, score))
    scored.sort(key=lambda item: item[2], reverse=True)
    return [item for item in scored[:top_k] if item[2] > 0] or scored[:top_k]


def _disease_triples(disease_id: str, disease: dict[str, Any]) -> list[dict[str, str]]:
    name = disease["name"]
    crop = disease.get("crop", "")
    triples: list[dict[str, str]] = [{"subject": crop, "relation": "易感", "object": name}]
    if disease.get("pathogen"):
        triples.append({"subject": name, "relation": "病原", "object": disease["pathogen"]})
    for symptom in disease.get("symptoms", [])[:3]:
        triples.append({"subject": name, "relation": "症状", "object": symptom})
    for key, value in disease.get("conditions", {}).items():
        if key in {"note", "ventilation"}:
            continue
        triples.append({"subject": name, "relation": "诱发条件", "object": f"{_condition_label(key)}{value}"})
    treatment = "；".join(disease.get("treatment", [])[:2])
    if treatment:
        triples.append({"subject": name, "relation": "防治", "object": treatment})
    return triples


def _hard_constraints(disease_id: str, disease: dict[str, Any]) -> list[dict[str, Any]]:
    constraints = []
    for key, value in disease.get("conditions", {}).items():
        metric = _metric_key(key)
        if not metric:
            continue
        operator, threshold = _parse_threshold(str(value))
        if threshold is None:
            continue
        constraints.append(
            {
                "disease": disease["name"],
                "metric": metric,
                "operator": operator or "min",
                "threshold": threshold,
                "raw": f"{_condition_label(key)}{value}",
                "description": f"诊断{disease['name']}通常需要{_condition_label(key)}{value}；当前{_condition_label(key)}若明显不满足，该诊断存疑",
                "source": "memory",
            }
        )
    return constraints


def _rule_strings(disease: dict[str, Any]) -> list[str]:
    rules = []
    conditions = disease.get("conditions", {})
    hum = conditions.get("humidity") or conditions.get("湿度")
    if hum:
        rules.append(f"{disease['name']}高发条件：湿度{hum}，若棚内湿度明显偏低应降低该诊断置信度")
    temp = conditions.get("temperature") or conditions.get("温度")
    if temp:
        rules.append(f"{disease['name']}适宜温度{temp}，环境温度偏离过大时该诊断证据减弱")
    if disease.get("symptoms"):
        rules.append(f"{disease['name']}典型症状：{disease['symptoms'][0]}，需与视觉/症状描述核对")
    return rules


def _memory_kg(crop: str, query: str, top_k: int = 3) -> dict[str, Any]:
    """Build KG triples, reference rules and hard constraints from DISEASE_DB."""
    relevant = _relevant_diseases(crop, query, top_k)
    triples: list[dict[str, str]] = []
    triple_strings: list[str] = []
    rules: list[str] = []
    hard_constraints: list[dict[str, Any]] = []

    for disease_id, disease, _score in relevant:
        disease_triples = _disease_triples(disease_id, disease)
        triples.extend(disease_triples)
        triple_strings.extend(f"({t['subject']})-[{t['relation']}]->({t['object']})" for t in disease_triples)
        rules.extend(_rule_strings(disease))
        hard_constraints.extend(_hard_constraints(disease_id, disease))

    return {
        "crop": _normalize_crop(crop),
        "query": query,
        "diseases": [disease["name"] for _, disease, _ in relevant],
        "triples": triples,
        "triple_strings": triple_strings[:15],
        "rules": rules[:6],
        "hard_constraints": hard_constraints,
    }


# ============================================================
# Neo4j 后端：真实 AgriKG 图谱检索
# ============================================================

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "agriai2026")

_driver = None

# AgriKG 病害标题/详情中的症状关键词，用于与查询做命中打分。
SYMPTOM_KEYWORDS = [
    "黄斑", "霉", "斑", "枯", "烂", "卷", "轮纹", "多角",
    "水渍", "褐", "灰", "萎蔫", "白粉", "锈", "斑点", "落叶",
    "畸形", "腐烂", "坏死",
]


def _neo4j_available() -> bool:
    """Return True only when the neo4j driver imports and the DB is reachable."""
    driver = _get_driver()
    if driver is None:
        return False
    try:
        with driver.session() as session:
            session.run("RETURN 1")
        return True
    except Exception:
        return False


def _get_driver():
    """Lazy Neo4j driver; returns None if the neo4j package is not installed."""
    global _driver
    if _driver is not None:
        return _driver
    try:
        from neo4j import GraphDatabase

        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        return _driver
    except Exception:
        return None


def _query_neo4j(cypher: str, params: dict | None = None) -> list:
    driver = _get_driver()
    if driver is None:
        return []
    try:
        with driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]
    except Exception:
        return []


def _parse_base_info(keys_str: Any, vals_str: Any) -> list[dict[str, str]]:
    """Parse AgriKG baseInfoKeyList/baseInfoValueList (## delimited) into pairs."""
    keys = [k.strip().rstrip("：:").strip() for k in (keys_str or "").split("##") if k.strip()]
    vals = [v.strip() for v in (vals_str or "").split("##") if v.strip()]
    pairs = []
    for i, key in enumerate(keys):
        value = vals[i] if i < len(vals) else ""
        if key:
            pairs.append({"key": key, "value": value})
    return pairs


def _neo4j_disease_candidates(crop: str, query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Search AgriKG :Disease nodes by crop + symptom keyword overlap."""
    crop_zh = _normalize_crop(crop)
    cypher = (
        "MATCH (d:Disease) "
        "WHERE ($crop = '' OR d.title CONTAINS $crop OR d.detail CONTAINS $crop) "
        "RETURN d.title AS disease, d.detail AS detail, "
        "d.baseInfoKeyList AS bkeys, d.baseInfoValueList AS bvals "
        "LIMIT 300"
    )
    rows = _query_neo4j(cypher, {"crop": crop_zh})
    scored = []
    for row in rows:
        text = f"{row.get('detail') or ''} {row.get('bvals') or ''}"
        score = 0
        matched = []
        for kw in SYMPTOM_KEYWORDS:
            if kw in query and kw in text:
                score += 1
                matched.append(kw)
        if crop_zh and crop_zh in (row.get("disease") or ""):
            score += 1
        if score > 0:
            scored.append(
                {
                    "disease": row["disease"],
                    "detail": (row.get("detail") or "")[:160],
                    "base_info": _parse_base_info(row.get("bkeys"), row.get("bvals")),
                    "score": score,
                    "matched": matched,
                }
            )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def _neo4j_disease_relations(disease_name: str, limit: int = 6) -> list[dict[str, str]]:
    """Fetch a disease's outgoing :RELATION neighbors (real AgriKG triples)."""
    cypher = (
        "MATCH (d:Disease {title: $name}) "
        "OPTIONAL MATCH (d)-[r:RELATION]->(e) "
        "RETURN collect({type: r.type, target: e.title}) AS rels"
    )
    rows = _query_neo4j(cypher, {"name": disease_name})
    if not rows:
        return []
    rels = rows[0].get("rels") or []
    return [r for r in rels if r.get("type") and r.get("target")][:limit]


def _neo4j_kg(crop: str, query: str, top_k: int = 3) -> dict[str, Any]:
    """Build AgriKG-backed triples/rules/diseases. Raises nothing; caller merges."""
    candidates = _neo4j_disease_candidates(crop, query, top_k)
    crop_zh = _normalize_crop(crop)
    triples: list[dict[str, str]] = []
    triple_strings: list[str] = []
    rules: list[str] = []

    for cand in candidates:
        name = cand["disease"]
        if crop_zh:
            triples.append({"subject": crop_zh, "relation": "易感(AgriKG)", "object": name})
        for rel in _neo4j_disease_relations(name):
            triples.append({"subject": name, "relation": rel["type"], "object": rel["target"]})
        for item in cand["base_info"][:4]:
            key, value = item["key"], item["value"]
            if any(tag in key for tag in ("症状", "为害", "表现")):
                triples.append({"subject": name, "relation": "症状(AgriKG)", "object": value[:40]})
            elif any(tag in key for tag in ("防治", "药", "治疗", "处理")):
                rules.append(f"{name}（AgriKG·{key}）：{value[:50]}")
            elif _metric_key(key):
                rules.append(f"{name}（AgriKG·{key}）：{value[:50]}")

    triple_strings = [f"({t['subject']})-[{t['relation']}]->({t['object']})" for t in triples]
    return {
        "diseases": [cand["disease"] for cand in candidates],
        "triples": triples,
        "triple_strings": triple_strings,
        "rules": rules,
        "neo4j_hits": len(candidates),
    }


# ============================================================
# 统一检索接口
# ============================================================


def _get_backend() -> str:
    backend = os.environ.get("AGRI_AI_KG_BACKEND", "auto").strip().lower()
    if backend not in {"auto", "neo4j", "memory"}:
        return "auto"
    return backend


def _merge(memory: dict[str, Any], neo: dict[str, Any]) -> dict[str, Any]:
    """Merge AgriKG triples/diseases/rules on top of the memory baseline.

    Memory diseases stay first so the pathology claim (sourced from DISEASE_DB)
    still matches for the Judge's KG consistency check; AgriKG only adds breadth.
    Hard constraints stay from memory (structured, reliable veto source).
    """
    diseases = list(memory.get("diseases", []))
    for name in neo.get("diseases", []):
        if name not in diseases:
            diseases.append(name)

    seen = {(t.get("subject"), t.get("relation"), t.get("object")) for t in memory.get("triples", [])}
    triples = list(memory.get("triples", []))
    for triple in neo.get("triples", []):
        key = (triple.get("subject"), triple.get("relation"), triple.get("object"))
        if key not in seen:
            seen.add(key)
            triples.append(triple)

    triple_strings = [f"({t['subject']})-[{t['relation']}]->({t['object']})" for t in triples]

    rules = list(memory.get("rules", []))
    for rule in neo.get("rules", []):
        if rule not in rules:
            rules.append(rule)

    merged = dict(memory)
    merged.update(
        {
            "diseases": diseases,
            "triples": triples,
            "triple_strings": triple_strings[:24],
            "rules": rules[:10],
            "hard_constraints": memory.get("hard_constraints", []),
        }
    )
    return merged


def query_kg(crop: str = "", query: str = "", top_k: int = 3) -> dict[str, Any]:
    """Build KG triples, reference rules and hard constraints for the Judge.

    Prefers Neo4j + AgriKG when available; otherwise synthesizes from DISEASE_DB.
    The returned dict always carries a ``backend`` field (``neo4j`` | ``memory``
    | ``fallback``) and a ``neo4j_connected`` flag for traceability.
    """
    memory = _memory_kg(crop, query, top_k)
    backend = _get_backend()

    if backend == "memory":
        memory["backend"] = "memory"
        memory["neo4j_connected"] = False
        return memory

    connected = _neo4j_available()
    if backend == "neo4j" and not connected:
        memory["backend"] = "fallback"
        memory["neo4j_connected"] = False
        memory["error"] = "AGRI_AI_KG_BACKEND=neo4j but Neo4j not reachable"
        return memory

    if not connected:
        memory["backend"] = "memory"
        memory["neo4j_connected"] = False
        return memory

    # Neo4j is reachable: enrich the memory baseline with real AgriKG triples.
    try:
        neo = _neo4j_kg(crop, query, top_k)
    except Exception as exc:
        memory["backend"] = "fallback"
        memory["neo4j_connected"] = True
        memory["error"] = str(exc)
        return memory

    if not neo.get("diseases"):
        memory["backend"] = "fallback"
        memory["neo4j_connected"] = True
        memory["error"] = "Neo4j reachable but no AgriKG disease hits"
        return memory

    merged = _merge(memory, neo)
    merged["backend"] = "neo4j"
    merged["neo4j_connected"] = True
    merged["neo4j_hits"] = neo.get("neo4j_hits", 0)
    return merged


def kg_status() -> dict[str, Any]:
    """Report KG backend configuration and connectivity (for CLI / debugging)."""
    backend = _get_backend()
    connected = _neo4j_available()
    return {
        "backend_requested": backend,
        "neo4j_connected": connected,
        "neo4j_uri": NEO4J_URI,
        "effective_backend": "neo4j" if (backend in {"auto", "neo4j"} and connected) else "memory",
        "mode": "neo4j" if connected else "memory",
        "note": "" if connected else "Neo4j 未连接，将使用 DISEASE_DB 记忆后端（离线可用）。",
    }


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Agri AI KG adapter smoke test")
    parser.add_argument("--crop", default="tomato")
    parser.add_argument("--query", default="叶片黄斑，叶背灰色霉层")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--status", action="store_true", help="print KG backend status and exit")
    args = parser.parse_args()

    if args.status:
        print(json.dumps(kg_status(), ensure_ascii=False, indent=2))
        return

    result = query_kg(args.crop, args.query, args.top_k)
    print(f"backend: {result.get('backend')}  neo4j_connected: {result.get('neo4j_connected')}")
    if result.get("error"):
        print(f"note: {result['error']}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
