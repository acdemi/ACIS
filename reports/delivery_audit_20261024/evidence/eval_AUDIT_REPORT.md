# ACIS 交付审计 · 第 4 项「效果可验证」复核报告

- 审计员: eval-auditor（Agent Team）, 任务 task-2
- 分支: `work/20261024-delivery-audit`（只读；未切换分支、未 commit、未改任何被跟踪文件）
- 时间: 2026-10-24 14:07–14:25 (Asia/Hong_Kong)
- 输出目录: `logs/delivery_audit_20261024/eval/`
- 约束遵守: 未调用真实 LLM / 外网；所有重跑均为 `--rules-only` 离线路径。
  说明: `evals/runner.py` 运行时会连 **本机** `http://localhost:6333`（Qdrant），
  返回 502（服务未起），属本机依赖缺失，不是外网调用。

---

## 1. 固定测试集与标签清点

| 名称 | 案例数 | 标签字段 | 文件路径 | 加载路径 |
|---|---|---|---|---|
| Challenge Set v1 | **24** (4 组×6) | `ground_truth`(24/24)、`expected_key_factors`(2–5/例)、`design_intent`(24/24)、`crop`、`intent`、`difficulty`、`group`；**无 capability 标签** | `benchmarks/challenge_set_v1.json` | 唯一入口 `scripts/run_challenge_evaluation.py:128 load_challenge_set()` → `flatten_challenge_set():103` → 临时 flattened JSON → `evals.config.load_dataset`；内置 loader 不可达（已实测抛 `BenchmarkValidationError`） |
| easy / medium / hard | 12 / 10 / 6 = **28** | `ground_truth`、`disease`、`crop`、`intent`、`observable_evidence`、`capabilities`、`design_intent`（easy 5/12、medium 5/10、hard 6/6 有） | `benchmarks/datasets/*.json` | `benchmarks.loader.load_dataset("benchmarks.datasets.<name>")`（`loader.py:27`） |
| planning / memory / debate / counterfactual / adversarial | 4/4/4/3/3 = **18** | 同上 + `design_intent`(全部)、`capabilities`(全部) | 同上 | `loader.load_suite()` / `--suite`（`loader.py:59-82`）；**不经** `benchmarks.datasets.<name>`（实测报错） |
| enriched | **18** | `ground_truth`、`metadata{design_intent, capabilities, observable_evidence, expected_reasoning_features, difficulty, ...}`、`expected_tools`、`expected_confidence_range` | `benchmarks/datasets/enriched.json` | `load_dataset("benchmarks.datasets.enriched")` |
| **合计** | **64** | 全部 64 例有 `ground_truth`；`expected_key_factors` **仅** challenge set 有 | | |

### 报告声称 vs 实际（`benchmarks/*.md`）

| 声称 | 出处 | 实际 | 结论 |
|---|---|---|---|
| 24 例 / 4 组 | CHALLENGE_SET_V1_REPORT.md:5 | 24 / 4（每组 6） | ✅ |
| 64 例 / 9 数据集 + 逐数据集数量 | 同上:13-23 | 64，12/10/6/18/12/6 全对 | ✅ |
| 难度 d1×2、d2×10、d3×12 | 同上:62 | 实际 **d1=2、d2=9、d3=13** | ❌ 差 1 例 |
| 「49 个带 ground_truth 的 cases」 | 同上:26 | **64/64 都有 GT**；49 = 其中「GT 为明确病害」的子集（其余 15 例 GT=证据不足） | ⚠️ 措辞错误（数字本身可对上） |
| 24 个 id 与 64 例零冲突；内置 9 数据集合计 64 | 同上:64-67 | 零冲突；合计 64 | ✅ |
| 全部 24 例 `expected_key_factors` 都在规则别名表 | 同上:82 | 34 个不同因子，`FACTOR_ALIASES` 缺失 0 个 | ✅ |
| 52/64 有 capability 标注、52/52 一致、12 例按设计未标注 | CAPABILITY_CONSISTENCY_REPORT.md:1-6 / README:84-92 | 标注 52，未标注 12 = easy 7 + medium 5 | ✅（一致性本身为自报，未独立语义复核） |

