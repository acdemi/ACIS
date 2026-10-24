# ACIS 最小交付评测（离线规则链路）

- 数据集：`evals.fixtures`（12 例）
- 随机种子：7
- 后端：RAG=memory / KG=memory / LLM Judge=disabled / SQLite 持久化=off
- 说明：天气与传感器为模拟数据，随机部分由种子固定；同一机器同一小时可复现。

| 用例 | 期望 | 实际病理结论 | 判定 | 置信度 | 风险 | Critic |
|---|---|---|---|---:|---|---|
| tomato_leaf_mold | 叶霉病 | 病理判断首选：番茄叶霉病 | PASS | 74% | medium | off |
| tomato_early_blight | 早疫病 | 病理判断首选：番茄早疫病 | PASS | 75% | medium | off |
| tomato_irrigate_with_risk | - | 病理证据不足，不能确认具体病害 | PASS | 58% | medium | off |
| tomato_monitor_no_disease | 证据不足 | 病理证据不足，不能确认具体病害 | PASS | 58% | medium | off |
| sugar_beet_leaf_spot | 褐斑病 | 病理判断首选：甜菜褐斑病 | PASS | 75% | medium | off |
| sugar_beet_root_rot | 根腐病 | 病理判断首选：甜菜根腐病 | PASS | 75% | medium | off |
| sugar_beet_alert | 证据不足 | 病理证据不足，不能确认具体病害 | PASS | 58% | medium | off |
| cotton_verticillium_wilt | 黄萎病 | 病理判断首选：棉花黄萎病 | PASS | 75% | medium | off |
| cotton_fusarium_wilt | 枯萎病 | 病理判断首选：棉花枯萎病 | PASS | 65% | medium | off |
| cotton_irrigate | 证据不足 | 病理证据不足，不能确认具体病害 | PASS | 58% | medium | off |
| tomato_irrigate_with_disease | 叶霉病 | 病理判断首选：番茄叶霉病 | PASS | 59% | high | on |
| tomato_mold_low_humidity | 叶霉病 | 病理判断首选：番茄叶霉病 | PASS | 60% | high | on |

- 期望命中：12/12（100%）
- Critic 触发：2 例
- 平均置信度：0.6583
