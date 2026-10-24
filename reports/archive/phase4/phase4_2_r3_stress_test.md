# Phase 4.2-R3 Stress Test Report

> Started: 2026-08-13T17:35:56.218268+00:00 | Finished: 2026-08-13T19:05:50.510431+00:00
> Case: amb_tomato_mold_blind_leaf | Config: C1 | Seed: 42
> Endpoint: base_url=https://opencode.ai/zen/go/v1 model=deepseek-v4-flash

**Verdict: PASS** — success 30/30 (100.0%)

## Per-call results

| # | timestamp | judge_mode | elapsed (s) | decision | judge log |
|---|---|---|---|---|---|
| 1 | 17:38:23 | deepseek | 147.39 | 番茄叶霉病 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 2 | 17:40:53 | deepseek | 150.3 | 无法定论 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 3 | 17:45:24 | deepseek | 271.06 | 未确诊 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 4 | 17:47:34 | deepseek | 129.99 | 无法定论（疑似番茄叶霉病） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 5 | 17:49:25 | deepseek | 110.16 | 无法定论（疑似番茄叶霉病，需进一步验证） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 6 | 17:51:06 | deepseek | 101.02 | 番茄叶霉病 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 7 | 17:56:22 | deepseek | 316.31 | 无法定论（需进一步检测） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 8 | 17:59:13 | deepseek | 170.89 | 番茄叶霉病 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 9 | 18:02:42 | deepseek | 209.11 | 无法定论：需排除叶霉病与早疫病 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 10 | 18:06:52 | deepseek | 249.71 | 无法定论（疑似番茄叶霉病，但环境条件不支持） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 11 | 18:09:54 | deepseek | 182.19 | 无法定论 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 12 | 18:13:24 | deepseek | 210.1 | 暂无法定论（疑为番茄叶霉病，需人工复核） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 13 | 18:18:06 | deepseek | 282.06 | 番茄叶霉病（待复核） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 14 | 18:24:16 | deepseek | 369.5 | 未确定 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 15 | 18:26:48 | deepseek | 152.4 | 无法定论（疑似番茄叶霉病，需进一步确认） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 16 | 18:29:13 | deepseek | 145.52 | 无法定论 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 17 | 18:33:31 | deepseek | 257.92 | 无法定论 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 18 | 18:37:35 | deepseek | 243.79 | 无法定论（疑似番茄叶霉病） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 19 | 18:40:29 | deepseek | 174.36 | 待定（疑似番茄叶霉病） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 20 | 18:42:42 | deepseek | 132.16 | 无法定论 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 21 | 18:46:50 | deepseek | 248.31 | 番茄叶霉病 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 22 | 18:49:01 | deepseek | 130.68 | 无法定论（需进一步检测） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 23 | 18:51:05 | deepseek | 124.57 | 无法定论（疑似番茄叶霉病） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 24 | 18:52:33 | deepseek | 87.73 | 番茄叶霉病 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 25 | 18:54:01 | deepseek | 88.16 | 无法定论 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 26 | 18:56:10 | deepseek | 128.72 | 无法定论（疑似番茄叶霉病，需实验室检测） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 27 | 18:58:33 | deepseek | 142.8 | 无法定论 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 28 | 19:00:41 | deepseek | 128.2 | 无法定论（需进一步病原检测） | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 29 | 19:03:54 | deepseek | 192.79 | 番茄叶霉病 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |
| 30 | 19:05:50 | deepseek | 116.4 | 无法定论 | INFO:agents.judge_agent:Judge request: base_url=https://opencode.ai/zen/go/v1/, model=deepseek-v4-flash, temperature=0.1 |

## Summary

- Success rate: 30/30 (100.0%)
- Elapsed distribution (s): min=87.73 mean=179.81 max=369.50

## Failures

_None._
