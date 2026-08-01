# Benchmark Capability Annotation Suggestions

- Generated: 2026-08-01T15:23:42+00:00
- Pending cases: 61

以下为自动推断的能力标注建议，供人工审查。**不会自动写入任何数据集文件**；审查通过后可在 case 的 `metadata.capabilities` 中显式声明。

| Dataset | Case ID | 推荐 capabilities | 推断依据 |
|---|---|---|---|
| easy | tomato_leaf_mold | — | query 关键词推断 |
| easy | tomato_early_blight | — | query 关键词推断 |
| easy | tomato_monitor | uncertainty_quantification | query 关键词推断 |
| easy | tomato_irrigate | uncertainty_quantification, multi_step_planning | query 关键词推断 |
| easy | cucumber_downy_mildew | — | query 关键词推断 |
| easy | sugar_beet_leaf_spot | — | query 关键词推断 |
| easy | sugar_beet_root_rot | — | query 关键词推断 |
| easy | sugar_beet_alert | uncertainty_quantification | query 关键词推断 |
| easy | cotton_verticillium_wilt | — | query 关键词推断 |
| easy | cotton_fusarium_wilt | — | query 关键词推断 |
| easy | cotton_irrigate | uncertainty_quantification, multi_step_planning | query 关键词推断 |
| easy | tomato_consult | uncertainty_quantification | query 关键词推断 |
| medium | tomato_irrigate_with_disease | multi_step_planning | query 关键词推断 |
| medium | tomato_leaf_mold_low_humidity | sensor_cross_validation | query 关键词推断 |
| medium | tomato_early_blight_high_humidity | sensor_cross_validation | query 关键词推断 |
| medium | cucumber_downy_mildew_alert | — | query 关键词推断 |
| medium | sugar_beet_leaf_spot_irrigate | multi_step_planning | query 关键词推断 |
| medium | sugar_beet_root_rot_wet | sensor_cross_validation | query 关键词推断 |
| medium | cotton_verticillium_wilt_weather | — | query 关键词推断 |
| medium | cotton_fusarium_wilt_alert | — | query 关键词推断 |
| medium | tomato_monitor_anomaly | uncertainty_quantification | query 关键词推断 |
| medium | sugar_beet_consult | uncertainty_quantification, multi_step_planning | query 关键词推断 |
| hard | tomato_ambiguous_mold_blight | conflict_resolution | query 关键词推断 |
| hard | tomato_mold_hot_dry | sensor_cross_validation | query 关键词推断 |
| hard | cotton_wilt_anomaly | sensor_cross_validation | query 关键词推断 |
| hard | sugar_beet_root_rot_overwatered | multi_step_planning, sensor_cross_validation | query 关键词推断 |
| hard | tomato_irrigate_after_rain | multi_step_planning | query 关键词推断 |
| hard | cucumber_mold_differentiation | — | query 关键词推断 |
| planning | tomato_leaf_mold_action_plan | multi_step_planning | query 关键词推断 |
| planning | tomato_early_blight_inspection_plan | multi_step_planning | query 关键词推断 |
| planning | sugar_beet_root_rot_weekly_plan | multi_step_planning | query 关键词推断 |
| planning | cotton_verticillium_quarantine_plan | multi_step_planning | query 关键词推断 |
| memory | tomato_leaf_mold_memory | knowledge_retrieval | query 关键词推断 |
| memory | sugar_beet_leaf_spot_memory | knowledge_retrieval | query 关键词推断 |
| memory | cotton_fusarium_memory | knowledge_retrieval | query 关键词推断 |
| memory | cucumber_downy_memory | knowledge_retrieval | query 关键词推断 |
| debate | tomato_irrigate_leaf_mold | conflict_resolution, multi_step_planning | query 关键词推断 |
| debate | sugar_beet_irrigate_leaf_spot | conflict_resolution, multi_step_planning | query 关键词推断 |
| debate | cotton_irrigate_verticillium | conflict_resolution, multi_step_planning | query 关键词推断 |
| debate | tomato_irrigate_early_blight | conflict_resolution, multi_step_planning | query 关键词推断 |
| counterfactual | tomato_mold_blight_ambiguous | conflict_resolution, counterfactual_reasoning | query 关键词推断 |
| counterfactual | tomato_early_blight_alternatives | counterfactual_reasoning | query 关键词推断 |
| counterfactual | sugar_beet_root_rot_nonpathogenic | counterfactual_reasoning | query 关键词推断 |
| adversarial | tomato_mold_low_humidity | conflict_resolution, sensor_cross_validation | query 关键词推断 |
| adversarial | tomato_irrigate_after_rain_anomaly | multi_step_planning, sensor_cross_validation | query 关键词推断 |
| adversarial | cotton_wilt_hot_dry | sensor_cross_validation | query 关键词推断 |
| enriched | mi_tomato_growth_slow | information_gathering, uncertainty_quantification | challenge=missing_information；features=information_request；design_intent=missing_information: 验证症状信息缺失时系统主动请求补充信息 |
| enriched | mi_sugar_beet_partial | information_gathering, uncertainty_quantification, sensor_cross_validation | challenge=missing_information；features=information_request；design_intent=missing_information: 验证长势异常但无典型症状时的信息补全路径 |
| enriched | mi_cotton_unclear | information_gathering, uncertainty_quantification, sensor_cross_validation | challenge=missing_information；features=information_request；design_intent=missing_information: 验证不完整症状描述的询问能力 |
| enriched | ce_tomato_mold_dry | conflict_resolution, counterfactual_reasoning, sensor_cross_validation | challenge=contradictory_evidence；features=conflict_resolution,counterfactual_analysis；design_intent=contradictory_evidence: 验证高湿型病害与低湿环境证据矛盾时的降权裁决 |
| enriched | ce_sugar_beet_root_rot_dry | conflict_resolution, counterfactual_reasoning, sensor_cross_validation | challenge=contradictory_evidence；features=conflict_resolution,counterfactual_analysis；design_intent=contradictory_evidence: 验证喜湿型根腐病与偏干土壤的矛盾判定 |
| enriched | ce_cotton_wilt_hot | conflict_resolution, counterfactual_reasoning, sensor_cross_validation | challenge=contradictory_evidence；features=conflict_resolution,counterfactual_analysis；design_intent=contradictory_evidence: 验证低温型黄萎病与高温环境的矛盾处理 |
| enriched | md_tomato_mold_blight | knowledge_retrieval, conflict_resolution, counterfactual_reasoning | challenge=multi_disease；features=counterfactual_analysis,knowledge_retrieval；design_intent=multi_disease: 验证叶霉病与早疫病并存时的候选排序与反事实排除 |
| enriched | md_sugar_beet_root_rot_plus | knowledge_retrieval, counterfactual_reasoning | challenge=multi_disease；features=counterfactual_analysis,knowledge_retrieval；design_intent=multi_disease: 验证褐斑病与根腐病并存时的优先级判定 |
| enriched | md_cotton_two_wilts | counterfactual_reasoning | challenge=multi_disease；features=counterfactual_analysis；design_intent=multi_disease: 验证棉花黄萎病与枯萎病的相似症状鉴别 |
| enriched | rk_cucumber_downy | knowledge_retrieval | challenge=rare_knowledge；features=knowledge_retrieval；design_intent=rare_knowledge: 验证非主流作物（黄瓜）的病害知识检索 |
| enriched | rk_tomato_nutrient | knowledge_retrieval, uncertainty_quantification, sensor_cross_validation | challenge=rare_knowledge；features=knowledge_retrieval；design_intent=rare_knowledge: 验证缺素/生理性问题的知识边界（非病害库覆盖） |
| enriched | rk_sugar_beet_cracking | knowledge_retrieval, uncertainty_quantification | challenge=rare_knowledge；features=knowledge_retrieval；design_intent=rare_knowledge: 验证非侵染性（生理性开裂）的边界判定 |
| enriched | sc_tomato_irrigate_after_rain | conflict_resolution, multi_step_planning, sensor_cross_validation | challenge=sensor_conflict；features=conflict_resolution；design_intent=sensor_conflict: 验证传感器异常叠加病害风险时的灌溉决策 |
| enriched | sc_cotton_wilt_anomaly | knowledge_retrieval, conflict_resolution, sensor_cross_validation | challenge=sensor_conflict；features=conflict_resolution,knowledge_retrieval；design_intent=sensor_conflict: 验证传感器异常与病害诊断的融合判断 |
| enriched | sc_sugar_beet_overwatered | knowledge_retrieval, conflict_resolution, multi_step_planning, sensor_cross_validation | challenge=sensor_conflict；features=conflict_resolution,knowledge_retrieval；design_intent=sensor_conflict: 验证土壤湿度证据与根腐病诊断的协同 |
