# CURRENT SPRINT

Phase: 2.1E  
Sprint: 04.5B  
Goal: Capability Annotation & Targeted Enrichment — 完成现有案例的显式能力标注，定向补充覆盖不足的能力案例

## Read Order
1. `docs/architecture/architecture.md`
2. `docs/architecture/principles.md`
3. `context/ARCHITECTURE_STATE.md`
4. `context/KNOWN_DEBT.md`
5. `benchmarks/capabilities.py`
6. `benchmarks/metadata.py`
7. `benchmarks/capability_matrix.py`
8. `benchmarks/CAPABILITY_ANNOTATION_SUGGESTIONS.md` (Sprint 04.5A 产出)
9. `benchmarks/datasets/enriched.json` (现有 15 个案例)

## Scope

### Allowed Files
- `benchmarks/datasets/enriched.json` (修改)  
  对现有 15 个 enriched 案例，根据 Sprint 04.5A 的标注建议进行显式能力标注（在 `metadata.capabilities` 字段中），并补充 `observable_evidence` 字段（若 case 需要）。
  新增 3+ 个案例，重点补充 `information_gathering` 能力覆盖。

- `benchmarks/datasets/planning.json` (修改)  
  对 4 个 planning 案例进行显式能力标注（仅添加 `metadata.capabilities`，不修改其他内容）。

- `benchmarks/datasets/memory.json` (修改)  
  对 4 个 memory 案例进行显式能力标注。

- `benchmarks/datasets/debate.json` (修改)  
  对 4 个 debate 案例进行显式能力标注。

- `benchmarks/datasets/counterfactual.json` (修改)  
  对 3 个 counterfactual 案例进行显式能力标注。

- `benchmarks/datasets/adversarial.json` (修改)  
  对 3 个 adversarial 案例进行显式能力标注。

- `benchmarks/datasets/easy.json` (修改，可选但推荐)  
  对 12 个 easy 案例中有明确推理特征的进行能力标注（至少标注 uncertainty_quantification 和 multi_step_planning 相关的案例），不作为强制要求，但标注越多越好。

- `benchmarks/datasets/medium.json` (修改，可选)  
  同上，至少标注具有冲突/多步规划特征的案例。

- `benchmarks/datasets/hard.json` (修改，可选)  
  同上，优先标注具有 sensor_cross_validation / conflict_resolution 的案例。

- `benchmarks/capability_matrix.py` (微调)  
  更新覆盖统计逻辑，支持从 `metadata.capabilities` 字段读取已标注数据；更新报告输出以区分“已标注”和“推断”。

- `benchmarks/CAPABILITY_COVERAGE.md` (自动生成，更新)
- `benchmarks/CAPABILITY_ANNOTATION_SUGGESTIONS.md` (自动更新，已标注的应从待标注列表中移除)
- `tests/test_capabilities.py` (扩展)  
  新增测试：验证标注后案例的 `capabilities` 字段有效、覆盖矩阵中标注计数正确、新增 enriched 案例的合理性。
- `context/KNOWN_DEBT.md` (更新)  
  添加关于 Capability Annotation 的数据治理债务条目（如已记录则更新状态）。

### Forbidden Files
- 所有冻结模块：`agents/`, `planner/`, `debate/`, `rag/`, `rule_engine/`, `storage/`, `gateway/`, `ui/`
- `orchestrator.py`, `workflow.py`, `kg_adapter.py`
- `evals/runner.py`, `evals/ablation.py` 的业务逻辑（只读，但可通过标准 CLI 运行验证）
- `benchmarks/schema.py`, `benchmarks/capabilities.py`（只读）

## Deliverables

1. **显式能力标注**  
   - 对 `enriched.json` (15)、`planning.json` (4)、`memory.json` (4)、`debate.json` (4)、`counterfactual.json` (3)、`adversarial.json` (3) 共 33 个案例，完成 100% 显式 `capabilities` 标注（参照建议进行人工审查后写入）。
   - 对 `easy/medium/hard` (共 28 个案例)，完成至少 50% 的显式标注（优先标注具有明确推理特征的案例，如包含 uncertainty、multi_step、sensor_conflict 的）。
   - 所有标注需经 Maintainer 审查确认（本次 Sprint 由 Codex 执行建议标注，Maintainer 在合并前逐条审核）。

2. **能力补充案例**  
   - 在 `enriched.json` 中新增至少 3 个案例，专门覆盖 `information_gathering` 能力（当前仅 3 个推断案例），确保 `information_gathering` 的显式标注案例数 ≥ 6。
   - 新增案例必须包含完整的 `metadata`（含 `capabilities`, `observable_evidence`），遵循 `BenchmarkMetadata` 规范。

3. **Observable Evidence 字段（可选升级）**  
   - 为已标注的 enriched 案例（及部分其他案例）添加 `observable_evidence` 字段，描述该能力在系统行为中的可观测表现（例如 `uncertainty_quantification` → `confidence < 0.6 或 need_more_information`）。
   - 此为非强制交付，但有助于为未来自动评估提供依据。

4. **更新覆盖矩阵**  
   - 重新生成 `CAPABILITY_COVERAGE.md`，区分“已标注”与“推断”，展示标注完成度。`information_gathering` 覆盖密度应显著提升。

5. **消融验证报告**  
   - 在已标注的新数据集上重新运行 `evals/ablation.py --dataset benchmarks.datasets.enriched`，生成消融报告，着重分析 `information_gathering` 等能力关闭 Planner 后的指标变化。
   - 不要求 accuracy 必须下降，但需观察 `planner_usage`, `tool_usage`, `counterfactual_count` 等过程指标的差异，并给出结构化统计。

## Acceptance Criteria

1. **标注完成率**  
   - 33 个能力套件案例 (planning/memory/debate/counterfactual/adversarial/enriched) 的 `capabilities` 字段显式标注率为 100%。  
   - easy/medium/hard 中至少 14 个案例（50%）具备显式能力标注。  
   - 所有显式标注均通过 `validate_metadata` 校验（`capabilities` 非空且取自合法枚举）。

2. **案例补充**  
   - `enriched.json` 新增 ≥3 个 `information_gathering` 专项案例，所有新案例携带 `capabilities` 和 `observable_evidence`（若实现）。

3. **文档更新**  
   - `CAPABILITY_COVERAGE.md` 显示 `information_gathering` 的已标注案例数 ≥6，总覆盖案例数 ≥9。  
   - `CAPABILITY_ANNOTATION_SUGGESTIONS.md` 中已标注案例不再出现。

4. **消融报告**  
   - 执行 `python evals/ablation.py --dataset benchmarks.datasets.enriched`，产出按能力分组的贡献统计。  
   - 至少出现 1 种能力在消融时呈现过程指标差异（如 `information_gathering` 关闭 Planner 后 `planner_usage` 降至 0 等），并在报告中注明。

5. **测试与质量**  
   - `pytest tests/test_capabilities.py` 及全套测试（当前 167 个）全部通过。  
   - ruff, mypy 对修改文件零新增错误。

## Stop Conditions
- 全部验收标准达成。
- 提交 PR 并附上消融报告摘要与标注清单，等待 Chief Maintainer 审核。
- 输出 `Sprint 04.5B Complete. Awaiting annotation review.` 后停止。**绝不自动进入 Sprint 05。**

## Design Principle
**先标注，后扩充；先定性，后定量。**  
显式能力标注是将 Benchmark 从“推断”提升为“科学基准”的关键一步。只有基于人工审查的标注数据，后续的消融分析和模块贡献研究才具有可复现的信任基础。扩充案例严格遵循能力覆盖缺口，避免无目的堆砌。