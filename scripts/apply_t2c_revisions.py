"""Apply AG-DISTILL-T2C minimal revisions to the WHE-02 candidate package.

Reads the T2A v1 package and the T2B audit findings, applies a fixed change
table (every change traceable to audit issue ids), performs structural
verification (only intended paths changed; no evidence-grade promotion; no
digits introduced), and emits the v2 package, a machine diff report and
revision_status.csv.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_PKG = ROOT / "reports" / "ag-distill-t2a-wheat-fhb-20261019" / "candidate_knowledge.json"
FINDINGS = ROOT / "reports" / "ag-distill-t2b-wheat-fhb-audit" / "audit_findings.json"
OUT_DIR = ROOT / "reports" / "ag-distill-t2c-wheat-fhb-revision"
V2_PATH = OUT_DIR / "candidate_knowledge_v2.json"
DIFF_PATH = OUT_DIR / "diff_report.json"
STATUS_PATH = OUT_DIR / "revision_status.csv"

DIGIT_RE = re.compile(r"[0-9]")
TEXT_APPEND_FIELDS = {"statement", "conditions", "failure_modes", "side_effects", "uncertainties"}

# --- change table (audit-issue-id traceable) ---------------------------------

REPLACEMENTS: list[dict[str, Any]] = [
    {
        "audit_ids": ["AUD-T2B-003", "AUD-T2B-004"],
        "unit_id": "WHE02-D-03",
        "field": "statement",
        "old": "镰刀菌侵染还可引起茎基腐和秆腐，表现为茎基部或茎秆褐变、输导组织坏死，与穗腐属同一病原复合体的不同侵染类型。",
        "new": "镰刀菌侵染还可引起茎基腐和秆腐，表现为茎基部或茎秆褐变、输导组织坏死；其与穗腐是否属同一病原复合体不作为本单元断言。",
        "reason": "复合体同一性主张过宽（P1）：移出主述，转为待核验问题；同时消除 statement 双主张（P3 原子性）",
    },
    {
        "audit_ids": ["AUD-T2B-010"],
        "unit_id": "WHE02-D-09",
        "field": "statement",
        "old": "赤霉病流行取决于菌源基数、花期降雨或高湿、以及感病品种三者叠加，任一条件缺失时流行程度显著降低。",
        "new": "赤霉病流行取决于菌源基数、花期降雨或高湿、以及感病品种三者叠加；关键条件缺失或弱化时流行程度通常明显降低，但不排除例外年份与替代路径，该边界待区域流行学数据核验。",
        "reason": "绝对化断言收敛为倾向性表述（P1），证据等级不升级",
    },
]

APPENDS: list[dict[str, Any]] = [
    {
        "audit_ids": ["AUD-T2B-003"],
        "unit_id": "WHE02-D-03",
        "field": "uncertainties",
        "item": "与穗腐是否属同一病原复合体的不同侵染类型：待区域病原分离数据核验；核验完成前不得主张三者复合体同一。",
        "reason": "被收敛的同一性主张以待核验形态保留",
    },
    {
        "audit_ids": ["AUD-T2B-010"],
        "unit_id": "WHE02-D-09",
        "field": "uncertainties",
        "item": "本单元不再使用逐项必然式表述；条件间替代关系与例外年份数据未核验。",
        "reason": "软化后声明的反例边界",
    },
    {
        "audit_ids": ["AUD-T2B-012"],
        "unit_id": "WHE02-R-01",
        "field": "conditions",
        "item": "适用前提：区域具备可用的流行预警或菌源监测信息；品种抽穗扬花不同步时统一时窗覆盖不全，须分批次判断。",
        "reason": "T2A 残余修订项：适用前提显式化（内容源自本单元 failure_modes 与 uncertainties，无新事实）",
    },
    {
        "audit_ids": ["AUD-T2B-014"],
        "unit_id": "WHE02-R-03",
        "field": "uncertainties",
        "item": "防治次数与补治间隔核验指向：现行登记标签与本地试验结果；核验前不得以模型常识填充数值。",
        "reason": "T2A 残余修订项：核定指向显式化",
    },
    {
        "audit_ids": ["AUD-T2B-015"],
        "unit_id": "WHE02-R-03",
        "field": "related_units",
        "item": "WHE02-R-08",
        "reason": "补治口径与扬花后递减边界互为约束（R-08 侧已含 R-03，本次补齐对称）",
    },
    {
        "audit_ids": ["AUD-T2B-016"],
        "unit_id": "WHE02-R-04",
        "field": "uncertainties",
        "item": "本单元不指定具体削减方式与操作参数，方式集合须按区域耕作制度条件化后另行核证。",
        "reason": "T2A 残余修订项：限定不具体化，防止引出无证据操作参数",
    },
    {
        "audit_ids": ["AUD-T2B-018"],
        "unit_id": "WHE02-R-06",
        "field": "uncertainties",
        "item": "区域绑定字段保持留空：本规则区域性强，适用范围须待区域降雨规律与品种生育期数据核验。",
        "reason": "T2A 残余修订项：区域绑定缺口记入 uncertainties",
    },
    {
        "audit_ids": ["AUD-T2B-020"],
        "unit_id": "WHE02-R-08",
        "field": "uncertainties",
        "item": "补治决策以扬花完成为定性衰减参照点，与补治口径规则互为边界约束；确切定量拐点未确定。",
        "reason": "T2A 残余修订项：定性边界落位（定量拐点保持待验证）",
    },
    {
        "audit_ids": ["AUD-T2B-026", "AUD-T2B-032", "AUD-T2B-038"],
        "unit_id": "WHE02-K-05",
        "field": "related_units",
        "item": "WHE02-D-10",
        "reason": "同族主张（症状-毒素独立）关系补链",
    },
    {
        "audit_ids": ["AUD-T2B-026", "AUD-T2B-032", "AUD-T2B-038"],
        "unit_id": "WHE02-K-05",
        "field": "related_units",
        "item": "WHE02-F-05",
        "reason": "同族主张（防效-毒素独立）关系补链",
    },
    {
        "audit_ids": ["AUD-T2B-026", "AUD-T2B-038"],
        "unit_id": "WHE02-K-05",
        "field": "related_units",
        "item": "WHE02-Q-10",
        "reason": "同族主张（两指标分测）关系补链",
    },
    {
        "audit_ids": ["AUD-T2B-032"],
        "unit_id": "WHE02-F-05",
        "field": "related_units",
        "item": "WHE02-K-05",
        "reason": "误合并失败模式与解耦知识单元互连",
    },
    {
        "audit_ids": ["AUD-T2B-032"],
        "unit_id": "WHE02-F-05",
        "field": "related_units",
        "item": "WHE02-D-10",
        "reason": "症状-毒素互替限制与误合并失败模式互连",
    },
    {
        "audit_ids": ["AUD-T2B-011"],
        "unit_id": "WHE02-D-10",
        "field": "related_units",
        "item": "WHE02-K-05",
        "reason": "同族主张补链（审计指定统一走关系补链条目）",
    },
    {
        "audit_ids": ["AUD-T2B-011"],
        "unit_id": "WHE02-D-10",
        "field": "related_units",
        "item": "WHE02-F-05",
        "reason": "同族主张补链",
    },
    {
        "audit_ids": ["AUD-T2B-028"],
        "unit_id": "WHE02-F-02",
        "field": "uncertainties",
        "item": "信息前提：花期天气预报与菌源监测不可得或不可靠时，本单元仅作定性参考，不得单独驱动放弃或维持防治的决策。",
        "reason": "T2A 残余修订项：不可操作情形限定（条件中信息可得性已有，此处补不可得时约束）",
    },
    {
        "audit_ids": ["AUD-T2B-038"],
        "unit_id": "WHE02-Q-10",
        "field": "related_units",
        "item": "WHE02-K-05",
        "reason": "防效-毒素分测主张与误合并知识互连",
    },
]

# --- dispositions for all 48 audit issues ------------------------------------

DISPOSITIONS: dict[str, dict[str, str]] = {
    "AUD-T2B-001": {"disposition": "deferred-p3", "change_summary": "-", "verification": "留待区域病原谱证据", "note": "P3 留待后续维护"},
    "AUD-T2B-002": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "十项重点复核通过", "note": ""},
    "AUD-T2B-003": {"disposition": "closed-direct", "change_summary": "D-03 statement 收敛（同一性移出主述）", "verification": "walk-diff 单路径变更 + 无数字断言", "note": "主张保持待核验，未升级证据"},
    "AUD-T2B-004": {"disposition": "closed-direct", "change_summary": "D-03 statement 重写消除双主张", "verification": "同上", "note": "随 P1 修正一并完成"},
    "AUD-T2B-005": {"disposition": "deferred-p3", "change_summary": "-", "verification": "留待区域证据", "note": "P3 留待后续维护"},
    "AUD-T2B-006": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-007": {"disposition": "deferred-p3", "change_summary": "-", "verification": "词面更正留待维护", "note": "P3 留待后续维护"},
    "AUD-T2B-008": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-009": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-010": {"disposition": "closed-direct", "change_summary": "D-09 statement 软化 + uncertainties 反例边界", "verification": "walk-diff 单路径变更", "note": "倾向性表述，未升级证据"},
    "AUD-T2B-011": {"disposition": "closed-no-action", "change_summary": "无问题维持；关系补链走 026/032", "verification": "复核通过", "note": "related_units 由 AUD-T2B-026/032 映射"},
    "AUD-T2B-012": {"disposition": "closed-direct", "change_summary": "R-01 conditions 增适用前提", "verification": "append 前查重 + 无数字断言", "note": "内容源自本单元既有文案"},
    "AUD-T2B-013": {"disposition": "deferred-p3", "change_summary": "-", "verification": "P3 留待维护", "note": ""},
    "AUD-T2B-014": {"disposition": "closed-direct", "change_summary": "R-03 uncertainties 增核验指向", "verification": "append 前查重", "note": "数值仍为 null 门禁"},
    "AUD-T2B-015": {"disposition": "closed-direct", "change_summary": "R-03 related_units += R-08", "verification": "对称性核对（R-08 已含 R-03）", "note": ""},
    "AUD-T2B-016": {"disposition": "closed-direct", "change_summary": "R-04 uncertainties 限定不指定方式", "verification": "append 前查重", "note": "不引入操作参数"},
    "AUD-T2B-017": {"disposition": "deferred-p3", "change_summary": "-", "verification": "P3 留待维护（配套定位已由 statement+failure_modes 覆盖）", "note": ""},
    "AUD-T2B-018": {"disposition": "closed-direct", "change_summary": "R-06 uncertainties 增区域留空声明", "verification": "append 前查重", "note": "region 保持 null"},
    "AUD-T2B-019": {"disposition": "open-blocked", "change_summary": "无数据变更（门禁已由 null+待核验承载）", "verification": "待现行登记标签证据", "note": "未核验前不得入决策链路"},
    "AUD-T2B-020": {"disposition": "closed-direct", "change_summary": "R-08 uncertainties 增定性边界", "verification": "append 前查重", "note": "定量拐点保持待验证"},
    "AUD-T2B-021": {"disposition": "deferred-p3", "change_summary": "-", "verification": "P3 留待维护", "note": "unit 空字符串修正延后"},
    "AUD-T2B-022": {"disposition": "open-blocked", "change_summary": "无数据变更", "verification": "与 AUD-T2B-035 绑定核验", "note": "限量文本未核验"},
    "AUD-T2B-023": {"disposition": "deferred-p3", "change_summary": "-", "verification": "P3 留待维护", "note": "unit 空字符串修正延后"},
    "AUD-T2B-024": {"disposition": "deferred-p3", "change_summary": "-", "verification": "P3 留待维护", "note": "unit 空字符串修正延后"},
    "AUD-T2B-025": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-026": {"disposition": "closed-direct", "change_summary": "K-05 related_units += D-10/F-05/Q-10", "verification": "append 前查重", "note": "不合并（角度差分）"},
    "AUD-T2B-027": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-028": {"disposition": "closed-direct", "change_summary": "F-02 uncertainties 增信息约束", "verification": "append 前查重", "note": "边界数值保持待验证"},
    "AUD-T2B-029": {"disposition": "closed-annotation", "change_summary": "不改分类", "verification": "manifest 注记（任务要求不强行改分类）", "note": "由架构师后续决策"},
    "AUD-T2B-030": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-031": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-032": {"disposition": "closed-direct", "change_summary": "F-05 related_units += K-05/D-10", "verification": "append 前查重", "note": ""},
    "AUD-T2B-033": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-034": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-035": {"disposition": "open-blocked", "change_summary": "无数据变更", "verification": "待现行限量标准文本", "note": "未核验前仅声明层"},
    "AUD-T2B-036": {"disposition": "open-blocked", "change_summary": "无数据变更", "verification": "待收购质量标准条款", "note": "未核验前仅声明层"},
    "AUD-T2B-037": {"disposition": "open-blocked", "change_summary": "无数据变更", "verification": "待登记标签/登记试验", "note": "防效承诺不予出具"},
    "AUD-T2B-038": {"disposition": "closed-direct", "change_summary": "Q-10 related_units += K-05；混合层注记维持", "verification": "append 前查重", "note": "provenance/layer 混合为可接受记法"},
    "AUD-T2B-039": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-040": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-041": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-042": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-043": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-044": {"disposition": "closed-no-action", "change_summary": "维持候选", "verification": "复核通过", "note": ""},
    "AUD-T2B-045": {"disposition": "closed-no-action", "change_summary": "全局核查通过", "verification": "混域推导链扫描", "note": ""},
    "AUD-T2B-046": {"disposition": "closed-no-action", "change_summary": "全局核查通过；张力细节并入 AUD-T2B-015 处置", "verification": "重复/矛盾扫描", "note": ""},
    "AUD-T2B-047": {"disposition": "closed-no-action", "change_summary": "全局核查通过；Q-10 混合层注记维持", "verification": "provenance 纪律核查", "note": ""},
    "AUD-T2B-048": {"disposition": "open-human", "change_summary": "无数据变更（方法层问题）", "verification": "人工决策：人工代理审计 / 异构模型重审 / 维持 agent 复核", "note": "teacher API 统一路由 deepseek-flash"},
}

DISTINCT_DISPOSITIONS = "closed-direct | closed-no-action | closed-annotation | deferred-p3 | open-blocked | open-human"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def walk_diff(old: Any, new: Any, path: str, out: list[dict[str, Any]]) -> None:
    if type(old) is not type(new):
        out.append({"path": path, "old": old, "new": new})
        return
    if isinstance(old, dict):
        for key in set(old) | set(new):
            walk_diff(old.get(key), new.get(key), f"{path}.{key}", out)
    elif isinstance(old, list):
        if len(old) != len(new):
            out.append({"path": path, "old": old, "new": new})
        else:
            for i, (a, b) in enumerate(zip(old, new)):
                walk_diff(a, b, f"{path}[{i}]", out)
    elif old != new:
        out.append({"path": path, "old": old, "new": new})


def apply_changes(package: dict[str, Any]) -> list[dict[str, Any]]:
    units: dict[str, dict[str, Any]] = {}
    for unit in package["units"]:
        units[str(unit["unit_id"])] = unit
    applied: list[dict[str, Any]] = []

    for change in REPLACEMENTS:
        unit = units[change["unit_id"]]
        current = unit[change["field"]]
        if current != change["old"]:
            raise SystemExit(f"MISMATCH {change['unit_id']}.{change['field']}: expected old value not found")
        if DIGIT_RE.search(str(change["new"])):
            raise SystemExit(f"DIGITS in new text: {change['unit_id']}.{change['field']}")
        applied.append({**change, "kind": "replace"})
        unit[change["field"]] = change["new"]

    for change in APPENDS:
        unit = units[change["unit_id"]]
        target = list(unit[change["field"]])
        if change["item"] in target:
            raise SystemExit(f"ALREADY PRESENT {change['unit_id']}.{change['field']}: {change['item']}")
        if change["field"] in TEXT_APPEND_FIELDS and DIGIT_RE.search(str(change["item"])):
            raise SystemExit(f"DIGITS in appended text: {change['unit_id']}.{change['field']}")
        target.append(change["item"])
        applied.append({**change, "kind": "append", "old": unit[change["field"]]})
        unit[change["field"]] = target

    return applied


def validate(package: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    old_ids = [str(u["unit_id"]) for u in base["units"]]
    new_ids = [str(u["unit_id"]) for u in package["units"]]
    checks["unit_count"] = {"base": len(old_ids), "revised": len(new_ids), "order_preserved": old_ids == new_ids}

    sig_old = {str(u["unit_id"]): (u["knowledge_layer"], u["provenance"], u["quantitative"]) for u in base["units"]}
    sig_new = {str(u["unit_id"]): (u["knowledge_layer"], u["provenance"], u["quantitative"]) for u in package["units"]}
    checks["evidence_grade_unchanged"] = sig_old == sig_new

    null_ok = all(
        q["value"] is None and q["value_status"] == "needs-verification"
        for u in package["units"]
        for q in u.get("quantitative", [])
    )
    checks["quantitative_all_null_needs_verification"] = null_ok

    all_ids = set(new_ids)
    broken: list[str] = []
    for u in package["units"]:
        for rel in u.get("related_units", []):
            if rel not in all_ids:
                broken.append(f"{u['unit_id']}->{rel}")
    checks["related_units_all_resolve"] = (not broken, broken)
    return checks


def expected_paths(applied: list[dict[str, Any]], base: dict[str, Any]) -> set[str]:
    allowed = {".package_id", ".round", ".revision"}
    index = {str(u["unit_id"]): i for i, u in enumerate(base["units"])}
    for change in applied:
        allowed.add(f".units[{index[change['unit_id']]}].{change['field']}")
    return allowed


def main() -> int:
    base = load_json(BASE_PKG)
    base_units: dict[str, dict[str, Any]] = {str(u["unit_id"]): json.loads(json.dumps(u, ensure_ascii=False)) for u in base["units"]}

    revised = json.loads(json.dumps(base, ensure_ascii=False))
    applied = apply_changes(revised)

    revised["package_id"] = "AG-DISTILL-T2C-WHE02-CANDIDATES-v2"
    revised["round"] = "AG-DISTILL-T2C"
    revised["revision"] = {
        "round": "AG-DISTILL-T2C",
        "date": "2026-10-19",
        "base_package": "AG-DISTILL-T2A-WHE02-CANDIDATES-v1",
        "base_sha256": sha256_file(BASE_PKG),
        "change_count": len(applied),
        "policy": "最小必要修订；未提高任何证据等级；quantitative value 全部保持 null；新增文本不含数字",
    }

    checks = validate(revised, base)
    findings = load_json(FINDINGS)["rows"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    diff_units: list[dict[str, Any]] = []
    for change in applied:
        diff_units.append(
            {
                "kind": change["kind"],
                "audit_ids": change["audit_ids"],
                "unit_id": change["unit_id"],
                "field": change["field"],
                "old": base_units[change["unit_id"]][change["field"]] if change["kind"] == "replace" else change["old"],
                "new": change["new"] if change["kind"] == "replace" else change["item"],
                "reason": change["reason"],
            }
        )
    diff_report = {"base_sha256": sha256_file(BASE_PKG), "change_count": len(applied), "changes": diff_units, "checks": checks}

    # walk-diff of the full document: only header fields and the change table
    # paths may differ, anything else is an implementation accident
    full_diff: list[dict[str, Any]] = []
    walk_diff(base, revised, "", full_diff)
    allowed = expected_paths(applied, base)
    unexpected = [d for d in full_diff if d["path"] not in allowed]
    if unexpected:
        for entry in unexpected:
            print(f"[FAIL] unexpected changed path: {entry['path']}")
        return 3

    with V2_PATH.open("w", encoding="utf-8") as handle:
        json.dump(revised, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    with STATUS_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["audit_issue_id", "candidate_id", "severity", "disposition", "change_summary",
             "verification", "evidence_grade_change", "note"]
        )
        for row in findings:
            disp = DISPOSITIONS[str(row["id"])]
            writer.writerow(
                [row["id"], row["unit_id"], row["severity"], disp["disposition"],
                 disp["change_summary"], disp["verification"], "none", disp["note"]]
            )

    with DIFF_PATH.open("w", encoding="utf-8") as handle:
        json.dump(diff_report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    counts: dict[str, int] = {}
    for row in findings:
        counts[DISPOSITIONS[str(row["id"])]["disposition"]] = counts.get(DISPOSITIONS[str(row["id"])]["disposition"], 0) + 1

    touched_units = {c["unit_id"] for c in applied}
    print(f"changes={len(applied)} units_touched={len(touched_units)} "
          f"unexpected_paths={len(unexpected)}")
    print(f"checks: unit_count={checks['unit_count']['base']}/{checks['unit_count']['revised']} "
          f"order={checks['unit_count']['order_preserved']} "
          f"evidence_unchanged={checks['evidence_grade_unchanged']} "
          f"quant_null={checks['quantitative_all_null_needs_verification']} "
          f"rel_resolve={checks['related_units_all_resolve'][0]}")
    print(f"dispositions: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
