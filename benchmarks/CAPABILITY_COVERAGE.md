# Benchmark Capability Coverage

- Generated: 2026-08-01T16:31:00+00:00
- Datasets: 9
- Total cases: 64
- Capability-annotated cases: 52 （其余 12 个为待标注，见 CAPABILITY_ANNOTATION_SUGGESTIONS.md）

## 能力覆盖矩阵

| Capability | 中文说明 | 已标注 | 待标注(推断) | 覆盖案例 | 覆盖密度 | 缺口 |
|---|---|---|---|---|---|---|
| information_gathering | 主动请求缺失信息（温度、湿度、近期用药等） | 6 | 0 | 6 | 9.4% |  |
| knowledge_retrieval | 从长尾/罕见知识库（KG/RAG）中检索相关证据 | 7 | 0 | 7 | 10.9% |  |
| conflict_resolution | 在多源矛盾（文本 vs 传感器、视觉 vs 环境）中消解冲突 | 17 | 0 | 17 | 26.6% |  |
| counterfactual_reasoning | 生成并评估替代诊断，抑制集体遗漏 | 8 | 0 | 8 | 12.5% |  |
| uncertainty_quantification | 在证据不足时主动降低置信度或拒绝回答 | 9 | 0 | 9 | 14.1% |  |
| multi_step_planning | 将复杂问题分解为子任务并依次调用工具 | 11 | 0 | 11 | 17.2% |  |
| sensor_cross_validation | 交叉验证多模态传感器读数，检测异常 | 8 | 2 | 10 | 15.6% |  |

## Summary

- 有案例覆盖的能力数：7/7
- 覆盖案例 ≥ 2 的能力数：7/7
- 覆盖密度 = 该能力覆盖案例数 / 全部案例数。
- 已标注 = case 的 metadata.capabilities 显式声明；待标注(推断) = 自动推断的推荐标注，需人工审查。