### 标签质量风险

1. **Challenge set 自带 0 capability 标签**：24 例均无 `capabilities`/`observable_evidence`，
   与 64 例 benchmark 的「能力可验证」口径不互通；64 例数据集也**没有** `expected_key_factors`，
   因子覆盖类指标只在 24 例 challenge set 上可算。
2. **GT 是唯一可判文本**，且判分是**子串包含**（`decision_semantics.py:62-72`）：
   `expected in decision`。实测 baseline 72 条记录中 **20 条** GT 病名只出现在
   「需排除…」这类否定语境中仍被判对（如 `amb_tomato_ring_before_gray`：
   "疑似番茄早疫病…需排除…叶霉病" 记 correct）。当前数据没有因此误判，但机制脆弱：
   若把被排除病害写进 GT 即可被白送分。challenge set 无 `acceptable_alternatives` 字段。
3. GT 词表仅 8 个取值（7 病害 + 证据不足）；同义/亚型写法（如"番茄叶霉病"vs"叶霉病"）
   靠子串失效与否决定对错，标签严格度不均。
4. 12 个未标注 capability 的案例（easy 7 + medium 5）在交付文档中被称为「难度案例按设计未标注」，
   实为 easy/medium 基础例，措辞与数据不符。

---

## 2. 复算（独立脚本，用仓库已提交评分实现）

脚本: `logs/delivery_audit_20261024/eval/recompute.py`
（accuracy=`decision_semantics.decision_correctness`；ECE=`challenge_scorer.calc_confidence_calibration`；
corr=独立实现的 Pearson/point-biserial，**仓库无已提交的 corr 实现**，见缺口 G5。）

### 2.1 baseline seed42（`reports/phase6_baseline_20261023/raw_results.json`，72 条）

| config | 报告 accuracy | 复算 | 报告 conf mean/sd | 复算 | 报告 ECE | 复算(committed) | 复算(range-bin) | 报告 corr | 复算 corr | false abst 报告/复算 |
|---|---|---|---|---|---|---|---|---|---|---|
| C0 | 0.833 (20/24) | 20/24 ✅ | 0.460/0.131 | 0.4604/0.1309 ✅ | 0.373 | 0.3729 ✅ | 0.3729 | 0.249 | 0.2491 ✅ | 3/3 ✅ |
| C1 | 0.792 (19/24) | 19/24 ✅ | 0.453/0.121 | 0.4525/0.1211 ✅ | 0.339 | **0.3758 ❌** | 0.3392 ✅ | 0.155 | 0.1546 ✅ | 4/4 ✅ |
| C2 | 1.000 (24/24) | 24/24 ✅ | 0.498/0.115 | 0.4979/0.1146 ✅ | 0.502 | 0.5021 ✅ | 0.5021 | n/a（无错误样本，相关度退化） | None ✅ | 0/0 ✅ |

- 报告置信度直方图（6/17/14/27/6/2/0）与 `logs/phase6_baseline_20261023/run.out.log`
  **逐条一致**（72 行，conf 逐例相同）；报告该表可信。
- C1 ECE 差异根因（已定位）：报告用**区间分箱**（`lo<=c<hi`，见未入库的 `logs/analyze_baseline.py:45-56`）；
  已提交的 `challenge_scorer.calc_confidence_calibration:154` 用
  `int(confidence/bin_size)`，因 IEEE-754 有 **0.3/0.1=2.9999…→2** 的边界缺陷，
  恰好把 conf=0.3 的样本移入 [0.2,0.3)，C1 因此从 0.3392 变 0.3758（C0/C2 无影响）。

### 2.2 自一致性（SC）两跑：报告数字来自**未入库信号**

`final_evidence.md:19-24` 表：

