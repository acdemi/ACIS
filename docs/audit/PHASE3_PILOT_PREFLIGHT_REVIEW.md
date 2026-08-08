# Phase 3 Pilot — Preflight Architecture Review

> **审查日期**: 2026-08-09
> **状态**: **READY WITH CONDITIONS**
> **审查人**: Research Evidence Auditor（architectural review record）

---

## 科学问题

**Benchmark Discriminability Probe**：hard 数据集（6 个跨病鉴别/异常/边界案例）是否能在当前架构下产生非饱和准确率（accuracy < 1.0）？

背景：Phase 2（`phase2_multiseed__20260808_143600`）在 enriched 数据集上 7 配置 × 5 seeds 准确率全部饱和于 1.000（E009，Confirmed）。hard 数据集包含 Phase 2 中已记录的难点组合（`ce_sugar_beet_root_rot_dry` 类环境矛盾案例、跨病鉴别 `cucumber_mold_differentiation`、`tomato_ambiguous_mold_blight` 等），是区分度的合理候选探针。

## 实验设计

| 项 | 值 |
|---|---|
| 定义 | `experiments/definitions/phase3_pilot_hard.yaml` |
| 数据集 | `benchmarks.datasets.hard`（6 cases） |
| 配置 | 7 模块消融 × 1 seed（42） |
| 预期执行 | 42 case-executions |
| 模型 | `deepseek-v4-flash`（`AGRI_AI_JUDGE_MODEL` / `AGRI_AI_CRITIC_MODEL`） |
| 知识后端 | `AGRI_AI_KG_BACKEND=neo4j`（真实 AgriKG 图谱：149,930 HudongItem / 309,326 RELATION，2026-08-09 导入） |
| 追踪 | `save_traces: true`，`capability_eval: true` |

## 审查条件（必须遵守）

1. **中性叙事**：报告标题使用 "Hard Dataset Discriminability Pilot"，不使用"打破饱和"等方向性用语。
2. **不预设结论**：准确率是否仍为 1.0 均为有效信息；不提前写入任务效度或模块性能结论。
3. **实验后停止**：完成后不自动扩展全量 Phase 3，等待新一轮 Evidence Review。
4. **证据账本冻结**：Pilot 完成前不在 `context/EVIDENCE_LEDGER.md` 更新 hard 数据集区分度条目（仅保留 E011/E012 Hypothesis）。

## 预检结果（2026-08-09 实测）

| 检查项 | 结果 |
|---|---|
| YAML 解析 | ✅ 7 runs × 1 seed，toggle 映射正确 |
| hard 数据集规模 | ✅ 6 cases |
| Neo4j 连接 | ✅ `bolt://localhost:7687` healthy（ACIS compose 项目） |
| KG 后端验证 | ✅ `query_kg('番茄', '叶片黄斑')` 返回 `backend: neo4j`，命中真实图谱实体 |
| 模型配置 | ⚠️ `deepseek-v4-flash` 为评审时指定的模型 ID；若 API 返回无效模型错误，Judge/Critic 将自动回退规则模式（`judge_mode=rules`，trace 可观测）——此回退本身是有效数据点 |
| 预期成本 | ≈ 42 例 × ~6.9k tokens ≈ 29 万 tokens |

## 评审意见（审计员补充，2026-08-09）

- 用户指示在 Pilot 之外追加**全量数据集测试**（9 个 benchmark 数据集 × all_on，seed 42），同样使用 `deepseek-v4-flash` + Neo4j 真实图谱后端，评估大规模/真实知识库下的表现。
- 追加的结论性叙事同样遵循中性原则：仅描述观测到的准确率差异，不解释为"性能提升/下降"。
- Pilot 完成前证据账本保持冻结。

## 决策

**READY WITH CONDITIONS** —— 条件为上述 4 条约束 + 全量测试使用同一中性叙事框架。批准启动 Pilot，完成后停止等待 Evidence Review。
