# Phase 4 Evaluation Pilot — Architecture Impact on Challenge Tasks

> Generated: 2026-08-09T14:20:51.982867+00:00
> Raw outputs: `E:\knowledge_database\ACIS\data\evaluation\challenge_raw`
> Coherence judge: LLM (deepseek-v4-flash) with per-case rule fallback

## Configurations

| configuration | description |
|---|---|
| C0 (Baseline) (`c0_bare_baseline`) | bare_baseline：无记忆、无规划、无辩论、无反思 |
| C1 (Full) (`c1_all_on`) | all_on：完整多 Agent 链路 |
| C2 (Critical Ablation) (`c2_no_memory`) | no_memory：关闭 RAG/KG/案例记忆，其余开启 |

## Aggregate Results

| configuration | n | accuracy (factor coverage) | ECE ↓ | abstention rate | coherence (0-3) |
|---|---|---|---|---|---|
| C0 (Baseline) (`c0_bare_baseline`) | 24 | 0.5611 | 0.4979 | 29.17% | 1.8333 |
| C1 (Full) (`c1_all_on`) | 24 | 0.5451 | 0.4571 | 25.00% | 1.6667 |
| C2 (Critical Ablation) (`c2_no_memory`) | 24 | 0.5062 | 0.5104 | 25.00% | 1.5833 |

## Per-Group Breakdown

| configuration | group | n | accuracy | ECE ↓ | abstention | coherence |
|---|---|---|---|---|---|---|
| C0 (Baseline) (`c0_bare_baseline`) | ambiguity | 6 | 0.5417 | 0.5300 | 16.67% | 1.8333 |
| C0 (Baseline) (`c0_bare_baseline`) | conflicting | 6 | 0.5250 | 0.4767 | 16.67% | 1.6667 |
| C0 (Baseline) (`c0_bare_baseline`) | incomplete | 6 | 0.7778 | 0.3333 | 83.33% | 2.5000 |
| C0 (Baseline) (`c0_bare_baseline`) | multi_step | 6 | 0.4000 | 0.6517 | 0.00% | 1.3333 |
| C1 (Full) (`c1_all_on`) | ambiguity | 6 | 0.5000 | 0.5533 | 0.00% | 1.6667 |
| C1 (Full) (`c1_all_on`) | conflicting | 6 | 0.7167 | 0.4400 | 16.67% | 2.0000 |
| C1 (Full) (`c1_all_on`) | incomplete | 6 | 0.5972 | 0.1667 | 83.33% | 1.8333 |
| C1 (Full) (`c1_all_on`) | multi_step | 6 | 0.3667 | 0.6683 | 0.00% | 1.1667 |
| C2 (Critical Ablation) (`c2_no_memory`) | ambiguity | 6 | 0.5000 | 0.5417 | 0.00% | 1.6667 |
| C2 (Critical Ablation) (`c2_no_memory`) | conflicting | 6 | 0.4917 | 0.6350 | 16.67% | 1.3333 |
| C2 (Critical Ablation) (`c2_no_memory`) | incomplete | 6 | 0.4583 | 0.2167 | 83.33% | 1.5000 |
| C2 (Critical Ablation) (`c2_no_memory`) | multi_step | 6 | 0.5750 | 0.6483 | 0.00% | 1.8333 |

## Judge Mode Distribution

| configuration | judge_mode -> count |
|---|---|
| C0 (Baseline) (`c0_bare_baseline`) | deepseek=24 |
| C1 (Full) (`c1_all_on`) | deepseek=24 |
| C2 (Critical Ablation) (`c2_no_memory`) | deepseek=24 |

## Interpretation Guide

- C1 在任一维度显著优于 C0 → 证据支持 ACIS 架构优势（补全 Phase 3 饱和结论）。
- 仅 ECE / 弃权率有差异 → 强调决策质量收益而非准确率收益。
- 全无差异 → 建议进入 Phase 6（架构重设计），不再增加工程复杂度。
- 注意：abstention rate 在 incomplete 组为期望行为（正确弃权），数值高并不等于性能差；需结合准确率解读。