| seed | 报告「可评案例」 | 报告 accuracy | 报告 ECE | 复算(committed raw) | 报告 corr | 复算(raw) | 用 traces 的 agreement 复算 |
|---|---|---|---|---|---|---|---|
| 42 | 13/24 | 0.846 (11/13) | 0.0769 | raw 全量 21/24；13 例子集 acc 11/13 ✅；ECE=0.1268(full)/0.0741(13) ❌ | 0.778 | −0.1231 ❌ | **ECE 0.076923 ✅ / corr 0.7785 ✅** |
| 43 | 24/24 | 0.792 (19/24) | 0.0708 | acc 19/24 ✅；ECE=0.175 ❌ | 0.538 | 0.5078 ❌ | **ECE 0.070833 ✅ / corr 0.5379 ✅** |

- 关键发现：已提交 raw JSON 里的 `confidence` 是**策略后置信度**（seed42 有 0.9/0.69/0.8364…；
  seed43 只有 {0.05, 0.9}），而报告 ECE/corr 的「置信度」是
  **`confidence := min(0.95, self_consistency.agreement)`**，该 agreement 只存在于
  **gitignored 的 trace 文件** `judge_analysis.confidence_design.self_consistency.agreement`。
  用 traces 重建后与报告**逐位吻合**（0.076923/0.7785/0.070833/0.5379），
  且 `final_evidence.md:28-34` 的 agreement 分层（3/5/16 例、0.333/0.600/0.938）也完全复现。
  → **报告数字是诚实的，但 committed 原始结果不足以复算它们。**
- 证据脚本: `eval/map_report_signal.py`、`eval/reconcile_agreement.py`、`eval/agreement_reconcile.json`。

### 2.3 ablation seed43（未跟踪 WIP，仅参考）

`reports/phase6_ablation_20261024/raw_results_c0c2_seed43.json`（`git ls-files` 无记录、`check-ignore`=未忽略）：
C0 9/24 (0.375)、C2 9/24 (0.375)，ECE 0.456/0.385，corr −0.071/0.248；judge fallback 18/48（rules）。
与 seed42 baseline 的 0.833/1.000 反差极大，且无对应报告；**不能作为交付证据**。

---

## 3. 脚本入库性与可复现缺口

### 已提交且实测可离线重跑（PASS 部分）

- `scripts/run_challenge_evaluation.py`：实测 `--rules-only --max-cases 2` 21.2 s 生成
  3 arms × 2 例 per-case raw JSON + arm `run_manifest.json` + `runner/{metrics.csv,traces/}`，
  格式正是 `challenge_report.py` 的输入契约。
- `src/openmetaphysics/evaluation/challenge_report.py`：实测对上述输出 0.77 s 生成 Markdown 报告
  （`eval/challenge_report_smoke.md`），对本地 2026-08-09 的 24 例 ×3 arms 也能重算
  （`eval/challenge_report_regen.md`：label accuracy 0.875/0.875/0.875）。
- `evals/runner.py`：实测离线跑 enriched 18 例 40.0 s（见 §5）。

### 缺口清单（文件:行）

