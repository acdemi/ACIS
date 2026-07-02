"""
农业知识库 MCP Server — 作物病虫害诊断与农事知识
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agri-knowledge")

# ============================================================
# 作物名称映射：英文 → 中文
# ============================================================
CROP_MAP = {
    "tomato": "番茄",
    "cucumber": "黄瓜",
    "pepper": "辣椒",
    "strawberry": "草莓",
    "eggplant": "茄子",
}


def _normalize_crop(crop: str) -> str:
    """将英文作物名转为中文，已是中文则原样返回"""
    if not crop:
        return ""
    return CROP_MAP.get(crop.lower(), crop)


# ============================================================
# 知识库：作物病害数据库
# ============================================================

DISEASE_DB = {
    "tomato_leaf_mold": {
        "name": "番茄叶霉病",
        "crop": "番茄",
        "pathogen": "黄枝孢霉 (Fulvia fulva)",
        "symptoms": [
            "叶片正面出现淡黄色不规则病斑",
            "叶片背面生灰紫色至黑褐色绒状霉层",
            "严重时叶片卷曲、干枯",
            "通常从下部叶片开始向上蔓延",
        ],
        "conditions": {
            "temperature": "20-25°C",
            "humidity": ">85%",
            "ventilation": "通风不良时易发",
        },
        "prevention": [
            "加强通风，降低温室湿度",
            "合理密植，改善株间通风",
            "避免大水漫灌，采用滴灌",
            "及时摘除下部老叶、病叶",
        ],
        "treatment": [
            "发病初期喷施 50% 多菌灵可湿性粉剂 500 倍液",
            "或用 70% 甲基托布津可湿性粉剂 800 倍液",
            "交替用药，每 7-10 天喷一次，连喷 2-3 次",
        ],
        "severity_indicators": {
            "high": ["霉层覆盖面积 > 30%", "已蔓延至上部叶片", "叶片大面积卷曲"],
            "medium": ["霉层可见但覆盖面积 < 30%", "仅下部叶片发病"],
            "low": ["仅个别叶片出现病斑", "无霉层"],
        },
    },
    "tomato_blight": {
        "name": "番茄早疫病",
        "crop": "番茄",
        "pathogen": "茄链格孢 (Alternaria solani)",
        "symptoms": [
            "叶片出现同心轮纹状病斑",
            "病斑边缘呈褐色，中央灰白色",
            "茎部出现椭圆形深褐色病斑",
            "果实蒂部出现凹陷褐色病斑",
        ],
        "conditions": {
            "temperature": "25-30°C",
            "humidity": ">80%",
            "note": "高温高湿交替时最易发生",
        },
        "prevention": [
            "选用抗病品种",
            "轮作倒茬，避免连作",
            "加强水肥管理，增强植株抗性",
            "及时清除病残体",
        ],
        "treatment": [
            "发病初期喷施 75% 百菌清可湿性粉剂 600 倍液",
            "或 64% 杀毒矾可湿性粉剂 500 倍液",
            "每 7 天喷一次，连喷 3-4 次",
        ],
        "severity_indicators": {
            "high": ["病斑数量 > 20 个/株", "茎部出现病斑", "果实已感染"],
            "medium": ["病斑数量 5-20 个/株", "仅叶片发病"],
            "low": ["病斑数量 < 5 个/株", "仅个别叶片"],
        },
    },
    "cucumber_downy_mildew": {
        "name": "黄瓜霜霉病",
        "crop": "黄瓜",
        "pathogen": "古巴假霜霉 (Pseudoperonospora cubensis)",
        "symptoms": [
            "叶片正面出现黄色褪绿斑块",
            "叶片背面出现灰黑色霉层",
            "病斑受叶脉限制呈多角形",
            "湿度大时霉层明显，干燥时病斑易破裂",
        ],
        "conditions": {
            "temperature": "15-22°C",
            "humidity": ">90%",
            "note": "叶面结露是发病关键条件",
        },
        "prevention": [
            "控制温室湿度，避免叶面结露",
            "采用膜下滴灌，减少空气湿度",
            "合理通风，尤其注意早晨排湿",
            "选用抗病品种",
        ],
        "treatment": [
            "发病初期用 72% 霜脲·锰锌可湿性粉剂 600 倍液",
            "或 69% 烯酰吗啉可湿性粉剂 800 倍液",
            "每 5-7 天喷一次，注意叶片背面也要喷到",
        ],
        "severity_indicators": {
            "high": ["病叶率 > 50%", "霉层大面积覆盖", "已蔓延至生长点"],
            "medium": ["病叶率 20-50%", "中下部叶片发病为主"],
            "low": ["病叶率 < 20%", "仅下部个别叶片"],
        },
    },
}

# ============================================================
# 知识库：农事操作指南
# ============================================================

FARMING_GUIDE = {
    "tomato": {
        "name": "番茄种植管理指南",
        "optimal_conditions": {
            "air_temp_day": "22-28°C",
            "air_temp_night": "15-18°C",
            "soil_moisture": "60-80% 田间持水量",
            "soil_ph": "6.0-7.0",
            "co2": "800-1200 ppm（温室补充 CO2 时）",
            "light": "20000-40000 lux",
        },
        "growth_stages": {
            "苗期": {"duration": "30-40天", "key_tasks": ["控水蹲苗", "适当降温炼苗", "防治猝倒病"]},
            "开花期": {"duration": "15-20天", "key_tasks": ["辅助授粉（振荡授粉）", "控制氮肥", "保持稳定温度"]},
            "结果期": {"duration": "60-90天", "key_tasks": ["加强水肥", "及时采收", "预防早疫病和叶霉病"]},
        },
        "irrigation": {
            "method": "滴灌",
            "frequency": "结果期每 2-3 天一次",
            "amount": "每次 15-20 m³/亩",
            "notes": "避免大水漫灌，保持土壤湿度稳定",
        },
    },
    "cucumber": {
        "name": "黄瓜种植管理指南",
        "optimal_conditions": {
            "air_temp_day": "25-30°C",
            "air_temp_night": "15-18°C",
            "soil_moisture": "70-85% 田间持水量",
            "soil_ph": "6.0-7.5",
            "co2": "600-1000 ppm",
            "light": "20000-35000 lux",
        },
        "growth_stages": {
            "苗期": {"duration": "25-35天", "key_tasks": ["温度管理", "间苗定苗", "预防猝倒病"]},
            "初花期": {"duration": "10-15天", "key_tasks": ["引蔓上架", "控制浇水", "预防霜霉病"]},
            "结瓜期": {"duration": "50-80天", "key_tasks": ["及时采收", "加强肥水", "重点防治霜霉病和白粉病"]},
        },
        "irrigation": {
            "method": "滴灌或沟灌",
            "frequency": "结瓜期每天或隔天一次",
            "amount": "每次 10-15 m³/亩",
            "notes": "黄瓜需水量大，但忌积水",
        },
    },
}

# ============================================================
# 症状关键词 → 疾病映射（用于匹配）
# ============================================================

_DISEASE_KEYWORDS = {
    "tomato_leaf_mold": ["黄斑", "黄色", "霉层", "霉", "灰紫色", "绒状", "卷曲", "叶片背面"],
    "tomato_blight": ["轮纹", "同心", "褐色", "灰白", "凹陷", "茎部"],
    "cucumber_downy_mildew": ["多角", "黄色褪绿", "灰黑色", "霉层", "结露", "叶片背面"],
}


# ============================================================
# MCP Tools
# ============================================================

@mcp.tool()
def search_disease(symptoms: str, crop: str = "") -> list[dict]:
    """根据症状描述搜索可能的病害。

    Args:
        symptoms: 症状描述，如"叶片背面有灰色霉层"
        crop: 作物名称（可选），中英文均可，如 tomato/番茄, cucumber/黄瓜
    """
    crop_zh = _normalize_crop(crop)

    results = []
    for disease_id, disease in DISEASE_DB.items():
        # 作物过滤
        if crop_zh and crop_zh not in disease["crop"]:
            continue

        # 关键词匹配
        match_score = 0
        matched_symptoms = []

        # 方式1: 检查知识库中预定义的疾病关键词是否出现在查询中
        disease_keywords = _DISEASE_KEYWORDS.get(disease_id, [])
        for kw in disease_keywords:
            if kw in symptoms:
                match_score += 1.0

        # 方式2: 逐条匹配症状描述中的关键词
        query_words = ["黄斑", "霉层", "灰色", "霉", "枯", "烂", "斑", "卷",
                       "轮纹", "多角", "水渍", "凹陷", "褐色", "灰白", "绒状", "背面"]
        for symptom in disease["symptoms"]:
            for word in query_words:
                if word in symptoms and word in symptom:
                    match_score += 1.0
                    if symptom not in matched_symptoms:
                        matched_symptoms.append(symptom)
                    break

        if match_score > 0:
            results.append({
                "disease_id": disease_id,
                "name": disease["name"],
                "crop": disease["crop"],
                "match_score": round(match_score, 1),
                "matched_symptoms": matched_symptoms,
                "full_info": disease,
            })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:5]


@mcp.tool()
def get_disease_info(disease_id: str) -> dict:
    """获取特定病害的详细信息。

    Args:
        disease_id: 病害ID，如 tomato_leaf_mold, cucumber_downy_mildew
    """
    disease = DISEASE_DB.get(disease_id)
    if not disease:
        return {"error": f"未找到病害: {disease_id}，可用ID: {list(DISEASE_DB.keys())}"}
    return disease


@mcp.tool()
def get_farming_guide(crop: str) -> dict:
    """获取作物种植管理指南。

    Args:
        crop: 作物名称，中英文均可 (tomato/番茄, cucumber/黄瓜)
    """
    crop_en = crop.lower() if crop else ""
    # 也尝试中文反查
    reverse_map = {v: k for k, v in CROP_MAP.items()}
    if crop in reverse_map:
        crop_en = reverse_map[crop]

    guide = FARMING_GUIDE.get(crop_en)
    if not guide:
        return {"error": f"未找到 {crop} 的种植指南，可用: {list(FARMING_GUIDE.keys())}"}
    return guide


@mcp.tool()
def get_optimal_conditions(crop: str, growth_stage: str = "") -> dict:
    """获取作物在特定生长阶段的最佳环境条件。

    Args:
        crop: 作物名称 (tomato/番茄, cucumber/黄瓜)
        growth_stage: 生长阶段（可选），如 开花期, 结果期
    """
    crop_en = crop.lower() if crop else ""
    reverse_map = {v: k for k, v in CROP_MAP.items()}
    if crop in reverse_map:
        crop_en = reverse_map[crop]

    guide = FARMING_GUIDE.get(crop_en)
    if not guide:
        return {"error": f"未找到 {crop} 的数据"}

    result = {
        "crop": crop,
        "optimal_conditions": guide["optimal_conditions"],
    }

    if growth_stage and growth_stage in guide.get("growth_stages", {}):
        result["stage"] = growth_stage
        result["stage_info"] = guide["growth_stages"][growth_stage]

    return result


@mcp.tool()
def diagnose_and_advise(
    crop: str,
    symptoms: str,
    current_conditions: dict = None,
) -> dict:
    """综合诊断工具：结合症状、当前环境条件和知识库，给出诊断和建议。

    Args:
        crop: 作物名称
        symptoms: 症状描述
        current_conditions: 当前环境条件（可选），如 {"temperature": 30, "humidity": 90}
    """
    # 1. 检索可能的病害
    diseases = search_disease(symptoms, crop)

    # 2. 获取最佳条件
    optimal = get_optimal_conditions(crop)

    # 3. 如果有当前条件，做偏差分析
    condition_issues = []
    if current_conditions:
        if "temperature" in current_conditions:
            temp = current_conditions["temperature"]
            if temp > 32:
                condition_issues.append(f"温度偏高（{temp}°C），可能加重病害")
            elif temp < 15:
                condition_issues.append(f"温度偏低（{temp}°C），可能影响生长")

        if "humidity" in current_conditions:
            hum = current_conditions["humidity"]
            if hum > 85:
                condition_issues.append(f"湿度过高（{hum}%），真菌病害风险增大")
            elif hum < 40:
                condition_issues.append(f"湿度过低（{hum}%），可能影响授粉")

    return {
        "possible_diseases": diseases[:3],
        "environment_issues": condition_issues,
        "optimal_conditions": optimal.get("optimal_conditions", {}),
        "recommended_actions": [
            "优先改善通风，降低湿度" if any("湿度" in i for i in condition_issues) else "维持当前环境管理",
            "密切观察症状变化，记录发展过程",
            "如症状加重，建议取样送检确认病原",
        ],
    }


# ============================================================
# MCP Resources
# ============================================================

@mcp.resource("knowledge://diseases")
def list_all_diseases() -> str:
    """所有已收录病害的概览"""
    lines = ["=== 农业病害知识库概览 ===\n"]
    for did, d in DISEASE_DB.items():
        lines.append(f"• {d['name']} ({d['crop']}) — ID: {did}")
        lines.append(f"  病原: {d['pathogen']}")
        lines.append(f"  主要症状: {d['symptoms'][0]}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
