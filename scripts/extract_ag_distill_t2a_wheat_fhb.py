"""AG-DISTILL-T2A — WHE-02 小麦赤霉病与毒素管理：在线教师模型分阶段提取运行器。

- 任务标识：AG-DISTILL-T2A
- Prompt 版本：t2a-p1
- 模型：DEEPSEEK_BASE_URL（.env 配置）；S1-S6 用 deepseek-chat，S7 审计用 deepseek-reasoner（失败自动降级 chat 并记录）
- 每阶段落盘：stage_logs/<stage>/prompt.txt、raw_response.txt、parsed.json、meta.json
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "ag-distill-t2a-wheat-fhb-20261019" / "stage_logs"
PROMPT_VERSION = "t2a-p1"
TASK_ID = "AG-DISTILL-T2A"

SYSTEM = """你是用于农业专业知识库的原子知识提取教师模型。输出必须是单个合法 JSON 对象，不得包含任何 JSON 之外的文字或代码围栏。

铁律：
1. 不编造文献、DOI、作者、标准编号中的具体数值、试验数据、农药登记信息。确实存在的政策/标准引用须给出可定位文本名称与本轮性质说明，数值留 null 并标记 needs-verification。
2. 每条知识单元只表达一个主要结论，可独立理解与检索。
3. 任何数字如出现在 statement 中，必须在 quantitative 数组中登记（否则不得出现数字）。
4. 不得将病害症状严重度等同于毒素风险低，也不得将防效等同粮食合格（框架内已有字段分开承载）。
5. 中文表述；url 无；不确定处写入 uncertainties。

单元 JSON Schema（你必须遵守字段名）：
{
  "unit_id": "WHE02-<阶段码>-<两位序号>",
  "title": "不超过 30 字",
  "statement": "单一主要结论，<=120 字；不含未登记数字",
  "knowledge_layer": "definition|mechanism|rule|diagnostic|risk-chain|failure-mode|quantitative",
  "provenance": "model-candidate|model-inference|needs-verification|source-supported",
  "provenance_note": "为何此等级，<=40 字",
  "main_triple": {"subject": "", "predicate": "", "object": ""},
  "conditions": ["适用前提，可为空数组"],
  "failure_modes": ["失效条件/反例，可为空数组"],
  "side_effects": ["潜在副作用，可为空数组"],
  "applicability": {"growth_stage": "", "region": null, "production_system": null, "variety_note": null},
  "quantitative": [{"metric": "", "value": null, "unit": "", "operator": null, "applicable_conditions": "", "comparison_baseline": null, "value_status": "needs-verification"}],
  "verification_methods": ["如何用实验/观测/标准文本核验"],
  "related_units": ["unit_id"],
  "uncertainties": ["明确的不确定性说明"]
}

各输出外层：{"units": [...], "stage_notes": "..."}，rule 形单元的 conditions 数组至少 1 条。
"""

BACKGROUNDB = """
背景（T1 域探测 WHE-02 界定）：
- 现有知识库（rag/knowledge_base.py）对小麦零覆盖，本主题全部条目均为新增域。
- 重提取优先级 P1；核心生育期=抽穗扬花期；区域留空=通用条件，区域差分写入 uncertainties。
- 对应域 A 病原与发生条件；B 生育期-花期风险；C 天气/田间微环境风险；D 监测预警边界；
  E 农艺防控适用条件；F 毒素形成与籽粒污染；G 收获干燥储存粮食安全；H 病害控制与毒素控制的区别；
  I 误区反例失败模式。
"""

STAGES: list[tuple[str, dict[str, Any]]] = [
    ("S1", {
        "model": "deepseek-chat", "temp": 0.2,
        "prompt": BACKGROUNDB + """
任务 S1：主题分解与知识缺口识别。对 WHE-02 完成：
1. 将主题按 A-I 域拆分为可提取子题清单（每子题 <=25 字）；
2. 指出仅凭本背景无法确证的知识缺口（写为缺口条目）；
3. 给出后续阶段的单元规划骨架（unit_plan: 每域预期 2~5 个单元的标题草案，不写正文）。
输出 {"subtopics": [...], "gaps": [...], "unit_plan": [{"scope": "", "planned_titles": [...]}], "stage_notes": "..."}""",
    }),
    ("S2", {
        "model": "deepseek-chat", "temp": 0.3,
        "prompt": BACKGROUNDB + """
