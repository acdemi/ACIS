# AG-DISTILL-T2C 执行报告 — WHE-02 候选知识修订闭环

- 日期：2026-10-19；分支：`work/20261019-t2c-t2d-wheat-fhb`（自 `work/20261019-t2b-wheat-fhb-audit` 派生）
- 本轮同时执行 AG-DISTILL-T2D（工程调查报告，仅读写文档不改代码）；T2C 数据产物在本目录，T2D 产物在 `reports/ag-distill-t2d-schema-survey-20261019/`。

## 1. 前置条件核验（任务门禁）

| 检查 | 结果 |
|---|---|
| T2B 完成？ | 是——`reports/ag-distill-t2b-wheat-fhb-audit/` 七件产物齐备（提交 427f7ae），归档 9e186a7 |
| 产物可定位？ | 是——claim_audit.csv 48 行 / audit_manifest.json / audit_findings.json / revision_queue.md |
| 候选 ID ↔ 审计记录可对应？ | 是——40/40 单元被覆盖、11/11 T2A revise 已映射（T2B 自检通过） |

未发生"按旧摘要猜测需修订单元"的情形：全部修订动作直接锚定 audit_issue_id。

## 2. 修订统计（前后数量）

| 指标 | v1 | v2 |
|---|---|---|
| 单元数 | 40 | 40（顺序不变） |
| 证据等级签名（layer/provenance/quantitative） | — | 完全一致（未提高任何等级） |
| quantitative 条目 | 全部 value=null + needs-verification | 同左（逐条保真） |
| 包标识 | AG-DISTILL-T2A-WHE02-CANDIDATES-v1 | AG-DISTILL-T2C-WHE02-CANDIDATES-v2 |
| 变更 | — | 19 项字段变更 × 12 单元（2 处 statement 重写、6 处 uncertainties 追加、2 处 conditions 追加、9 处 related_units 补链） |

语句级新文本均为"限定/收敛/指向核验"性质，**不含数字、不含新事实主张**。

## 3. 问题处置（48 项审计问题）

- closed-direct 13（含 P1×2：D-03、D-09 的实质收敛；P2×8：R-01/R-03/R-04/R-06/R-08/F-02 的显式化与边界；关系补链 K-05/F-05/D-10/Q-10）
- closed-no-action 20（T2B no-issue 单元与全局核查；维持候选）
- closed-annotation 1（F-02 前缀/层级不一致——按任务不改分类）
- open-blocked 5（合规门禁 R-07/K-02/Q-04/Q-05/Q-06：无数据变更，待现行标签/标准文本）
- open-human 1（AUD-T2B-048 审计独立性，人工决策）
- deferred-p3 8（P3 留待维护，未闭未弃）
- **未伪闭环：open 项无任何"措辞改写即视为解决"的记录**

争议主张处置合规性自证：
- D-03（病原复合体同一性）：主述收敛 + uncertainties 待核验声明 —— 符合任务第 5 条（未持证据解决争议主张，明确保持待验证）。
- D-09（条件依赖）：软化 + 反例边界声明 —— 同上。
- 五条合规门禁：零数据变更、保持 open —— 符合第 5/6/8 条。
- 第 6 条（不因修订提高证据等级）：脚本以 v1/v2 签名比对强制执行，同时验证 quantitative 全 null。

## 4. 回归检查（结构校验）

`scripts/apply_t2c_revisions.py` 执行结果：
- 旧值断言全部命中（2 处 statement 与原文逐字一致）
- append 去重检查通过（无重复条目）
- 全文档 walk-diff：变更路径 == 变更表路径，**unexpected_paths=0**
- unit_count 40/40、顺序保持；证据签名不变；quantitative 全 null；related_units 全部可解析（含新增 11 条引用）
- 新增自由文本无数字（防"顺手填数值"回归）
- ruff check：All checks passed！mypy：no issues

## 5. 可追溯链

每项处置满足 `audit_issue_id -> candidate_id -> proposed_change -> verification -> final_status`：
- 机器层：`diff_report.json`（19 条，均含 audit_ids）→ `revision_status.csv`（48 行，disposition/verification/note）
- 叙述层：`revision_log.md`（逐项旧值/新值/原因/复核）

## 6. 勘误与遗留

- 勘误：T2B AUD-T2B-011 行误引"AUD-T2B-036"（应为 026/032/038 补链簇）；T2B 文件未改动，已在 revision_log/open queue 登记。
- 遗留：5 项合规门禁待证据责任人；1 项审计独立性待人工决策；8 项 P3 维护项。
- T2A 原始候选包与原始日志未被覆盖（v1 文件与 stage_logs 原样）。

## 7. 完成标准对照

全部满足：修订可追溯 ✓；闭环有明确理由 ✓；未解决保持 open ✓；未引入无来源事实/数值 ✓；结构检查通过且全量差异记录 ✓；正式知识库/Schema/分支合并状态未动 ✓。

## 8. 剩余风险与待人工验收

1. v2 语言层修订由 agent 复核润色，仍属"agent 复核"性质（T2B 已声明方法限制），P1 语义修订需人工验收。
2. 合规门禁五项在证据到位前不可用于决策场景；如被下游误用为判定依据，风险在数据面已由 null 门禁部分缓解，但仍需使用方约定。
3. 关系补链使 related_units 图更密，若后续导出 KG 需确认对称性处理（本轮已保证新增边双向对称）。
