"""Critic / 反驳轮次：debate → critic → judge 流程中的二次裁决。

冲突时执行"反驳"：识别对立双方、衡量证据、对较弱方降权并记录裁决。两种模式：
- 规则模式（默认，确定性）：依据传感器读数 + 症状强度判定灌溉 vs 病害/湿度风险等。
- LLM 模式（``use_llm=True``）：用 DeepSeek 对冲突做多轮结构化反驳裁决，每轮输出
  winner/loser/resolution/adjustments 并据此调整置信度；若该轮 ``escalate=true`` 且未达
  ``max_rounds``，则带上一轮结论再裁决一轮，最终仍无法判定才升级人工复核。无 key 或调用
  失败时自动回退规则模式。

无冲突时为空操作，冲突-free 的运行行为完全不变。结果写入 ``DebateResult.critic``，
Judge 据此调整融合与人工复核标记，``format_decision`` 透出【Critic 反驳轮次】。
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # 仅类型提示，运行时不导入 orchestrator，避免循环依赖
    from orchestrator import AgentOutput, DebateResult, RequestContext

HIGH_HUMIDITY = 80.0
LOW_HUMIDITY = 55.0
DISEASE_CLAIM_PREFIX = "病理判断首选："
DISEASE_INSUFFICIENT = "病理证据不足"


def _sensor_humidity(outputs: list[Any]) -> float | None:
    sensor = next((o for o in outputs if o.agent == "传感器Agent"), None)
    if sensor is None:
        return None
    readings = sensor.evidence.get("reading", {}).get("readings", {})
    value = readings.get("air_humidity")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _sensor_readings(outputs: list[Any]) -> dict[str, float]:
    sensor = next((o for o in outputs if o.agent == "传感器Agent"), None)
    if sensor is None:
        return {}
    readings = sensor.evidence.get("reading", {}).get("readings", {})
    out: dict[str, float] = {}
    for key in ("air_humidity", "air_temperature", "soil_moisture", "co2"):
        value = readings.get(key)
        if value is None:
            continue
        try:
            out[key] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _agent(outputs: list[Any], name: str) -> Any | None:
    return next((o for o in outputs if o.agent == name), None)


class CriticEngine:
    """确定性 + 可选 LLM 多轮反驳引擎：冲突时降权较弱方并记录裁决；无冲突时空操作。"""

    name = "CriticAgent"

    def __init__(self, use_llm: bool = False, max_rounds: int = 2):
        self.use_llm = use_llm
        self.max_rounds = max(1, max_rounds)

    def run(
        self,
        context: Any,
        outputs: list[Any],
        debate: Any,
    ) -> tuple[list[Any], Any]:
        if not debate.conflicts:
            return outputs, debate  # 无冲突：空操作，行为不变

        if self.use_llm:
            try:
                result = self._llm_multi_round(context, outputs, debate)
                if result is not None:
                    return result
            except Exception as exc:  # LLM 失败 → 回退规则，并记录原因
                refined, debate2 = self._rules_resolve(context, outputs, debate)
                return refined, replace(debate2, critic={**debate2.critic, "llm_error": str(exc)})

        return self._rules_resolve(context, outputs, debate)

    # ------------------------------------------------------------------
    # 规则模式
    # ------------------------------------------------------------------

    def _rules_resolve(self, context: Any, outputs: list[Any], debate: Any) -> tuple[list[Any], Any]:
        meteorology = _agent(outputs, "气象Agent")
        pathology = _agent(outputs, "病理Agent")
        cultivation = _agent(outputs, "栽培Agent")

        irrigation_on = bool(meteorology and "支持灌溉" in meteorology.claim)
        high_hum_warning = any(
            "湿度偏高" in w for w in (cultivation.warnings if cultivation else [])
        )
        disease_claimed = bool(
            pathology
            and DISEASE_CLAIM_PREFIX in pathology.claim
            and DISEASE_INSUFFICIENT not in pathology.claim
        )
        humidity = _sensor_humidity(outputs)
        high_humidity = humidity is not None and humidity > HIGH_HUMIDITY
        intent = getattr(context, "intent", "") if context else ""
        irrigation_conflict = irrigation_on and (
            high_hum_warning or high_humidity or (disease_claimed and intent == "irrigate")
        )
        if irrigation_conflict:
            return self._resolve_irrigation_vs_risk(
                outputs, debate, meteorology, pathology, humidity, high_hum_warning, disease_claimed
            )
        if disease_claimed and humidity is not None and humidity < LOW_HUMIDITY:
            return self._resolve_disease_vs_env(outputs, debate, pathology, humidity)

        critic = {
            "triggered": True,
            "rounds": 1,
            "mode": "rules",
            "conflict_type": "unresolved",
            "resolution": "反驳轮次无法判定胜负，建议人工复核并补充证据",
            "escalate": True,
        }
        return outputs, replace(debate, critic=critic)

    @staticmethod
    def _resolve_irrigation_vs_risk(
        outputs: list[Any],
        debate: Any,
        meteorology: Any,
        pathology: Any,
        humidity: float | None,
        high_hum_warning: bool,
        disease_claimed: bool,
    ) -> tuple[list[Any], Any]:
        high_humidity = humidity is not None and humidity > HIGH_HUMIDITY
        reason_parts: list[str] = []
        if disease_claimed and pathology is not None:
            disease_name = pathology.claim.replace(DISEASE_CLAIM_PREFIX, "")
            reason_parts.append(f"病理已诊断{disease_name}")
        if high_humidity:
            reason_parts.append(f"棚内湿度{humidity}%偏高")
        if high_hum_warning:
            reason_parts.append("栽培Agent已预警湿度偏高")
        reason = "；".join(reason_parts) or "病害/湿度风险优先"

        original_conf = float(meteorology.confidence) if meteorology else 0.72
        new_conf = max(0.15, round(original_conf * 0.6, 2))

        refined: list[Any] = []
        for output in outputs:
            if output.agent == "气象Agent":
                refined.append(
                    replace(
                        output,
                        confidence=new_conf,
                        warnings=list(output.warnings) + [f"Critic反驳：{reason}，灌溉建议降权"],
                        evidence={**output.evidence, "rebuttal": {"down_weighted": True, "reason": reason}},
                    )
                )
            else:
                refined.append(output)

        critic = {
            "triggered": True,
            "rounds": 1,
            "mode": "rules",
            "conflict_type": "irrigation_vs_disease_risk",
            "winner": "病理/栽培Agent（病害风险优先）",
            "loser": "气象Agent（灌溉建议）",
            "resolution": f"反驳轮次裁定：{reason}；暂缓灌溉，先控湿防病",
            "down_weighted": [{"agent": "气象Agent", "from": original_conf, "to": new_conf}],
            "escalate": False,
        }
        new_consensus = list(debate.consensus) + [critic["resolution"]]
        return refined, replace(debate, consensus=new_consensus, critic=critic)

    @staticmethod
    def _resolve_disease_vs_env(
        outputs: list[Any], debate: Any, pathology: Any, humidity: float
    ) -> tuple[list[Any], Any]:
        """高湿型病害 vs 低湿环境：环境不支持该病害高发，降权病理诊断并建议复核。"""
        disease_name = pathology.claim.replace(DISEASE_CLAIM_PREFIX, "").strip()
        original_conf = float(pathology.confidence)
        new_conf = max(0.15, round(original_conf * 0.55, 2))
        reason = f"当前空气湿度{humidity}%偏低，不支持{disease_name}等高湿型病害高发，病理诊断降权"
        refined: list[Any] = []
        for output in outputs:
            if output.agent == "病理Agent":
                refined.append(
                    replace(
                        output,
                        confidence=new_conf,
                        warnings=list(output.warnings) + [f"Critic反驳：{reason}"],
                        evidence={**output.evidence, "rebuttal": {"down_weighted": True, "reason": reason}},
                    )
                )
            else:
                refined.append(output)
        critic = {
            "triggered": True,
            "rounds": 1,
            "mode": "rules",
            "conflict_type": "disease_vs_low_humidity",
            "winner": "传感器/栽培Agent（环境数据）",
            "loser": "病理Agent（诊断存疑）",
            "resolution": f"反驳轮次裁定：{reason}；建议复核现场湿度趋势并采样送检",
            "down_weighted": [{"agent": "病理Agent", "from": original_conf, "to": new_conf}],
            "escalate": False,
        }
        new_consensus = list(debate.consensus) + [critic["resolution"]]
        return refined, replace(debate, consensus=new_consensus, critic=critic)

    # ------------------------------------------------------------------
    # LLM 多轮模式（DeepSeek 结构化反驳）
    # ------------------------------------------------------------------

    def _llm_multi_round(
        self,
        context: Any,
        outputs: list[Any],
        debate: Any,
    ) -> tuple[list[Any], Any] | None:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return None  # 无 key → 交由 run() 回退规则

        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        model = os.environ.get("AGRI_AI_CRITIC_MODEL") or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

        current_outputs = outputs
        rounds_log: list[dict[str, Any]] = []
        final_critic: dict[str, Any] = {}
        last_verdict: dict[str, Any] = {}
        round_num = 0

        for round_num in range(1, self.max_rounds + 1):
            verdict = self._llm_call(client, model, context, current_outputs, debate, round_num, last_verdict)
            current_outputs, critic = self._apply_verdict(current_outputs, verdict, model, round_num)
            rounds_log.append(
                {
                    "round": round_num,
                    "winner": verdict.get("winner"),
                    "loser": verdict.get("loser"),
                    "resolution": verdict.get("resolution"),
                    "escalate": verdict.get("escalate"),
                    "down_weighted": critic.get("down_weighted"),
                }
            )
            final_critic = critic
            last_verdict = verdict
            if not verdict.get("escalate"):
                break  # 该轮已裁定，无需再反驳

        final_critic = {
            **final_critic,
            "triggered": True,
            "rounds": round_num,
            "mode": "llm",
            "model": model,
            "conflict_type": "llm_rebuttal",
            "rounds_log": rounds_log,
        }
        resolution = final_critic.get("resolution", "")
        new_consensus = list(debate.consensus) + ([resolution] if resolution else [])
        return current_outputs, replace(debate, consensus=new_consensus, critic=final_critic)

    def _llm_call(
        self,
        client: Any,
        model: str,
        context: Any,
        outputs: list[Any],
        debate: Any,
        round_num: int,
        prev_verdict: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._build_rebuttal_payload(context, outputs, debate, round_num, prev_verdict)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self._rebuttal_system_prompt(round_num)},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)

    @staticmethod
    def _build_rebuttal_payload(
        context: Any,
        outputs: list[Any],
        debate: Any,
        round_num: int = 1,
        prev_verdict: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "现场": {
                "作物": getattr(context, "crop", ""),
                "温室": getattr(context, "greenhouse_id", ""),
                "意图": getattr(context, "intent", ""),
                "症状/问题": getattr(context, "query", ""),
                "传感器读数": _sensor_readings(outputs),
            },
            "debate冲突": list(debate.conflicts),
            "专家意见": [
                {
                    "agent": o.agent,
                    "claim": o.claim,
                    "confidence": o.confidence,
                    "warnings": list(o.warnings),
                }
                for o in outputs
                if o.layer == "专家层"
            ],
            "当前轮次": round_num,
            "输出要求": {
                "winner": "胜方 agent 名称或一方描述",
                "loser": "败方 agent 名称或一方描述",
                "resolution": "一句中文裁决，说明为何这一方证据更强",
                "adjustments": [{"agent": "被降权 agent 名称", "factor": "0.1-1.0 之间的保留系数"}],
                "escalate": "true/false，是否仍需人工复核或下一轮再辩",
            },
        }
        if round_num > 1 and prev_verdict:
            payload["上一轮裁决"] = {
                "winner": prev_verdict.get("winner"),
                "resolution": prev_verdict.get("resolution"),
                "escalate": prev_verdict.get("escalate"),
                "提示": "上一轮标记 escalate=true 仍存疑，请基于当前（已降权）证据给出最终裁决；仍无法判定则 escalate=true。",
            }
        return payload

    @staticmethod
    def _rebuttal_system_prompt(round_num: int = 1) -> str:
        base = (
            "你是农业多智能体系统中的 Critic（反驳裁判）。Debate 阶段发现了专家间的冲突，"
            "你的任务是对冲突做一次结构化反驳裁决：综合症状、传感器读数与各专家证据，判定哪一方证据更强，"
            "对较弱一方的置信度给出保留系数（0.1-1.0），并给出一句裁决理由。"
        )
        rule = (
            "规则：必须基于现场证据裁决，不得凭空判断；证据不足时 escalate=true；"
            "只对确实存在冲突的专家给 adjustments；factor 越小降权越多；"
            "只输出 JSON，字段严格为：winner, loser, resolution, adjustments, escalate。"
        )
        if round_num > 1:
            base = "【多轮反驳·第 %d 轮】" % round_num + base + "这是后续轮次，请基于上一轮结论与当前已降权的证据做最终裁定。"
        return base + "\n" + rule

    @staticmethod
    def _apply_verdict(
        outputs: list[Any],
        verdict: dict[str, Any],
        model: str,
        round_num: int,
    ) -> tuple[list[Any], dict[str, Any]]:
        adjustments = verdict.get("adjustments") or []
        if not isinstance(adjustments, list):
            adjustments = []
        factor_by_agent: dict[str, float] = {}
        for adj in adjustments:
            if not isinstance(adj, dict):
                continue
            agent = str(adj.get("agent", "")).strip()
            try:
                factor = float(adj.get("factor", 1.0))
            except (TypeError, ValueError):
                factor = 1.0
            factor = max(0.1, min(1.0, factor))
            if agent:
                factor_by_agent[agent] = factor

        refined: list[Any] = []
        down_weighted: list[dict[str, Any]] = []
        for output in outputs:
            factor = factor_by_agent.get(output.agent)
            if factor is not None and factor < 1.0:
                new_conf = max(0.1, round(float(output.confidence) * factor, 2))
                down_weighted.append({"agent": output.agent, "from": float(output.confidence), "to": new_conf})
                refined.append(
                    replace(
                        output,
                        confidence=new_conf,
                        warnings=list(output.warnings) + [f"Critic反驳(LLM·r{round_num})：{verdict.get('resolution', '')}"],
                        evidence={**output.evidence, "rebuttal": {"down_weighted": True, "factor": factor, "round": round_num}},
                    )
                )
            else:
                refined.append(output)

        critic = {
            "triggered": True,
            "mode": "llm",
            "model": model,
            "conflict_type": "llm_rebuttal",
            "winner": str(verdict.get("winner", "")),
            "loser": str(verdict.get("loser", "")),
            "resolution": str(verdict.get("resolution", "")),
            "down_weighted": down_weighted,
            "escalate": bool(verdict.get("escalate", False)),
        }
        return refined, critic