任务 S2：核心概念及机制提取。围绕赤霉病病原分类认知、侵染循环（初侵染源-传播-侵染部位-潜育-流行）、
花期生物学与感病窗口机制，提取 definition/mechanism 类单元。产出 6~10 个单元（unit_id 前缀 WHE02-D）。
要点：直立区分"穗腐/茎基腐/秆腐"类型描述；机制单元须写清条件依赖；不做防治建议（留给 S3）。""",
    }),
    ("S3", {
        "model": "deepseek-chat", "temp": 0.3,
        "prompt": BACKGROUNDB + """
任务 S3：条件规则与时间窗口提取。围绕"抽穗-扬花-灌浆"时序和药剂防治的时窗性规则、"初次防治+补治"
节奏、农艺性降险措施（菌源削减、排水降湿、播期调节）提取 rule 类单元。产出 5~9 个（unit_id 前缀 WHE02-R）。
要求：每条规则必须写 conditions（≥1），并写 failure_modes 与适用边界；不填防治次数/间隔的具体数值，
若必须表达次数则 value=null + value_status=needs-verification；不写具体农药剂量。""",
    }),
    ("S4", {
        "model": "deepseek-chat", "temp": 0.3,
        "prompt": BACKGROUNDB + """
任务 S4：提取"病害风险"与"毒素风险"的关系单元（risk-chain 层）。必须明确：
- 田间病害流行等级（病穗率/严重度）与最终粮粒 DON 污染之间不是单向充分关系；
- 毒素风险由"病粒率、污染梯度、检测限量框架"承载，与防治决策不同源；
- 提"病害控制"≠"毒素控制"的解耦单元。产出 3~5 个（unit_id 前缀 WHE02-K），并加入一条 failure-mode
说明"误合并"问题。""",
    }),
    ("S5", {
        "model": "deepseek-chat", "temp": 0.3,
        "prompt": BACKGROUNDB + """
任务 S5：失败模式、反例与边界提取。围绕：白穗鉴别的常见混淆、花期不见雨/菌源低时的防治必要性问题、
雨后抢晴喷药失败面、品种"耐病"误读、储粮受潮后毒素升高等，提取 failure-mode/diagnostic 边界单元。
产出 4~7 个（unit_id 前缀 WHE02-F）。每条写 failure_modes[]（≥1）；标 provenance=model-inference 的须给推理链简述。""",
    }),
    ("S6", {
        "model": "deepseek-chat", "temp": 0.2,
        "prompt": BACKGROUNDB + """
