# ACIS Benchmark Suite（Phase 2.1E）

## 设计哲学

**真实性优先于难度**：基准中的每个 case 都来自真实可能的农业场景。基准的
目标是“区分模块能力”，而不是“让系统犯错”——一个 case 的价值在于它能让某个
认知模块的贡献变得**可测量**（accuracy / confidence / recall / memory_hits /
debate_rounds / counterfactual_count / capability_scores 等），而非仅仅降低准确率。

## 目录结构

```text
benchmarks/
├── schema.py                 # 通用数据集 schema（id/query/ground_truth/sensor_override）
├── loader.py                 # 数据集加载：module-style 名称、.json 路径、capability suites
├── taxonomy.py               # 能力套件定义（planning/memory/debate/counterfactual/adversarial）
├── capabilities.py           # 7 种认知能力枚举（信息收集/知识检索/冲突消解/反事实/不确定性/多步规划/传感器交叉验证）
├── metadata.py               # BenchmarkMetadata + ObservableEvidence 契约（可验证能力标注）
├── capability_matrix.py      # 自动生成 CAPABILITY_MATRIX / COVERAGE / CAPABILITY_COVERAGE / CONSISTENCY_REPORT
├── CAPABILITY_MATRIX.md      # 自动生成的能力矩阵（勿手写）
├── COVERAGE.md               # 自动生成的覆盖报告（勿手写）
├── CAPABILITY_COVERAGE.md    # 自动生成的能力覆盖矩阵（勿手写）
├── CAPABILITY_CONSISTENCY_REPORT.md  # 自动生成的一致性报告（勿手写）
└── datasets/
    ├── easy.json             # 难度分层：简单（12 案例）
    ├── medium.json           # 难度分层：中等（10 案例）
    ├── hard.json             # 难度分层：困难（6 案例）
    ├── planning.json         # 能力套件：Planner 任务分解（4）
    ├── memory.json           # 能力套件：RAG/KG/案例检索（4）
    ├── debate.json           # 能力套件：多 Agent 冲突消解（4）
    ├── counterfactual.json   # 能力套件：反事实推理覆盖（3）
    ├── adversarial.json      # 能力套件：系统边界（3）
    └── enriched.json         # 扩展挑战集：五类认知挑战（18，含 6 个 information_gathering）
```

总计 **9 个数据集 / 64 案例**；52 例显式标注能力（36 能力案例 + 16 难度案例），
12 个纯特征匹配的难度案例按设计不标注。

## 挑战分类（enriched.json）

每个 enriched case 的 `metadata.challenge_type` 属于以下五类之一，每类 ≥3 例：

| Challenge Type | 含义 | 典型 expected_reasoning_features |
|---|---|---|
| `missing_information` | 症状信息缺失，应主动请求补充信息（6 例） | `information_request` |
| `contradictory_evidence` | 症状与现场/环境证据矛盾，需冲突消解 | `conflict_resolution`, `counterfactual_analysis` |
| `multi_disease` | 多病害症状并存，需候选排序与反事实排除 | `counterfactual_analysis`, `knowledge_retrieval` |
| `rare_knowledge` | 非主流作物或非侵染性（生理性）问题 | `knowledge_retrieval` |
| `sensor_conflict` | 传感器异常与病害/农事决策叠加 | `conflict_resolution` |

## BenchmarkMetadata 与能力契约（Sprint 04.5B）

每个 enriched case 必须携带完整 `metadata`；能力标注（enriched 在 metadata 内，
套件/难度数据集在 case 级）由以下字段构成可验证契约：

| 字段 | 说明 |
|---|---|
| `challenge_type` | 五类挑战之一 |
| `expected_reasoning_features` | 期望出现的推理特征列表（非空） |
| `difficulty` | 1–5 整数 |
| `crop` | 作物（tomato / sugar_beet / cotton / cucumber …） |
| `disease` | 期望病害名或 null |
| `noise_level` | low / medium / high |
| `modalities` | 输入模态列表（text / sensor / image） |
| `design_intent` | 中文设计意图：说明该 case 测试哪个模块的哪种能力 |
| `capabilities` | 声明的能力列表（非空） |
| `observable_evidence` | 每条证据：`capability` / `expected_behavior` / `success_condition`（与 capabilities 1:1 覆盖） |

`capability_matrix.py` 对每个标注案例执行一致性检查
（capabilities ↔ observable_evidence ↔ design_intent），当前 **52/52 一致、0 不一致**
（见 `CAPABILITY_CONSISTENCY_REPORT.md`）。

## 运行时能力度量（Sprint 04.5C）

`evals/capability_metrics.py` 将 `success_condition` 翻译为 Trace 可检查逻辑，
runner 运行时为每个 case 计算 7 种能力分数（0/1），输出到 `metrics.csv` 能力列与
`results/summary.md` 的 “Capability Performance” 章节。消融联动已验证：
关闭 Planner 后 `information_gathering` / `multi_step_planning` 归零；
关闭 Memory 后 `knowledge_retrieval` 归零。

## 使用方式

```powershell
# 难度分层 / 能力套件 / 扩展挑战集，统一入口
python evals/runner.py --dataset benchmarks.datasets.easy
python evals/runner.py --dataset benchmarks.datasets.enriched
python evals/runner.py --suite planning        # 能力套件快捷方式
python evals/runner.py --suite all             # 运行全部能力套件

# 消融（Sprint 04 / 04.5）
python evals/ablation.py --dataset benchmarks.datasets.enriched
python evals/ablation.py --suite planning

# 自动生成文档（CAPABILITY_MATRIX / COVERAGE / CAPABILITY_COVERAGE / CONSISTENCY_REPORT）
python -m benchmarks.capability_matrix

# 为一次消融运行追加按 challenge_type / capability 分组的模块贡献统计
python -m benchmarks.capability_matrix --ablation-dir results/ablation/enriched/<timestamp>
```

## 验证约定

- 所有新增代码必须通过 `pytest`（当前 189）、`ruff`、`mypy`。
- 所有 JSON 数据集文件为只读基线（Sprint 04.5B 后冻结），修改需架构评审批准。
- `CAPABILITY_*` 与 `COVERAGE.md` 由 `capability_matrix.py` 自动生成，禁止手写编辑。