| # | 缺口 | 证据 |
|---|---|---|
| G1 | **Phase 6 raw bundle 的生成脚本未入库**：`{manifest, results}`（20 字段）聚合器不在任何被跟踪文件里；`grep completed_calls/execution_semantics` 只命中 phase4_2 脚本，格式不同 | `reports/phase6_baseline_20261023/raw_results.json:1`；`scripts/run_challenge_evaluation.py:257,364` 只写 arm/root manifest |
| G2 | 无任何被跟踪脚本消费 `reports/phase6_*/raw_results.json` | grep 全仓 `raw_results`：只有 `challenge_report.py`（读目录型 raw）与 phase4_2 报告生成器（格式不同） |
| G3 | `final_evidence.md` 声称的分析脚本确为 gitignored | `git check-ignore`：`logs/final_eval.py`、`logs/restricted_eval.py`、`logs/mapping_compare.py`、`logs/analyze_baseline.py`、`logs/deep_stats.py`、`logs/percase.py` 全部 ignored；`.gitignore:40` `logs/`；`git ls-files logs/` 空 |
| G4 | `final_evidence.md:66` 明列 `logs/final_eval.py` 等 → **报告数字无入库脚本可复现**；脚本本身用自写 ece/corr（`logs/final_eval.py:3-19`），未调用 committed scorer | 见上 |
| G5 | `corr(conf,correct)` **无已提交实现**（全仓无 pearson 函数）；所有报告的 corr 只能用未入库脚本或审计临时脚本复算 | grep `pearson/correlation` 无匹配 |
| G6 | 已提交报告与当前报告生成器**版本漂移**：`reports/phase4_evaluation_pilot.md:15-21` 是旧表（"accuracy (factor coverage)"/ECE 0.4979…），当前 `challenge_report.py:442-470` 生成的是 label accuracy/factor coverage 分离的新表，重算得 0.875/0.875/0.875、ECE 0.3229/0.2846/0.2812 | 旧报告未随 2026-10-17 指标契约改造重新生成 |
| G7 | `evals/runner.py` CLI **无 `--llm-judge` 开关**，`EvalConfig.use_llm_judge` 默认 False（`config.py:47`），CLI 永远走规则 Judge；且 `--rules-only` 同时关掉 LangGraph，无法用「LangGraph + 规则 Judge」组合复跑 | `runner.py:320-355,367` |
| G8 | `reports/phase6_ablation_20261024/raw_results_c0c2_seed43.json` 未跟踪（WIP），且该目录无分析/报告 | `git ls-files 'reports/phase6_ablation_20261024/*'` 空；`check-ignore`=False |
| G9 | 工作树有 5 个被跟踪文件未提交修改（**非本次审计所为**，mtime 2026-10-23 20:49）：`decision_semantics.py`、`evals/metrics.py`、`challenge_report.py`、`tests/test_challenge_evaluation.py`、`tests/test_metrics.py`；另有未跟踪 `tests/fixtures/`。交付态与 HEAD 不一致 | `git status --porcelain` |

---

## 4. 结果 ↔ 脚本 ↔ 报告对应关系

| 检查 | 结果 |
|---|---|
| case_id/trace_id 互查 | **100%**：baseline 72 条 → 72 个 trace 文件；sc42 24/24；sc43 24/24；ablation 48/48 全部在 `logs/phase6_*/run_*/config_*/<arm>/runner/traces/` 找到；且 trace 内 `judge.decision`/`judge.confidence` 与 raw 记录**逐条一致**（72/72、24/24、24/24、48/48） |
| case 字段 ↔ 数据集 | 4 个 bundle 共 168 条记录，`case_id` 全部存在于 challenge set；`group/difficulty/ground_truth/expected_key_factors` **0 处不一致** |
| dataset 指纹 | Phase 6 bundle **完全没有** `dataset_sha256`；manifest 只记 `case_ids:[1..24]`（序号非 id）、configs、seeds、时间、completed_calls。指纹机制仅存在于 `experiments/fingerprint.py:64-95` + `experiments/manager.py:302`，落在 **gitignored 的 `results/`**：11 个实验目录中 7 个有 sha256（4 个实测 verify=True），4 个无 sha256，3 个无 manifest.json |
| `git ls-files results/` | **空**（`.gitignore:37`）；`git ls-files logs/` **空**（`.gitignore:40`）；`data/evaluation/challenge_raw` 亦未跟踪（`.gitignore:20` data/）。即：metrics.csv、traces、per-case raw **均不随仓库交付**，只有 `reports/` 里的汇总 JSON/MD 入库 |
| 对交付的含义 | 全新 clone 只能验证「accuracy 类」指标（baseline 全部 + sc 两跑的 accuracy）；**无法**验证 sc 两跑的 ECE/corr（需 agreement）、无法反向核对 trace、无法校验数据集版本指纹 |

---

## 5. 实测离线评测

命令（产物全部写入 `logs/delivery_audit_20261024/eval/`）：

```
python evals/runner.py --dataset benchmarks.datasets.enriched --rules-only \
  --output-dir logs/delivery_audit_20261024/eval/run_timed
```