任务 S6：定量知识及其证据需求提取。列出本主题的定量指标（流行学触发阈值、病穗率与毒素相关性指标、
病粒率收购分类指标、DON/ZEN 限量、药剂防效区间、储粮水分安全界限等）。
要求：所有 value=null + value_status=needs-verification；写清 unit、operator、applicable_conditions、
comparison_baseline（缺则 null）；verification_methods 给出可定位核查方向（去向说明，不编标准编号）。
产出 6~10 个（unit_id 前缀 WHE02-Q）。statement 中不得出现具体数字。""",
    }),
    ("S7", {
        "model": "deepseek-reasoner", "temp": 0.2, "json_mode": False,
        "prompt": "",
    }),
]


def call_api(model: str, user_prompt: str, temperature: float, use_json_mode: bool, timeout: int = 180) -> dict:
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    key = env.get("DEEPSEEK_API_KEY", "").strip()
    base = (env.get("DEEPSEEK_BASE_URL", "").strip() or "https://api.deepseek.com").rstrip("/")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": 8192,
    }
    if use_json_mode:
        payload["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {"text": text, "usage": usage, "model": data.get("model", model)}


def parse_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("` \n")
        if t.lower().startswith("json"):
            t = t[4:]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("{"), t.rfind("}")
        if start >= 0 and end > start:
            return json.loads(t[start : end + 1])
        raise


def run_stage(tag: str, model: str, user_prompt: str, temperature: float, use_json_mode: bool) -> dict:
    stage_dir = OUT_DIR / tag
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "prompt.txt").write_text(user_prompt, encoding="utf-8")
    attempts = []
    last_err = None
    for attempt in range(1, 4):
        try:
            t0 = time.time()
            result = call_api(model, user_prompt, temperature, use_json_mode)
            elapsed = round(time.time() - t0, 1)
            (stage_dir / "raw_response.txt").write_text(result["text"], encoding="utf-8")
            parsed = parse_json(result["text"])
            (stage_dir / "parsed.json").write_text(
                json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            meta = {
                "task_id": TASK_ID, "stage": tag, "prompt_version": PROMPT_VERSION,
                "attempt": attempt, "requested_model": model, "served_model": result["model"],
                "usage": result["usage"], "elapsed_sec": elapsed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            (stage_dir / "meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"stage": tag, "status": "ok", "meta": meta, "parsed": parsed, "model": model}
        except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            last_err = exc
            attempts.append({"attempt": attempt, "error": f"{type(exc).__name__}: {str(exc)[:300]}"})
            time.sleep(4 * attempt)
    (stage_dir / "meta.json").write_text(
        json.dumps({
            "task_id": TASK_ID, "stage": tag, "prompt_version": PROMPT_VERSION,
            "status": "failed", "attempts": attempts, "last_error": last_err and type(last_err).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"stage": tag, "status": "failed", "attempts": attempts, "model": model}


def condense_units(parsed: dict) -> list[dict]:
    units = parsed.get("units", []) if isinstance(parsed, dict) else []
    out = []
    for u in units:
        out.append({
            "unit_id": u.get("unit_id"), "title": u.get("title"), "statement": u.get("statement"),
            "knowledge_layer": u.get("knowledge_layer"), "provenance": u.get("provenance"),
            "quantitative": [
                {"metric": q.get("metric"), "value": q.get("value"), "unit": q.get("unit"),
                 "value_status": q.get("value_status")}
                for q in u.get("quantitative", [])
            ],
        })
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []
    for tag, cfg in STAGES:
        if tag == "S7":
            continue
        print(f"[stage {tag}] start", flush=True)
        result = run_stage(tag, cfg["model"], cfg["prompt"], cfg["temp"], cfg.get("json_mode", True))
        print(f"[stage {tag}] {result['status']}", flush=True)
        summary.append({"stage": tag, "status": result["status"], "model": result["model"],
                        "meta": result.get("meta") or {}})
    ok_stages = {s["stage"]: s["status"] for s in summary}
    s7_dir = OUT_DIR / "S7"
    s7_dir.mkdir(parents=True, exist_ok=True)
    s7_status = "skipped"
    if all(ok_stages.get(s) == "ok" for s in ["S2", "S3", "S4", "S5", "S6"]):
        cond = {}
        for s in ["S2", "S3", "S4", "S5", "S6"]:
            with open(OUT_DIR / s / "parsed.json", encoding="utf-8") as f:
                cond[s] = condense_units(json.load(f))
        s7_prompt = """你是独立审计员（另一岗位），对候选知识单元做质量与证据纪律审计。逐条给出 verdict，并给全局发现。审计要点：
1. 单元是否原子（只表达一个主要结论）；
2. 是否有未在 quantitative 登记的数字；是否有 value=null 却又写了具体数值的矛盾；
3. 是否有编造文献/标准号/登记信息的迹象；needs-verification 是否被诚实保留；
4. 病害风险与毒素风险是否被错误合并；rule 单元是否缺 conditions/failure_modes；
5. 区域/品种适用性是否被过度通用化。
输出单个 JSON：{"audits": [{"unit_id": "", "verdict": "pass|revise|reject", "reason": "<=30 字", "revisions_needed": [...]}, ...], "global_findings": [...]}"""
        s7_prompt += "\n候选单元清单：\n" + json.dumps(cond, ensure_ascii=False, indent=1)
        (s7_dir / "prompt.txt").write_text(s7_prompt, encoding="utf-8")
        print("[stage S7] start", flush=True)
        result = run_stage("S7", "deepseek-reasoner", s7_prompt, 0.2, False)
        if result["status"] == "failed":
            fallback = run_stage("S7", "deepseek-chat", s7_prompt, 0.2, True)
            result = fallback
            result["downgraded_from"] = "deepseek-reasoner"
        print(f"[stage S7] {result['status']}", flush=True)
        summary.append({"stage": "S7", "status": result["status"], "model": result["model"],
                        "meta": result.get("meta") or {}})
        s7_status = result["status"]
    else:
        summary.append({"stage": "S7", "status": "skipped_due_to_upstream_failure"})
    (OUT_DIR / "run_summary.json").write_text(
        json.dumps({"task_id": TASK_ID, "prompt_version": PROMPT_VERSION, "stages": summary,
                    "s7_status": s7_status},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({s["stage"]: s["status"] for s in summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
