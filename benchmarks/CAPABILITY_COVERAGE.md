# Benchmark Capability Coverage

- Generated: 2026-08-01T15:23:42+00:00
- Datasets: 9
- Total cases: 61
- Capability-annotated cases: 0 （其余 61 个为待标注，见 CAPABILITY_ANNOTATION_SUGGESTIONS.md）

## 能力覆盖矩阵

| Capability | 中文说明 | 已标注 | 待标注(推断) | 覆盖案例 | 覆盖密度 | 缺口 |
|---|---|---|---|---|---|---|
| information_gathering | 主动请求缺失信息（温度、湿度、近期用药等） | 0 | 3 | 3 | 4.9% |  |
| knowledge_retrieval | 从长尾/罕见知识库（KG/RAG）中检索相关证据 | 0 | 11 | 11 | 18.0% |  |
| conflict_resolution | 在多源矛盾（文本 vs 传感器、视觉 vs 环境）中消解冲突 | 0 | 14 | 14 | 23.0% |  |
| counterfactual_reasoning | 生成并评估替代诊断，抑制集体遗漏 | 0 | 9 | 9 | 14.8% |  |
| uncertainty_quantification | 在证据不足时主动降低置信度或拒绝回答 | 0 | 12 | 12 | 19.7% |  |
| multi_step_planning | 将复杂问题分解为子任务并依次调用工具 | 0 | 18 | 18 | 29.5% |  |
| sensor_cross_validation | 交叉验证多模态传感器读数，检测异常 | 0 | 18 | 18 | 29.5% |  |

## Summary

- 有案例覆盖的能力数：7/7
- 覆盖案例 ≥ 2 的能力数：7/7
- 覆盖密度 = 该能力覆盖案例数 / 全部案例数。
- 已标注 = case 的 metadata.capabilities 显式声明；待标注(推断) = 自动推断的推荐标注，需人工审查。
