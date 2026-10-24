# 2026-10-19 — AG-DISTILL-T2C：WHE-02 候选知识修订闭环归档

## 对话主题与目标

- 任务 AG-DISTILL-T2C：基于 T2B 审计记录（48 项）对 40 个 WHE-02 候选单元做最小必要修订，形成可追溯闭环；处理候选层，不动正式知识库。

## 变更文件清单

新增：
- `reports/ag-distill-t2c-wheat-fhb-revision/candidate_knowledge_v2.json`（修订后候选包，AG-DISTILL-T2C-WHE02-CANDIDATES-v2，含 base_sha256 追溯与修订政策声明）
- `reports/ag-distill-t2c-wheat-fhb-revision/diff_report.json`（19 条变更机读 diff + 检查结果）
- `reports/ag-distill-t2c-wheat-fhb-revision/revision_log.md`（逐项旧值/新值/原因/依据审计ID/复核）
- `reports/ag-distill-t2c-wheat-fhb-revision/revision_status.csv`（48 行逐问题处置）
- `reports/ag-distill-t2c-wheat-fhb-revision/open_issues_queue.md`（更新后未解决问题队列）
- `reports/ag-distill-t2c-wheat-fhb-revision/execution_report.md`
- `scripts/apply_t2c_revisions.py`（变更执行器：旧值断言→应用→walk-diff 验证）

## 变更摘要

- 19 项字段变更 × 12 单元：D-03/D-09 statement 收敛（P1 实质问题，含原子性消除）；R-01/R-03/R-04/R-06/R-08/F-02 显式化与定性边界（P2）；同族主张关系补链 K-05/F-05/D-10/Q-10（11 条新边，双向对称）。
- 处置分布：closed-direct 13 / closed-no-action 20 / closed-annotation 1 / open-blocked 5（合规门禁：R-07、K-02、Q-04、Q-05、Q-）/ open-human 1（AUD-T2B-048 审计独立性）/ deferred-p3 8。
- 五条合规门禁零数据变更（value=null+needs-verification 门禁保留）；未以措辞改写闭环任何争议主张；未提高任何证据等级。
- 勘误登记：T2B AUD-T2B-011 行误引"AUD-T2B-036"（应为 026/032/038 补链簇）；T2B 文件未改动。

## 验证结果

- 结构校验全绿：40/40 单元与顺序保持、证据签名（layer/provenance/quantitative）不变、quantitative 全 null、related_units 全部可解析、全文档 walk-diff unexpected_paths=0、新增自由文本无数字。
- `ruff check`/`mypy`：通过。
- T2A v1 原始候选包与原始日志未覆盖。

## 分支与提交

- 分支：`work/20261019-t2c-t2d-wheat-fhb`（自 `work/20261019-t2b-wheat-fhb-audit` 派生；与 T2D 同轮双任务）
- 提交：`f37d3c2` feat(AG-DISTILL-T2C): minimal revisions to WHE02 candidates v2 (19 changes/12 units, 34 closed/6 open/8 deferred)

## 状态与下一步（待用户指示）

- 等待人工验收 v2；五项合规门禁证据认领；AUD-T2B-048 独立性处置；P3 维护项排期。
