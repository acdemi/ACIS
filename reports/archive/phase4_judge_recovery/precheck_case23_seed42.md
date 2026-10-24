# Phase 4.2-R Pre-check Report

> Generated: 2026-10-19T11:51:23.290959+00:00
> Case: ms_tomato_blight_stem | seed: 42 | configs: ['C1']
> Harness reference: reports\phase4_2_raw_results.json
> Reference execution semantics: `direct_llm_baseline_legacy`
> Real execution semantics: `acis_real_agent`

| config | real decision | real confidence | judge_mode | harness diagnosis | harness confidence | label match | conf. offset | comparison |
|---|---|---|---|---|---|---|---|---|
| C1 | 番茄早疫病 | 0.72 | deepseek | 番茄早疫病 | 0.85 | match (早疫病 vs 早疫病) | 0.130 | incomparable |

## Verdict

**INCOMPARABLE** — C1: direct_llm_baseline_legacy vs acis_real_agent

The reference was produced by a different execution path. Confidence offsets are retained for diagnosis but are not treated as equality gates.
