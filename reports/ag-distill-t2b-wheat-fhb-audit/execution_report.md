# AG-DISTILL-T2B 执行报告 — WHE-02 候选单元独立复核

- 日期：2026-10-19
- 分支：`work/20261019-t2b-wheat-fhb-audit`（自 `work/20261019-t2a-wheat-fhb` 派生）
- 任务源：AG-DISTILL-T2B（候选包 40 单元逐单元审计）
- 前置：用户批准"恢复并完成 T2B"（T2B 曾中断于前置检查阶段零产出）

## 1. 审计对象

| 项 | 值 |
|---|---|
| 包路径 | `reports/ag-distill-t2a-wheat-fhb-20261019/candidate_knowledge.json` |
| package_id | AG-DISTILL-T2A-WHE02-CANDIDATES-v1 |
| 单元构成 | D×10、R×8、K×5、F×7、Q×10（40/40） |
| 入场校验 | 结构、provenance 分布（16 candidate / 15 inference / 9 needs-verification / 0 source-supported）、T2A 审计 29 pass / 11 revise / 0 reject、全部定量 value=null —— 与 T2A 报告一致 |
| sha256 | 由 `emit_t2b_audit.py` 计入 `audit_manifest.json.audited_package.sha256` |
| T2A 日志 | `stage_logs/*` 仅读未改 |

## 2. 方法与限制（如实声明）

- **审计方式**：agent 逐单元复核（覆盖任务规定的 10 项重点：真实性、量化可信、时效、区域差分、关系边界、原子性、混域、重复矛盾、provenance 状态使用、原语完备）。产出临时聚焦稿 `working/g1_D.json–g4_Q.json`，全部 40 单元完整读取后形成审计行。
- **异构模型审计阻塞**：复核探针向教师 API 双路由（deepseek-chat、deepseek-reasoner 两申报）请求，`served_model` 均返回 `deepseek-flash` —— 审计独立性无法由"不同模型重审"达成。**本轮审计不称为独立模型审计**。
- T2A 侧的"同一 deepseek-flash 服务映像"问题（T2A 冲突清单第 3 条）在此同样成立：同模型对同数据的自我二次校核不再计入本轮方法价值。
- **证据纪律**：本轮未新增任何外部事实；所有被质疑替代事实保持原 null / needs-verification 门禁。

## 3. 结果摘要

- 审计行 48（单元级 44 + 全局 4），检查全通过：40/40 覆盖、无重复 ID、severity 合法、T2A 11 项 revise 全部映射（11/11）。
- severity 分布：**P0=0，P1=7，P2=10，P3=11，none(通过/无问题)=20**。
- 由此明确：**候选包不存在可直接导致错误决策的已证实事实错误（P0 层无发现）**；主要风险集中在
  (a) 2 条实质性主张过宽（D-03 病原复合体同一性、D-09 条件依赖绝对化）；
  (b) 5 条合规/标准类主张的发布门禁（R-07、K-02、Q-04、Q-05、Q-06）。
- 无问题单元 20 行维持候选；全局核查三项通过（无混域推导链、无隐性重复/矛盾——唯 R-03 与 R-08 的窗口边界存在轻微张力已登记为 P2；provenance 纪律与日志可追溯性均合规）。

## 4. 与 T2A 执行报告四冲突的衔接

| T2A 冲突 | T2B 落地 |
|---|---|
| 分支起源偏差（域扫描/审计图在未合并分支） | T2B 从 t2a 分支工作，归档注明 |
| 候选包既有 Schema 缺位（`adaptation_status=待适配`） | 未复核/修改 Schema；候选入库仍须架构师先定 Schema |
| T2A 中 judge 模型映射 deepseek-flash | 本轮再次实证（两申报→同一服务），登记为审计独立性阻塞（AUD-T2B-048） |
| served_model 报表映射 | manifest auditor 字段带探针结果（requested vs served） |

## 5. 产物清单

- `reports/ag-distill-t2b-wheat-fhb-audit/audit_findings.json`（源数据，含 audit 行 sha256）
- `reports/ag-distill-t2b-wheat-fhb-audit/claim_audit.csv`（48 行，UTF-8 BOM）
- `reports/ag-distill-t2b-wheat-fhb-audit/audit_manifest.json`
- `reports/ag-distill-t2b-wheat-fhb-audit/revision_queue.md`（按风险排序）
- `reports/ag-distill-t2b-wheat-fhb-audit/evidence_gaps.md`
- `reports/ag-distill-t2b-wheat-fhb-audit/execution_report.md`（本文件）
- `reports/ag-distill-t2b-wheat-fhb-audit/working/g1_D.json–g4_Q.json`（审计输入，保留作 traceability）
- `scripts/emit_t2b_audit.py`（产物生成器，ruff/mypy 通过）

## 6. 局限与建议

- 本轮复核由 LLM 执行（agent 复核），**不构成外部证据**；进入 T2C 前，建议由人工对 7 条 P1 做采否确认。
- 未做：跨包批量检索、毒理外部对照、田间数据比对（任务范围外）。
- T2C 门禁提示：P1 处置不得以改写措辞关闭；合规类主张必须完成"文本核验地点→登记元数据"闭环（evidence_gaps.md 优先级 1）。

## 7. 决策请求

1. 是否进入 T2C（修订闭环）——需要用户明确批准（T2C 任务自身门禁）。
2. P1 五条合规门禁的证据责任人：由用户/证据责任人提供（本轮不代写）。
