# Evaluation Fixtures

轻量回归入口，用来确认主图、规则编排和可选 DeepSeek Judge 的基本输出结构没有破坏。

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='.'
python evals/smoke_eval.py
```

当前检查项：

- `summary` / `decision` / `action_plan` 非空
- `confidence` 保持在 `0..1`
- `risk_level` 只允许 `low | medium | high`
- `traces` 保留 Agent 输出链路
- `judge_mode` 明确标记为 `rules` 或 `deepseek`

未设置 `DEEPSEEK_API_KEY` 时，`+llm-judge` 用例会验证自动回退规则裁决。

RAG 额外检查：

- 每条决策必须包含 `RAG` trace。
- `RAG` trace 的 evidence 必须声明 `backend`，值为 `memory`、`qdrant` 或 `fallback`。
- 默认 smoke eval 不要求 Qdrant 运行，验证离线 fallback 可用。

## 固定场景回归

`evals/fixture_eval.py` 运行 12 个确定性 crop/intent/病害 断言（含 2 个 Critic 必触发用例）：

```powershell
python evals/fixture_eval.py
```

## Evaluation Runner（Sprint 02）

`evals/runner.py` 执行 benchmark 数据集，为每个 case 收集 unified Trace，计算评估指标，
并写出 `results/metrics.csv` 与 `results/summary.md`。

```powershell
python evals/runner.py --dataset benchmarks.datasets.enriched
python evals/runner.py --suite all
```

可配置项：

- `--planner-on/--planner-off`、`--debate-on/--debate-off`、
  `--memory-on/--memory-off`、`--tool-router-on/--tool-router-off`
- `--dataset <module 路径或 .json 文件>`（默认 `evals.fixtures`）
- `--output-dir`（默认 `results`）、`--seed`（默认 7）、`--rules-only`、`--max-cases N`

指标：`accuracy` / `average_confidence` / `average_runtime` /
`planner_usage` / `tool_usage` / `memory_hits` / `debate_rounds` /
`counterfactual_count` / `collective_omission_count`。

## Ablation Framework（Sprint 04）

`evals/ablation.py` 以 `all_on` 为基线，依次关闭 Planner / Debate / Memory /
Counterfactual / Tool Router / Critic，输出各组合的指标与模块贡献度：

```powershell
python evals/ablation.py --dataset benchmarks.datasets.enriched
python evals/ablation.py --suite planning
```

结果写入 `results/ablation/<timestamp>/`（REPORT.md + 各组合 summary/metrics）。

## Benchmark 与 Capability Framework（Sprint 03 / 04.5A）

- 数据集：`benchmarks/datasets/` 9 个文件、61 案例（easy/medium/hard + planning/memory/debate/counterfactual/adversarial + enriched）。
- 能力枚举：`benchmarks/capabilities.py`（7 种认知能力）。
- 覆盖矩阵自动生成：

```powershell
python -m benchmarks.capability_matrix
```

输出 `benchmarks/CAPABILITY_COVERAGE.md` 与 `benchmarks/CAPABILITY_ANNOTATION_SUGGESTIONS.md`（61 案例待人工标注）。

## 验证现状（2026-08-01）

- `pytest`：167 passed。
- `smoke_eval.py`：3 套 × 3 场景 passed。
- `fixture_eval.py`：12 场景 passed。
- enriched 基准：accuracy 1.00（15/15），详见 `results/summary.md`。
