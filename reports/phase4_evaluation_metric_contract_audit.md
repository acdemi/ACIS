# ACIS Phase 4 Evaluation Metric Contract Audit

> Date: 2026-10-17
> Branch: `work/20261017-phase4-eval-reliability`
> Scope: read-only audit followed by minimal evaluation-layer contract repair.
> No benchmark case, model provider, credential, frozen module public signature,
> or Agent architecture was changed.

## Executive Summary

The previously observed `label accuracy = 1.00`, `factor coverage = 0.00`,
`factor coherence = 0` triple was caused by three different factors:

1. label accuracy and factor coverage answer different questions;
2. the Challenge report discarded the formal `action_plan` field before factor scoring;
3. `coherence` was historically a quantized factor-coverage value, not a logical-consistency metric.

The historical confusion was real, but it did not mean the model decision was
wrong. The rule-path decision was label-correct. Its final user-visible explanation
did not contain three of the four expected diagnostic factors, and the old scorer
also ignored the non-empty formal action plan. After the minimum repair, the same
trace gives:

| metric | historical behavior | repaired contract |
|---|---:|---:|
| label accuracy | 1.00 | 1.00 |
| factor coverage | 0.00 | 0.25 |
| factor coverage level (legacy coherence) | 0 | 1 |
| abstention | false | false |
| Judge fallback | hidden in mode only | 100%, `authentication_error` |

Factor coverage remains below 1.00 because the final rule-Judge output does not
state the symptom factors `concentric_ring`, `stem_lesion`, and `fruit_stage`.
Those factors are present in the internal expert trace, but the defined Phase 4
contract scores the final user-visible decision explanation, not hidden expert
evidence. A full-trace coverage metric would be a separate future metric.

## A. Metric Contract

### A1. Final Decision Label Accuracy

- Business question: did the final decision select the benchmark label?
- Formula: `mean(I(decision_correctness(ground_truth, final_decision)))`.
- Numerator: labeled cases whose final Judge decision is semantically correct.
- Denominator: cases with both a non-empty `ground_truth` and a non-empty final
  Judge decision. Missing values are excluded, not counted as wrong.
- Scored object: final `judge.decision`, not pathology claim or intermediate expert text.
- Ground truth: `benchmarks/challenge_set_v1.json` `ground_truth`, version 1.
- Abstention: an expected `证据不足`/`ABSTAIN` is correct only for an abstaining
  final decision; a diagnosis and an abstention never cross-match.
- Rules fallback: the final rules decision remains a real decision of the rule
  path and can be included in overall label accuracy. The result must also be
  stratified by `judge_mode` and accompanied by fallback rate.
- Missing Judge event: case is unscored (`None`), not wrong and not confidence 0.
- Implementation: `evals.metrics.compute_trace_metrics`,
  `decision_semantics.decision_correctness`.
- Callers: `evals.runner.run_evaluation`, `evals.report.write_summary_markdown`,
  ablation/report consumers.
- Compatibility: aggregate exposes canonical `label_accuracy`; legacy `accuracy`
  remains as an alias. CSV field `accuracy` is kept for old artifacts.

### A2. Factor Coverage

- Business question: how many expected diagnostic/action factors are explicit in
  the final user-visible decision output?
- Formula: `covered_factors / expected_factors`.
- Per factor: decision, reasoning text, and action-plan text are inspected by the
  documented LLM factor judge or deterministic `FACTOR_ALIASES` fallback.
- `action_plan`: covered when the formal `action_plan` list contains at least one
  non-empty action; this is a structured field check, not a keyword check.
- Scored object: final `decision`, `reasoning_trace`, `summary`, and structured
  `action_plan`. Internal expert events and the full Trace are not included.
- Ground truth: case-level `expected_key_factors`.
- Missing expected factors: unscored (`None`), never 0.
- Empty final output: unscored (`None`); partially populated output is scored normally.
- Rules fallback: can be scored as the rule-path explanation, but the report must
  identify it as rules mode rather than LLM success.
