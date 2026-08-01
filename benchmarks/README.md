# ACIS Benchmark Suite（Phase 2.1E）

## 设计哲学

**真实性优先于难度**：基准中的每个 case 都来自真实可能的农业场景。基准的
目标是“区分模块能力”，而不是“让系统犯错”——一个 case 的价值在于它能让某个
认知模块的贡献变得**可测量**（accuracy / confidence / recall / memory_hits /
debate_rounds / counterfactual_count 等），而非仅仅降低准确率。

## 目录结构

```text
benchmarks/
├── schema.py                 # 通用数据集 schema（id/query/ground_truth/sensor_override）
├── loader.py                 # 数据集加载：module-style 名称、.json 路径、capability suites
├── taxonomy.py               # 能力套件定义（planning/memory/debate/counterfactual/adversarial）
├── metadata.py               # BenchmarkMetadata：五类挑战 + 标准化 case 元数据
├── capability_matrix.py      # 自动生成 CAPABILITY_MATRIX.md / COVERAGE.md + 挑战分组消融统计
├── CAPABILITY_MATRIX.md      # 自动生成的能力矩阵（勿手写）
├── COVERAGE.md               # 自动生成的覆盖报告（勿手写）
└── datasets/
    ├── easy.json             # 难度分层：简单（10+ 案例）
    ├── medium.json           # 难度分层：中等（10+ 案例）
    ├── hard.json             # 难度分层：困难（5+ 案例）
    ├── planning.json         # 能力套件：Planner 任务分解（4）
    ├── memory.json           # 能力套件：RAG/KG/案例检索（4）
    ├── debate.json           # 能力套件：多 Agent 冲突消解（4）
    ├── counterfactual.json   # 能力套件：反事实推理覆盖（3）
    ├── adversarial.json      # 能力套件：系统边界（3）
    └── enriched.json         # 扩展挑战集：五类认知挑战（15）
```

## 挑战分类（enriched.json）

每个 enriched case 的 `metadata.challenge_type` 属于以下五类之一，每类 ≥3 例：

| Challenge Type | 含义 | 典型 expected_reasoning_features |
|---|---|---|
| `missing_information` | 症状信息缺失，应主动请求补充信息 | `information_request` |
| `contradictory_evidence` | 症状与现场/环境证据矛盾，需冲突消解 | `conflict_resolution`, `counterfactual_analysis` |
| `multi_disease` | 多病害症状并存，需候选排序与反事实排除 | `counterfactual_analysis`, `knowledge_retrieval` |
| `rare_knowledge` | 非主流作物或非侵染性（生理性）问题 | `knowledge_retrieval` |
| `sensor_conflict` | 传感器异常与病害/农事决策叠加 | `conflict_resolution` |

## BenchmarkMetadata 字段

每个 enriched case 除公共字段（`id` / `query` / `ground_truth` /
`expected_confidence_range` / `expected_tools` / `sensor_override`）外，
必须携带完整的 `metadata`：

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

# 自动生成文档（输出 benchmarks/CAPABILITY_MATRIX.md + COVERAGE.md）
python -m benchmarks.capability_matrix

# 为一次消融运行追加按 challenge_type 分组的模块贡献统计
python -m benchmarks.capability_matrix --ablation-dir results/ablation/enriched/<timestamp>
```

## 验证约定

- 所有新增代码必须通过 `pytest`、`ruff`、`mypy`。
- `easy.json / medium.json / hard.json` 以及五个能力套件文件为只读基线，
  修改需架构评审批准。
- `CAPABILITY_MATRIX.md` 与 `COVERAGE.md` 由 `capability_matrix.py` 自动生成，
  禁止手写编辑。
