# Phase 4.2-R Pre-check Report

> Generated: 2026-08-12T10:20:31.496008+00:00
> Case: amb_tomato_mold_blind_leaf | seed: 42 | configs: ['C0', 'C1', 'C2']
> Harness reference: reports\phase4_2_harness\phase4_2_raw_results.json

| config | real decision | real confidence | judge_mode | harness diagnosis | harness confidence | label match | conf. offset |
|---|---|---|---|---|---|---|---|
| C0 | 无法定论 | 0.3 | deepseek | 番茄叶霉病 | 0.92 | DIFFERS (ABSTAIN vs 叶霉病) | 0.620 |
| C1 | 番茄叶霉病 | 0.72 | deepseek | 番茄叶霉病 | 0.85 | match (叶霉病 vs 叶霉病) | 0.130 |
| C2 | 番茄叶霉病 | 0.65 | deepseek | 番茄叶霉病 | 0.95 | match (叶霉病 vs 叶霉病) | 0.300 |

## Verdict

**FAIL** — C0: confidence offset 0.620 > 0.3
