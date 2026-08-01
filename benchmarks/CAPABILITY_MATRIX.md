# Benchmark Capability Matrix

- Generated: 2026-08-01T16:31:00+00:00

## 能力套件矩阵

| Suite | Case Count | Planner | Memory | Debate | Counterfactual | Adversarial |
|---|---|---|---|---|---|---|
| planning | 4 | ✓ |  |  |  |  |
| memory | 4 |  | ✓ |  |  |  |
| debate | 4 |  |  | ✓ |  |  |
| counterfactual | 3 |  |  |  | ✓ |  |
| adversarial | 3 |  |  |  |  | ✓ |

## 扩展挑战矩阵（enriched.json）

| Challenge Type | Case Count | 主要 Reasoning Features |
|---|---|---|
| missing_information | 6 | information_request |
| contradictory_evidence | 3 | conflict_resolution, counterfactual_analysis |
| multi_disease | 3 | counterfactual_analysis, knowledge_retrieval |
| rare_knowledge | 3 | knowledge_retrieval |
| sensor_conflict | 3 | conflict_resolution, knowledge_retrieval |

## 数据集清单

| Dataset | Cases | Target |
|---|---|---|
| easy | 12 | difficulty tier（通用回归） |
| medium | 10 | difficulty tier（通用回归） |
| hard | 6 | difficulty tier（通用回归） |
| planning | 4 | capability: planner |
| memory | 4 | capability: memory |
| debate | 4 | capability: debate |
| counterfactual | 3 | capability: counterfactual |
| adversarial | 3 | capability: adversarial |
| enriched | 18 | challenge: 五类认知挑战 |

每个 case 均携带 `design_intent`；enriched case 另带标准化的 `metadata`（challenge_type / expected_reasoning_features / difficulty / crop / disease / noise_level / modalities）。
