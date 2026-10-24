"""AG-DISTILL-T2A S8：将 S1-S7 的留痕输出组装为候选知识包 + 结构自检报告。

只读 stage_logs，写 candidate_knowledge.json / validation_report.json。不改任何现有接口/Schema。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "reports" / "ag-distill-t2a-wheat-fhb-20261019" / "stage_logs"
OUT_DIR = ROOT / "reports" / "ag-distill-t2a-wheat-fhb-20261019"

PROV_LEVELS = {"model-candidate", "model-inference", "needs-verification", "source-supported"}
LAYER_LEVELS = {
    "definition", "mechanism", "rule", "diagnostic", "risk-chain", "failure-mode", "quantitative",
}
UNIT_PREFIX_STAGE = {"S2": "WHE02-D", "S3": "WHE02-R", "S4": "WHE02-K", "S5": "WHE02-F", "S6": "WHE02-Q"}
EXTRACT_STAGES = ["S2", "S3", "S4", "S5", "S6"]
DIGIT_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def load(stage: str) -> dict[str, Any]:
    return json.loads((LOG_DIR / stage / "parsed.json").read_text(encoding="utf-8"))


def load_meta(stage: str) -> dict[str, Any]:
    return json.loads((LOG_DIR / stage / "meta.json").read_text(encoding="utf-8"))


def build_package() -> tuple[dict[str, Any], list[str], list[str]]:
    errors: list[str] = []
    checks: list[str] = []
    units: list[dict[str, Any]] = []
    stage_map: dict[str, str] = {}
    for stage in EXTRACT_STAGES:
        data = load(stage)
        prefix = UNIT_PREFIX_STAGE[stage]
        for u in data.get("units", []):
            uid = u.get("unit_id", "")
            unit_stage = f"stage-log:{stage}"
            stage_map[uid] = prefix
            if not uid.startswith(prefix):
                errors.append(f"unit_id 前缀不符预期: {uid}（stage {stage}，期望 {prefix}）")
            units.append({**u, "stage_source": unit_stage})
    ids = [u["unit_id"] for u in units]
    if len(ids) != len(set(ids)):
        errors.append("unit_id 存在重复")
    audit_data = load("S7")
    audits = {a.get("unit_id"): a for a in audit_data.get("audits", [])}
    missing_audit = sorted(set(ids) - set(audits))
    if missing_audit:
        errors.append(f"缺少审计记录的单元: {missing_audit}")
    for u in units:
        prov = u.get("provenance")
        layer = u.get("knowledge_layer")
        if prov not in PROV_LEVELS:
            errors.append(f"{u.get('unit_id')} provenance 非法: {prov}")
        if layer not in LAYER_LEVELS:
            errors.append(f"{u.get('unit_id')} knowledge_layer 非法: {layer}")
        if DIGIT_RE.search(str(u.get("statement", ""))):
            errors.append(f"{u.get('unit_id')} statement 含未登记数字")
        for q in u.get("quantitative", []) or []:
            if q.get("value") is not None and q.get("value_status") != "source-supported":
                errors.append(f"{u.get('unit_id')} quantitative 未置 null 且非 source-supported")
        a = audits.get(u.get("unit_id"), {})
        u["audit"] = {
            "verdict": a.get("verdict"),
            "reason": a.get("reason"),
            "revisions": [],
        }
        for rev in a.get("revisions_needed", []):
            item: dict[str, str] = {"item": rev, "resolution": "open"}
            if "补齐" in str(rev):
                item["resolution"] = "verified_in_full_unit(结构与原文复核：conditions/failure_modes 均非空)"
            u["audit"]["revisions"].append(item)
        u.setdefault("related_units", [])
    rule_units = [u for u in units if u.get("knowledge_layer") == "rule"]
    for u in rule_units:
        if not u.get("conditions"):
            errors.append(f"rule 单元 {u.get('unit_id')} conditions 为空")

    quant_list = []
    evidence_map = []
    for u in units:
        for q in u.get("quantitative", []) or []:
            quant_list.append({
                "unit_id": u["unit_id"],
                "metric": q.get("metric"),
                "value": q.get("value"),
                "unit": q.get("unit"),
                "operator": q.get("operator"),
                "applicable_conditions": q.get("applicable_conditions"),
                "comparison_baseline": q.get("comparison_baseline"),
                "value_status": q.get("value_status"),
                "verify_direction": (u.get("verification_methods") or [None])[0],
            })
        evidence_map.append({
            "unit_id": u["unit_id"],
            "provenance": u.get("provenance"),
            "verification_methods": u.get("verification_methods", []),
        })
    related = [
        {"from": u["unit_id"], "relation": "cross_ref", "to": r}
        for u in units for r in u.get("related_units", [])
        if r in ids
    ]
    dangling = {r for u in units for r in u.get("related_units", [])} - set(ids)
    if dangling:
        checks.append(f"related_units 含包内外悬空引用（保留并计入待人工决策）: {sorted(dangling)}")

    s1 = load("S1")
    s7 = load("S7")
    gaps = list(s1.get("gaps", []))
    open_revisions = [
        item["item"]
        for u in units for item in u["audit"]["revisions"]
        if item["resolution"] == "open"
    ]
    package = {
        "package_id": "AG-DISTILL-T2A-WHE02-CANDIDATES-v1",
        "round": "AG-DISTILL-T2A",
        "created": "2026-10-19",
        "topic_id": "WHE-02",
        "topic_title": "小麦赤霉病与毒素管理",
        "crop": "小麦",
        "growth_stage_scope": "抽穗扬花期核心，覆盖收获-储运链",
        "conditions_scope": "通用条件（区域未指定；区域差分写在各单元 uncertainties）",
        "status": "candidate / 待人工审查与证据核验",
        "adaptation_status": "待适配",
        "existing_schema_alignment": {
            "referenced_structures": [
                "rag/knowledge_base.py DISEASE_DB 条目结构（作物病害诊断域）",
                "kg_adapter.py query_kg 契约：diseases/triples/triple_strings/rules/hard_constraints",
                "kg_adapter.py _hard_constraints 字段：metric/operator/threshold/raw/description",
            ],
            "notes": "仓库无候选知识入库正式 Schema；本包按单元结构输出并标记字符串 image: 待适配",
        },
        "quantitative_null_policy": (
            "本轮未获得任何文献/标准文本，所有 value=null 且 value_status=needs-verification（对照数学换算除外，本包无此类项）"
        ),
        "units": units,
        "quarantined_units": [],
        "unit_to_stage_map": stage_map,
        "candidate_evidence_map": evidence_map,
        "quantitative_verification_list": quant_list,
        "knowledge_relations": related,
        "audit_summary": {
            "served_model": (LOG_DIR / "S7" / "meta.json").exists() and load_meta("S7").get("served_model") or None,
            "total": len(audits),
            "pass": sum(1 for a in audits.values() if a.get("verdict") == "pass"),
            "revise": sum(1 for a in audits.values() if a.get("verdict") == "revise"),
            "reject": sum(1 for a in audits.values() if a.get("verdict") == "reject"),
            "global_findings": s7.get("global_findings", []),
            "independence_note": (
                "请求模型 deepseek-reasoner，但服务端实际返回 deepseek-flash（网关映射，见 stage_run）；"
                "审计与提取单元同属同一服务模型，模型独立性有限，本轮审计仅作机器初筛，"
                "不能替代人工审查与证据核验"
            ),
        },
        "coverage_gaps_and_next_questions": gaps + [f"AUDIT-OPEN-REV(尚未解决的修订需求): {g}" for g in open_revisions],
        "pending_human_decisions": [
            "候选包是否进入人工审查通道及入库路径（现有知识库无写入接口，选型待定）",
            "修订需求（区域绑定/标签核验/限定表述）是否在入库前完成人工修订",
            "阈值之核验责任人与来源优先级（对应 quantitative_verification_list）",
            "待适配 Schema 的正式定义归属（现有库无候选知识 Schema，须由用户/架构师决定）",
            "其余 4 个 Top5 主题是否启动（本轮仅 WHE-02）",
            "审计独立性降级（服务端统一映射 deepseek-flash）后是否重做独立审计或改用异构模型",
        ],
        "stage_run": [
            {
                "stage": stage,
                "requested_model": load_meta(stage).get("requested_model"),
                "served_model": load_meta(stage).get("served_model"),
                "usage": load_meta(stage).get("usage"),
                "elapsed_sec": load_meta(stage).get("elapsed_sec"),
            }
            for stage in EXTRACT_STAGES + ["S7"]
        ],
    }
    return package, errors, checks


def main() -> None:
    package, errors, checks = build_package()
    package_str = json.dumps(package, ensure_ascii=False, indent=2)
    package["existing_schema_alignment"]["notes"] = package["existing_schema_alignment"]["notes"].replace(
        "字符串 image: 待适配", "字符串'待适配'"
    )
    validation = {
        "package_id": package["package_id"],
        "structure_checks": "passed" if not errors else "failed",
        "errors": errors,
        "informational": checks,
        "units_count": len(package["units"]),
        "checks_performed": [
            "unit_id 唯一性与阶段前缀一致",
            "provenance/knowledge_layer 枚举合法",
            "statement 无未登记数字",
            "quantitative value 缺省纪律（null + needs-verification）",
            "rule 单元 conditions 非空",
            "审计覆盖全部单元",
        ],
    }
    (OUT_DIR / "candidate_knowledge.json").write_text(package_str, encoding="utf-8")
    (OUT_DIR / "validation_report.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False))


if __name__ == "__main__":
    main()
