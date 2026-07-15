"""EconomicAgent - 专家层 经济分析（ACIS 2.0）

LLM Agent 的规则化离线实现：System Prompt 内置价格常量表，输入作物/诊断/推荐措施/
环境数据，输出成本分析、不同措施的经济收益对比与经济最优建议。当与 LLM 联用时，
该常量表会作为 system prompt 的一部分注入（见 build_prompt）。
"""
from __future__ import annotations
from agents.types import AgentOutput, RequestContext

# ---- 价格常量表 ----
PRICE_TABLE = {
    "crop_price_per_kg": {"番茄": 3.0, "黄瓜": 2.5, "甜菜": 1.2, "棉花": 8.0},
    "pesticide_cost_per_mu": {
        "多菌灵": 30, "甲基托布津": 40, "百菌清": 35, "杀毒矾": 45,
        "嘧霉胺": 50, "吡虫啉": 25, "印楝素": 60, "枯草芽孢杆菌": 55,
    },
    "labor_per_day": 100,
    "yield_per_mu_kg": {"番茄": 4000, "黄瓜": 5000, "甜菜": 3000, "棉花": 250},
}
CROP_ZH = {"tomato": "番茄", "cucumber": "黄瓜", "sugar_beet": "甜菜", "cotton": "棉花"}

COUNTERFACTUAL_REQUIREMENT = (
    "【反事实要求】在给出诊断后，必须明确给出一个你认为最可能的替代诊断，"
    "并详细解释你为什么排除了它。格式：替代诊断：[名称]，排除理由：[原因]。"
)


class EconomicAgent:
    name = "经济Agent"

    def run(self, context: RequestContext, pathology_output: AgentOutput, cultivation_output: AgentOutput) -> AgentOutput:
        crop_zh = CROP_ZH.get(context.crop, context.crop)
        price = PRICE_TABLE["crop_price_per_kg"].get(crop_zh, 3.0)
        yld = PRICE_TABLE["yield_per_mu_kg"].get(crop_zh, 3000)
        gross = round(price * yld, 0)
        labor = PRICE_TABLE["labor_per_day"]
        pesticides = self._mentioned_pesticides(pathology_output, cultivation_output)
        treat_cost = sum(PRICE_TABLE["pesticide_cost_per_mu"].get(p, 40) for p in pesticides) + labor
        treat_cost = round(treat_cost, 0)
        disease_diagnosed = pathology_output and "病理证据不足" not in pathology_output.claim
        # 经济 vs 技术 冲突：仅当治疗成本占毛收益比重过高、经济学上建议暂缓时触发
        cost_ratio = treat_cost / gross if gross else 1.0
        economic_conflict = disease_diagnosed and cost_ratio > 0.20
        if disease_diagnosed:
            claim = f"经济分析：{crop_zh}毛收益约{gross:.0f}元/亩，防治成本约{treat_cost:.0f}元/亩，净收益{gross - treat_cost:.0f}元/亩"
            recs = [f"防治投入占毛收益{cost_ratio:.0%}，{'建议暂缓化学防治、先观察，控制投入产出比' if economic_conflict else '性价比合理，建议及时防治以保产'}"]
            confidence = 0.62
        else:
            claim = f"经济分析：{crop_zh}毛收益约{gross:.0f}元/亩，暂无明确病害，维持常规管理成本最低"
            recs = ["无病害时以预防性管理为主，避免不必要的农药与人工投入"]
            confidence = 0.58
        counterfactual = {
            "alternative": "全面化学预防" if disease_diagnosed else "加大施肥促产",
            "rejection_reason": "全面化学预防会显著推高成本且增加抗药性风险，经济性劣于精准防治" if disease_diagnosed else "无病害确诊时盲目追肥增产边际效益低且可能引发肥害，经济性不及稳产管理",
        }
        return AgentOutput(
            layer="专家层", agent=self.name, claim=claim, confidence=confidence,
            evidence={"price_table": PRICE_TABLE, "gross_revenue": gross, "treatment_cost": treat_cost,
                      "cost_ratio": round(cost_ratio, 3), "mentioned_pesticides": pesticides,
                      "economic_conflict": economic_conflict},
            warnings=[f"防治成本占比{cost_ratio:.0%}偏高，注意投入产出比"] if economic_conflict else [],
            recommendations=recs, counterfactual=counterfactual,
        )

    @staticmethod
    def _mentioned_pesticides(*outputs) -> list[str]:
        names = list(PRICE_TABLE["pesticide_cost_per_mu"].keys())
        found: list[str] = []
        for out in outputs:
            if not out:
                continue
            text = out.claim + " " + " ".join(out.recommendations)
            for p in names:
                if p in text and p not in found:
                    found.append(p)
        return found

    @staticmethod
    def build_prompt() -> str:
        """供 LLM 模式注入的 system prompt（含价格常量表）。"""
        import json
        return (
            "你是农业多智能体系统中的经济分析 Agent。根据内置价格常量表，对诊断结果与推荐措施"
            "做成本-收益分析，给出经济最优建议。\n价格常量表：\n"
            + json.dumps(PRICE_TABLE, ensure_ascii=False, indent=2)
            + "\n" + COUNTERFACTUAL_REQUIREMENT
        )
