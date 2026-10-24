# Phase 4.2 Validation Report (data summary only)

> Generated: 2026-08-10T03:28:27.938275+00:00
> Model: deepseek-v4-flash | temperature: 0.1 | base_url: https://api.deepseek.com
> Challenge set: benchmarks/challenge_set_v1.json
> Configs: ['C0', 'C1', 'C2'] | seeds: [42, 43, 44] | cases: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
> Total calls: 216

## 1. Call counts and validity

| seed | config | calls | valid | invalid | errors |
|---|---|---|---|---|---|
| 42 | C0 | 24 | 24 | 0 | 0 |
| 42 | C1 | 24 | 24 | 0 | 0 |
| 42 | C2 | 24 | 24 | 0 | 0 |
| 43 | C0 | 24 | 24 | 0 | 0 |
| 43 | C1 | 24 | 24 | 0 | 0 |
| 43 | C2 | 24 | 24 | 0 | 0 |
| 44 | C0 | 24 | 24 | 0 | 0 |
| 44 | C1 | 24 | 24 | 0 | 0 |
| 44 | C2 | 24 | 23 | 1 | 0 |

## 2. Per-config summary

| config | calls | ABSTAIN | diagnosis values | mean confidence (min-max) | mean coherence | validity rate | mean latency (s) |
|---|---|---|---|---|---|---|---|
| C0 | 72 | 41 | ABSTAIN=41, 番茄叶霉病=4, 早疫病=4, 褐斑病=3, 棉花黄萎病=3, 黄瓜霜霉病=2 | 0.3904 (0.0-0.95) | 2.9722 | 100.0% | 6.5333 |
| C1 | 72 | 33 | ABSTAIN=33, 番茄叶霉病=9, 棉花黄萎病=9, 番茄早疫病=8, 黄瓜霜霉病=6, 棉花枯萎病=4 | 0.5036 (0.0-0.95) | 3.3056 | 100.0% | 6.616 |
| C2 | 72 | 31 | ABSTAIN=31, 番茄叶霉病=9, 棉花黄萎病=9, 番茄早疫病=7, 甜菜褐斑病=5, 棉花枯萎病=4 | 0.5197 (0.0-0.95) | 3.3521 | 98.61% | 6.9335 |

## 3. Seed pass-through (audit)

| seed | calls | seed_accepted | seed_rejected |
|---|---|---|---|
| 42 | 72 | 72 | 0 |
| 43 | 72 | 72 | 0 |
| 44 | 72 | 72 | 0 |

## 4. Malformed outputs (validation only, not corrected)

| seed | config | case | error |
|---|---|---|---|
| 44 | C2 | 8 | invalid JSON: Invalid control character at: line 5 column 457 (char 523) |
