# Phase 4.2-R Stability Report (data only)

> Generated: 2026-08-17T12:58:51.612216+00:00
> Source: 2026-08-15T14:01:53.978822+00:00 | configs: ['C0', 'C1', 'C2'] | seeds: [42, 43, 44]
> Coherence judge: rule engine
> Pilot reference: recorded Phase 4.1 observations (source: reports/phase4_evaluation_pilot.md (Phase 4.1 pilot, recorded observations))

## 1. Mean ± Std across seeds (per configuration)

| config | metric | mean | std |
|---|---|---|---|
| C0 | accuracy | 0.3623 | 0.1624 |
| C0 | ece | 0.4597 | 0.1887 |
| C0 | abstention_rate | 23.6100 | 18.7358 |
| C0 | coherence | 1.2222 | 0.5118 |
| C1 | accuracy | 0.2799 | 0.1505 |
| C1 | ece | 0.5408 | 0.1808 |
| C1 | abstention_rate | 16.6667 | 13.6069 |
| C1 | coherence | 0.9722 | 0.4440 |
| C2 | accuracy | 0.2975 | 0.1247 |
| C2 | ece | 0.5411 | 0.1212 |
| C2 | abstention_rate | 23.6100 | 16.7814 |
| C2 | coherence | 0.9722 | 0.3269 |

## 1b. Per-difficulty breakdown (Mean ± Std across seeds)

| config | difficulty | metric | mean | std |
|---|---|---|---|---|
| C0 | 1 | accuracy | 0.5278 | 0.4101 |
| C0 | 1 | ece | 0.5267 | 0.2076 |
| C0 | 1 | abstention_rate | 50.0000 | 40.8248 |
| C0 | 1 | coherence | 1.6667 | 1.2472 |
| C0 | 2 | accuracy | 0.3179 | 0.1372 |
| C0 | 2 | ece | 0.4919 | 0.1740 |
| C0 | 2 | abstention_rate | 14.8133 | 10.4746 |
| C0 | 2 | coherence | 1.0741 | 0.4091 |
| C0 | 3 | accuracy | 0.3675 | 0.1590 |
| C0 | 3 | ece | 0.5015 | 0.1623 |
| C0 | 3 | abstention_rate | 25.6433 | 22.0588 |
| C0 | 3 | coherence | 1.2564 | 0.5229 |
| C1 | 1 | accuracy | 0.1389 | 0.1964 |
| C1 | 1 | ece | 0.5200 | 0.0849 |
| C1 | 1 | abstention_rate | 0.0000 | 0.0000 |
| C1 | 1 | coherence | 0.5000 | 0.7071 |
| C1 | 2 | accuracy | 0.2685 | 0.0796 |
| C1 | 2 | ece | 0.5315 | 0.1811 |
| C1 | 2 | abstention_rate | 14.8133 | 13.8566 |
| C1 | 2 | coherence | 1.0370 | 0.2771 |
| C1 | 3 | accuracy | 0.3094 | 0.1988 |
| C1 | 3 | ece | 0.5505 | 0.1981 |
| C1 | 3 | abstention_rate | 20.5133 | 23.7807 |
| C1 | 3 | coherence | 1.0000 | 0.5475 |
| C2 | 1 | accuracy | 0.4167 | 0.3402 |
| C2 | 1 | ece | 0.4517 | 0.0958 |
| C2 | 1 | abstention_rate | 50.0000 | 40.8248 |
| C2 | 1 | coherence | 1.3333 | 1.0274 |
| C2 | 2 | accuracy | 0.2593 | 0.0655 |
| C2 | 2 | ece | 0.5770 | 0.1103 |
| C2 | 2 | abstention_rate | 25.9233 | 18.8834 |
| C2 | 2 | coherence | 0.9259 | 0.1888 |
| C2 | 3 | accuracy | 0.3055 | 0.1402 |
| C2 | 3 | ece | 0.5300 | 0.1338 |
| C2 | 3 | abstention_rate | 17.9500 | 13.0751 |
| C2 | 3 | coherence | 0.9487 | 0.3459 |

## 2. Empirically observed Full Ranking & Pairwise Dominance

Metric directions as recorded: accuracy/abstention/coherence descending, ECE ascending (reference note only, no judgment).

| seed | metric | ranking |
|---|---|---|
| run_42 | accuracy | C0 > C2 > C1 |
| run_42 | ece | C0 > C2 > C1 |
| run_42 | abstention_rate | C0 > C2 > C1 |
| run_42 | coherence | C0 > C2 > C1 |
| run_43 | accuracy | C1 > C0 > C2 |
| run_43 | ece | C1 > C0 > C2 |
| run_43 | abstention_rate | C2 > C1 > C0 |
| run_43 | coherence | C1 > C0 > C2 |
| run_44 | accuracy | C2 > C1 > C0 |
| run_44 | ece | C1 > C2 > C0 |
| run_44 | abstention_rate | C2 > C1 > C0 |
| run_44 | coherence | C2 > C1 > C0 |

Pairwise dominance (number of seeds where the left config wins per metric):

| metric | pair | dominance |
|---|---|---|
| accuracy | C0 vs C1 | C0 ahead in 1/3 seeds |
| accuracy | C0 vs C2 | C0 ahead in 2/3 seeds |
| accuracy | C1 vs C2 | C1 ahead in 1/3 seeds |
| ece | C0 vs C1 | C0 ahead in 1/3 seeds |
| ece | C0 vs C2 | C0 ahead in 2/3 seeds |
| ece | C1 vs C2 | C1 ahead in 2/3 seeds |
| abstention_rate | C0 vs C1 | C0 ahead in 1/3 seeds |
| abstention_rate | C0 vs C2 | C0 ahead in 1/3 seeds |
| abstention_rate | C1 vs C2 | C1 ahead in 0/3 seeds |
| coherence | C0 vs C1 | C0 ahead in 1/3 seeds |
| coherence | C0 vs C2 | C0 ahead in 2/3 seeds |
| coherence | C1 vs C2 | C1 ahead in 1/3 seeds |

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
