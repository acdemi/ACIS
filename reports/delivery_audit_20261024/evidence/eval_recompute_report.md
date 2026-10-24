# Phase 6 metric recomputation (independent script, committed scorers)

## baseline_42

| slice | n | acc | conf mean | sd(pop) | ECE committed | ECE reimpl | corr | false abst | judge_mode |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| C0 | 24 | 20/24 (0.8333) | 0.4604 | 0.1309 | 0.372917 | 0.372917 | 0.2491 | 3 | {'deepseek': 24} |
| C1 | 24 | 19/24 (0.7917) | 0.4525 | 0.1211 | 0.375833 | 0.375833 | 0.1546 | 4 | {'deepseek': 24} |
| C2 | 24 | 24/24 (1.0) | 0.4979 | 0.1146 | 0.502083 | 0.502083 | None | 0 | {'deepseek': 24} |

pooled confidence histogram (72): {'[0.0,0.1)': 0, '[0.1,0.2)': 0, '[0.2,0.3)': 9, '[0.3,0.4)': 14, '[0.4,0.5)': 14, '[0.5,0.6)': 27, '[0.6,0.7)': 6, '[0.7,0.8)': 2, '[0.8,0.9)': 0, '[0.9,1.0)': 0}

## sc_c1_42

| slice | n | acc | conf mean | sd(pop) | ECE committed | ECE reimpl | corr | false abst | judge_mode |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| full24 | 24 | 21/24 (0.875) | 0.8148 | 0.0898 | 0.126817 | 0.126817 | -0.1619 | 2 | {'deepseek': 13, 'rules': 11} |
| restricted13 | 13 | 11/13 (0.8462) | 0.8951 | 0.0169 | 0.074123 | 0.074123 | -0.1231 | 2 | {'deepseek': 13} |

## sc43_c1_43

| slice | n | acc | conf mean | sd(pop) | ECE committed | ECE reimpl | corr | false abst | judge_mode |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| full24 | 24 | 19/24 (0.7917) | 0.6167 | 0.4007 | 0.175 | 0.175 | 0.5078 | 4 | {'deepseek': 24} |

## ablation_c0c2_43

| slice | n | acc | conf mean | sd(pop) | ECE committed | ECE reimpl | corr | false abst | judge_mode |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| C0 | 24 | 9/24 (0.375) | 0.6321 | 0.3182 | 0.456238 | 0.456238 | -0.0707 | 14 | {'deepseek': 24} |
| C2 | 24 | 9/24 (0.375) | 0.5738 | 0.2203 | 0.384679 | 0.384679 | 0.2482 | 5 | {'deepseek': 6, 'rules': 18} |

## Report claim vs recomputed

| slice | metric | report | recomputed | match |
|---|---|---:|---:|:--:|
| baseline_42/C0 | accuracy | 0.833 | 0.8333 | YES |
| baseline_42/C0 | accuracy_fraction | 20/24 | 20/24 | YES |
| baseline_42/C0 | conf_mean | 0.46 | 0.4604 | YES |
| baseline_42/C0 | conf_sd(pop) | 0.131 | 0.1309 | YES |
| baseline_42/C0 | ece | 0.373 | 0.372917 | YES |
| baseline_42/C0 | corr | 0.249 | 0.2491 | YES |
| baseline_42/C0 | false_abstention | 3 | 3 | YES |
| baseline_42/C1 | accuracy | 0.792 | 0.7917 | YES |
| baseline_42/C1 | accuracy_fraction | 19/24 | 19/24 | YES |
| baseline_42/C1 | conf_mean | 0.453 | 0.4525 | YES |
| baseline_42/C1 | conf_sd(pop) | 0.121 | 0.1211 | YES |
| baseline_42/C1 | ece | 0.339 | 0.375833 | NO |
| baseline_42/C1 | corr | 0.155 | 0.1546 | YES |
| baseline_42/C1 | false_abstention | 4 | 4 | YES |
| baseline_42/C2 | accuracy | 1.0 | 1.0 | YES |
| baseline_42/C2 | accuracy_fraction | 24/24 | 24/24 | YES |
| baseline_42/C2 | conf_mean | 0.498 | 0.4979 | YES |
| baseline_42/C2 | conf_sd(pop) | 0.115 | 0.1146 | YES |
| baseline_42/C2 | ece | 0.502 | 0.502083 | YES |
| baseline_42/C2 | corr | None | None | YES |
| baseline_42/C2 | false_abstention | 0 | 0 | YES |
| sc_c1_42/restricted13 | accuracy | 0.846 | 0.8462 | YES |
| sc_c1_42/restricted13 | accuracy_fraction | 11/13 | 11/13 | YES |
| sc_c1_42/restricted13 | ece | 0.0769 | 0.074123 | NO |
| sc_c1_42/restricted13 | corr | 0.778 | -0.1231 | NO |
| sc43_c1_43/full24 | accuracy | 0.792 | 0.7917 | YES |
| sc43_c1_43/full24 | accuracy_fraction | 19/24 | 19/24 | YES |
| sc43_c1_43/full24 | ece | 0.0708 | 0.175 | NO |
| sc43_c1_43/full24 | corr | 0.538 | 0.5078 | NO |

## Dataset <-> raw-result integrity

- baseline_42: records=72 distinct_case_ids=24 unknown_ids=0 field_mismatches=0
- sc_c1_42: records=24 distinct_case_ids=24 unknown_ids=0 field_mismatches=0
- sc43_c1_43: records=24 distinct_case_ids=24 unknown_ids=0 field_mismatches=0
- ablation_c0c2_43: records=48 distinct_case_ids=24 unknown_ids=0 field_mismatches=0

## Trace cross-check (case/trace id -> local trace file)

- baseline_42/C0: found=24 missing=0 decision_matches=24 confidence_matches=24
- baseline_42/C1: found=24 missing=0 decision_matches=24 confidence_matches=24
- baseline_42/C2: found=24 missing=0 decision_matches=24 confidence_matches=24
- sc_c1_42/trace_check_full: found=24 missing=0 decision_matches=24 confidence_matches=24
- sc_c1_42/trace_check_restricted: found=13 missing=0 decision_matches=13 confidence_matches=13
- ablation_c0c2_43/C0: found=24 missing=0 decision_matches=24 confidence_matches=24
- ablation_c0c2_43/C2: found=24 missing=0 decision_matches=24 confidence_matches=24
