# CURRENT SPRINT

Phase: 2.1E  
Sprint: 04.5A  
Goal: Capability Framework — 定义 ACIS 认知能力模型，建立覆盖度评估体系

## Read Order
1. `docs/architecture/architecture.md`
2. `docs/architecture/principles.md`
3. `context/ARCHITECTURE_STATE.md`
4. `context/KNOWN_DEBT.md`
5. `benchmarks/schema.py`
6. `benchmarks/loader.py`
7. `benchmarks/metadata.py` (existing, will be enhanced)
8. `benchmarks/capability_matrix.py` (existing, will be enhanced)

## Scope

### Allowed Files
- `benchmarks/capabilities.py` (新建)  
  定义 ACIS 认知能力枚举（Capability enum），包含以下稳定能力类别：
  - `information_gathering` — 主动请求缺失信息（温度、湿度、近期用药等）
  - `knowledge_retrieval` — 从长尾/罕见知识库（KG/RAG）中检索相关证据
  - `conflict_resolution` — 在多源矛盾（文本 vs 传感器、视觉 vs 环境）中消解冲突
  - `counterfactual_reasoning` — 生成并评估替代诊断，抑制集体遗漏
  - `uncertainty_quantification` — 在证据不足时主动降低置信度或拒绝回答
  - `multi_step_planning` — 将复杂问题分解为子任务并依次调用工具
  - `sensor_cross_validation` — 交叉验证多模态传感器读数，检测异常

- `benchmarks/capability_matrix.py` (增强)  
  增加功能：
  - 扫描所有现有数据集（easy/medium/hard/planning/memory/debate/counterfactual/adversarial/enriched）中的每个 case
  - 自动推断或读取每个 case 的 `capabilities` 字段，生成能力覆盖矩阵
  - 输出 `benchmarks/CAPABILITY_COVERAGE.md`，展示每种能力的案例数、覆盖缺口
  - 若某个 case 缺少能力标注，自动根据 `expected_reasoning_features` 或 `design_intent` 给出推荐标注（仅提示，不自动写入数据文件）
  - 保留原有的能力套件矩阵与挑战类型矩阵

- `benchmarks/metadata.py` (微调)  
  - `BenchmarkMetadata` 中新增 `capabilities` 字段（Capability 列表），替代或补充 `expected_reasoning_features`
  - 保留 `challenge_type`，但不再作为主分类维度
  - 更新 `validate_metadata` 要求至少包含一个 capability

- `benchmarks/CAPABILITY_COVERAGE.md` (自动生成，勿手写)
- `tests/test_capabilities.py` (新建)  
  测试能力枚举完整性、覆盖矩阵生成、元数据验证

### Forbidden Files
- 所有冻结模块：`agents/`、`planner/`、`debate/`、`rag/`、`rule_engine/`、`storage/`、`gateway/`、`ui/`
- `orchestrator.py`, `workflow.py`, `kg_adapter.py`
- 所有现有 JSON 数据集文件（只读，不修改内容）
- `evals/runner.py`、`evals/ablation.py` 的业务逻辑（只读）

## Deliverables

1. **能力枚举 (Capability enum)**  
   `benchmarks/capabilities.py` 中定义稳定的能力枚举，每个能力附带中文说明和典型触发场景。

2. **能力覆盖矩阵**  
   自动生成 `benchmarks/CAPABILITY_COVERAGE.md`，包含：
   - 每种能力的案例数（区分已标注/待标注）
   - 每种能力的覆盖密度（百分比）
   - 明显覆盖不足的能力标记（如案例数 <2）

3. **元数据增强**  
   `BenchmarkMetadata` 新增 `capabilities` 字段，校验规则要求非空。

4. **现有案例的能力标注建议**  
   对尚未携带 `capabilities` 字段的案例，生成一份 `benchmarks/CAPABILITY_ANNOTATION_SUGGESTIONS.md`，列出推荐标注以供人工审查。**不自动修改任何数据集文件。**

5. **单元测试**  
   - 测试能力枚举定义完整
   - 测试覆盖矩阵生成逻辑
   - 测试元数据验证（缺失 capabilities 会被拒绝）

## Acceptance Criteria

1. `benchmarks/capabilities.py` 中至少定义 7 种能力，每种有清晰描述。
2. 运行 `python -m benchmarks.capability_matrix` 生成最新的 `CAPABILITY_COVERAGE.md`，报告覆盖情况。
3. 现有所有数据集（共 9 个文件，约 60+ 案例）的覆盖矩阵中，至少 5 种能力有案例覆盖。
4. 新案例元数据若缺少 `capabilities` 字段，`validate_metadata` 会报错。
5. `pytest tests/test_capabilities.py` 全绿，没有破坏已有 150 个测试。
6. `ruff`、`mypy` 对新文件零错误。

## Stop Conditions
- 完成上述验收项，输出 `Sprint 04.5A Complete. Awaiting review.` 并停止。
- **绝不进入 Sprint 04.5B。** 等待 Chief Architect 审查能力覆盖模型后再决定下一步。

## Design Principle
**能力抽象化，测量标准化**。  
定义系统“应该具备什么认知能力”，而非“当前版本有哪些模块”。能力模型稳定，模块可重构。基准的科研价值来源于它测量了**可复现的认知维度**，而非特定代码路径。