- Implementation: `challenge_scorer.calc_factor_coverage`,
  `calc_factor_scores`, `challenge_report.score_case`.
- Limitation: coverage records explicit mention/presence, not whether the factor
  supports or contradicts the final conclusion.

### A3. Factor Coverage Level (legacy name: Factor Coherence)

- Business question: same as factor coverage, quantized for a compact display.
- Formula: `min(3, floor(3 * coverage + 0.5))`.
- Range: 0-3.
- Scored object and missing-data rules: inherited from factor coverage.
- This is **not** a logical-consistency metric. Contradictory reasoning can have
  high coverage while the final label is wrong.
- Implementation: `calc_factor_scores`; `calc_reasoning_coherence` remains as a
  compatibility API but its report label is now `factor_coverage_level`.
- Existing reports use the historical name `coherence`; existing values should not
  be reinterpreted as logical consistency.

### A4. Label ECE (Confidence Calibration for Labels)

- Business question: is confidence calibrated against final-label correctness?
- Formula: `ECE = sum_b(n_b/n * |acc_b - conf_b|)`, with 10 equal-width bins.
- Correctness label: `decision_correctness(ground_truth, final_decision)`.
- Denominator: cases with numeric confidence and label correctness available.
- Missing labeled pairs: `None` (unscored), never 0/perfect calibration.
- Confidence contract: finite value in `[0,1]`; violations raise
  `ChallengeScoringError`.
- Rules fallback: ECE may be computed for the rule path, but must not be described
  as LLM calibration unless `judge_mode=deepseek`.
- Implementation: `challenge_scorer.calc_confidence_calibration`;
  label domain assembled in `challenge_report`.

### A5. Factor ECE (Confidence Calibration for Factor Coverage)

- Business question: is confidence calibrated against full expected-factor coverage?
- Formula: same binned ECE as above.
- Correctness label: `factor_coverage == 1.0`; partial coverage is not correct.
- Denominator: cases with numeric confidence and computable factor coverage.
- Missing pairs: `None`, never 0/perfect calibration.
- Historical reports named this simply `ECE`; all old Phase 4 ECE values are this
  factor-coverage ECE, not label ECE.
- Implementation: `challenge_report._calibration(domain="factor")` and
  `generate_stability_report.aggregate_scored`.

### A6. Average Confidence and Confidence Offset

- `average_confidence`: arithmetic mean of final decision confidence over available
  values. It is descriptive and is not calibration.
- `confidence_offset`: exists only in the real-vs-reference precheck as
  `abs(real_confidence - reference_confidence)`. It is not a Phase 4 aggregate
  metric and is only comparable when both outputs share execution semantics and
  the real Judge completed the LLM path.
- No standalone aggregate `confidence_deviation` implementation exists.

### A7. Abstention Behaviour

- Overall abstention rate: `100 * abstained / valid decisions`.
- Correct abstention rate: among cases expected to abstain, percentage that abstain.
- False abstention rate: among cases expected to diagnose, percentage that abstain.
- Missing decision: excluded from denominators; no valid decisions yields `None`.
- Explicit `abstained=True` can carry status even if decision text is empty.
- High overall abstention is descriptive. Correct-abstention and false-abstention
  rates must be interpreted separately.
- Implementation: `calc_abstention_rate`, `challenge_report._aggregate_group`,
  `generate_stability_report`.

### A8. Judge Fallback Rate and Mode Distribution

- Business question: did the requested LLM Judge actually execute?
- Formula: `100 * fallback_cases / cases with known LLM outcome`.
- `judge_mode` distribution is descriptive and is kept separately.
- New records use `judge_runtime.outcome` and `fallback_reason_code`.
- Legacy fallback inference is allowed only when the manifest explicitly says
  `use_llm_judge=true` and `judge_mode=rules`; it is labelled
  `legacy_inferred_rules_fallback`.
