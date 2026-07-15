"""JudgeAgent - 最终裁决层（规则 + DeepSeek）

ACIS 2.0 增强：
- 反事实一致性审查：利用各专家 Agent 提出的 counterfactual（替代诊断 + 排除理由）。
- 集体忽略检测：若 KG 中存在某病害但所有专家(含反事实)均未提及，视为集体忽略，
  争议分 +0.2 并适度下调置信度。
"""
from __future__ import annotations
import json, os
from dataclasses import asdict
from typing import Any
from agents.types import AgentOutput, RequestContext, DebateResult, DecisionOutput
from kg_adapter import query_kg, propose_triple, load_draft_triples

class JudgeAgent:
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self.calibrator = self._load_calibrator()

    @staticmethod
    def _load_calibrator():
        try:
            from utils.confidence_calibration import Calibrator
            return Calibrator()
        except Exception:
            class _Passthrough:
                enabled = False
                def calibrate(self, agent, raw):
                    return float(raw)
                def status(self):
                    return {"enabled": False, "note": "calibrator unavailable, passthrough"}
            return _Passthrough()

    def run(self, context: RequestContext, outputs: list[AgentOutput], debate: DebateResult, debate_round: int = 1) -> DecisionOutput:
        kg = query_kg(context.crop, context.query)
        if self.use_llm:
            try:
                return self._run_llm_judge(context, outputs, debate, kg, debate_round)
            except Exception as exc:
                decision = self._run_rule_judge(context, outputs, debate, kg, debate_round)
                decision.debate.missing_evidence.append(f"DeepSeek Judge 不可用，已回退规则裁决：{exc}")
                return decision
        return self._run_rule_judge(context, outputs, debate, kg, debate_round)

    @staticmethod
    def _sensor_readings(outputs) -> dict[str, float]:
        sensor = next((o for o in outputs if o.agent == "传感器Agent"), None)
        if not sensor: return {}
        readings = sensor.evidence.get("reading", {}).get("readings", {})
        km = {"air_temperature": "temperature", "air_humidity": "humidity", "soil_moisture": "soil_moisture", "co2": "co2"}
        result = {}
        for rk, mk in km.items():
            v = readings.get(rk)
            if v is not None:
                try: result[mk] = float(v)
                except: pass
        return result

    def _kg_consistency(self, outputs, kg, sensor_readings):
        kg_diseases = list(kg.get("diseases", []))
        hard_constraints = kg.get("hard_constraints", [])
        agent_diagnoses, rule_violations, vetoed = [], [], False
        pathology = next((o for o in outputs if o.agent == "病理Agent"), None)
        if pathology:
            claim = pathology.claim
            matched = next((d for d in kg_diseases if d in claim), None)
            kg_match = "完全匹配" if matched else ("部分匹配" if kg_diseases else "无KG数据")
            for c in hard_constraints:
                if not matched or c["disease"] != matched: continue
                cur = sensor_readings.get(c["metric"])
                if cur is None: continue
                if c["operator"] == ">" and cur < c["threshold"] * 0.6:
                    metric = c["metric"]
                    threshold = c["threshold"]
                    rule_violations.append(f"{matched}要求{metric}>{threshold}，当前{cur}，硬约束不满足")
                    kg_match = "冲突"; vetoed = True; break
            agent_diagnoses.append({"agent": pathology.agent, "claim": claim, "kg_match": kg_match, "conflict_reason": rule_violations[-1] if rule_violations else ""})
        return {"agent_diagnoses": agent_diagnoses, "rule_violations": rule_violations, "vetoed": vetoed, "kg_diseases": kg_diseases}

    @staticmethod
    def _collective_omission(outputs, kg) -> list[str]:
        """KG 中存在、但所有专家(主诊断 + 反事实替代诊断)均未提及的病害。"""
        kg_diseases = list(kg.get("diseases", []))
        if not kg_diseases:
            return []
        mentioned = set()
        for o in outputs:
            if o.layer != "专家层":
                continue
            for d in kg_diseases:
                if d in o.claim:
                    mentioned.add(d)
            alt = (o.counterfactual or {}).get("alternative", "")
            for d in kg_diseases:
                if d in alt:
                    mentioned.add(d)
        return [d for d in kg_diseases if d not in mentioned]

    def _omission_analysis(self, outputs, kg, consistency) -> dict[str, Any]:
        """反事实一致性 + 集体忽略分析（规则版与 LLM 版共用）。"""
        omitted = self._collective_omission(outputs, kg)
        primary_match = consistency["agent_diagnoses"][0].get("kg_match") if consistency["agent_diagnoses"] else "无KG数据"
        penalty_applied = bool(omitted) and primary_match != "完全匹配"
        counterfactuals = [
            {"agent": o.agent, "alternative": (o.counterfactual or {}).get("alternative", ""),
             "rejection_reason": (o.counterfactual or {}).get("rejection_reason", "")}
            for o in outputs if o.layer == "专家层" and o.counterfactual
        ]
        return {
            "omitted_diseases": omitted,
            "penalty_applied": penalty_applied,
            "controversy_delta": 0.2 if penalty_applied else 0.0,
            "counterfactuals": counterfactuals,
        }

    def _kg_evolution(self, outputs, kg, context) -> dict[str, Any]:
        """ACIS 2.0: KG 进化 -- 专家证据充分但 KG 缺失关系时提议三元组；
        可选加载未审核草稿(AGRI_AI_KG_DRAFTS_LOAD=1)，引用时注明并略降置信度。"""
        kg_diseases = set(kg.get("diseases", []))
        crop = kg.get("crop") or context.crop
        proposed: list[str] = []
        pathology = next((o for o in outputs if o.agent == "病理Agent"), None)
        if pathology:
            for d in (pathology.evidence or {}).get("possible_diseases", []):
                name = d.get("name", "")
                score = d.get("match_score", 0)
                if name and name not in kg_diseases and score > 0:
                    conf = min(0.9, 0.45 + score * 0.08)
                    rec = propose_triple(crop, "易感", name, conf, f"病理Agent匹配度{score}，KG中缺失")
                    if rec:
                        proposed.append(name)
        drafts: list[dict[str, Any]] = []
        used_drafts = False
        if os.environ.get("AGRI_AI_KG_DRAFTS_LOAD", "0") in {"1", "true", "True"}:
            drafts = [t for t in load_draft_triples() if t.get("subject") == crop]
            used_drafts = bool(drafts)
        return {"proposed": proposed, "drafts": drafts, "used_drafts": used_drafts}

    def _run_rule_judge(self, context, outputs, debate, kg, debate_round=1):
        expert = [o for o in outputs if o.layer == "专家层"]
        # ACIS 2.0: 校准各专家置信度后再融合
        cal_conf = [self.calibrator.calibrate(o.agent, o.confidence) for o in expert]
        weighted_total = sum(cal_conf) or 1.0
        confidence = round(min(0.92, max(0.25, sum(c * c for c in cal_conf) / weighted_total)), 2)
        sensor_readings = self._sensor_readings(outputs)
        consistency = self._kg_consistency(outputs, kg, sensor_readings)
        pathology = next((o for o in outputs if o.agent == "病理Agent"), None)
        meteorology = next((o for o in outputs if o.agent == "气象Agent"), None)
        cultivation = next((o for o in outputs if o.agent == "栽培Agent"), None)
        vetoed = consistency["vetoed"]
        if context.intent == "irrigate" and meteorology:
            decision = meteorology.claim
        elif pathology and "病理证据不足" not in pathology.claim and not vetoed:
            decision = pathology.claim
        elif cultivation:
            decision = cultivation.claim
        else:
            decision = "继续采集证据后再决策"
        if vetoed: confidence = round(min(confidence, 0.6), 2)
        omission = self._omission_analysis(outputs, kg, consistency)
        if omission["penalty_applied"]:
            confidence = round(max(0.25, confidence - omission["controversy_delta"]), 2)
        kg_evo = self._kg_evolution(outputs, kg, context)
        if kg_evo["used_drafts"]:
            confidence = round(max(0.25, confidence - 0.03), 2)
        action_plan = []
        for o in outputs:
            for r in o.recommendations:
                if r not in action_plan: action_plan.append(r)
        if debate.missing_evidence: action_plan.append("补充叶片近景图像，提升视觉和病理交叉验证置信度")
        if debate.conflicts: action_plan.append("存在策略冲突时，以病害风险控制优先，再安排水肥作业")
        if consistency["rule_violations"]: action_plan.append("当前环境与首选诊断的KG硬约束冲突，建议复核传感器数据并人工确认")
        if omission["penalty_applied"]: action_plan.append("存在集体忽略风险，建议补充检索KG中未覆盖病害并人工复核")
        need_human_review = bool(vetoed or debate.conflicts or confidence < 0.5 or debate.critic.get("escalate"))
        kg_join = "、".join(consistency["kg_diseases"]) or "无"
        trace_parts = [f"KG参照疾病：{kg_join}"]
        if consistency["rule_violations"]: trace_parts.append("硬约束否决：" + "；".join(consistency["rule_violations"]))
        else: trace_parts.append("未触发KG硬约束否决")
        trace_parts.append(f"风险等级={debate.risk_level}，置信度={confidence}")
        if debate.critic.get("triggered"): trace_parts.append("Critic反驳：" + debate.critic.get("resolution", ""))
        if omission["penalty_applied"]:
            omitted_join = "、".join(omission["omitted_diseases"])
            trace_parts.append(f"集体忽略预警：KG存在但专家均未考虑的病害--{omitted_join}，争议分+0.2")
        if kg_evo["used_drafts"]:
            n_drafts = len(kg_evo["drafts"])
            trace_parts.append(f"基于未审核知识：引用{n_drafts}条草稿三元组，置信度略降")
        if kg_evo["proposed"]:
            n_prop = len(kg_evo["proposed"])
            proposed_join = "、".join(kg_evo["proposed"])
            trace_parts.append(f"KG进化：提议{n_prop}条缺失三元组--{proposed_join}")
        if debate_round >= 2:
            r2 = next((o for o in outputs if o.agent == "病理Agent" and (o.evidence or {}).get("rebuttal_round") == 2), None)
            r1 = next((o for o in outputs if o.agent == "病理Agent" and (o.evidence or {}).get("rebuttal_round") != 2), None)
            if r2 and r1:
                cmp_note = "第二轮病理意见与首轮一致" if r2.claim == r1.claim else f"第二轮病理意见调整为{r2.claim}"
            else:
                cmp_note = "已结合第二轮辩论上下文"
            trace_parts.append(f"第二轮辩论后裁决：{cmp_note}")
        summary = f"Orchestrator 已完成 {context.greenhouse_id}/{context.crop} 的{context.intent} 工作流：{decision}。风险等级：{debate.risk_level}。"
        if debate_round >= 2:
            summary = f"【第二轮辩论后裁决】{summary}"
        return DecisionOutput(summary=summary, decision=decision, confidence=confidence, risk_level=debate.risk_level, action_plan=action_plan[:6], debate=debate, traces=outputs, judge_mode="rules", need_human_review=need_human_review, reasoning_trace="；".join(trace_parts), judge_analysis={"kg": {"diseases": consistency["kg_diseases"], "rules": kg.get("rules", []), "backend": kg.get("backend", "memory")}, "consistency": consistency, "sensor_readings": sensor_readings, "critic": debate.critic, "collective_omission": omission, "kg_evolution": kg_evo, "calibration": self.calibrator.status()})

    def _run_llm_judge(self, context, outputs, debate, kg, debate_round=1):
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key: raise ValueError("未设置 DEEPSEEK_API_KEY")
        from openai import OpenAI
        payload = self._build_judge_payload(context, outputs, debate, kg)
        client = OpenAI(api_key=api_key, base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        model = os.environ.get("AGRI_AI_JUDGE_MODEL") or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        resp = client.chat.completions.create(model=model, messages=[{"role": "system", "content": self._judge_system_prompt()}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}], temperature=0.1, response_format={"type": "json_object"})
        llm = json.loads(resp.choices[0].message.content or "{}")
        fb = self._run_rule_judge(context, outputs, debate, kg, debate_round)
        decision = str(llm.get("final_diagnosis") or llm.get("decision") or fb.decision)
        action_plan = self._clean_string_list(llm.get("action_plan")) or fb.action_plan
        confidence = self._clean_confidence(llm.get("final_confidence", llm.get("confidence")), fb.confidence)
        risk_level = str(llm.get("risk_level") or fb.risk_level).lower()
        if risk_level not in {"low", "medium", "high"}: risk_level = fb.risk_level
        need_human_review = bool(llm.get("need_human_review", fb.need_human_review))
        if confidence > 0.9 and (need_human_review or debate.conflicts): confidence = 0.9; need_human_review = True
        summary = str(llm.get("summary") or fb.summary)
        if "DeepSeek" not in summary: summary = f"DeepSeek Judge 结构化裁决：{summary}"
        if debate_round >= 2: summary = f"【第二轮辩论后裁决】{summary}"
        omission = fb.judge_analysis.get("collective_omission", {})
        return DecisionOutput(summary=summary, decision=decision, confidence=confidence, risk_level=risk_level, action_plan=action_plan[:6], debate=debate, traces=outputs, judge_mode="deepseek", need_human_review=need_human_review, reasoning_trace=str(llm.get("reasoning_trace") or fb.reasoning_trace), judge_analysis={"consistency_analysis": llm.get("consistency_analysis", {}), "evidence_scores": llm.get("evidence_scores", {}), "kg_contribution": llm.get("kg_contribution", ""), "kg": {"diseases": kg.get("diseases", []), "rules": kg.get("rules", []), "backend": kg.get("backend", "memory")}, "critic": debate.critic, "collective_omission": omission, "kg_evolution": fb.judge_analysis.get("kg_evolution", {}), "calibration": self.calibrator.status()})

    def _build_judge_payload(self, context, outputs, debate, kg):
        sr = self._sensor_readings(outputs)
        return {"现场数据": {"作物": context.crop, "温室": context.greenhouse_id, "意图": context.intent, "症状描述": context.query, "环境参数": sr}, "专家Agent意见": [{"agent": o.agent, "layer": o.layer, "diagnosis": o.claim, "confidence": o.confidence, "evidence": o.evidence, "warnings": o.warnings, "action": o.recommendations, "counterfactual": o.counterfactual} for o in outputs], "知识图谱": {"kg_triples": kg.get("triple_strings", []), "kg_rules": kg.get("rules", []), "hard_constraints": kg.get("hard_constraints", [])}, "debate": asdict(debate), "output_schema": {"final_diagnosis": "最终疾病名称", "final_confidence": "0到1的数字", "need_human_review": "true/false", "summary": "一句中文总结", "risk_level": "low|medium|high", "action_plan": "最多6条可执行中文建议", "reasoning_trace": "300字内裁决逻辑", "consistency_analysis": {"agent_diagnoses": [{"agent": "", "claim": "", "kg_match": "完全匹配/部分匹配/冲突", "conflict_reason": ""}], "critical_conflicts": [], "rule_violations": [], "collective_omission": "KG中存在但所有专家(含反事实)均未提及的病害列表"}, "evidence_scores": {"agent_name": "1-10分数"}, "kg_contribution": "KG对置信度的提升/降低幅度，如+0.15"}}

    @staticmethod
    def _judge_system_prompt() -> str:
        return """你是农业多智能体决策系统中的首席裁判官 (Judge Agent)。你的任务不是自己诊断，而是严格审查其他农业专家 Agent 的诊断意见，并利用农业知识图谱 (KG) 作为客观验证基准，进行一致性检查、争议裁决，最终输出一个高置信度的决策。

你将收到一份 JSON，包含：现场数据、专家Agent意见(含每人的 counterfactual 反事实替代诊断)、知识图谱(kg_triples/kg_rules/hard_constraints)、debate、output_schema。

你必须严格按顺序执行以下审查步骤：
1. 知识图谱一致性校验：逐一检查每个专家诊断是否在 KG 中有直接或间接支持，标记 完全匹配/部分匹配/冲突。
2. 专家间交叉验证：找出共识点与分歧点。
3. 规则硬约束检查：检查环境参数是否违反 hard_constraints；若违反，该诊断直接否决。
4. 证据权重计算：给每个专家证据打分(1-10)。
5. 最终裁决与置信度融合：综合专家加权信任分与KG匹配度。
6. 反事实一致性审查：检查每位专家给出的"替代诊断及排除理由"是否合理；若多位专家的反事实指向同一被忽略方向，需重点复核。
7. 集体忽略检测：若 KG 中存在某病害，但所有专家(含反事实)均未提及，视为集体忽略风险，应在 consistency_analysis.collective_omission 中标注，并将最终置信度适度下调(约0.2)。

重要约束：
- 综合KG、专家、规则三方，绝不依赖单一方面。
- KG与专家经验严重对立时，倾向降低置信度而非强行站队。
- 没有足够证据时，宁可给"无法定论"并建议采集更多数据。
- 只输出 JSON。"""

    @staticmethod
    def _clean_string_list(v): return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []
    @staticmethod
    def _clean_confidence(v, default):
        try: return round(min(0.95, max(0.1, float(v))), 2)
        except: return default
