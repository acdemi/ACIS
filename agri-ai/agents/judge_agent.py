"""JudgeAgent — 最终裁决层（规则 + DeepSeek）"""
from __future__ import annotations
import json, os
from dataclasses import asdict
from typing import Any
from agents.types import AgentOutput, RequestContext, DebateResult, DecisionOutput
from kg_adapter import query_kg

class JudgeAgent:
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def run(self, context: RequestContext, outputs: list[AgentOutput], debate: DebateResult) -> DecisionOutput:
        kg = query_kg(context.crop, context.query)
        if self.use_llm:
            try:
                return self._run_llm_judge(context, outputs, debate, kg)
            except Exception as exc:
                decision = self._run_rule_judge(context, outputs, debate, kg)
                decision.debate.missing_evidence.append(f"DeepSeek Judge 不可用，已回退规则裁决：{exc}")
                return decision
        return self._run_rule_judge(context, outputs, debate, kg)

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
                    rule_violations.append(f"{matched}要求{c['metric']}>{c['threshold']}，当前{cur}，硬约束不满足")
                    kg_match = "冲突"; vetoed = True; break
            agent_diagnoses.append({"agent": pathology.agent, "claim": claim, "kg_match": kg_match, "conflict_reason": rule_violations[-1] if rule_violations else ""})
        return {"agent_diagnoses": agent_diagnoses, "rule_violations": rule_violations, "vetoed": vetoed, "kg_diseases": kg_diseases}

    def _run_rule_judge(self, context, outputs, debate, kg):
        expert = [o for o in outputs if o.layer == "专家层"]
        weighted_total = sum(o.confidence for o in expert) or 1.0
        confidence = round(min(0.92, max(0.25, sum(o.confidence * o.confidence for o in expert) / weighted_total)), 2)
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
        action_plan = []
        for o in outputs:
            for r in o.recommendations:
                if r not in action_plan: action_plan.append(r)
        if debate.missing_evidence: action_plan.append("补充叶片近景图像，提升视觉和病理交叉验证置信度")
        if debate.conflicts: action_plan.append("存在策略冲突时，以病害风险控制优先，再安排水肥作业")
        if consistency["rule_violations"]: action_plan.append("当前环境与首选诊断的KG硬约束冲突，建议复核传感器数据并人工确认")
        need_human_review = bool(vetoed or debate.conflicts or confidence < 0.5 or debate.critic.get("escalate"))
        trace_parts = [f"KG参照疾病：{'、'.join(consistency['kg_diseases']) or '无'}"]
        if consistency["rule_violations"]: trace_parts.append("硬约束否决：" + "；".join(consistency["rule_violations"]))
        else: trace_parts.append("未触发KG硬约束否决")
        trace_parts.append(f"风险等级={debate.risk_level}，置信度={confidence}")
        if debate.critic.get("triggered"): trace_parts.append("Critic反驳：" + debate.critic.get("resolution", ""))
        summary = f"Orchestrator 已完成 {context.greenhouse_id}/{context.crop} 的{context.intent} 工作流：{decision}。风险等级：{debate.risk_level}。"
        return DecisionOutput(summary=summary, decision=decision, confidence=confidence, risk_level=debate.risk_level, action_plan=action_plan[:6], debate=debate, traces=outputs, judge_mode="rules", need_human_review=need_human_review, reasoning_trace="；".join(trace_parts), judge_analysis={"kg": {"diseases": consistency["kg_diseases"], "rules": kg.get("rules", []), "backend": kg.get("backend", "memory")}, "consistency": consistency, "sensor_readings": sensor_readings, "critic": debate.critic})

    def _run_llm_judge(self, context, outputs, debate, kg):
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key: raise ValueError("未设置 DEEPSEEK_API_KEY")
        from openai import OpenAI
        payload = self._build_judge_payload(context, outputs, debate, kg)
        client = OpenAI(api_key=api_key, base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        model = os.environ.get("AGRI_AI_JUDGE_MODEL") or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        resp = client.chat.completions.create(model=model, messages=[{"role": "system", "content": self._judge_system_prompt()}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}], temperature=0.1, response_format={"type": "json_object"})
        llm = json.loads(resp.choices[0].message.content or "{}")
        fb = self._run_rule_judge(context, outputs, debate, kg)
        decision = str(llm.get("final_diagnosis") or llm.get("decision") or fb.decision)
        action_plan = self._clean_string_list(llm.get("action_plan")) or fb.action_plan
        confidence = self._clean_confidence(llm.get("final_confidence", llm.get("confidence")), fb.confidence)
        risk_level = str(llm.get("risk_level") or fb.risk_level).lower()
        if risk_level not in {"low", "medium", "high"}: risk_level = fb.risk_level
        need_human_review = bool(llm.get("need_human_review", fb.need_human_review))
        if confidence > 0.9 and (need_human_review or debate.conflicts): confidence = 0.9; need_human_review = True
        summary = str(llm.get("summary") or fb.summary)
        if "DeepSeek" not in summary: summary = f"DeepSeek Judge 结构化裁决：{summary}"
        return DecisionOutput(summary=summary, decision=decision, confidence=confidence, risk_level=risk_level, action_plan=action_plan[:6], debate=debate, traces=outputs, judge_mode="deepseek", need_human_review=need_human_review, reasoning_trace=str(llm.get("reasoning_trace") or fb.reasoning_trace), judge_analysis={"consistency_analysis": llm.get("consistency_analysis", {}), "evidence_scores": llm.get("evidence_scores", {}), "kg_contribution": llm.get("kg_contribution", ""), "kg": {"diseases": kg.get("diseases", []), "rules": kg.get("rules", []), "backend": kg.get("backend", "memory")}, "critic": debate.critic})

    def _build_judge_payload(self, context, outputs, debate, kg):
        sr = self._sensor_readings(outputs)
        return {"现场数据": {"作物": context.crop, "温室": context.greenhouse_id, "意图": context.intent, "症状描述": context.query, "环境参数": sr}, "专家Agent意见": [{"agent": o.agent, "layer": o.layer, "diagnosis": o.claim, "confidence": o.confidence, "evidence": o.evidence, "warnings": o.warnings, "action": o.recommendations} for o in outputs], "知识图谱": {"kg_triples": kg.get("triple_strings", []), "kg_rules": kg.get("rules", []), "hard_constraints": kg.get("hard_constraints", [])}, "debate": asdict(debate), "output_schema": {"final_diagnosis": "最终疾病名称", "final_confidence": "0到1的数字", "need_human_review": "true/false", "summary": "一句中文总结", "risk_level": "low|medium|high", "action_plan": "最多6条可执行中文建议", "reasoning_trace": "300字内裁决逻辑", "consistency_analysis": {"agent_diagnoses": [{"agent": "", "claim": "", "kg_match": "完全匹配/部分匹配/冲突", "conflict_reason": ""}], "critical_conflicts": [], "rule_violations": []}, "evidence_scores": {"agent_name": "1-10分数"}, "kg_contribution": "KG对置信度的提升/降低幅度，如+0.15"}}

    @staticmethod
    def _judge_system_prompt() -> str:
        return """你是农业多智能体决策系统中的首席裁判官 (Judge Agent)。你的任务不是自己诊断，而是严格审查其他农业专家 Agent 的诊断意见，并利用农业知识图谱 (KG) 作为客观验证基准，进行一致性检查、争议裁决，最终输出一个高置信度的决策。

你将收到一份 JSON，包含：现场数据、专家Agent意见、知识图谱(kg_triples/kg_rules/hard_constraints)、debate、output_schema。

你必须严格按顺序执行以下审查步骤：
1. 知识图谱一致性校验：逐一检查每个专家诊断是否在 KG 中有直接或间接支持，标记 完全匹配/部分匹配/冲突。
2. 专家间交叉验证：找出共识点与分歧点。
3. 规则硬约束检查：检查环境参数是否违反 hard_constraints；若违反，该诊断直接否决。
4. 证据权重计算：给每个专家证据打分(1-10)。
5. 最终裁决与置信度融合：综合专家加权信任分与KG匹配度。

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
