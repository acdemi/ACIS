# ACIS Phase 4 Recovery — Real Judge Verified

> Date: 2026-10-19
> Branch: `work/20261019-judge-recovery`（基于 `work/20261019-docs-sync-reliability` 4ecd5c7）
> Procedure: `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md`（Step 1 → Step 2 → Step 3）
> Verdict: **RECOVERED** — 真实 LLM Judge 认证与结构化决策验证通过，六次最小预检零回退
> Phase 5: 仍未启动（架构决策未做）

## 1. Step 1 — 配置重检（掩码输出）

`.env` 最后写入 2026-10-19 19:38（用户经正常渠道更新）。

| item | observed |
|---|---|
| `AGRI_AI_JUDGE_API_KEY` | absent |
| `DEEPSEEK_API_KEY` | present（length 35，prefix sk-***，未显示） |
| resolved key source | `DEEPSEEK_API_KEY` |
| provider | `deepseek` |
| endpoint ID | `https://api.deepseek.com`（来源 `DEEPSEEK_BASE_URL`） |
| model | `deepseek-chat`（默认） |
| timeout / SDK retries | 60s / 2（默认） |
| proxy variables | 全部 absent |

## 2. Step 2 — 恰好一次受控 Judge 验证请求

探针：`logs/judge_auth_probe_20261019.py`（gitignored；单次 SDK 调用，遵循修复后重试归属）。

- HTTP 200，无异常；finish_reason=stop
- 结构化响应 `{"decision":"auth_ok"}` 解析成功
- token usage: prompt 20 / completion 7
- **STEP2_VERDICT: PASS**
- 观察：响应 `model` 字段为 `deepseek-flash`（请求的是 `deepseek-chat`）——服务端伺服型号命名，记录备查，不影响配置契约

## 3. Step 3 — 六次最小真实 Agent 预检（3 案例 × seed 42/43）

命令模板按 BLOCKED 报告第 1 节执行；`--compare-harness reports/phase4_2_raw_results.json`。
产出：`reports/phase4_judge_recovery_20261019/precheck_case{23,14,9}_seed{42,43}.md`，
trace 于 `logs/phase4_judge_recovery_20261019/`。执行窗口 19:51–19:56，每轮约 1 分钟。

| case | role | ground truth | seed | real decision | conf | GT 判定 | harness 参考 | conf offset |
|---|---|---|---|---|---|---|---|---|
| 23 `ms_tomato_blight_stem` | 确定性诊断 | 早疫病 | 42 | 番茄早疫病 | 0.72 | ✓ | 番茄早疫病 0.85 | 0.130 |
| 23 | | 早疫病 | 43 | 番茄早疫病 | 0.62 | ✓ | 番茄早疫病 0.90 | 0.280 |
| 14 `inc_tomato_vague_spot` | 证据不足/弃权 | 证据不足 | 42 | 番茄早疫病 | 0.45 | ✗ | ABSTAIN 0.20 | 0.250 |
| 14 | | 证据不足 | 43 | 无法定论（早疫病与叶霉病均证据不足） | 0.35 | ✓（弃权） | ABSTAIN 0.00 | 0.350 |
| 9 `conf_tomato_blight_cool_rain` | 证据冲突 | 早疫病 | 42 | 番茄早疫病 | 0.62 | ✓ | ABSTAIN 0.10 | 0.520 |
| 9 | | 早疫病 | 43 | 番茄早疫病 | 0.55 | ✓ | 番茄早疫病 0.65 | 0.100 |

trace 级核验（case23/seed42 trace `6791d448…`）：`judge_mode=deepseek`、`outcome=success`、
`judge_total_tokens=10216`、无 `fallback_reason_code`。运行日志另见 judge 请求 200 OK 与
usage 记录（prompt 6716 / completion 1412 等）。

## 4. Findings

1. **恢复目标达成**：6/6 运行 `judge_mode=deepseek`、零 rules 回退、零 authentication_error；
   凭证阻塞解除，评测器与指标契约保持在修复后状态。
2. **GT 标签 5/6 正确**：case14/seed42 将"证据不足"案例误判为番茄早疫病（弃权案例的决策质量风险点）。
3. **case14 跨 seed 决策翻转**（42: 疾病 / 43: 弃权）——再次印证 Phase 4.2-R 的高方差发现（样本量 1 案例不足以扩展结论）。
4. **全部 6 轮 comparison=INCOMPARABLE**：harness 参考为 `direct_llm_baseline_legacy` 语义，真实链路为
   `acis_real_agent`——修复后契约按设计不做等值门限判定；置信度偏移 0.10–0.52 仅作诊断保留。
   harness 与真实链路的口径对齐（原 R4 FAIL 项）仍是开放问题。
5. 服务器侧 `deepseek-chat` 由 `deepseek-flash` 伺服（响应 model 字段）；如后续要求严格型号审计需注意。

## 5. 证据完整性说明

- 预检运行期间（19:51–19:56）工作树为干净的已提交代码；运行后 22:20–22:25 出现另一会话的
  未提交修改（`decision_semantics.py`、`evals/metrics.py`、`src/openmetaphysics/evaluation/challenge_report.py`、
  `tests/test_challenge_evaluation.py`、`tests/test_metrics.py`、`tests/fixtures/`）。
  这些修改不属于本轮，未纳入本轮提交，未被改写或回退。
- 未修改 benchmark、ground truth、factor、阈值或评分定义；未更换 provider/model 配置。

## 6. 结论

**RECOVERED**。真实 LLM Judge 可验证运行能力已恢复；Phase 4 证据链可以在真实 Judge 下继续。
Phase 5（扩展评测）vs Phase 6（架构重设计）的架构决策仍待做出，未获指示前不启动。
