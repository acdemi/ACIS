# Challenge Set v1 — Distribution Analysis & Design (Phase 4)

> **Date**: 2026-08-09 | **Status**: ready for Evidence Review
> **Scope**: root-cause analysis of Phase 3 accuracy saturation, design of
> `benchmarks/challenge_set_v1.json` (24 cases / 4 probe groups), and the new
> metrics in `src/openmetaphysics/evaluation/challenge_scorer.py`.

---

## 1. 现有 64 cases 的分布分析

Phase 3 full scan（`phase3_full_datasets__20260808_193850`）在 9 个数据集、
64 cases、Neo4j 真实图谱后端的全部配置下测得 **accuracy = 1.00 (64/64)**。
分布统计如下：

| dataset | cases | intent 分布 | 症状-关键词覆盖 |
|---|---|---|---|
| easy | 12 | diagnose 8 / irrigate 2 / monitor 1 / consult 1 | 100% |
| medium | 10 | diagnose 6 / irrigate 2 / alert 2 | 100% |
| hard | 6 | diagnose 5 / irrigate 1 | 100% |
| enriched | 18 | mi 3 / ce 3 / md 3 / rk 3 / sc 3 / ig 3 | 100% |
| planning/memory/debate | 12 | 计划、记忆、辩论类 | 100% |
| counterfactual/adversarial | 6 | 反事实、边界裁决 | 100% |

程序化验证（`rag.knowledge_base.search_disease` + 内置 `_DISEASE_KEYWORDS`）：
- 49 个带 ground_truth 的 cases 中，**48 个 query 直接包含目标病害自身的
  关键词**（如 霉层/轮纹/褐斑/根腐/维管束），仅 1 个经通用词表间接命中；
- **49/49 的目标病害是检索结果的 top-1**。

## 2. 准确率饱和的根本原因

1. **Query 症状过于典型（症状词即疾病关键词）**：每个诊断类 query 都原样
   携带 DISEASE_DB 的判别性症状词，子串匹配（`search_disease` 与
   `kg_adapter._relevant_diseases`）必然把目标病害排在 top-1。
2. **区分特征过于明显（无共享词干扰）**：query 只给目标病害的完整特征集，
   从不给"两种病害共享症状 + 决定性特征缺失"的组合，因此匹配分数从不接近。
3. **准确率定义是子串包含**（`evals/metrics.py:_accuracy`，
   `expected in claim`）：claim 形如"病理判断首选：X"，命中即 1.0；
   "证据不足"类 GT 仅要求 claim 含"病理证据不足"——规则引擎零命中时自动
   满足，属于平凡通过。
4. **环境矛盾只压低置信度、不改变决策字符串**：Phase 3 观测到置信度随
   数据集变化（adversarial 0.28 vs memory 0.52）而准确率不变——区分度
   已经存在于置信度，但二元准确率无法承载。
5. **指标天花板**：一旦所有 case 均可子串命中，任何配置消融都无法在准确率
   上产生差异；没有指标奖励"证据不足时正确弃权"、"置信度-正确率一致性"、
   "推理因子覆盖率"。

## 3. Challenge Set 设计（`benchmarks/challenge_set_v1.json`）

24 个新 cases，4 组 × 6 个，全部使用现有知识库实体（AgriKG / DISEASE_DB
的 7 种病害、4 种作物），不引入外部知识。每个 case 含
`id / group / difficulty(1-3) / input / expected_key_factors /
ground_truth / crop / intent`。

| group | 压力来源 | 示例 | 对现有引擎的破坏性 |
|---|---|---|---|
| ambiguity (6) | 共享症状歧义，决定性特征缺失或被否定 | `amb_cotton_edge_vas`（叶缘黄化+维管束褐变、否定半边黄化与萎蔫） | 关键词引擎被误导至枯萎病，正确为黄萎病 |
| conflicting (6) | 环境读数与病害发病条件矛盾 | `conf_cucumber_hot_dry`（霜霉病需 >90% 湿度，棚内 35℃ 干燥） | 决策字符串仍正确，但置信度/风险必须变化 |
| incomplete (6) | 信息缺失、部分关键词误导 | `inc_tomato_vague_spot`（"斑点"同时命中两病通用词表） | 引擎凭字典序盲猜，正确为证据不足（3 个 case 可直接把准确率拉到 0） |
| multi_step (6) | 症状+环境+决策请求串联推理 | `ms_cucumber_downy_irrigate`（诊断→结露风险→灌溉决策） | 单跳关键词命中无法覆盖完整因子集 |

难度分布：d1 × 2（incomplete），d2 × 10，d3 × 12。

隔离性（Part C 由 `tests/test_challenge_set_valid.py` 强制）：
- 文件置于 `benchmarks/challenge_set_v1.json`，不在 `datasets/` 下，
  内置 loader（`benchmarks.datasets.*`）不可达；
- 24 个 id 与 64 个既有 id 零冲突；内置 9 数据集数量不变（合计 64）。

## 4. 新评估指标（`src/openmetaphysics/evaluation/challenge_scorer.py`）

| 函数 | 输出 | 用途 |
|---|---|---|
| `calc_confidence_calibration(outputs)` | ECE ∈ [0,1]，10 bins | 奖励置信度-正确率一致性（Phase 3 观测到置信度变化但无指标承载） |
| `calc_abstention_rate(outputs)` | 百分比 ∈ [0,100] | 奖励证据不足时的正确弃权（incomplete 组核心信号） |
| `calc_reasoning_coherence(output, expected_factors)` | ∈ [0,3] | 用 deepseek-v4-flash 逐因子判定覆盖（LLM 不可用时规则回退，保证可运行） |

关键性质：
- 除模型 API 外无外部依赖；LLM 失败自动回退 `FACTOR_ALIASES` 规则引擎；
- 覆盖判定对"显式排除/说明缺失"同样计分（如"未见半边黄化"覆盖
  `half_leaf_yellowing`），与 ambiguity 组的否定式设计匹配；
- 全部 24 个 case 的 `expected_key_factors` 均已纳入规则别名表
  （`test_every_shipped_factor_has_rule_alias` 强制）。