- Unknown legacy provenance is counted as `unknown`, never as success.
- Zero known outcomes yields `None`, not 0%.
- Implementation: `challenge_report._fallback_state`, aggregate report fields,
  `generate_stability_report` reliability section.

### A9. Metrics That Do Not Exist

- **Factor consistency**: no implemented metric determines whether a covered
  factor supports or contradicts the final diagnosis. `coherence` was historically
  a misleading name for quantized coverage.
- **Aggregate confidence deviation**: no Phase 4 aggregate implementation exists.
  Only the precheck `confidence_offset` diagnostic exists.
- **True LLM quality under rules fallback**: cannot be inferred. Zero Judge tokens
  and `judge_mode=rules` identify a rule-path result only.

## B. Three Anomalies and Evidence

### B1. Why can label accuracy be 1.00 while factor coverage is 0?

The final decision is checked against one label, while factor coverage checks an
independent expected-factor set. The real precheck decision was
`病理判断首选：番茄早疫病` for ground truth `早疫病`, so label accuracy is 1.00.
The old Challenge scorer received only `decision + reasoning_trace`; that text did
not mention `concentric_ring`, `stem_lesion`, `fruit_stage`, or an action-plan cue.
The exact same trace therefore legitimately produced factor coverage 0 under the
old input projection.

### B2. Was factor coverage 0 a true result or a scorer omission?

Both conditions existed:

- It was true that the final user-visible explanation did not state three diagnostic
  factors.
- The scorer also omitted the formal `action_plan` field. The trace has a non-empty
  6-item action plan, but `score_case()` discarded it. After including the field,
  factor coverage rises from 0.00 to 0.25 and factor level from 0 to 1.
- The internal expert trace contains evidence for all four factors. A diagnostic
  rule-vocabulary scan over the expert trace yields coverage 1.00. That evidence is
  not part of the defined final-output factor metric.

This is the remaining contract decision boundary: if the research question is
"did the system consider the factor internally?", full-trace coverage should be a
separate metric. If the question is "did the final decision explain the factor?",
the current metric is correct and must remain 0.25 for this trace.

### B3. Was factor coherence 0 actual logical inconsistency?

No. The historical `coherence` function is exactly quantized factor coverage. It
has no contradiction detector. The value 0 meant no expected-factor text matched,
not that the reasoning was logically contradictory. The repaired report calls it
`factor coverage level (0-3)` and the same trace now yields 1 after action-plan
inclusion. A contradictory fixture can have full coverage while label accuracy is
0, proving these are separate dimensions.

### B4. `reasoning_trace` versus `action_plan`

- `reasoning_trace` is an unstructured explanatory audit string. In rules fallback,
  it currently records KG/risk/round metadata, not a complete diagnostic rationale.
- `action_plan` is a formal `DecisionOutput` list containing executable actions.
- `decision` and `summary` are formal final-output strings.
- Expert, debate, critic, memory, and judge-analysis events are internal Trace
  evidence, not final user-visible explanation fields.
- The minimum contract now includes `action_plan`; it does not silently include the
  internal expert trace.

### B5. Can rules fallback participate in label accuracy?

Yes, as a genuine decision produced by the rules path. It must be reported under
`judge_mode=rules` with a separate fallback rate and reason. It cannot be presented
as evidence that the LLM Judge succeeded, and LLM-quality claims cannot be made from
fallback-only runs.

## C. Changes and Tests

Changed implementation:

- `src/openmetaphysics/evaluation/challenge_scorer.py`
- `src/openmetaphysics/evaluation/challenge_report.py`
- `scripts/generate_stability_report.py`
- `evals/metrics.py`
- `evals/report.py`
- `evals/runner.py`
- `scripts/run_phase4_2_real_agent.py` (LLM-request flag and summary propagation)
- `scripts/run_challenge_evaluation.py` (summary propagation)
- `benchmarks/CHALLENGE_SET_V1_REPORT.md` (metric naming clarification)

