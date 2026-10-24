# ACIS C0/C1/C2 实验与指标审计（2026-10-24）

> 审计对象：仓库内已提交的 Phase 4.2 / Phase 6 原始结果、manifest、报告与本地 trace。
> 审计方式：读取原始 JSON + manifest，用仓库内 `decision_semantics` / `challenge_scorer` 独立复算；不新增模型调用。
> 结论先行：**这些实验足以证明"管线可运行、真实 Judge 通道可成功、fallback 可统计"，不足以证明"完整架构优于裸基线"。**

---

## 1. 实验清单与有效样本

| 实验 | 原始结果 | 时间 | 条件（manifest） | 用例×配置×seed | 调用 | 正常模型回答 | 规则回退 | 无效输出 |
|---|---|---|---|---:|---:|---:|---:|---:|
| Phase 6 基线 | `reports/phase6_baseline_20261023/raw_results.json` | 2026-10-23 | opencode / `deepseek-v4.1-flash` / temp 0.1 / use_llm_judge=true | 24×3×1（seed42） | 72 | **72** | 0 | 0 |
| Phase 6 SC C1 | `reports/phase6_sc_20261023/raw_results_c1_seed42.json` | 2026-10-23 | 同上 + 自一致性 k=3 | 24×1×1（seed42） | 24 | **13** | **11**（`connection_error`，retry_exhausted 11/11） | 0 |
| Phase 6 SC C1 | `reports/phase6_sc43_20261024/raw_results_c1_seed43.json` | 2026-10-24 | 同上 + 采样重试 | 24×1×1（seed43） | 24 | **24** | 0 | 0 |
| Phase 6 消融（WIP，未跟踪） | `reports/phase6_ablation_20261024/raw_results_c0c2_seed43.json` | 2026-10-24 | 同上 | 24×2×1（seed43） | 48 | C0 24 / C2 6 | C2 18（`connection_error`） | 0 |
| Phase 4.2 验证 | `reports/phase4_2_raw_results.json` | 2026-08-10 | `deepseek-v4-flash` / api.deepseek.com / temp 0.1 | 24×3×3（seed42/43/44） | 216 | 215（1 条无效 JSON） | 未记录 | **1** |
| Phase 4.2-R 真实 Agent | `reports/phase4_2_real_agent/raw_results.json` | 2026-08-12 | 真实链路；端点/凭证问题 | 24×3×3 | 216 | **25** | **191** | 0 |
| Phase 4.2-R3 稳定性 | `reports/phase4_2_r3_raw_results.json` | 2026-08-15 | rule-engine coherence judge | 24×3×3 | 216 | **110** | **106** | 0 |

**关键区分**
- **正常模型回答**：`judge_mode=deepseek` 且 `judge_runtime.outcome=success`。
- **最终失败 / 规则回退**：`judge_mode=rules` / `outcome=fallback`；Phase 6 的 SC42 与 ablation C2 可看到 `retry_exhausted=true`，说明重试预算耗尽后回退。
- **重试成功**：**现有 raw 无法区分**。SDK 内部重试次数、每次尝试的结果没有落盘；只记录了最终 `retry_exhausted` 布尔值。因此"正常回答"里可能包含重试成功，但无法统计。
- **有效样本**：所有决策都可评分；但"真实模型有效样本"应只计 `deepseek/success`（上表加粗数），不能用规则回退样本去评价模型/架构。

> Phase 6 消融的 `reports/phase6_ablation_20261024/` 当前**未被 git 跟踪**，且无对应分析报告；本审计将其列为"参考"，不作为交付证据。

---

## 2. Phase 6 基线（seed42，72 次真实 Judge，0 回退）

