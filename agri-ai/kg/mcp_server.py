"""
知识图谱 MCP Server — 基于 Neo4j + AgriKG 的农业知识图谱查询

替代原来的硬编码 JSON 知识库。

数据来源：qq547276542/Agriculture_KnowledgeGraph（AgriKG）
导入脚本：scripts/import_agrikg.py

真实图谱 schema（由 import_agrikg.py 导入）：
  节点 :HudongItem {title, detail, url, image, openTypeList,
                    baseInfoKeyList, baseInfoValueList}
  节点 :NewNode {title}
  标签 :Disease / :Pest（导入时按标题关键词为部分 HudongItem 追加）
  关系 (:HudongItem|:NewNode)-[:RELATION {type}]->(:HudongItem|:NewNode)

需要安装：pip install neo4j
需要运行：Neo4j 数据库（默认 bolt://localhost:7687），并已导入 AgriKG 数据
"""

import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agri-knowledge-graph")

# ============================================================
# Neo4j 连接配置
# ============================================================

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "agriai2026")

_driver = None


def _get_driver():
    """懒加载 Neo4j 驱动"""
    global _driver
    if _driver is not None:
        return _driver
    try:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        return _driver
    except Exception:
        return None


def _neo4j_available() -> bool:
    """检查 Neo4j 是否可连接"""
    driver = _get_driver()
    if driver is None:
        return False
    try:
        with driver.session() as session:
            session.run("RETURN 1")
            return True
    except Exception:
        return False


def _query_neo4j(cypher: str, params: dict = None) -> list:
    """执行 Cypher 查询并返回结果"""
    driver = _get_driver()
    if driver is None:
        return []
    try:
        with driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]
    except Exception:
        return []


# ============================================================
# 备用数据（Neo4j 不可用时使用）
# 与 knowledge_mcp_server.py 的 DISEASE_DB 结构一致
# ============================================================

FALLBACK_DISEASES = {
    "tomato_leaf_mold": {
        "name": "番茄叶霉病",
        "crop": "番茄",
        "pathogen": "黄枝孢霉",
        "symptoms": ["叶片正面淡黄色病斑", "背面灰紫色绒状霉层", "叶片卷曲"],
        "conditions": {"temperature": "20-25℃", "humidity": ">85%"},
        "treatment": ["加强通风", "多菌灵500倍液喷施", "甲基托布津800倍液"],
    },
    "tomato_blight": {
        "name": "番茄早疫病",
        "crop": "番茄",
        "pathogen": "茄链格孢",
        "symptoms": ["同心轮纹状病斑", "褐色边缘", "灰白色中央"],
        "conditions": {"temperature": "25-30℃", "humidity": ">80%"},
        "treatment": ["百菌清600倍液", "杀毒矾500倍液", "轮作倒茬"],
    },
    "cucumber_downy_mildew": {
        "name": "黄瓜霜霉病",
        "crop": "黄瓜",
        "pathogen": "古巴假霜霉",
        "symptoms": ["叶片正面黄色褪绿斑块", "背面灰黑色霉层", "多角形病斑"],
        "conditions": {"temperature": "15-22℃", "humidity": ">90%"},
        "treatment": ["霜脲锰锌600倍液", "烯酰吗啉800倍液", "膜下滴灌控湿"],
    },
}

CROP_MAP = {
    "tomato": "番茄", "cucumber": "黄瓜", "rice": "水稻", "wheat": "小麦",
    "corn": "玉米", "maize": "玉米", "grape": "葡萄", "apple": "苹果",
    "pepper": "辣椒", "eggplant": "茄子", "potato": "马铃薯",
}

CROPS = ["番茄", "黄瓜", "水稻", "小麦", "玉米", "葡萄", "苹果", "柑橘",
         "白菜", "辣椒", "茄子", "马铃薯", "棉花", "大豆", "茶", "梨",
         "桃", "草莓", "西瓜", "甜瓜"]

SYMPTOM_KEYWORDS = ["黄斑", "霉", "斑", "枯", "烂", "卷", "轮纹", "多角",
                    "水渍", "褐", "灰", "萎蔫", "白粉", "锈", "斑点", "落叶",
                    "畸形", "腐烂", "坏死"]


def _crop_zh(crop: str) -> str:
    if not crop:
        return ""
    return CROP_MAP.get(crop.lower(), crop)


def _guess_crop(title: str) -> str:
    for c in CROPS:
        if c in title:
            return c
    return ""


