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

## Evaluation Runner（Sprint 02）

`evals/runner.py` 执行 benchmark 数据集，为每个 case 收集 unified Trace，
计算评估指标，并写出 `results/metrics.csv` 与 `results/summary.md`。

```powershell
$env:PYTHONIOENCODING='utf-8'
python evals/runner.py --dataset evals.fixtures
```

可配置项：

- `--planner-on/--planner-off`、`--debate-on/--debate-off`、
  `--memory-on/--memory-off`、`--tool-router-on/--tool-router-off`
- `--dataset <module 路径或 .json 文件>`（默认 `evals.fixtures`）
- `--output-dir`（默认 `results`）、`--seed`（默认 7）、`--rules-only`、
  `--max-cases N`

指标：`accuracy` / `average_confidence` / `average_runtime` /
`planner_usage` / `tool_usage` / `memory_hits` / `debate_rounds` /
`counterfactual_count` / `collective_omission_count`。