| config | n | 正常/回退 | label accuracy（复算） | ECE（committed scorer） | corr(conf, correct) | conf mean | 报告值 |
|---|---:|---|---:|---:|---:|---:|---|
| C0 裸基线 | 24 | 24 / 0 | **0.8333（20/24）** | 0.3729 | 0.2491 | 0.4604 | 0.833 / 0.373 / 0.249 ✅ |
| C1 全开 | 24 | 24 / 0 | **0.7917（19/24）** | **0.3758** | 0.1546 | 0.4525 | 0.792 / **0.339** / 0.155 |
| C2 关记忆 | 24 | 24 / 0 | **1.0000（24/24）** | 0.5021 | n/a（无错误样本） | 0.4979 | 1.000 / 0.502 / n/a ✅ |

**审计发现**
1. **C1 的 ECE 不可由 committed scorer 精确复现**：报告写 0.339，用 `challenge_scorer.calc_confidence_calibration` 得 0.3758。差异来自分箱口径——`challenge_scorer.py:154` 使用 `int(conf/bin_size)`，`0.3/0.1=2.9999…→2` 的浮点边界把 conf=0.3 样本放进 [0.2,0.3)，改用区间分箱可得 0.3392。其余 23/24 单元格可精确复现。
2. **报告写"84/84 Judge 调用"**（`baseline_analysis.md:6`），manifest 与 raw 实际为 **72 calls**（24×3×1 seed）。这是文档错误，不影响原始数据。
3. 单 seed、n=24：C0 与 C1 相差 1 例；C2 24/24 只是单 seed 的结果，不能据此宣称"关记忆更好"。

---

## 3. 自一致性（SC）实验：指标依赖未入库的 agreement

| run | 可评样本 | label accuracy | ECE | corr | agreement 分层 |
|---|---:|---:|---:|---:|---|
| seed42（C1） | **13/24**（11 次回退） | 0.8462（11/13） | 0.0769 | 0.7785 | 0.95×10、0.5×3 |
| seed43（C1） | **24/24** | 0.7917（19/24） | 0.0708 | 0.5379 | 0.95×16、0.5×5、0.0×3 |

**审计发现**
- 报告 ECE/corr 的"置信度"是 **`min(0.95, agreement)`**，agreement 只存在于本机 `logs/.../runner/traces/`（gitignored）。用 traces 重建后与报告逐位吻合（0.076923/0.7785、0.070833/0.5379），**报告数字诚实，但 committed raw 不能复算**。
- 用 raw 中的 `confidence` 字段直接复算，会得到不同结果（seed42: 0.0741/13 例或 0.1268/24 例、corr −0.1231；seed43: ECE 0.175、corr 0.5078）。**不要把 raw confidence 当作 agreement 指标。**
- 覆盖范围：只有 C1、2 个 seed；seed42 只有 13/24 可评。结论只能限定为"C1 在 2 个 seed 的 13–24 个有效样本上，agreement 与正确性正相关"，不能外推为"置信度链路已普遍校准"。

---

## 4. Phase 4.2 系列：报告里的 "accuracy" 不是 label accuracy

`scripts/generate_stability_report.py:66-75` 明确写了历史键名映射：

- 报告里的 `accuracy` = **factor coverage（legacy accuracy）**
- 报告里的 `coherence` = **factor coverage level（legacy coherence）**
- `label_accuracy` 是单独字段，但 Phase 4.2-R 的稳定性报告主表未把它作为排名指标。

因此：
- `phase4_2_real_agent/stability_report.md` 的 "C0 accuracy 0.1893 / C1 0.1438" 与 `phase4_2_r3_stability_report.md` 的 "C0 0.3623 / C1 0.2799" 都是 **factor coverage**，不是"诊断准确率"。这类引用属于口径错误，**不应作为公开结论**。
- Phase 4.2 validation 报告（`reports/archive/phase4/phase4_validation_report.md`）**没有 label accuracy**；只有调用数、ABSTAIN、诊断值分布、置信度、coherence。其 216 次调用中 215 有效、1 条 malformed JSON（seed44/C2/case8）。
- 用 `decision_semantics` 对 Phase 4.2 validation 的 `output.diagnosis` 和 GT 做审计侧复算会得到另一组数字（C0 0.597 / C1 0.792 / C2 0.806），但**这不是原报告口径**，只能作为"若换用 label accuracy 会得到什么"的参考，不能替换报告结论，也不能作为公开结论。