def _parse_base_info(keys_str, vals_str) -> list:
    """把互动百科的 baseInfoKeyList/baseInfoValueList（## 分隔）解析为 [{key,value}]"""
    keys = [k.strip().rstrip("：:").strip()
            for k in (keys_str or "").split("##") if k.strip()]
    vals = [v.strip() for v in (vals_str or "").split("##") if v.strip()]
    pairs = []
    for i, k in enumerate(keys):
        v = vals[i] if i < len(vals) else ""
        if k:
            pairs.append({"key": k, "value": v})
    return pairs


def _get_disease_base(disease_name: str) -> list:
    rows = _query_neo4j(
        "MATCH (d:Disease {title: $name}) "
        "RETURN d.baseInfoKeyList AS bk, d.baseInfoValueList AS bv",
        {"name": disease_name},
    )
    if rows:
        return _parse_base_info(rows[0].get("bk"), rows[0].get("bv"))
    return []


def _fallback_search_disease(symptoms: str, crop: str = "") -> list:
    """Neo4j 不可用时的降级搜索"""
    crop_zh = _crop_zh(crop)
    results = []
    for disease in FALLBACK_DISEASES.values():
        if crop_zh and crop_zh not in disease["crop"]:
            continue
        score = 0
        matched = []
        for symptom in disease["symptoms"]:
            for word in SYMPTOM_KEYWORDS:
                if word in symptoms and word in symptom:
                    score += 1
                    if symptom not in matched:
                        matched.append(symptom)
                    break
        if score > 0:
            results.append({
                "disease": disease["name"],
                "crop": disease["crop"],
                "score": score,
                "matched_symptoms": matched,
                "treatment": disease["treatment"],
                "conditions": disease["conditions"],
                "source": "fallback",
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]


# ============================================================
# MCP Tools —— 病害相关（保留原工具名以兼容上层）
# ============================================================

@mcp.tool()
def search_disease(symptoms: str, crop: str = "") -> list:
    """根据症状搜索可能的病害。

    Args:
        symptoms: 症状描述（如 叶片黄斑、叶背灰色霉层）
        crop: 作物名称，可选（tomato/番茄 均可）
    """
    if _neo4j_available():
        crop_zh = _crop_zh(crop)
        cypher = (
            "MATCH (d:Disease) "
            "WHERE ($crop = '' OR d.title CONTAINS $crop OR d.detail CONTAINS $crop) "
            "RETURN d.title AS disease, d.detail AS detail, "
            "d.baseInfoKeyList AS bkeys, d.baseInfoValueList AS bvals "
            "LIMIT 300"
        )
        rows = _query_neo4j(cypher, {"crop": crop_zh})
        scored = []
        for r in rows:
            text = (r.get("detail") or "") + " " + (r.get("bvals") or "")
            score = 0
            matched = []
            for kw in SYMPTOM_KEYWORDS:
                if kw in symptoms and kw in text:
                    score += 1
                    matched.append(kw)
            if crop_zh and crop_zh in (r.get("disease") or ""):
                score += 1
            if score > 0:
                scored.append({
                    "disease": r["disease"],
                    "crop": crop_zh or _guess_crop(r["disease"]),
                    "score": score,
                    "matched_symptoms": matched,
                    "detail": (r.get("detail") or "")[:120],
                    "source": "neo4j",
                })
        if scored:
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:5]
    return _fallback_search_disease(symptoms, crop)


@mcp.tool()
def get_disease_chain(disease_name: str) -> dict:
    """查询病害的完整信息：详情、属性(base info)、关系邻居。

    Args:
        disease_name: 病害名称（如 葡萄蔓枯病）
    """
    if not _neo4j_available():
        for disease in FALLBACK_DISEASES.values():
            if disease_name in disease["name"]:
                return {
                    "disease": disease["name"], "crop": disease["crop"],
                    "symptoms": disease["symptoms"], "pathogen": disease["pathogen"],
                    "conditions": disease["conditions"], "treatment": disease["treatment"],
                    "source": "fallback",
                }
        return {"error": "Neo4j not available",
                "note": "请先启动 Neo4j 并导入 AgriKG 数据",
                "known_diseases": list(FALLBACK_DISEASES.keys())}

    cypher = (
        "MATCH (d:Disease {title: $name}) "
        "OPTIONAL MATCH (d)-[r:RELATION]->(e) "
        "RETURN d.title AS disease, d.detail AS detail, "
        "d.baseInfoKeyList AS bkeys, d.baseInfoValueList AS bvals, "
        "collect({type: r.type, target: e.title}) AS rels"
    )
    rows = _query_neo4j(cypher, {"name": disease_name})
    if rows:
        r = rows[0]
        rels = [x for x in (r.get("rels") or []) if x.get("type")]
        return {
            "disease": r["disease"],
            "detail": r.get("detail") or "",
            "base_info": _parse_base_info(r.get("bkeys"), r.get("bvals")),
            "relations": rels,
            "source": "neo4j",
        }
    return {"error": "未知病害: " + disease_name}


