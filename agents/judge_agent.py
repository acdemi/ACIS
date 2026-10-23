"""JudgeAgent - 最终裁决层（规则 + DeepSeek）

ACIS 2.0 增强：
- 反事实一致性审查：利用各专家 Agent 提出的 counterfactual（替代诊断 + 排除理由）。
- 集体忽略检测：若 KG 中存在某病害但所有专家(含反事实)均未提及，视为集体忽略，
  争议分 +0.2 并适度下调置信度。
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from typing import Any

from agents.types import AgentOutput, DebateResult, DecisionOutput, RequestContext
from decision_semantics import is_abstention as _is_abstention
from decision_semantics import decision_text as _decision_text
from decision_semantics import normalize_decision_label as _normalize_label
from kg_adapter import load_draft_triples, propose_triple, query_kg
from utils.confidence_calibration import (
    DecisionCalibrator,
    combine_decision_score,
    compute_decision_signals,
)
from utils.judge_runtime import (
    JudgeRuntimeConfig,
    classify_failure,
    redact_error_detail,
    judge_default_headers,
    resolve_judge_config,
)
from utils.omission import (
    apply_omission_penalty,
    omission_action,
    omission_reason,
    omission_score,
)

_logger = logging.getLogger(__name__)


class JudgeConfigurationError(ValueError):
    """Judge configuration prevents an LLM request from being attempted."""


class JudgeResponseFormatError(ValueError):
    """Provider response does not satisfy the Judge decision contract."""


def classify_judge_failure(exc: Exception) -> str:
    """Backward-compatible alias for the shared failure classifier."""
    return classify_failure(exc)


def judge_runtime_metadata(
    config: JudgeRuntimeConfig,
    *,
    outcome: str,
    reason_code: str | None = None,
    detail: str = "",
    retry_exhausted: bool = False,
    token_usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build trace-safe Judge metadata without credentials or headers."""
    metadata: dict[str, Any] = {
        "outcome": outcome,
        "judge_mode": "deepseek" if outcome == "success" else "rules",
        **config.public_metadata(),
        "retry_exhausted": retry_exhausted,
    }
    if reason_code:
        metadata["fallback_reason_code"] = reason_code
        metadata["fallback_detail"] = redact_error_detail(
            detail, api_key=config.api_key
        )
    if token_usage is not None:
        metadata["token_usage"] = dict(token_usage)
    return metadata


def _attach_judge_runtime(decision: DecisionOutput, metadata: dict[str, Any]) -> None:
    """Store runtime observability inside the existing additive analysis dict."""
    decision.judge_analysis["judge_runtime"] = metadata