---

## 5. 能证明什么、不能证明什么

### 能证明（有原始结果支撑）
1. **真实模型通道可运行**：Phase 6 基线 seed42 的 72/72 次调用均为 `deepseek/success`、有 token usage、零回退；2026-10-19 还有 6/6 零回退的受控验证。
2. **规则回退真实发生且可统计**：Phase 4.2-R 191/216、R3 106/216、SC42 11/24、ablation C2 18/24 均为 rules 回退；回退后系统仍产出决策。
3. **C0/C1/C2 在该条件（seed42、24 例、真实 Judge）下的标签准确率**：C0 20/24、C1 19/24、C2 24/24；可复算。
4. **MVP 离线规则链路**：12/12 fixture、12/12 delivery eval（`reports/delivery_eval/`），可重复。
5. **评测基础设施存在**：固定 Challenge Set 24 例、64 例 benchmark、消融与稳定性脚本、逐 case raw。

### 不能证明
1. **不能证明"完整 ACIS（C1）优于裸基线（C0）"**：单 seed 差 1 例；R3 排名跨 seed 翻转；不同实验的 fallback 率差异巨大，accuracy 不可跨条件比较。
2. **不能证明"关记忆（C2）更好"**：C2 24/24 仅 seed42；另一份未提交的 C2 对照回退率很高，不能作为公开证据。
3. **不能证明置信度校准具有普遍性**：只有 C1、2 seed、有效样本 13/24；指标依赖未入库 agreement。
4. **不能证明生产可靠性/性能**：没有真实田间数据、没有并发/长时间运行、没有外部服务 SLA。
5. **不能把 Phase 4.2-R 的 "accuracy" 当诊断准确率**：它是 factor coverage；且 191/216 是规则回退，模型未真正参与。

---

## 6. 最小补充验证方案（若要形成可公开的架构收益结论）

**E1（主实验，约 1–1.5 小时 / 约 216–432 次调用）**
- 条件：同一 provider/model/temperature；C0/C1/C2 × 24 例 × 3 seeds；**要求记录每次调用**：
  `judge_mode`、`outcome`、`fallback_reason_code`、`retry_attempts`（新增）、`token_usage`、`self_consistency.agreement`（新增）、`confidence`、`decision`、`trace_id`。
- 主指标（预注册）：label accuracy；次指标：ECE、corr、fallback rate、平均延迟/Token。
- 统计：逐 seed 报告 + 3 seed 均值±std；配对 McNemar / bootstrap 95% CI；先报告有效样本数和回退率，再比较 accuracy。
- 通过条件示例：C1 相对 C0 的 95% CI 下界 > 0 且 fallback 率无系统性差异——否则结论写"未发现收益"。

**E2（低成本对照，约 5–10 分钟，无 API）**
- 规则链路下 C0/C1/C2 × 24 例 × 3 seeds（216 次离线运行，`--rules-only`，固定 seed），同口径评分；用于隔离"模块组合"与"模型波动"，不支持 LLM 质量结论。

**E3（可复现性）**
- 将 E1/E2 的 raw、分析脚本、agreement 字段、数据集 sha256 入库；报告同时给出"正常模型回答/回退/无效"计数；否则不得把 accuracy 作为管线收益。

---

## 7. 公开表述建议

可以公开说明：
- "完成 24 例挑战集的 C0/C1/C2 真实 Judge 基线（seed42，72 次调用零回退），并如实记录 C1 未优于 C0。"
- "实现/验证规则回退：在 216 次真实链路调用中统计到 191 次 API 连接失败回退，服务仍可用。"
- "搭建统一 Trace、离线 12 例固定评测与故障注入流程。"

不要作为公开结论：
- "完整架构准确率提升 / 优于基线"；
- "R3 accuracy 0.36 / Phase 4.2 accuracy 0.19"（口径是 factor coverage，不是诊断准确率）；
- "置信度校准已解决"（只有 C1 两 seed、13–24 有效样本）；
- "生产级/真实田间验证"。
