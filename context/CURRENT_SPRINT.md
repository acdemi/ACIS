# CURRENT SPRINT

Phase: 2.1E
Sprint: 04.5B
Goal: 将 Capability Framework 从“推断模型”升级为“可验证的数据契约（Verifiable Capability Contract）”

## Read Order
1. docs/architecture/architecture.md
2. docs/architecture/principles.md
3. context/ARCHITECTURE_STATE.md
4. context/KNOWN_DEBT.md
5. benchmarks/capabilities.py
6. benchmarks/metadata.py
7. benchmarks/CAPABILITY_ANNOTATION_SUGGESTIONS.md (Sprint 04.5A 产出)
8. benchmarks/datasets/enriched.json (现有 15 个案例)

## Scope

### Allowed Files
- `benchmarks/datasets/enriched.json` (修改)
  对现有 15 个 enriched 案例进行显式能力标注，补充结构化 `observable_evidence`。
  新增 3+ 个 `information_gathering` 专项案例，每个案例必须包含完整的 metadata。

- `benchmarks/datasets/planning.json` (修改) — 显式能力标注
- `benchmarks/datasets/memory.json` (修改) — 显式能力标注
- `benchmarks/datasets/debate.json` (修改) — 显式能力标注
- `benchmarks/datasets/counterfactual.json` (修改) — 显式能力标注
- `benchmarks/datasets/adversarial.json` (修改) — 显式能力标注

- `benchmarks/datasets/easy.json` (修改，按价值优先原则)
  仅对**能够明确推断 Capability** 的案例进行标注，不强制数量。
  优先标注包含 uncertainty_quantification、multi_step_planning 特征的案例。
  不标注纯特征匹配型案例（如简单病害识别）。

- `benchmarks/datasets/medium.json` (修改，同上原则)
- `benchmarks/datasets/hard.json` (修改，同上原则)

- `benchmarks/metadata.py` (增强)
  新增 `ObservableEvidence` 结构化 Schema：
  ObservableEvidence {
  capability: Capability,
  expected_behavior: str, // 中文描述期望行为
  success_condition: str // 可验证的成功条件
  }

更新 `BenchmarkMetadata` 以支持 `observable_evidence: list[ObservableEvidence]`。
更新 `validate_metadata` 以校验 evidence 与 capability 的一致性。

- `benchmarks/capability_matrix.py` (增强)
新增 Capability Consistency Check：对每个标注案例，验证 `capabilities` ↔ `observable_evidence` ↔ `design_intent` 三者逻辑一致。
不一致的案例在报告中标记为 ⚠️ 并输出到 `CAPABILITY_CONSISTENCY_REPORT.md`。

- `benchmarks/CAPABILITY_COVERAGE.md` (自动生成，更新)
- `benchmarks/CAPABILITY_CONSISTENCY_REPORT.md` (自动生成，新建)
- `tests/test_capabilities.py` (扩展)
- `context/KNOWN_DEBT.md` (更新 Capability Annotation 债务状态)

### Forbidden Files
- 所有冻结模块
- `evals/runner.py`, `evals/ablation.py` 的业务逻辑（只读，可通过 CLI 运行验证）
- `benchmarks/schema.py`, `benchmarks/capabilities.py`（只读）

## Deliverables

1. **显式能力标注（价值优先）**
 - 能力套件案例（33 个）100% 显式标注 `capabilities`。
 - Difficulty 分层案例中，对**能够明确推断 Capability** 的案例进行标注，数量不设硬性下限。
 - 不强制标注无法明确推断的案例（如纯特征匹配型简单案例）。

2. **结构化 Observable Evidence**
 - 定义并冻结 `ObservableEvidence` Schema。
 - 为所有已标注的 enriched 案例及能力套件案例添加 `observable_evidence`。

3. **Capability Consistency Check**
 - 自动验证每个案例的 `capabilities` ↔ `observable_evidence` ↔ `design_intent` 三者一致。
 - 生成 `CAPABILITY_CONSISTENCY_REPORT.md`，标记不一致案例。

4. **information_gathering 专项案例补充**
 - 在 `enriched.json` 中新增 ≥3 个案例，使该能力已标注案例 ≥6。

5. **消融验证报告**
 - 在已标注数据集上运行消融，输出按能力分组的贡献统计。

## Acceptance Criteria

1. **标注完成**：33 个能力套件案例 100% 标注。Difficulty 案例中可明确推断的均已标注。
2. **Schema 冻结**：`ObservableEvidence` Schema 定义完整，所有新增 evidence 符合格式。
3. **一致性检查**：`CAPABILITY_CONSISTENCY_REPORT.md` 生成，已标注案例的一致性达到 100%（无未解决的不一致标记）。
4. **案例补充**：`enriched.json` 新增 ≥3 个 `information_gathering` 案例，全部携带 capabilities 和 observable_evidence。
5. **覆盖更新**：`CAPABILITY_COVERAGE.md` 显示 `information_gathering` 已标注案例 ≥6。
6. **消融报告**：至少 1 种能力在消融时呈现过程指标差异。
7. **测试通过**：`pytest` 全绿，`ruff`/`mypy` 零新增错误。

## Stop Conditions
- 完成全部验收项，提交 PR 包含标注清单与一致性报告。
- 输出 `Sprint 04.5B Complete. Awaiting annotation review.` 后停止。
- **绝不自动进入 Sprint 05。** 等待 Chief Maintainer 审查标注质量。

## Design Principle
**可验证优先于完整性**。宁可少标，不可乱标。每个标注必须能通过 Capability → Evidence → Intent 的一致性检验。Benchmark 的价值不在于标注覆盖率，而在于每一条标注都是可复现、可验证的科学断言。