@mcp.tool()
def list_crop_diseases(crop_name: str) -> list:
    """查询某种作物可能有的所有病害。

    Args:
        crop_name: 作物名称（如 番茄、黄瓜、水稻、葡萄）
    """
    crop_zh = _crop_zh(crop_name)
    if _neo4j_available():
        cypher = (
            "MATCH (d:Disease) "
            "WHERE d.title CONTAINS $crop OR d.detail CONTAINS $crop "
            "RETURN d.title AS disease LIMIT 80"
        )
        rows = _query_neo4j(cypher, {"crop": crop_zh})
        if rows:
            return [{"disease": r["disease"], "crop": crop_zh} for r in rows]
    return [{"disease": d["name"], "crop": d["crop"]}
            for d in FALLBACK_DISEASES.values() if crop_zh in d["crop"]]


@mcp.tool()
def search_pesticide(disease_name: str) -> list:
    """查询与某种病害相关的防治/药剂信息。

    AgriKG 没有结构化农药节点，这里返回该病害 RELATION 邻居中与防治/药剂相关
    的条目，以及 base info 中的防治字段。

    Args:
        disease_name: 病害名称
    """
    if not _neo4j_available():
        for d in FALLBACK_DISEASES.values():
            if disease_name in d["name"]:
                return d["treatment"]
        return []

    cypher = (
        "MATCH (d:Disease {title: $name})-[r:RELATION]->(e) "
        "WHERE r.type CONTAINS '防治' OR r.type CONTAINS '药' OR r.type CONTAINS '治疗' "
        "OR e.title CONTAINS '药' OR e.title CONTAINS '剂' "
        "RETURN e.title AS name, r.type AS relation"
    )
    rows = _query_neo4j(cypher, {"name": disease_name})
    result = [{"pesticide": r["name"], "relation": r["relation"]} for r in rows]
    for item in _get_disease_base(disease_name):
        if any(k in item["key"] for k in ("防治", "药", "治疗", "处理")):
            result.append({"pesticide": item["value"], "relation": item["key"]})
    if result:
        return result
    for d in FALLBACK_DISEASES.values():
        if disease_name in d["name"]:
            return d["treatment"]
    return []


@mcp.tool()
def search_by_conditions(temperature: float = None, humidity: float = None) -> list:
    """根据环境条件查询可能的病害。

    注意：AgriKG 不含结构化温湿度字段，该工具始终返回备用规则库的匹配结果。

    Args:
        temperature: 当前温度（℃）
        humidity: 当前湿度（%）
    """
    results = []
    for d in FALLBACK_DISEASES.values():
        cond = d.get("conditions", {})
        match = True
        if temperature:
            t = str(cond.get("temperature", ""))
            if "20-25" in t and (temperature < 18 or temperature > 27):
                match = False
            if "25-30" in t and (temperature < 23 or temperature > 32):
                match = False
            if "15-22" in t and (temperature < 13 or temperature > 24):
                match = False
        if match:
            results.append({"disease": d["name"], "crop": d["crop"],
                            "conditions": cond, "source": "fallback"})
    return results


@mcp.tool()
def get_kg_status() -> dict:
    """获取知识图谱连接状态与规模"""
    available = _neo4j_available()
    status = {
        "neo4j_connected": available,
        "neo4j_uri": NEO4J_URI,
        "fallback_available": True,
        "mode": "neo4j" if available else "fallback",
    }
    if available:
        nodes = _query_neo4j(
            "MATCH (n) UNWIND labels(n) AS lb "
            "RETURN lb AS label, count(*) AS cnt"
        )
        rels = _query_neo4j(
            "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS cnt"
        )
        status["nodes"] = {n["label"]: n["cnt"] for n in nodes}
        status["relationships"] = {r["t"]: r["cnt"] for r in rels}
        status["schema"] = "HudongItem / NewNode / Disease / Pest + [:RELATION {type}]"
        status["note"] = ""
    else:
        status["note"] = "Neo4j 未连接。请启动 Neo4j 并运行 scripts/import_agrikg.py 导入 AgriKG 数据。"
    return status


