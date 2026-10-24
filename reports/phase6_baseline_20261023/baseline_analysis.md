# Phase 6 Baseline — Real Judge Full Run (2026-10-23)

> Branch: `work/20261023-phase6-arch-redesign`
> Channel: opencode zen gateway `https://opencode.ai/zen/go/v1` + `deepseek-v4.1-flash` (free tier)
> Design: 3 configs × 24 Challenge Set v1 cases × seed 42 = 72 executions, real LLM Judge
> Fallbacks: **0** (84/84 Judge calls HTTP 200)

## 1. Results

| config | definition | accuracy | conf mean | conf sd | ECE(10-bin) | corr(conf, correct) | false abstention | mean runtime |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | bare baseline (all modules off) | 0.833 (20/24) | 0.460 | 0.131 | 0.373 | 0.249 | 3 | 43.7s |
| C1 | all modules on | 0.792 (19/24) | 0.453 | 0.121 | 0.339 | 0.155 | 4 | 54.6s |
| C2 | all on **except memory** | **1.000 (24/24)** | 0.498 | 0.115 | 0.502 | n/a (no errors) | **0** | 42.5s |

Confidence histogram (all 72 runs pooled): [0.2,0.3)=6, [0.3,0.4)=17, [0.4,0.5)=14,
[0.5,0.6)=27, [0.6,0.7)=6, [0.7,0.8)=2, **[0.8,1.0]=0**.

## 2. Findings

### F1 — Confidence is compressed and nearly non-discriminative (primary defect)

Mean confidence 0.46–0.50 while accuracy is 0.79–1.00: the system is **systematically
under-confident**, and ECE is 0.34–0.50 (well above the 0.10 acceptance bar).
No single run produced confidence above 0.72; none reached 0.80.
The point-biserial correlation between confidence and correctness is only **0.155 (C1)**
and **0.249 (C0)** — confidence barely separates right from wrong answers:
correct cases average 0.475/0.462, wrong cases 0.388/0.416 (bands overlap).

**Root cause located** (`agents/judge_agent.py:367-374`): in the real-LLM path the
returned confidence is the model's self-reported `final_confidence` taken **verbatim**
(only clamped to [0,1] and rounded). The per-agent calibrator
(`utils/confidence_calibration.py`) is used **only by the rules path**
(`judge_agent.py:256-258`); the real-LLM path applies no calibration, no agreement
term, and no evidence-based adjustment.

### F2 — Memory injection is actively harmful on this challenge set

C1 and C2 differ **only** in `memory_on`. C1 scores 19/24, C2 scores 24/24.
Five cases flip from wrong to correct when memory is disabled:

| case | GT | C1 | C2 |
|---|---|---:|---:|
| `amb_tomato_curl_mold` | 叶霉病 | 0 (conf 0.38) | 1 (conf 0.55) |
| `amb_tomato_mold_blind_leaf` | 叶霉病 | 0 (0.38) | 1 (0.48) |
| `conf_tomato_blight_cool_rain` | 早疫病 | 0 (0.34) | 1 (0.58) |
| `inc_tomato_yellow_no_cue` | 证据不足 | 0 (0.58) | 1 (0.32) |
| `ms_tomato_mold_ventilate` | 叶霉病 | 0 (0.40) | 1 (0.55) |

Every flipping case is a **tomato** case, and memory-on consistently produced
*lower* confidence before answering wrong. This is consistent with retrieved
memory injecting loosely related evidence into the Judge payload.

### F3 — False abstention on diagnosable cases

Cases whose ground truth is a disease but which the system answered with an
abstention ("证据不足"/"无法定论"): C0 = 3, C1 = 4, C2 = 0. Abstention is not
reserved for genuinely ambiguous inputs.

### F4 — Accuracy ranking is unstable and C2's 24/24 is not yet trustworthy

Single seed (n=24) cannot separate C0/C1 (20 vs 19 correct). C2's perfect score is
5 flips above C1 — promising but must be replicated on ≥2 additional seeds before
any architecture conclusion is drawn.

## 3. Redesign implications

The evidence points at three connected defects, all in the aggregation layer rather
than the module set (see ADR-005):

1. **Confidence chain**: replace "LLM self-report = confidence" with a derived,
   calibrated quantity (self-report + structural agreement + evidence sufficiency,
   fitted post-hoc on labeled data).
2. **Abstention policy**: replace free-text-triggered abstention with a decision rule
   over calibrated confidence and evidence sufficiency, so abstention is reserved for
   genuinely insufficient evidence.
3. **Memory gating**: gate retrieval by relevance before it reaches the Judge payload.

## 4. Artifacts

- `reports/phase6_baseline_20261023/raw_results.json` (232 KB, full per-case records)
- `logs/phase6_baseline_20261023/run_42/config_{C0,C1,C2}/**/runner/` (72 traces, metrics.csv, summary.md)
- `logs/phase6_baseline_20261023/run.{out,err}.log` (84 Judge calls, zero errors)
- Analysis scripts (gitignored): `logs/analyze_baseline.py`, `logs/deep_stats.py`, `logs/percase.py`
