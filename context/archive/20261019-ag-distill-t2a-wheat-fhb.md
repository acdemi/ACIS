# 归档：AG-DISTILL-T2A WHE-02 小麦赤霉病深度提取（2026-10-19）

## 对话主题与目标

- 主题：AG-DISTILL-T2A — 对 Top5 之一 WHE-02（小麦赤霉病与毒素管理）做在线教师模型的
  原子知识深度提取 + 机器审计 + 候选包组装（仅 WHE-02，不启动其他主题）
- 范围 A-I：病原/发生条件、花期风险、天气微环境、监测预警边界、防控适用条件、
  毒素形成与污染、收获储运安全、病害风险 vs 毒素风险解耦、误区反例
- 执行方式：8 阶段管线（S1-S7 教师模型 API + S8 本地组包），逐阶段留痕

## 变更文件清单（新增）

| 文件 | 说明 |
|---|---|
| `scripts/extract_ag_distill_t2a_wheat_fhb.py` | 分阶段教师模型提取运行器（ruff/mypy 通过） |
| `scripts/assemble_ag_distill_t2a_wheat_fhb.py` | S8 候选包组装 + 结构自检（ruff/mypy 通过） |
| `reports/ag-distill-t2a-wheat-fhb-20261019/stage_logs/S1..S7/` | 每阶段 prompt/raw_response/parsed/meta 全套留痕 |
| `reports/ag-distill-t2a-wheat-fhb-20261019/stage_logs/run_summary.json` | 管线汇总 |
| `reports/ag-distill-t2a-wheat-fhb-20261019/candidate_knowledge.json` | 候选包（40 单元，待适配） |
| `reports/ag-distill-t2a-wheat-fhb-20261019/validation_report.json` | 结构自检（全绿） |
| `reports/ag-distill-t2a-wheat-fhb-20261019/execution_report.md` | 结构化执行报告 |
| `context/archive/20261019-ag-distill-t2a-wheat-fhb.md` | 本归档 |

## 变更摘要

- 前置检查发现并登记 4 项冲突/偏差（分支来源偏离、schema 转为"待适配"、
  judge_runtime/decision_semantics 未合并、服务端模型映射 deepseek-flash）。
- 教师 API 最小预检 HTTP 200（解除 10-18 的 401 阻塞）；8 阶段全部成功，
  全部 40 单元 × 7 项结构检查通过。
- 产物候选包：40 单元（定义 2 / 机制 6 / 诊断 2 / 规则 9 / 风险链 6 / 失效模式 5 / 定量 10），
  provenance 分布 model-candidate 16 / model-inference 15 / needs-verification 9 /
  source-supported 0（本轮无文献材料，诚实留空）；全部定量 value=null + needs-verification。
- 机器审计 29 pass / 11 revise / 0 reject；独立性因服务端统一映射降级为"同模型机器初筛"，
  已写入 audit_summary.independence_note 并列入待人工决策。
- 关键解耦：病害风险（防治决策）与毒素风险（检测/限量/储运）信息源分离（risk-chain 层）；
  症状严重度 ≠ 毒素安全；防效 ≠ 粮食合格。

## 验证结果

- ruff：2 个新脚本全部通过；mypy：2 个新脚本全部通过。
- 结构自检 scripts/assemble_* 运行结果：passed，0 errors，0 informational。
- 证据纪律抽查（6 单元）：无编造标准编号/DOI/登记号；数值零编造（value 全 null）；
  rule 单元 conditions/failure_modes 非空（S3/S5 全量复核 0 缺失）。
- 本轮未运行项目 pytest（无代码路径被改动/依赖），不适用。

## 分支名与提交号

- 分支：`work/20261019-t2a-wheat-fhb`（自 `work/20261019-ag-distill-domain-scan` 派生，
  偏离"从 main 建分支"的原因见执行报告 §7-1）
- 提交 1：`c957d54` feat(knowledge): AG-DISTILL-T2A WHE-02 staged teacher extraction and candidate package
- 提交 2：本归档提交（见分支最新提交）

## 状态

- 已完成（WHE-02 深度提取 + 质量审计；候选知识未入库、未升级为正式资产）。
- 等待人工审查：candidate_knowledge.json / execution_report.md；
  待你决策：入库路径与 Schema 归属、修订工作流化、另 4 主题是否启动。