| 指标 | 值 |
|---|---|
| 耗时 | **40.0 s / 18 例**（两次运行一致） |
| label_accuracy | **0.4444（8/18）**，两次运行完全相同（确定性） |
| average_confidence | 0.62；average_runtime 1.696 s |
| capability | counterfactual / info_gathering / knowledge_retrieval / multi_step / uncertainty = 1.00；conflict_resolution 0.11；sensor_cross_validation 0.28 |
| LLM 判定 | `judge_total_tokens=0`、judge_mode=rules → **零 API 调用** ✅ |
| 环境依赖 | 运行中反复出现 `http://localhost:6333` Qdrant 502 → 记忆层降级；Neo4j 未起 |

结论：**固定测试集 + 评测脚本可离线互跑**（PASS），但离线 accuracy 0.4444 与
`evals/README.md:99`/`CHALLENGE_SET_V1_REPORT.md:13` 声称的 accuracy=1.00（64/64）**不可复现**——
后者依赖 Qdrant/Neo4j 服务与真实 Agent 链路；Phase 6 的 LLM 指标则依赖真实 API，均超出离线边界。

---

## 6. 分项判定

| 分项 | 判定 | 依据 |
|---|---|---|
| 1 固定测试集与标签 | **PASS（含瑕疵）** | 24+64 例全部入库、数量与字段实测一致、加载路径独立且被 14 个测试强制；瑕疵：难度分布与「49 个 GT」两处文档数字错误、12 例无 capability（challenge set 24 例全无 capability）、GT 为唯一判据且子串匹配可被否定句白送 |
| 2 复算 | **PARTIAL** | baseline 3×8 指标中 23/24 项精确可复算；C1 ECE 需报告口径（且暴露 committed scorer 边界 bug）；SC 两跑 accuracy 可复算，ECE/corr **必须依赖未入库 trace 的 agreement** |
| 3 脚本入库性 | **PARTIAL** | challenge-set 管线（runner+报告器）已入库且离线可重跑（实测）；Phase 6 bundle 生成器/分析脚本全未入库，报告数字无入库脚本可复现（G1-G5） |
| 4 结果↔脚本↔报告对应 | **PARTIAL** | case/trace 对应与数据集字段对应 100% 强证据；但 traces/指纹不入库，bundle 无 dataset_sha256，全新 clone 无法闭环 |
| 5 实测离线评测 | **PASS（离线）/ 与文档数字不符** | 40 s 跑通 18 例、零 API、确定性；accuracy 0.4444 ≠ 文档 1.00（服务缺失所致） |
| **第 4 项总判定** | **PARTIAL** | 数据集与原始结果入库、评分代码入库、baseline 指标基本可复算（PASS 面）；但「原始结果 ↔ 报告数字」的 Phase 6 环节把关键中间量（agreement、traces、分析脚本）留在 gitignore 内，且存在文档数字错误与指标实现缺陷，故**未达「闭环可复算」**，也未到 FAIL |

## 7. 建议（交付前）

1. 把 `logs/final_eval.py`、`analyze_baseline.py` 及 Phase 6 bundle 生成器提升为 `scripts/` 入库脚本，
   并让它们调用 `challenge_scorer.calc_confidence_calibration`（不要各写一份 ECE）。
2. 在 raw bundle 的 manifest 增加 `dataset_sha256`/`dataset_source`/`scorer_commit`，
   并把 `agreement` 写进每条 result 记录（一个字段即可让 SC 指标自包含）。
3. 修 `challenge_scorer.py:154` 的边界分箱（用 `min(bins-1, int(confidence*bins))` 或
   把 1.0 归入末箱的显式区间判断），统一 ECE 口径。
4. 修正 `baseline_analysis.md:6`（72 次而非 84 次 Judge 调用）、`:62` 难度分布、
   `CHALLENGE_SET_V1_REPORT.md:26` 的「49 个带 GT」措辞、`README.md:99` 的 accuracy 1.00 标注运行条件。
5. 重新生成 `reports/phase4_evaluation_pilot.md`（当前与报告器 schema 不一致）。
6. 明确「否定语境中的病名」计分规则（至少加 `excluded_labels` 检测），补齐 `acceptable_alternatives`。
