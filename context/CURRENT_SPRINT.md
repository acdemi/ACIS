# CURRENT SPRINT

Phase: 2.1E → 2.2 Transition
Sprint: 06
Goal: Research Evaluation Infrastructure — 论文级统计引擎、数据集指纹、图表生成

> **状态（2026-08-08）**：Sprint 06 已完成（见 `docs/RESEARCH_EVAL_SPRINT_06_REPORT.md`），
> 按 Stop Conditions 等待架构师审查，不自动进入 Sprint 07。

## Read Order
1. docs/rfc/RFC001-System Architecture.md
2. docs/architecture/principles.md
3. docs/ACIS.md
4. context/ARCHITECTURE_STATE.md
5. experiments/schema.py
6. experiments/catalog.py
7. experiments/archive.py
8. evals/metrics.py
9. evals/capability_metrics.py

## Scope

### Allowed Files
- `experiments/analysis.py` (新建)
  统计分析引擎：
  - 多实验聚合：读取同一实验定义多次运行，计算 mean/std/ci95
  - Bootstrap CI：1000 resamples，95 percentile interval
  - Ablation effect size：Δ = baseline - ablated，含方向与幅度
  - 能力分数与模块开关的关联分析

- `experiments/fingerprint.py` (新建)
  数据集指纹：
  - 计算数据集文件 SHA256
  - 写入 manifest.json（mandatory 字段）
  - 提供校验命令：`python -m experiments.manager verify <experiment>`

- `experiments/figures.py` (新建)
  论文图表生成（matplotlib，PNG 输出）：
  - 图1: Ablation Capability Impact（消融柱状图）
  - 图2: Capability Radar（7 轴能力雷达图）
  - 图3: Calibration Curve（置信度校准曲线）
  - 图4: Experiment Comparison Heatmap（实验对比热力图）

- `experiments/report.py` (新建)
  论文级报告生成器：
  - 自动生成 LaTeX 格式统计表格
  - 统计显著性标注（bootstrap p-value）
  - 图表嵌入 Markdown

- `experiments/manager.py` (扩展)
  新增命令：
  - `analyze <experiment>` — 统计聚合 + 效应量
  - `figure <experiment>` — 生成论文图表
  - `report <experiment>` — 生成完整论文报告
  - `verify <experiment>` — 校验数据集指纹

- `experiments/definitions/` (新增模板)
  `paper_evaluation.yaml` — 多模块消融 + 5 种子复现实验

- `tests/test_analysis.py` (新建)
- `tests/test_fingerprint.py` (新建)
- `docs/RESEARCH_EVAL_SPRINT_06_REPORT.md` (新建)

### Forbidden Files
- 所有冻结模块（agents/, planner/, debate/, rag/, rule_engine/, storage/, gateway/, ui/）
- orchestrator.py, workflow.py, kg_adapter.py
- benchmarks/ 下所有 JSON 数据集文件（只读）
- evals/ 核心逻辑（只读消费）
- trace/types.py（只读，仅允许 backward-compatible 添加）

## Deliverables

1. **统计分析引擎 (06A)**
   - `experiments/analysis.py`
   - 聚合：多实验 mean/std/ci95
   - Bootstrap：1000 iterations，95% CI
   - 效应量：Δ capability = baseline_score - ablated_score
   - 输出 JSON + Markdown 表格

2. **数据集指纹 (06B)**
   - `experiments/fingerprint.py`
   - SHA256 计算 + manifest 注入（mandatory）
   - `verify` 命令校验实验数据完整性

3. **论文图表生成器 (06C)**
   - `experiments/figures.py`
   - 4 种标准图表，PNG 格式，保存到实验归档目录
   - 图表标题、轴标签、图例使用中英双语

4. **论文级报告 (06D)**
   - `experiments/report.py`
   - LaTeX 表格 + 效应量标注
   - Bootstrap p-value 显著性标记
   - 图表嵌入

5. **多种子实验模板**
   - `paper_evaluation.yaml`：4 种模块组合 × 5 种子（42/123/456/789/1024）
   - 运行后产出多种子汇总统计

## Acceptance Criteria

1. `python -m experiments.manager analyze paper_main` 输出 mean/std/95% CI
2. `python -m experiments.manager verify <experiment>` 校验数据集指纹通过；修改数据集后校验失败
3. `python -m experiments.manager figure paper_main` 生成 4 张 PNG 图表
4. `python -m experiments.manager report paper_main` 生成含 LaTeX 表格和显著性标注的报告
5. `python -m experiments.manager run experiments/definitions/paper_evaluation.yaml` 产出 20 次运行 + 汇总统计
6. `manifest.json` 中包含 `dataset_sha256` 字段（mandatory）
7. `pytest` 全绿（含新测试），ruff & mypy clean

## Stop Conditions
- 全部验收项达成，输出 `Sprint 06 Complete. Awaiting review.` 后停止。
- **不自动进入 Sprint 07。** 等待架构师审查论文级实验输出的完整性与统计可信度。

## Design Principle
**可信度优先于完整度。效应量优先于 p 值。复现优先于美观。**
每个数字都可追溯到原始 Trace 和数据集版本，每次运行都可精确复现，每个结论都附有效应量估计和置信区间。