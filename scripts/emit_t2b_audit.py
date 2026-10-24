"""Emit AG-DISTILL-T2B audit products (claim_audit.csv + audit_manifest.json)."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PKG_PATH = ROOT / "reports" / "ag-distill-t2a-wheat-fhb-20261019" / "candidate_knowledge.json"
FINDINGS_PATH = ROOT / "reports" / "ag-distill-t2b-wheat-fhb-audit" / "audit_findings.json"
OUT_DIR = ROOT / "reports" / "ag-distill-t2b-wheat-fhb-audit"
CSV_PATH = OUT_DIR / "claim_audit.csv"
MANIFEST_PATH = OUT_DIR / "audit_manifest.json"

CSV_FIELDS = {
    "audit_id": "id",
    "candidate_id": "unit_id",
    "class": "class",
    "claim_excerpt": "claim",
    "audit_category": "category",
    "issue": "issue",
    "evidence_status": "evidence_status",
    "severity": "severity",
    "recommended_action": "action",
    "needs_external_source": "ext_src",
    "needs_human_approval": "human_appr",
    "t2a_revise_ref": "t2a_ref",
}

VALID_SEVERITY = {"P0", "P1", "P2", "P3", "none"}

T2A_REVISED_UNITS = [
    "WHE02-D-03",
    "WHE02-D-09",
    "WHE02-R-01",
    "WHE02-R-02",
    "WHE02-R-03",
    "WHE02-R-04",
    "WHE02-R-05",
    "WHE02-R-06",
    "WHE02-R-07",
    "WHE02-R-08",
    "WHE02-F-02",
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_checks(rows: list[dict[str, Any]], unit_ids: list[str]) -> dict[str, Any]:
    errors: list[str] = []
    ids = [str(row["id"]) for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate audit ids")
    for row in rows:
        if str(row["severity"]) not in VALID_SEVERITY:
            errors.append(f"invalid severity: {row['id']}")
        for flag in ("ext_src", "human_appr"):
            if not isinstance(row[flag], bool):
                errors.append(f"invalid {flag}: {row['id']}")
    unit_set = set(unit_ids)
    referenced: set[str] = set()
    for row in rows:
        uid = str(row["unit_id"])
        if uid.startswith("GLOBAL-"):
            continue
        if uid not in unit_set:
            errors.append(f"unknown unit: {uid}")
            continue
        referenced.add(uid)
    missing = sorted(unit_set - referenced)
    if missing:
        errors.append(f"units without finding row: {missing}")
    mapping: dict[str, list[str]] = {}
    for target in T2A_REVISED_UNITS:
        suffix = target.replace("WHE02-", "")
        hit = [str(row["id"]) for row in rows if str(row.get("t2a_ref") or "").startswith(suffix)]
        if not hit:
            errors.append(f"T2A revise item unmapped: {target}")
        mapping[target] = hit
    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row["severity"])] = counts.get(str(row["severity"]), 0) + 1
    return {"errors": errors, "units_total": len(unit_ids), "units_covered": len(unit_set & referenced),
            "revise_mapping": mapping, "severity_counts": counts}


def main() -> int:
    package = load_json(PKG_PATH)
    findings_doc = load_json(FINDINGS_PATH)
    rows = list(findings_doc["rows"])
    unit_ids = [str(u["unit_id"]) for u in package.get("units", [])]
    checks = run_checks(rows, unit_ids)

    if checks["errors"]:
        for err in checks["errors"]:
            print(f"[FAIL] {err}")
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(CSV_FIELDS.keys()))
        for row in rows:
            writer.writerow([row[src] for src in CSV_FIELDS.values()])

    manifest = {
        "audit_id": "AG-DISTILL-T2B-AUDIT-001",
        "round": "AG-DISTILL-T2B",
        "date": "2026-10-19",
        "audited_package": {
            "path": str(PKG_PATH.relative_to(ROOT)),
            "package_id": package["package_id"],
            "created": package["created"],
            "unit_count": len(unit_ids),
            "sha256": sha256_file(PKG_PATH),
        },
        "t2a_stage_logs": {
            "path": "reports/ag-distill-t2a-wheat-fhb-20261019/stage_logs",
            "note": "本轮未修改任何 T2A 原始日志",
        },
        "auditor": {
            "type": "agent-review",
            "persona": "opencode agent（GLM）逐单元 LLM 复核",
            "heterogeneous_model_audit_available": False,
            "probe": {
                "requested": ["deepseek-chat", "deepseek-reasoner"],
                "served": ["deepseek-flash", "deepseek-flash"],
                "conclusion": "教师 API 统一路由 deepseek-flash，异构模型审计不可用，已登记阻塞",
            },
            "disclaimers": [
                "本轮复核不得宣称独立模型审计",
                "agent 复核不构成外部证据，后续核验仍需真实文献/标准/登记资料或人工审计",
            ],
        },
        "risk_scale": {
            "P0": "已证实错误且直接导致错误决策的信息源",
            "P1": "实质性主张缺陷或合规类发布门禁（须修订+核验）",
            "P2": "边界/前提不明确或结构问题（可修订，部分需证据）",
            "P3": "措辞/数据规范/结构注记（低风险改进）",
        },
        "coverage": {
            "units_total": checks["units_total"],
            "units_covered": checks["units_covered"],
            "unit_classes": {"D": 10, "R": 8, "K": 5, "F": 7, "Q": 10},
        },
        "totals": {
            "rows": len(rows),
            "unit_level_rows": len(unit_ids),
            "global_rows": 4,
            "severity_counts": checks["severity_counts"],
        },
        "t2a_revise_mapping_status": f"{len(T2A_REVISED_UNITS)}/11 已映射",
        "t2a_revise_mapping": checks["revise_mapping"],
        "notations": [
            "AUD-T2B-029: WHE02-F-02 unit_id 前缀 F 与 knowledge_layer=rule 不一致，按任务要求不改分类，仅登记",
            "AUD-T2B-038: WHE02-Q-10 为 layer=quantitative 与 provenance=model-inference 的混合层，可接受，注记",
            "T2A 浓缩呈现的 R-01/R-04/R-08 '补齐 conditions/failure_modes' 已复核为完整单元非空（condensed-view 假象）",
        ],
        "outputs": [
            "reports/ag-distill-t2b-wheat-fhb-audit/claim_audit.csv",
            "reports/ag-distill-t2b-wheat-fhb-audit/audit_manifest.json",
            "reports/ag-distill-t2b-wheat-fhb-audit/audit_findings.json",
            "reports/ag-distill-t2b-wheat-fhb-audit/revision_queue.md",
            "reports/ag-distill-t2b-wheat-fhb-audit/evidence_gaps.md",
            "reports/ag-distill-t2b-wheat-fhb-audit/execution_report.md",
        ],
        "inputs_dumps": [
            "reports/ag-distill-t2b-wheat-fhb-audit/working/g1_D.json",
            "reports/ag-distill-t2b-wheat-fhb-audit/working/g2_R.json",
            "reports/ag-distill-t2b-wheat-fhb-audit/working/g3_K_F.json",
            "reports/ag-distill-t2b-wheat-fhb-audit/working/g4_Q.json",
        ],
    }
    manifest["audit_findings_sha256"] = sha256_file(FINDINGS_PATH)

    with MANIFEST_PATH.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"rows={len(rows)} units={checks['units_covered']}/{checks['units_total']} "
          f"sev={checks['severity_counts']} mapped={len(T2A_REVISED_UNITS)}/11")
    print("CSV + manifest emitted OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
