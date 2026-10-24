# Phase 4.2-R Pre-check Report

> Generated: 2026-10-19T11:53:54.923267+00:00
> Case: inc_tomato_vague_spot | seed: 42 | configs: ['C1']
> Harness reference: reports\phase4_2_raw_results.json
> Reference execution semantics: `direct_llm_baseline_legacy`
> Real execution semantics: `acis_real_agent`

| config | real decision | real confidence | judge_mode | harness diagnosis | harness confidence | label match | conf. offset | comparison |
|---|---|---|---|---|---|---|---|---|
| C1 | 番茄早疫病 | 0.45 | deepseek | ABSTAIN | 0.2 | DIFFERS (早疫病 vs ABSTAIN) | 0.250 | incomparable |

## Verdict

**INCOMPARABLE** — C1: direct_llm_baseline_legacy vs acis_real_agent (labels differ)

The reference was produced by a different execution path. Confidence offsets are retained for diagnosis but are not treated as equality gates.
