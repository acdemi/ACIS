# Phase 4.2-R Pre-check Report

> Generated: 2026-10-17T15:19:29.115235+00:00
> Case: ms_tomato_blight_stem | seed: 42 | configs: ['C1']
> Harness reference: reports\phase4_2_raw_results.json
> Reference execution semantics: `direct_llm_baseline_legacy`
> Real execution semantics: `acis_real_agent`

| config | real decision | real confidence | judge_mode | harness diagnosis | harness confidence | label match | conf. offset | comparison |
|---|---|---|---|---|---|---|---|---|
| C1 | 病理判断首选：番茄早疫病 | 0.75 | rules | 番茄早疫病 | 0.85 | match (早疫病 vs 早疫病) | 0.100 | real_judge_fallback |

## Verdict

**FAIL** — C1: real Judge fell back to rules [authentication_error]