Changed tests:

- `tests/test_challenge_scorer.py`
- `tests/test_challenge_evaluation.py`
- `tests/test_metrics.py`
- `tests/test_stability_metric_contract.py`

Key tests:

| behavior | test |
|---|---|
| structured action plan covers `action_plan` | `test_action_plan_factor_uses_structured_action_plan_field` |
| label and factor metrics independent | `test_score_case_separates_label_accuracy_from_factor_coverage` |
| missing output unscored | `test_missing_output_is_unscored_not_zero` |
| no labeled ECE unscored | `test_calibration_without_labels_is_unscored_not_perfect` |
| no valid abstention denominator unscored | `test_abstention_rate_without_valid_decisions_is_unscored` |
| confidence contract boundaries | `test_calibration_rejects_out_of_contract_confidence` |
| correct vs false abstention | `test_abstention_behavior_separates_correct_and_false_abstention` |
| fallback rate and reason | `test_judge_fallback_rate_and_reason_are_reported` |
| legacy fallback compatibility | `test_legacy_rules_mode_is_inferred_fallback_when_llm_requested` |
| contradictory reasoning remains separate from label correctness | `test_conflicting_reasoning_and_label_are_reported_separately` |
| actual precheck trace replay | `test_replay_precheck_trace_under_metric_contract` |
| missing Judge event confidence/accuracy unknown | `test_missing_judge_event_is_unscored_not_wrong_or_zero_confidence` |
| stability path separation | `tests/test_stability_metric_contract.py` |

### Verification Results

- Focused metric contract/schema regression: **83 passed**.
- Full repository regression: **307 passed**, 22 non-blocking Qdrant warnings.
- Ruff on all changed Python files: **All checks passed**.
- Mypy with external imports skipped: **6 source files passed**.
- Historical stability report regenerated locally with rule-only factor scoring:
  successful; legacy metric keys are displayed with explicit new names.
- Actual precheck trace replay:
  `label_correct=True`, `factor_coverage=0.25`, `factor_coverage_level=1`,
  `fallback_state=True`, `fallback_reason=authentication_error`.

## D. Remaining Uncertainty

1. **Full-trace factor coverage is not implemented.** The current official factor
   metric measures final output explanation. Expert evidence can materially change
   coverage, but including it without a new contract could inflate coverage using
   retrieved disease templates.
2. **Factor-scorer fallback provenance is not per-case recorded.** The report notes
   whether LLM factor scoring was requested and whether a key existed, but cannot
   currently distinguish successful LLM factor scoring from per-case rule fallback.
3. **Historical fallback rate may be unknown.** Older real-agent raw records lack
   `judge_runtime.outcome`; the stability report now shows `unknown` rather than
   silently converting rules mode to a known failure or success.
4. **ECE sample sizes are small.** A 24-case arm distributed into 10 bins is noisy;
   ECE should not be overinterpreted without confidence intervals or more samples.
5. **No successful live LLM Judge run exists in the 2026-10-17 precheck.** The
   credential returned HTTP 401, so model-output variability and LLM reasoning
   coverage remain unmeasured.

## E. Next-Stage Readiness

The metric contract is now explicit enough to run another **minimum real-agent
precheck**, but Phase 5 is not ready to start. The next precheck should wait for a
valid credential and should use a same-execution reference, not a direct-LLM
baseline. The minimal sample should cover deterministic diagnosis, correct
abstention, and conflicting evidence with two repeats per case, and must report:

- label accuracy,
- factor coverage and factor level,
- label ECE and factor ECE,
- overall/correct/false abstention rates,
- Judge mode and fallback rate/reasons,
- factor-scorer mode.

If the intended research question requires credit for internal expert reasoning,
resolve the full-trace factor-coverage contract before running Phase 5.