class JudgeAgent:
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self.calibrator = self._load_calibrator()
        self.decision_calibrator = self._load_decision_calibrator()

    @staticmethod
    def _load_decision_calibrator():
        try:
            return DecisionCalibrator()
        except Exception:  # noqa: BLE001 - optional calibrator fallback
            class _Passthrough:
                enabled = False
                def calibrate(self, score):
                    return float(score)
                def status(self):
                    return {"enabled": False, "note": "decision calibrator unavailable"}
            return _Passthrough()

    @staticmethod
    def _load_calibrator():
        try:
            from utils.confidence_calibration import Calibrator
            return Calibrator()
        except Exception:  # noqa: BLE001 - optional calibrator fallback
            class _Passthrough:
                enabled = False
                def calibrate(self, agent, raw):
                    return float(raw)
                def status(self):
                    return {"enabled": False, "note": "calibrator unavailable, passthrough"}
            return _Passthrough()

    def run(self, context: RequestContext, outputs: list[AgentOutput], debate: DebateResult, debate_round: int = 1) -> DecisionOutput:
        kg = query_kg(context.crop, context.query)
        runtime = resolve_judge_config()
        if self.use_llm:
            try:
                return self._run_llm_judge(
                    context, outputs, debate, kg, debate_round, runtime=runtime
                )
            except Exception as exc:  # noqa: BLE001 - single Judge fallback boundary
                reason_code = classify_judge_failure(exc)
                decision = self._run_rule_judge(context, outputs, debate, kg, debate_round)
                detail = redact_error_detail(exc, api_key=runtime.api_key)
                metadata = judge_runtime_metadata(
                    runtime,
                    outcome="fallback",
                    reason_code=reason_code,
                    detail=f"{type(exc).__name__}: {detail}",
                    retry_exhausted=reason_code in {
                        "connection_error", "timeout", "rate_limit", "server_error"
                    },
                )
                _attach_judge_runtime(decision, metadata)
                decision.debate.missing_evidence.append(
                    f"LLM Judge 不可用，已回退规则裁决 "
                    f"[{reason_code}] {type(exc).__name__}: {detail}"
                )
                _logger.warning(
                    "Judge fallback: code=%s provider=%s endpoint=%s model=%s "
                    "sdk_max_retries=%s detail=%s",
                    reason_code,
                    runtime.provider,
                    runtime.endpoint_id,
                    runtime.model,
                    runtime.max_retries,
                    detail,
                )
                return decision
        decision = self._run_rule_judge(context, outputs, debate, kg, debate_round)
        _attach_judge_runtime(
            decision,
            judge_runtime_metadata(
                runtime,
                outcome="rules",
                reason_code="disabled_by_configuration",
                detail="JudgeAgent(use_llm=False)",
            ),
        )
        return decision

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
                except (TypeError, ValueError):
                    pass
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
        """反事实一致性 + 集体漏检分析（规则版与 LLM 版共用）。

        Phase 7A Sprint 02：结构化集体漏检 (ignored_candidates / omission_score /
        omission_reason)，按 omission_score 驱动置信度惩罚（>0.50 减 0.05，上限 0.10，不低于 0.50）。
        """
        omitted = self._collective_omission(outputs, kg)
        retrieved = list(kg.get("diseases", []))
        score = omission_score(len(omitted), len(retrieved))
        reason = omission_reason(omitted)
        action = omission_action(score)
        counterfactuals = [
            {"agent": o.agent, "alternative": (o.counterfactual or {}).get("alternative", ""),
             "rejection_reason": (o.counterfactual or {}).get("rejection_reason", "")}
            for o in outputs if o.layer == "专家层" and o.counterfactual
        ]
        return {
            "omitted_diseases": omitted,
            "penalty_applied": action["level"] == "penalize",
            "controversy_delta": action["confidence_delta"],
            "counterfactuals": counterfactuals,
            "ignored_candidates": omitted,
            "retrieved_candidates": retrieved,
            "omission_score": score,
            "omission_reason": reason,
            "omission_level": action["level"],
            "append_warning": action["append_warning"],
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
        confidence = apply_omission_penalty(confidence, omission["omission_score"])
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
        if omission["append_warning"]: action_plan.append("存在集体忽略风险，建议补充检索KG中未覆盖病害并人工复核")
        need_human_review = bool(vetoed or debate.conflicts or confidence < 0.5 or debate.critic.get("escalate"))
        kg_join = "、".join(consistency["kg_diseases"]) or "无"
        trace_parts = [f"KG参照疾病：{kg_join}"]
        if consistency["rule_violations"]: trace_parts.append("硬约束否决：" + "；".join(consistency["rule_violations"]))
        else: trace_parts.append("未触发KG硬约束否决")
        trace_parts.append(f"风险等级={debate.risk_level}，置信度={confidence}")
        if debate.critic.get("triggered"): trace_parts.append("Critic反驳：" + debate.critic.get("resolution", ""))
        if omission["append_warning"]:
            omitted_join = "、".join(omission["ignored_candidates"]) or "无"
            score_pct = format(omission["omission_score"], ".0%")
            trace_parts.append(f"集体漏检预警：KG中存在专家均未考虑的病害--{omitted_join}（漏检比例 {score_pct}）")
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

    def _run_llm_judge(self, context, outputs, debate, kg, debate_round=1, *, runtime=None):
        config = runtime or resolve_judge_config()
        if not config.configured:
            raise JudgeConfigurationError("未设置 Judge API Key")
        from openai import OpenAI
        outputs, memory_gate = self._gate_memory_outputs(outputs)
        payload = self._build_judge_payload(context, outputs, debate, kg)
        client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
            default_headers=judge_default_headers(),
        )
        _logger.info(
            "Judge request: provider=%s endpoint=%s model=%s "
            "timeout=%ss sdk_max_retries=%s temperature=0.1",
            config.provider,
            config.endpoint_id,
            config.model,
            config.timeout_seconds,
            config.max_retries,
        )
        messages = [
            {"role": "system", "content": self._judge_system_prompt()},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        try:
            resp = client.chat.completions.create(model=config.model, messages=messages, temperature=0.1, response_format={"type": "json_object"})
        except Exception as exc:
            _logger.error(
                "Judge exception: type=%s code=%s provider=%s endpoint=%s model=%s",
                type(exc).__name__,
                classify_judge_failure(exc),
                config.provider,
                config.endpoint_id,
                config.model,
            )
            raise
        try:
            content = resp.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise JudgeResponseFormatError("响应缺少 choices[0].message.content") from exc
        if not isinstance(content, str) or not content.strip():
            raise JudgeResponseFormatError("Judge 返回了空响应")
        try:
            llm = json.loads(content)
        except json.JSONDecodeError as exc:
            raise JudgeResponseFormatError("Judge 响应不是有效 JSON") from exc
        if not isinstance(llm, dict):
            raise JudgeResponseFormatError("Judge 响应必须是 JSON 对象")
        decision_text = llm.get("final_diagnosis") or llm.get("decision")
        if not isinstance(decision_text, str) or not decision_text.strip():
            raise JudgeResponseFormatError("缺少非空 final_diagnosis/decision")
        raw_confidence = llm.get("final_confidence", llm.get("confidence"))
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError) as exc:
            raise JudgeResponseFormatError("final_confidence/confidence 必须是数字") from exc
        if not 0.0 <= confidence <= 1.0:
            raise JudgeResponseFormatError("confidence 必须位于 [0,1]")
        self_report = round(confidence, 2)
        token_usage = self._extract_token_usage(resp)
        _logger.info(
            "Judge response: status=success provider=%s endpoint=%s model=%s usage=%s",
            config.provider,
            config.endpoint_id,
            config.model,
            token_usage,
        )
        fb = self._run_rule_judge(context, outputs, debate, kg, debate_round)
        consistency = self._sample_self_consistency(
            client, config, messages, decision_text.strip(), kg
        )
        signals = compute_decision_signals(
            llm, fb.judge_analysis, debate, consistency.get("agreement")
        )
        structural_score = combine_decision_score(signals)
        confidence = self.decision_calibrator.calibrate(structural_score)
        decision, abstention_policy = self._apply_abstention_policy(
            decision_text.strip(), signals, outputs
        )
        confidence_design = {
            "self_report": self_report,
            "structural_score": structural_score,
            "derived_confidence": confidence,
            "signals": signals,
            "abstention": abstention_policy,
            "self_consistency": consistency,
            "calibration": self.decision_calibrator.status(),
        }
        action_plan = self._clean_string_list(llm.get("action_plan")) or fb.action_plan
        risk_level = str(llm.get("risk_level") or fb.risk_level).lower()
        if risk_level not in {"low", "medium", "high"}: risk_level = fb.risk_level
        need_human_review = bool(llm.get("need_human_review", fb.need_human_review))
        if abstention_policy.get("overridden"): need_human_review = True
        if confidence > 0.9 and (need_human_review or debate.conflicts): confidence = 0.9; need_human_review = True
        summary = str(llm.get("summary") or fb.summary)
        if "DeepSeek" not in summary: summary = f"DeepSeek Judge 结构化裁决：{summary}"
        if debate_round >= 2: summary = f"【第二轮辩论后裁决】{summary}"
        omission = fb.judge_analysis.get("collective_omission", {})
        result = DecisionOutput(summary=summary, decision=decision, confidence=confidence, risk_level=risk_level, action_plan=action_plan[:6], debate=debate, traces=outputs, judge_mode="deepseek", need_human_review=need_human_review, reasoning_trace=str(llm.get("reasoning_trace") or fb.reasoning_trace), judge_analysis={"consistency_analysis": llm.get("consistency_analysis", {}), "evidence_scores": llm.get("evidence_scores", {}), "kg_contribution": llm.get("kg_contribution", ""), "kg": {"diseases": kg.get("diseases", []), "rules": kg.get("rules", []), "backend": kg.get("backend", "memory")}, "critic": debate.critic, "collective_omission": omission, "kg_evolution": fb.judge_analysis.get("kg_evolution", {}), "calibration": self.calibrator.status(), "confidence_design": confidence_design, "memory_gate": memory_gate}, token_usage=token_usage)
        _attach_judge_runtime(
            result,
            judge_runtime_metadata(
                config,
                outcome="success",
                token_usage=token_usage,
            ),
        )
        return result

    @staticmethod
    def _self_consistency_k() -> int:
        try:
            k = int(os.environ.get("AGRI_AI_JUDGE_SELF_CONSISTENCY_K", "3"))
        except ValueError:
            k = 3
        return max(1, min(k, 5))

    def _sample_self_consistency(self, client, config, messages, primary_decision, kg):
        """ADR-005: sample the Judge k times and measure decision agreement.

        Agreement across samples is the only signal in this system that has been
        shown to carry information about correctness; the other aggregate signals
        do not separate correct from wrong decisions.
        """
        k = self._self_consistency_k()
        if k <= 1:
            return {"k": 1, "agreement": None, "labels": []}
        known = [str(d) for d in (kg.get("diseases") or []) if str(d).strip()]
        primary_label = _normalize_label({"decision": primary_decision}, known_labels=known)
        labels = []
        for _ in range(k - 1):
            try:
                resp = client.chat.completions.create(
                    model=config.model,
                    messages=messages,
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )
                data = json.loads(resp.choices[0].message.content)
            except Exception:  # noqa: BLE001 - a failed sample only weakens the signal
                continue
            text = data.get("final_diagnosis") or data.get("decision") or ""
            labels.append(_normalize_label({"decision": text}, known_labels=known))
        if not labels:
            return {"k": k, "agreement": None, "labels": [], "primary_label": primary_label}
        agreement = sum(1 for label in labels if label == primary_label) / len(labels)
        return {
            "k": k,
            "agreement": round(agreement, 4),
            "labels": labels,
            "primary_label": primary_label,
        }

    @staticmethod
    def _gate_memory_outputs(outputs):
        """ADR-005 memory gate: drop low-confidence / no-match memory evidence.

        Memory-layer outputs (RAG, KG, case history, outcome replay) are merged
        into the Judge payload by the orchestrator.  Baseline evidence shows the
        low-confidence ones inject noise (C1 19/24 vs C2 24/24, differing only in
        memory).  Gating happens here, at aggregation, so no frozen module moves.
        """
        if os.environ.get("AGRI_AI_MEMORY_GATE", "1") in {"0", "false", "False"}:
            return list(outputs), {"enabled": False, "dropped": [], "kept": 0}
        try:
            min_conf = float(os.environ.get("AGRI_AI_MEMORY_GATE_MIN_CONF", "0.45"))
        except ValueError:
            min_conf = 0.45
        no_match = ("暂无", "未检索到", "无强匹配", "未命中")
        kept, dropped = [], []
        for output in outputs:
            layer = str(getattr(output, "layer", "") or "")
            if layer != "记忆层":
                kept.append(output)
                continue
            claim = str(getattr(output, "claim", "") or "")
            try:
                confidence = float(getattr(output, "confidence", 0.0) or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
            if confidence < min_conf or any(token in claim for token in no_match):
                dropped.append({
                    "agent": str(getattr(output, "agent", "")),
                    "confidence": round(confidence, 3),
                    "reason": "low_confidence" if confidence < min_conf else "no_match",
                })
                continue
            kept.append(output)
        return kept, {
            "enabled": True,
            "min_confidence": min_conf,
            "kept": sum(1 for o in kept if str(getattr(o, "layer", "")) == "记忆层"),
            "dropped": dropped,
        }

    @staticmethod
    def _plurality_claim(outputs):
        """Most frequent non-abstaining claim; used only to override false abstention."""
        counts = {}
        for output in outputs:
            text = _decision_text(output).strip()
            if not text or _is_abstention(output):
                continue
            counts[text[:40]] = counts.get(text[:40], 0) + 1
        if not counts:
            return ""
        return max(counts.items(), key=lambda item: item[1])[0]

    def _apply_abstention_policy(self, decision, signals, outputs):
        """ADR-005: abstention must be earned by insufficient evidence."""
        if not _is_abstention(decision):
            return decision, {"abstained": False, "overridden": False}
        sufficiency = 0.5 * float(signals.get("kg_support", 0.0)) + 0.5 * float(
            signals.get("evidence_strength", 0.0)
        )
        try:
            threshold = float(os.environ.get("AGRI_AI_ABSTAIN_MIN_SUFFICIENCY", "0.55"))
        except ValueError:
            threshold = 0.55
        detail = {
            "abstained": True,
            "overridden": False,
            "sufficiency": round(sufficiency, 4),
            "threshold": threshold,
        }
        if signals.get("conflict_count", 0) > 0 or sufficiency < threshold:
            return decision, detail
        candidate = self._plurality_claim(outputs)
        if not candidate:
            return decision, detail
        detail.update({"abstained": False, "overridden": True, "candidate": candidate})
        return candidate, detail

    def _build_judge_payload(self, context, outputs, debate, kg):
        sr = self._sensor_readings(outputs)
        return {"现场数据": {"作物": context.crop, "温室": context.greenhouse_id, "意图": context.intent, "症状描述": context.query, "环境参数": sr}, "专家Agent意见": [{"agent": o.agent, "layer": o.layer, "diagnosis": o.claim, "confidence": o.confidence, "evidence": o.evidence, "warnings": o.warnings, "action": o.recommendations, "counterfactual": o.counterfactual, "counterfactual_observations": o.counterfactual_observations} for o in outputs], "知识图谱": {"kg_triples": kg.get("triple_strings", []), "kg_rules": kg.get("rules", []), "hard_constraints": kg.get("hard_constraints", [])}, "debate": asdict(debate), "output_schema": {"final_diagnosis": "最终疾病名称", "final_confidence": "0到1的数字", "need_human_review": "true/false", "summary": "一句中文总结", "risk_level": "low|medium|high", "action_plan": "最多6条可执行中文建议", "reasoning_trace": "300字内裁决逻辑", "consistency_analysis": {"agent_diagnoses": [{"agent": "", "claim": "", "kg_match": "完全匹配/部分匹配/冲突", "conflict_reason": ""}], "critical_conflicts": [], "rule_violations": [], "collective_omission": "KG中存在但所有专家(含反事实)均未提及的病害列表"}, "evidence_scores": {"agent_name": "1-10分数"}, "kg_contribution": "KG对置信度的提升/降低幅度，如+0.15"}}

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
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _extract_token_usage(resp: Any) -> dict[str, int] | None:
        """Extract additive token-usage observability from an LLM response.

        Returns ``None`` when usage is unavailable (rule fallback, API error,
        or the response object lacks the attribute), preserving backward
        compatibility with older traces.
        """
        try:
            usage = resp.usage
            if usage is None:
                return None
            return {
                "judge_prompt_tokens": int(usage.prompt_tokens),
                "judge_completion_tokens": int(usage.completion_tokens),
                "judge_total_tokens": int(usage.total_tokens),
            }
        except (AttributeError, TypeError, ValueError):
            return None
