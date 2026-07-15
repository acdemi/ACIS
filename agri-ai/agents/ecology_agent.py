"""EcologyAgent - 专家层 生态影响评估（ACIS 2.0）

内置农药-天敌对照表。当栽培/病理 Agent 推荐化学农药时，自动检查生态影响并给出
警告或替代方案。高毒农药触发“生态 vs 效率”冲突，中毒农药仅作告警。
"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext

# ---- 农药-天敌对照表 ----
PESTICIDE_ECOLOGY = {
    "吡虫啉": {"toxicity": "高", "affected": "瓢虫/蜜蜂等授粉与天敌昆虫", "alternative": "印楝素或苦参碱"},
    "多菌灵": {"toxicity": "中", "affected": "广谱杀菌，对天敌影响中等", "alternative": "枯草芽孢杆菌"},
    "嘧霉胺": {"toxicity": "中", "affected": "对捕食螨有一定影响", "alternative": "枯草芽孢杆菌配合通风降湿"},
    "百菌清": {"toxicity": "中", "affected": "广谱保护性杀菌剂", "alternative": "波尔多液"},
    "甲基托布津": {"toxicity": "中", "affected": "广谱杀菌剂", "alternative": "木霉菌制剂"},
    "杀毒矾": {"toxicity": "中", "affected": "对水生生物有毒", "alternative": "霜脲氰·锰锌"},
}

COUNTERFACTUAL_REQUIREMENT = (
    "【反事实要求】在给出诊断后，必须明确给出一个你认为最可能的替代诊断，"
    "并详细解释你为什么排除了它。格式：替代诊断：[名称]，排除理由：[原因]。"
)


class EcologyAgent:
    name = "生态Agent"

    def run(self, context: RequestContext, expert_outputs: list[AgentOutput]) -> AgentOutput:
        hits = self._scan_pesticides(expert_outputs)
        warnings, recommendations = [], []
        ecological_conflict = False
        for pesticide, info in hits.items():
            tox = info["toxicity"]
            alt = info["alternative"]
            affected = info["affected"]
            if tox == "高":
                ecological_conflict = True
                warnings.append(f"{pesticide}对{affected}毒性高，建议换用{alt}")
                recommendations.append(f"避免使用{pesticide}，改用{alt}以保护天敌与授粉昆虫")
            else:
                # 中毒农药仅作建议（不计入 warnings，避免抬升风险等级）
                recommendations.append(f"{pesticide}对{affected}影响{tox}，建议轮换或配合{alt}")
        if not recommendations:
            recommendations.append("当前推荐措施生态友好，维持综合防治策略")
        if hits:
            claim = "生态评估：检测到化学农药使用建议，已给出天敌保护替代方案"
            confidence = 0.6
        else:
            claim = "生态评估：未检测到高风险化学农药，当前措施生态兼容"
            confidence = 0.65
        # 反事实：若不采纳生态替代方案
        worst = max((i["toxicity"] for i in hits.values()), default="无")
        counterfactual = {
            "alternative": "坚持使用高毒化学农药快速控病" if hits else "不施加任何生态约束",
            "rejection_reason": (f"高毒农药虽短期见效，但会杀伤{('、'.join(i['affected'] for i in hits.values()))}，破坏天敌-害虫平衡，导致再猖獗"
                                 if hits else "完全不约束农药使用会积累生态风险与抗药性，违背IPM原则"),
        }
        return AgentOutput(
            layer="专家层", agent=self.name, claim=claim, confidence=confidence,
            evidence={"pesticide_ecology": PESTICIDE_ECOLOGY, "detected_pesticides": list(hits.keys()),
                      "ecological_conflict": ecological_conflict, "max_toxicity": worst},
            warnings=warnings, recommendations=recommendations, counterfactual=counterfactual,
        )

    @staticmethod
    def _scan_pesticides(expert_outputs) -> dict:
        hits = {}
        for out in expert_outputs:
            if not out:
                continue
            text = out.claim + " " + " ".join(out.recommendations)
            # 也扫描病理 Agent 证据中的治疗方案
            ev = out.evidence or {}
            if isinstance(ev, dict):
                for d in ev.get("possible_diseases", []):
                    full = d.get("full_info", {}) if isinstance(d, dict) else {}
                    text += " " + " ".join(full.get("treatment", []))
            for p in PESTICIDE_ECOLOGY:
                if p in text and p not in hits:
                    hits[p] = PESTICIDE_ECOLOGY[p]
        return hits
