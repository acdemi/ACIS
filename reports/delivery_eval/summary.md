# ACIS 离线农业诊断回归评测

- 数据集：`evals.fixtures`（12 例）
- 运行模式：RAG=memory / KG=memory / LLM Judge=disabled / LLM Critic=disabled / SQLite 持久化=off
- 固定模拟时钟：`2026-06-15T10:00:00`；运行延迟仍按实际执行耗时测量。
- 结果边界：这些是工程回归夹具，不是人工确认标签或真实田间诊断质量评测。
- 计分：按夹具的参考意图选择 Diagnosis Accuracy 分母；另报系统实际意图准确率。病名只做裁剪前缀规范化后的精确匹配。

| 用例 | 参考/实际意图 | 参考标签 | 最终决策 | Diagnosis | Top-3 | 耗时(ms) | Trace 事件 |
|---|---|---|---|---|---|---:|---:|
| tomato_leaf_mold | diagnose/diagnose | 叶霉病 | 病理判断首选：番茄叶霉病 | PASS | PASS | 4076.460 | 22 |
| tomato_early_blight | diagnose/diagnose | 早疫病 | 病理判断首选：番茄早疫病 | PASS | PASS | 22.060 | 22 |
| tomato_irrigate_with_risk | irrigate/irrigate | - | 气象条件支持灌溉 | 不计分 | 不计分 | 15.680 | 19 |
| tomato_monitor_no_disease | monitor/monitor | 证据不足 | 已生成栽培管理建议 | 不计分 | 不计分 | 14.108 | 19 |
| sugar_beet_leaf_spot | diagnose/diagnose | 褐斑病 | 病理判断首选：甜菜褐斑病 | PASS | PASS | 15.354 | 22 |
| sugar_beet_root_rot | diagnose/diagnose | 根腐病 | 病理判断首选：甜菜根腐病 | PASS | PASS | 16.615 | 22 |
| sugar_beet_alert | alert/alert | 证据不足 | 已生成栽培管理建议 | 不计分 | 不计分 | 18.106 | 19 |
| cotton_verticillium_wilt | diagnose/diagnose | 黄萎病 | 病理判断首选：棉花黄萎病 | PASS | PASS | 23.460 | 22 |
| cotton_fusarium_wilt | diagnose/diagnose | 枯萎病 | 病理判断首选：棉花枯萎病 | PASS | PASS | 16.143 | 22 |
| cotton_irrigate | irrigate/irrigate | 证据不足 | 气象条件支持灌溉 | 不计分 | 不计分 | 15.260 | 19 |
| tomato_irrigate_with_disease | irrigate/irrigate | 叶霉病 | 气象条件支持灌溉 | 不计分 | 不计分 | 16.534 | 22 |
| tomato_mold_low_humidity | diagnose/diagnose | 叶霉病 | 已生成栽培管理建议 | FAIL | PASS | 14.381 | 22 |

- Diagnosis Accuracy：6/7（0.8571）
- Top-3 Accuracy：7/7（1.0；以系统候选列表和单标签夹具计算）
- 意图分类准确率：12/12（1.0；独立于诊断准确率）
- 执行延迟：平均 355.347 ms / P50 16.338 ms / P95 1847.31 ms（本地离线流水线，不代表生产延迟）
- 平均置信度：0.655（仅描述性统计，不是校准指标）
- Critic 触发：2 例；这不是 Agent Fallback Rate。

## 未测量指标

- macro_f1：未测量（fixture set does not provide expert-reviewed multi-class labels）。
- factor_coverage：未测量（no reference factors are annotated for these fixtures）。
- abstention_quality：未测量（no expert-reviewed insufficient-evidence diagnosis set）。
- confidence_calibration：未测量（no held-out expert-reviewed calibration set）。
- retrieval_recall_at_k：未测量（no gold relevant-source identifiers）。
- agent_fallback_rate：未测量（no suite-wide normalized fallback denominator）。
- token_cost：未测量（LLM is disabled and provider pricing metadata is unavailable）。
