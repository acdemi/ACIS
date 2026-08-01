# Benchmark Capability Consistency Report

- Generated: 2026-08-01T16:31:00+00:00
- Annotated cases: 52
- Consistent: 52
- Inconsistent: 0

## 一致性检查（capabilities ↔ observable_evidence ↔ design_intent）

| Dataset | Case ID | Status | Capabilities | Issues |
|---|---|---|---|---|
| easy | tomato_leaf_mold | unannotated | — | — |
| easy | tomato_early_blight | unannotated | — | — |
| easy | tomato_monitor | consistent | uncertainty_quantification | — |
| easy | tomato_irrigate | consistent | multi_step_planning, uncertainty_quantification | — |
| easy | cucumber_downy_mildew | unannotated | — | — |
| easy | sugar_beet_leaf_spot | unannotated | — | — |
| easy | sugar_beet_root_rot | unannotated | — | — |
| easy | sugar_beet_alert | consistent | uncertainty_quantification | — |
| easy | cotton_verticillium_wilt | unannotated | — | — |
| easy | cotton_fusarium_wilt | unannotated | — | — |
| easy | cotton_irrigate | consistent | multi_step_planning, uncertainty_quantification | — |
| easy | tomato_consult | consistent | multi_step_planning, uncertainty_quantification | — |
| medium | tomato_irrigate_with_disease | consistent | conflict_resolution, multi_step_planning | — |
| medium | tomato_leaf_mold_low_humidity | consistent | conflict_resolution | — |
| medium | tomato_early_blight_high_humidity | unannotated | — | — |
| medium | cucumber_downy_mildew_alert | unannotated | — | — |
| medium | sugar_beet_leaf_spot_irrigate | consistent | conflict_resolution, multi_step_planning | — |
| medium | sugar_beet_root_rot_wet | unannotated | — | — |
| medium | cotton_verticillium_wilt_weather | unannotated | — | — |
| medium | cotton_fusarium_wilt_alert | unannotated | — | — |
| medium | tomato_monitor_anomaly | consistent | uncertainty_quantification | — |
| medium | sugar_beet_consult | consistent | multi_step_planning, uncertainty_quantification | — |
| hard | tomato_ambiguous_mold_blight | consistent | counterfactual_reasoning | — |
| hard | tomato_mold_hot_dry | consistent | conflict_resolution, sensor_cross_validation | — |
| hard | cotton_wilt_anomaly | consistent | sensor_cross_validation | — |
| hard | sugar_beet_root_rot_overwatered | consistent | sensor_cross_validation | — |
| hard | tomato_irrigate_after_rain | consistent | multi_step_planning, conflict_resolution, sensor_cross_validation | — |
| hard | cucumber_mold_differentiation | consistent | counterfactual_reasoning | — |
| planning | tomato_leaf_mold_action_plan | consistent | multi_step_planning | — |
| planning | tomato_early_blight_inspection_plan | consistent | multi_step_planning | — |
| planning | sugar_beet_root_rot_weekly_plan | consistent | multi_step_planning | — |
| planning | cotton_verticillium_quarantine_plan | consistent | multi_step_planning | — |
| memory | tomato_leaf_mold_memory | consistent | knowledge_retrieval | — |
| memory | sugar_beet_leaf_spot_memory | consistent | knowledge_retrieval | — |
| memory | cotton_fusarium_memory | consistent | knowledge_retrieval | — |
| memory | cucumber_downy_memory | consistent | knowledge_retrieval | — |
| debate | tomato_irrigate_leaf_mold | consistent | conflict_resolution | — |
| debate | sugar_beet_irrigate_leaf_spot | consistent | conflict_resolution | — |
| debate | cotton_irrigate_verticillium | consistent | conflict_resolution | — |
| debate | tomato_irrigate_early_blight | consistent | conflict_resolution | — |
| counterfactual | tomato_mold_blight_ambiguous | consistent | counterfactual_reasoning | — |
| counterfactual | tomato_early_blight_alternatives | consistent | counterfactual_reasoning | — |
| counterfactual | sugar_beet_root_rot_nonpathogenic | consistent | counterfactual_reasoning | — |
| adversarial | tomato_mold_low_humidity | consistent | conflict_resolution | — |
| adversarial | tomato_irrigate_after_rain_anomaly | consistent | conflict_resolution, sensor_cross_validation | — |
| adversarial | cotton_wilt_hot_dry | consistent | conflict_resolution | — |
| enriched | mi_tomato_growth_slow | consistent | information_gathering | — |
| enriched | mi_sugar_beet_partial | consistent | information_gathering | — |
| enriched | mi_cotton_unclear | consistent | information_gathering | — |
| enriched | ce_tomato_mold_dry | consistent | conflict_resolution | — |
| enriched | ce_sugar_beet_root_rot_dry | consistent | conflict_resolution | — |
| enriched | ce_cotton_wilt_hot | consistent | conflict_resolution | — |
| enriched | md_tomato_mold_blight | consistent | counterfactual_reasoning | — |
| enriched | md_sugar_beet_root_rot_plus | consistent | counterfactual_reasoning | — |
| enriched | md_cotton_two_wilts | consistent | counterfactual_reasoning | — |
| enriched | rk_cucumber_downy | consistent | knowledge_retrieval | — |
| enriched | rk_tomato_nutrient | consistent | knowledge_retrieval, uncertainty_quantification | — |
| enriched | rk_sugar_beet_cracking | consistent | knowledge_retrieval, uncertainty_quantification | — |
| enriched | sc_tomato_irrigate_after_rain | consistent | sensor_cross_validation, conflict_resolution | — |
| enriched | sc_cotton_wilt_anomaly | consistent | sensor_cross_validation, conflict_resolution | — |
| enriched | sc_sugar_beet_overwatered | consistent | sensor_cross_validation | — |
| enriched | ig_tomato_missing_info | consistent | information_gathering | — |
| enriched | ig_sugar_beet_missing_info | consistent | information_gathering | — |
| enriched | ig_cotton_missing_info | consistent | information_gathering | — |

所有已标注案例均通过 Capability → Evidence → Intent 一致性检验。