# ============================================================
# MCP Tools —— 通用知识图谱检索（AgriKG 原生能力）
# ============================================================

@mcp.tool()
def search_entity(title: str) -> list:
    """按名称(模糊)搜索知识图谱中的实体。

    Args:
        title: 实体名称或关键词
    """
    if not _neo4j_available():
        return [{"error": "Neo4j not available"}]
    cypher = (
        "MATCH (n) WHERE (n:HudongItem OR n:NewNode) AND n.title CONTAINS $title "
        "RETURN labels(n) AS labels, n.title AS title, "
        "n.detail AS detail, n.baseInfoKeyList AS bk, n.baseInfoValueList AS bv "
        "LIMIT 10"
    )
    rows = _query_neo4j(cypher, {"title": title})
    out = []
    for r in rows:
        out.append({
            "title": r["title"],
            "labels": r.get("labels") or [],
            "detail": (r.get("detail") or "")[:200],
            "base_info": _parse_base_info(r.get("bk"), r.get("bv")),
        })
    return out


@mcp.tool()
def get_entity_relations(title: str) -> dict:
    """查询某个实体的出入关系邻居。

    Args:
        title: 实体名称（精确匹配）
    """
    if not _neo4j_available():
        return {"error": "Neo4j not available"}
    cypher = (
        "MATCH (n) WHERE (n:HudongItem OR n:NewNode) AND n.title = $title "
        "OPTIONAL MATCH (n)-[r1:RELATION]->(out) "
        "OPTIONAL MATCH (inn)-[r2:RELATION]->(n) "
        "RETURN n.title AS title, labels(n) AS labels, "
        "collect(DISTINCT {type: r1.type, target: out.title}) AS out_rels, "
        "collect(DISTINCT {type: r2.type, source: inn.title}) AS in_rels"
    )
    rows = _query_neo4j(cypher, {"title": title})
    if not rows:
        return {"error": "未找到实体: " + title}
    r = rows[0]
    out_rels = [x for x in (r.get("out_rels") or []) if x.get("type")]
    in_rels = [x for x in (r.get("in_rels") or []) if x.get("type")]
    return {"title": r["title"], "labels": r.get("labels") or [],
            "out_relations": out_rels, "in_relations": in_rels}


@mcp.tool()
def find_entity_path(entity1: str, entity2: str) -> dict:
    """查询两个实体之间通过 RELATION 连接的最短路径(最多 6 跳)。

    Args:
        entity1: 起始实体名称
        entity2: 目标实体名称
    """
    if not _neo4j_available():
        return {"error": "Neo4j not available"}
    cypher = (
        "MATCH (a), (b) "
        "WHERE a.title = $e1 AND b.title = $e2 "
        "AND (a:HudongItem OR a:NewNode) AND (b:HudongItem OR b:NewNode) "
        "MATCH p = shortestPath((a)-[:RELATION*..6]-(b)) "
        "RETURN [n IN nodes(p) | n.title] AS path, "
        "[r IN relationships(p) | r.type] AS rels"
    )
    rows = _query_neo4j(cypher, {"e1": entity1, "e2": entity2})
    if not rows:
        return {"error": "未找到路径（实体不存在或超过 6 跳）",
                "entity1": entity1, "entity2": entity2}
    r = rows[0]
    return {"path": r.get("path") or [], "relations": r.get("rels") or []}


# ============================================================
# MCP Resource
# ============================================================

@mcp.resource("knowledge://diseases")
def list_diseases() -> str:
    """所有可查询病害的概览"""
    if _neo4j_available():
        rows = _query_neo4j("MATCH (d:Disease) RETURN d.title AS name LIMIT 100")
        if rows:
            lines = ["=== 知识图谱中的病害（AgriKG） ===", ""]
            for r in rows:
                lines.append("• " + r["name"])
            return "\n".join(lines)

    lines = ["=== 备用数据库中的病害 ===", ""]
    for d in FALLBACK_DISEASES.values():
        lines.append("• " + d["name"] + " (" + d["crop"] + ")")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()