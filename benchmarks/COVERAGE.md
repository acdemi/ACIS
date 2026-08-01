# Benchmark Coverage Report

- Generated: 2026-08-01T15:23:42+00:00
- Datasets: 9
- Total cases: 61

## Dataset Inventory

| Dataset | Cases | Target | metadata complete |
|---|---|---|---|
| easy | 12 | difficulty tier（通用回归） | n/a（非 enriched） |
| medium | 10 | difficulty tier（通用回归） | n/a（非 enriched） |
| hard | 6 | difficulty tier（通用回归） | n/a（非 enriched） |
| planning | 4 | capability: planner | n/a（非 enriched） |
| memory | 4 | capability: memory | n/a（非 enriched） |
| debate | 4 | capability: debate | n/a（非 enriched） |
| counterfactual | 3 | capability: counterfactual | n/a（非 enriched） |
| adversarial | 3 | capability: adversarial | n/a（非 enriched） |
| enriched | 15 | challenge: 五类认知挑战 | 15/15 |

## Capability Suite Coverage

| Module | Suite Cases | design_intent |
|---|---|---|
| planner | 4 | 4 |
| memory | 4 | 4 |
| debate | 4 | 4 |
| counterfactual | 3 | 3 |
| adversarial | 3 | 3 |

## Enriched Challenge Coverage

| Challenge Type | Cases | metadata complete | reasoning features covered |
|---|---|---|---|
| missing_information | 3 | 3 | information_request |
| contradictory_evidence | 3 | 3 | conflict_resolution, counterfactual_analysis |
| multi_disease | 3 | 3 | counterfactual_analysis, knowledge_retrieval |
| rare_knowledge | 3 | 3 | knowledge_retrieval |
| sensor_conflict | 3 | 3 | conflict_resolution, knowledge_retrieval |

## Summary

- Capability suite cases with design_intent: 18/18
- Enriched cases passing the full metadata contract: 15/15
- 设计原则：真实性优先于难度 —— 每个 case 来源于真实农业场景，目标是区分模块能力而非让系统犯错。
