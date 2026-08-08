# Research Report: paper_main

## Overview

- Experiment: `paper_main`
- Directory: `results\experiments\paper_main__20260808_064250`
- Dataset: `benchmarks.datasets.enriched`
- Dataset SHA-256: `5efc214f7fd8204793df649a2003348f85e1d8e78229babd375e93fea424abe8`
- Git: `57176ae` (0.45C-Capability_Evaluation_Engine)
- Python: `3.13.3`
- Baseline: `all_on`
- Runs analysed: 4

## Run Statistics (LaTeX)

Mean ± std with 95% bootstrap CI (1000 resamples). Multi-seed runs aggregate at the seed level.

```latex
\begin{tabular}{lccccccc}
\toprule
run & seeds & cases & accuracy & confidence & planner_usage & tool_usage & memory_hits \\
\midrule
all\_on & 1 & 6 & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $0.642 \pm 0.088$ $[0.583, 0.702]$ & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $1.833 \pm 0.753$ $[1.333, 2.333]$ \\
no\_memory & 1 & 6 & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $0.642 \pm 0.088$ $[0.583, 0.702]$ & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $0.000 \pm 0.000$ $[0.000, 0.000]$ \\
no\_debate & 1 & 6 & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $0.635 \pm 0.078$ $[0.583, 0.688]$ & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $1.833 \pm 0.753$ $[1.333, 2.333]$ \\
no\_counterfactual & 1 & 6 & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $0.642 \pm 0.088$ $[0.583, 0.702]$ & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $1.000 \pm 0.000$ $[1.000, 1.000]$ & $1.833 \pm 0.753$ $[1.333, 2.333]$ \\
\bottomrule
\end{tabular}
```

## Capability Summary

| run | conflict_resolution | counterfactual_reasoning | information_gathering | knowledge_retrieval | multi_step_planning | sensor_cross_validation | uncertainty_quantification |
|---|---|---|---|---|---|---|---|
| all_on | 0.167 | 1.000 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| no_memory | 0.167 | 1.000 | 1.000 | 0.000 | 1.000 | 0.500 | 1.000 |
| no_debate | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| no_counterfactual | 0.167 | 0.000 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |

## Effect Sizes (LaTeX)

$\Delta = \mathrm{baseline} - \mathrm{ablated}$ with 95% bootstrap CI and two-sided bootstrap p-value. Significance: `*` p<0.05, `**` p<0.01, `***` p<0.001, `ns` not significant.

```latex
\begin{tabular}{llrrrl}
\toprule
ablated & field & $\Delta$ & CI low & CI high & sig \\
\midrule
no\_memory & accuracy & 0.000 & 0.000 & 0.000 & ns \\
no\_memory & confidence & 0.000 & -0.087 & 0.087 & ns \\
no\_memory & conflict\_resolution & 0.000 & -0.500 & 0.500 & ns \\
no\_memory & counterfactual\_reasoning & 0.000 & 0.000 & 0.000 & ns \\
no\_memory & information\_gathering & 0.000 & 0.000 & 0.000 & ns \\
no\_memory & knowledge\_retrieval & 1.000 & 1.000 & 1.000 & *** \\
no\_memory & multi\_step\_planning & 0.000 & 0.000 & 0.000 & ns \\
no\_memory & sensor\_cross\_validation & 0.000 & -0.500 & 0.500 & ns \\
no\_memory & uncertainty\_quantification & 0.000 & 0.000 & 0.000 & ns \\
no\_debate & accuracy & 0.000 & 0.000 & 0.000 & ns \\
no\_debate & confidence & 0.007 & -0.077 & 0.090 & ns \\
no\_debate & conflict\_resolution & 0.167 & 0.000 & 0.500 & ns \\
no\_debate & counterfactual\_reasoning & 0.000 & 0.000 & 0.000 & ns \\
no\_debate & information\_gathering & 0.000 & 0.000 & 0.000 & ns \\
no\_debate & knowledge\_retrieval & 0.000 & 0.000 & 0.000 & ns \\
no\_debate & multi\_step\_planning & 0.000 & 0.000 & 0.000 & ns \\
no\_debate & sensor\_cross\_validation & 0.000 & -0.500 & 0.500 & ns \\
no\_debate & uncertainty\_quantification & 0.000 & 0.000 & 0.000 & ns \\
no\_counterfactual & accuracy & 0.000 & 0.000 & 0.000 & ns \\
no\_counterfactual & confidence & 0.000 & -0.087 & 0.087 & ns \\
no\_counterfactual & conflict\_resolution & 0.000 & -0.500 & 0.500 & ns \\
no\_counterfactual & counterfactual\_reasoning & 1.000 & 1.000 & 1.000 & *** \\
no\_counterfactual & information\_gathering & 0.000 & 0.000 & 0.000 & ns \\
no\_counterfactual & knowledge\_retrieval & 0.000 & 0.000 & 0.000 & ns \\
no\_counterfactual & multi\_step\_planning & 0.000 & 0.000 & 0.000 & ns \\
no\_counterfactual & sensor\_cross\_validation & 0.000 & -0.500 & 0.500 & ns \\
no\_counterfactual & uncertainty\_quantification & 0.000 & 0.000 & 0.000 & ns \\
\bottomrule
\end{tabular}
```

## Module × Capability Association (mean Δ)

| module | conflict_resolution | counterfactual_reasoning | information_gathering | knowledge_retrieval | multi_step_planning | sensor_cross_validation | uncertainty_quantification |
|---|---|---|---|---|---|---|---|
| counterfactual | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| debate | 0.167 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| memory | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |

## Figures

### Figure 1: Ablation Capability Impact / 消融能力影响

![ablation_capability_impact.png](results/experiments/paper_main__20260808_064250/figures/ablation_capability_impact.png)

### Figure 2: Capability Radar / 能力雷达

![capability_radar.png](results/experiments/paper_main__20260808_064250/figures/capability_radar.png)

### Figure 3: Calibration Curve / 校准曲线

![calibration_curve.png](results/experiments/paper_main__20260808_064250/figures/calibration_curve.png)

### Figure 4: Comparison Heatmap / 对比热力图

![comparison_heatmap.png](results/experiments/paper_main__20260808_064250/figures/comparison_heatmap.png)

---

> 设计原则：可信度优先于完整度，效应量优先于 p 值，复现优先于美观。
> Design principle: credibility over completeness, effect size over p-value, reproduction over aesthetics.
