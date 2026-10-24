"""AG-DISTILL-T2E release-readiness mechanical checks for the WHE-02 candidate chain.

Output: human summary + full JSON to stdout; JSON file additionally written to
AGRI_T2E_OUT (env override) so the script can run against a read-only worktree.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T2A_DIR = ROOT / "reports" / "ag-distill-t2a-wheat-fhb-20261019"
T2B_DIR = ROOT / "reports" / "ag-distill-t2b-wheat-fhb-audit"
T2C_DIR = ROOT / "reports" / "ag-distill-t2c-wheat-fhb-revision"
T2D_DIR = ROOT / "reports" / "ag-distill-t2d-schema-survey-20261019"
V1 = T2A_DIR / "candidate_knowledge.json"
V2 = T2C_DIR / "candidate_knowledge_v2.json"
FINDINGS = T2B_DIR / "audit_findings.json"
STATUS = T2C_DIR / "revision_status.csv"
OUT_JSON = ROOT / "reports" / "ag-distill-t2e-release-acceptance" / "release_checks.json"

PROV_ENUM = {"model-candidate", "model-inference", "needs-verification"}
P1_AUDIT_IDS = {"AUD-T2B-003", "AUD-T2B-010", "AUD-T2B-019", "AUD-T2B-022", "AUD-T2B-035", "AUD-T2B-036", "AUD-T2B-037"}
REVISED_11 = [
    "WHE02-D-03", "WHE02-D-09", "WHE02-R-01", "WHE02-R-02", "WHE02-R-03",
    "WHE02-R-04", "WHE02-R-05", "WHE02-R-06", "WHE02-R-07", "WHE02-R-08", "WHE02-F-02",
]
EQUIV_TERMS = ("等于", "等同", "等效", "替代", "合格")
GUARD_TERMS = ("不能", "并非", "不等价", "不必然", "不得", "须以", "只能分别判定", "不可互替",
               "而非", "不排除", "不再", "但")
GUARD_WINDOW = 40
DOSAGE_RE = re.compile(r"倍液|毫升|升/亩|[0-9]+\s*(?:g|kg|ml|L)\s*/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_products() -> dict[str, Any]:
    required = {
        "T2A": [V1, T2A_DIR / "validation_report.json", T2A_DIR / "execution_report.md",
                T2A_DIR / "stage_logs" / "run_summary.json"],
        "T2B": [FINDINGS, T2B_DIR / "claim_audit.csv", T2B_DIR / "revision_queue.md", T2B_DIR / "evidence_gaps.md",
                T2B_DIR / "audit_manifest.json", T2B_DIR / "execution_report.md"],
        "T2C": [V2, T2C_DIR / "diff_report.json", T2C_DIR / "revision_log.md", STATUS,
                T2C_DIR / "open_issues_queue.md", T2C_DIR / "execution_report.md"],
        "T2D": [T2D_DIR / "schema_ingestion_survey.md"],
    }
    result: dict[str, Any] = {}
    missing: list[str] = []
    for group, files in required.items():
        states = {str(p.relative_to(ROOT)): p.exists() for p in files}
        missing.extend(k for k, ok in states.items() if not ok)
        result[group] = states
    return {"exists": result, "missing": missing, "ok": not missing}


def check_units(v1: dict[str, Any], v2: dict[str, Any]) -> dict[str, Any]:
    u1 = {str(u["unit_id"]): u for u in v1["units"]}
    u2 = {str(u["unit_id"]): u for u in v2["units"]}
    ids_ok = set(u1) == set(u2) and len(u2) == 40
    field_gaps: list[str] = []
    prov_bad: list[str] = []
    stage_bad: list[str] = []
    verdicts: dict[str, int] = {}
    quant_bad: list[str] = []
    quant_total = 0
    for uid, u in u2.items():
        for field in ("statement", "title", "conditions", "provenance"):
            if not u.get(field):
                field_gaps.append(f"{uid}.{field}")
        if str(u.get("provenance")) not in PROV_ENUM:
            prov_bad.append(uid)
        stage = str(u.get("stage_source", "")).replace("stage-log:", "")
        stage_dir = T2A_DIR / "stage_logs" / stage
        if stage and not (stage_dir.exists() and (stage_dir / "meta.json").exists() and (stage_dir / "parsed.json").exists()):
            stage_bad.append(f"{uid}:{stage}")
        verdict = str((u.get("audit") or {}).get("verdict"))
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        for q in u.get("quantitative", []):
            quant_total += 1
            if q["value"] is not None or q["value_status"] != "needs-verification":
                quant_bad.append(f"{uid}/{q['metric']}")
    return {
        "unit_count_v1": len(u1), "unit_count_v2": len(u2), "ids_identical": ids_ok,
        "fields_complete_gaps": field_gaps, "provenance_violations": prov_bad,
        "stage_trace_gaps": stage_bad, "t2a_verdict_distribution": verdicts,
        "quantitative_entries_total": quant_total,
        "quantitative_non_null_or_unverified": quant_bad,
    }


def check_chain(v2: dict[str, Any], status_rows: list[dict[str, str]]) -> dict[str, Any]:
    manifest = load(T2B_DIR / "audit_manifest.json")
    recorded = str(manifest["audited_package"]["sha256"])
    actual = sha256_file(V1)
    dispositions = {str(row["audit_issue_id"]): str(row["disposition"]) for row in status_rows}
    p1 = {aid: dispositions.get(aid, "MISSING") for aid in sorted(P1_AUDIT_IDS)}
    revise_map = {uid: any(str(r["candidate_id"]) == uid for r in status_rows) for uid in REVISED_11}
    return {
        "v1_sha256_actual": actual, "v1_sha256_t2b_manifest": recorded, "sha_match": actual == recorded,
        "p1_dispositions": p1,
        "p1_all_closed_or_blocked": all(v in {"closed-direct", "open-blocked"} for v in p1.values()),
        "t2a_revise_11_all_in_status_csv": all(revise_map.values()), "t2a_revise_detail": revise_map,
        "open_items": sorted(aid for aid, d in dispositions.items() if d.startswith("open")),
        "deferred_items": sorted(aid for aid, d in dispositions.items() if d == "deferred-p3"),
        "status_csv_rows": len(status_rows),
        "v2_header": {
            "package_id": v2.get("package_id"), "round": v2.get("round"),
            "adaptation_status": v2.get("adaptation_status"),
            "policy": (v2.get("revision") or {}).get("policy"),
        },
    }


def scan_text(v2: dict[str, Any]) -> dict[str, Any]:
    def guarded(text: str, index: int, extra_blob: str = "") -> bool:
        window = text[max(0, index - GUARD_WINDOW): index + GUARD_WINDOW]
        return any(g in window or g in extra_blob for g in GUARD_TERMS)

    eq_hits: list[str] = []
    dosage_hits: list[str] = []
    for u in v2["units"]:
        statement = str(u["statement"])
        extras = [str(c) for c in u.get("uncertainties", [])] + [str(c) for c in u.get("failure_modes", [])]
        extra_blob = " ".join(extras)
        for term in EQUIV_TERMS:
            start = 0
            while (pos := statement.find(term, start)) != -1:
                if not guarded(statement, pos, extra_blob):
                    eq_hits.append(f"{u['unit_id']}@{term}")
                start = pos + len(term)
        combined = " ".join([statement, str(u.get("title", "")), *[str(c) for c in u.get("conditions", [])]])
        if DOSAGE_RE.search(combined):
            dosage_hits.append(str(u["unit_id"]))
    return {"equivalence_hits_without_guard": eq_hits, "dosage_pattern_hits": dosage_hits}


def check_repo() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              encoding="utf-8", check=True).stdout

    changed = [line for line in run(["diff", "main...HEAD", "--name-only"]).splitlines() if line.strip()]
    allowed_prefixes = ("docs/", "context/", "reports/", "scripts/")
    outside = [p for p in changed if not p.startswith(allowed_prefixes)]
    untracked = [line for line in run(["status", "--porcelain", "--untracked-files=all"]).splitlines()
                 if line.startswith("??")]
    commits = run(["log", "main..HEAD", "--oneline"]).splitlines()
    return {"main_diff_files": changed, "files_outside_safe_prefixes": outside,
            "sources_configs_touched": bool(outside), "untracked": untracked,
            "commits_chain_count": len(commits)}


def main() -> int:
    products = check_products()
    v1 = load(V1)
    v2 = load(V2)
    with STATUS.open("r", encoding="utf-8-sig", newline="") as handle:
        status_rows = [dict(r) for r in csv.DictReader(handle)]
    units = check_units(v1, v2)
    chain = check_chain(v2, status_rows)
    scans = scan_text(v2)
    repo = check_repo()
    report = {
        "check_executed": "AG-DISTILL-T2E",
        "products": products, "units": units, "chain": chain, "text_scans": scans, "repo": repo,
    }
    out_path = Path(os.environ["AGRI_T2E_OUT"]) if os.environ.get("AGRI_T2E_OUT") else OUT_JSON
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    ok = (products["ok"] and units["ids_identical"] and not units["fields_complete_gaps"]
          and not units["provenance_violations"] and not units["stage_trace_gaps"]
          and not units["quantitative_non_null_or_unverified"] and chain["sha_match"]
          and chain["p1_all_closed_or_blocked"] and chain["t2a_revise_11_all_in_status_csv"]
          and not scans["equivalence_hits_without_guard"] and not scans["dosage_pattern_hits"]
          and not repo["sources_configs_touched"])
    print(f"PRODUCTS_OK={products['ok']} UNIT_COUNT={units['unit_count_v2']}")
    print(f"IDS={units['ids_identical']} FIELD_GAPS={len(units['fields_complete_gaps'])} "
          f"PROV_BAD={len(units['provenance_violations'])} STAGE_GAPS={len(units['stage_trace_gaps'])}")
    print(f"VERDICTS={units['t2a_verdict_distribution']}")
    print(f"QUANT={units['quantitative_entries_total']} "
          f"BAD={len(units['quantitative_non_null_or_unverified'])} SHA_MATCH={chain['sha_match']} "
          f"P1_OK={chain['p1_all_closed_or_blocked']} "
          f"REVISE_11_OK={chain['t2a_revise_11_all_in_status_csv']} STATUS_ROWS={chain['status_csv_rows']}")
    print(f"SCAN_EQ_NONGUARDED={scans['equivalence_hits_without_guard']} SCAN_DOSAGE={scans['dosage_pattern_hits']}")
    print(f"OUTSIDE={repo['files_outside_safe_prefixes']} UNSOURCED_UNTRACKED={repo['untracked']} "
          f"COMMITS={repo['commits_chain_count']}")
    print(f"OVERALL={'PASS' if ok else 'FAIL'}")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
