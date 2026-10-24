# Phase 4.2-R Stability Report (data only)

> Generated: 2026-08-13T02:35:28.562082+00:00
> Source: 2026-08-12T10:46:54.646837+00:00 | configs: ['C0', 'C1', 'C2'] | seeds: [42, 43, 44]
> Coherence judge: LLM with per-case rule fallback
> Pilot reference: recorded Phase 4.1 observations (source: reports/phase4_evaluation_pilot.md (Phase 4.1 pilot, recorded observations))

## 1. Mean ± Std across seeds (per configuration)

| config | metric | mean | std |
|---|---|---|---|
| C0 | accuracy | 0.1893 | 0.0792 |
| C0 | ece | 0.5846 | 0.1927 |
| C0 | abstention_rate | 25.0000 | 35.3553 |
| C0 | coherence | 0.6667 | 0.2357 |
| C1 | accuracy | 0.1438 | 0.0000 |
| C1 | ece | 0.7114 | 0.0010 |
| C1 | abstention_rate | 0.0000 | 0.0000 |
| C1 | coherence | 0.5417 | 0.0000 |
| C2 | accuracy | 0.1438 | 0.0000 |
| C2 | ece | 0.7121 | 0.0000 |
| C2 | abstention_rate | 0.0000 | 0.0000 |
| C2 | coherence | 0.5417 | 0.0000 |

## 1b. Per-difficulty breakdown (Mean ± Std across seeds)

| config | difficulty | metric | mean | std |
|---|---|---|---|---|
| C0 | 1 | accuracy | 0.2222 | 0.3143 |
| C0 | 1 | ece | 0.4533 | 0.1791 |
| C0 | 1 | abstention_rate | 33.3333 | 47.1405 |
| C0 | 1 | coherence | 0.6667 | 0.9428 |
| C0 | 2 | accuracy | 0.1759 | 0.0524 |
| C0 | 2 | ece | 0.5826 | 0.2195 |
| C0 | 2 | abstention_rate | 25.9267 | 36.6658 |
| C0 | 2 | coherence | 0.6667 | 0.1571 |
| C0 | 3 | accuracy | 0.1936 | 0.0617 |
| C0 | 3 | ece | 0.6267 | 0.1472 |
| C0 | 3 | abstention_rate | 23.0767 | 32.6353 |
| C0 | 3 | coherence | 0.6667 | 0.1813 |
| C1 | 1 | accuracy | 0.0000 | 0.0000 |
| C1 | 1 | ece | 0.5800 | 0.0000 |
| C1 | 1 | abstention_rate | 0.0000 | 0.0000 |
| C1 | 1 | coherence | 0.0000 | 0.0000 |
| C1 | 2 | accuracy | 0.1667 | 0.0000 |
| C1 | 2 | ece | 0.7322 | 0.0000 |
| C1 | 2 | abstention_rate | 0.0000 | 0.0000 |
| C1 | 2 | coherence | 0.6667 | 0.0000 |
| C1 | 3 | accuracy | 0.1500 | 0.0000 |
| C1 | 3 | ece | 0.7172 | 0.0018 |
| C1 | 3 | abstention_rate | 0.0000 | 0.0000 |
| C1 | 3 | coherence | 0.5385 | 0.0000 |
| C2 | 1 | accuracy | 0.0000 | 0.0000 |
| C2 | 1 | ece | 0.5800 | 0.0000 |
| C2 | 1 | abstention_rate | 0.0000 | 0.0000 |
| C2 | 1 | coherence | 0.0000 | 0.0000 |
| C2 | 2 | accuracy | 0.1667 | 0.0000 |
| C2 | 2 | ece | 0.7322 | 0.0000 |
| C2 | 2 | abstention_rate | 0.0000 | 0.0000 |
| C2 | 2 | coherence | 0.6667 | 0.0000 |
| C2 | 3 | accuracy | 0.1500 | 0.0000 |
| C2 | 3 | ece | 0.7185 | 0.0000 |
| C2 | 3 | abstention_rate | 0.0000 | 0.0000 |
| C2 | 3 | coherence | 0.5385 | 0.0000 |

## 2. Empirically observed Full Ranking & Pairwise Dominance

Metric directions as recorded: accuracy/abstention/coherence descending, ECE ascending (reference note only, no judgment).

| seed | metric | ranking |
|---|---|---|
| run_42 | accuracy | C0 > C2 > C1 |
| run_42 | ece | C0 > C1 > C2 |
| run_42 | abstention_rate | C0 > C2 > C1 |
| run_42 | coherence | C0 > C2 > C1 |
| run_43 | accuracy | C2 > C1 > C0 |
| run_43 | ece | C1 > C2 > C0 |
| run_43 | abstention_rate | C2 > C1 > C0 |
| run_43 | coherence | C2 > C1 > C0 |
| run_44 | accuracy | C2 > C1 > C0 |
| run_44 | ece | C1 > C2 > C0 |
| run_44 | abstention_rate | C2 > C1 > C0 |
| run_44 | coherence | C2 > C1 > C0 |

Pairwise dominance (number of seeds where the left config wins per metric):

| metric | pair | dominance |
|---|---|---|
| accuracy | C0 vs C1 | C0 ahead in 1/3 seeds |
| accuracy | C0 vs C2 | C0 ahead in 1/3 seeds |
| accuracy | C1 vs C2 | C1 ahead in 0/3 seeds |
| ece | C0 vs C1 | C0 ahead in 1/3 seeds |
| ece | C0 vs C2 | C0 ahead in 1/3 seeds |
| ece | C1 vs C2 | C1 ahead in 3/3 seeds |
| abstention_rate | C0 vs C1 | C0 ahead in 1/3 seeds |
| abstention_rate | C0 vs C2 | C0 ahead in 1/3 seeds |
| abstention_rate | C1 vs C2 | C1 ahead in 0/3 seeds |
| coherence | C0 vs C1 | C0 ahead in 1/3 seeds |
| coherence | C0 vs C2 | C0 ahead in 1/3 seeds |
| coherence | C1 vs C2 | C1 ahead in 0/3 seeds |

## 3. Phase 4.1 pilot reference (recorded, informational)

Comparison mode: within_agent_only — rankings above are empirically observed within Phase 4.2-R; the pilot orderings are listed as reference data without match/flip judgment.

| metric | pilot observed ranking |
|---|---|
| accuracy | c0_bare_baseline > c1_all_on > c2_no_memory |
| ece | c1_all_on > c0_bare_baseline > c2_no_memory |
| abstention_rate | c0_bare_baseline > c1_all_on > c2_no_memory |
| coherence | c0_bare_baseline > c1_all_on > c2_no_memory |

## 4. Pilot reference values (Phase 4.1, recorded)

| config | accuracy | ECE | abstention rate | coherence |
|---|---|---|---|---|
| C0 | 0.5611 | 0.4979 | 29.17 | 1.8333 |
| C1 | 0.5451 | 0.4571 | 25.0 | 1.6667 |
| C2 | 0.5062 | 0.5104 | 25.0 | 1.5833 |

_This report records measurements and observed orderings only; no stability judgment is attached._
