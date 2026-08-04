# CURRENT SPRINT

Phase: 2.1E  
Sprint: 04.5C  
Goal: Capability Evaluation Engine — 将能力契约接入运行时，实现能力指标的自动度量

## Read Order
1. `docs/architecture/architecture.md`
2. `docs/architecture/principles.md`
3. `context/ARCHITECTURE_STATE.md`
4. `context/KNOWN_DEBT.md`
5. `benchmarks/capabilities.py`
6. `benchmarks/metadata.py`
7. `benchmarks/capability_matrix.py`
8. `evals/runner.py`
9. `evals/metrics.py`
10. `evals/report.py`

## Scope

### Allowed Files
- `evals/capability_metrics.py` (新建)  
  定义能力指标的提取与计算方法：
  - 读取 case 的 `observable_evidence`
  - 从 Trace 中提取对应的行为证据（如 Planner 是否请求了缺失信息、是否生成了反事实候选等）
  - 将 `success_condition` 翻译为可执行的检查逻辑
  - 输出每个 case 的能力达成分数（Capability Score）

- `evals/metrics.py` (扩展)  
  集成能力指标：新增 `capability_scores` 字段到 `CaseMetrics`，并在聚合报告中增加按能力维度的统计

- `evals/runner.py` (微调)  
  在运行每个 case 后，若该 case 有 `observable_evidence`，自动调用 `capability_metrics` 计算分数并记录到 Trace 或 Metrics 中（不修改核心推理逻辑）

- `evals/report.py` (微调)  
  在 `summary.md` 和 `metrics.csv` 中增加能力分数列/章节

- `tests/test_capability_metrics.py` (新建)  
  单元测试：验证每种能力的 scoring 逻辑正确，处理缺失证据的情况，模拟 Trace 数据

### Forbidden Files
- 所有冻结模块（`agents/`, `planner/`, `debate/`, `rag/`, `rule_engine/`, `storage/`, `gateway/`, `ui/`）
- `orchestrator.py`, `workflow.py`, `kg_adapter.py`
- `benchmarks/` 目录下所有 JSON 数据集文件（只读）
- `benchmarks/capabilities.py`, `benchmarks/metadata.py` 的接口签名不可变（只读）

## Deliverables

1. **能力指标计算模块**  
   为以下 7 种能力设计至少一个可自动计算的指标（基于 Trace 和 evidence）：
   - `information_gathering`：是否请求了缺失信息（planner output 中包含询问）
   - `knowledge_retrieval`：是否触发了 RAG/KG 查询（memory_hits ≥ 1）
   - `conflict_resolution`：是否识别并消解了矛盾（debate_rounds ≥ 1 且 critic 参与）
   - `counterfactual_reasoning`：是否生成了替代诊断（counterfactual_count ≥ 1）
   - `uncertainty_quantification`：置信度是否在合理范围内（confidence ≤ 0.7 当 evidence 不足时）
   - `multi_step_planning`：是否分解了多个步骤（planner steps ≥ 2）
   - `sensor_cross_validation`：是否使用了传感器数据且与视觉/文本交叉验证（tool_usage 包含 sensor 且 memory 中有环境数据）

2. **Trace 驱动验证**  
   利用已有的 Unified Trace，从事件流中自动提取上述行为证据，不依赖外部人工判断。

3. **能力分数集成到评测报告**  
   - 每个 case 的 `CaseMetrics` 新增 `capability_scores` 字段（字典，capability -> score 0-1）
   - `metrics.csv` 增加各能力分数列
   - `summary.md` 增加“Capability Performance”章节，展示每种能力的平均得分和案例分布

4. **与 Ablation 联动**  
   确保 `evals/ablation.py` 能继续正常运行，并且生成的能力分数也随模块开关变化（例如关闭 Planner 后 `information_gathering` 分数应为 0）。能力分数消融将提供比 accuracy 更细粒度的模块贡献证据。

5. **测试与验证**  
   - 为每种能力至少编写一个单元测试，使用模拟 Trace 验证 scoring 正确性
   - 在真实 enriched 数据集上运行，确认所有已标注案例都能产生有效的能力分数

## Acceptance Criteria

1. `python evals/runner.py --dataset benchmarks.datasets.enriched` 运行时，每个案例输出中包含 `capability_scores` 字段，且数值在 0-1 之间。
2. 生成的能力分数与案例声明的 `capabilities` 对应：若案例标注了某能力，则对应分数应 > 0（除非系统完全未表现该能力）；若案例未标注，则仍可计算但不强制要求。
3. 关闭 Planner 后 (`--planner-off`)，`information_gathering` 分数降为 0；关闭 Memory 后，`knowledge_retrieval` 分数降为 0（验证消融联动）。
4. `results/summary.md` 包含“Capability Performance”表格，列出每种能力的平均得分。
5. `tests/test_capability_metrics.py` 至少覆盖全部 7 种能力的 scoring 逻辑，`pytest` 全绿。
6. `ruff` 和 `mypy` 对新增/修改文件零错误。

## Stop Conditions
- 完成所有验收项，输出 `Sprint 04.5C Complete. Awaiting review.` 后停止。
- **不自动进入 Sprint 05。** 等待架构师审查能力指标的设计与准确性。

## Design Principle
**从“静态标签”到“运行时验证”**。能力契约的价值只有在运行时被度量才能实现。每个 observable_evidence 的 success_condition 应该能被 Trace 自动检查，从而使 Benchmark 成为真正的 Agent Capability Test Suite。