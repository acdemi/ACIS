# 2026-10-19 — AG-DISTILL-T2D：知识资产 Schema 与入库契约调查归档

## 对话主题与目标

- 任务 AG-DISTILL-T2D：调查 ACIS 现有知识资产的格式/归属/ID/约束/写入接口/发布流，为 WHE-02 候选确定唯一适配路径；只调查并提最小方案，不改代码、不写入、不合并。

## 变更文件清单

新增：
- `reports/ag-distill-t2d-schema-survey-20261019/schema_ingestion_survey.md`（工程调查报告：9 问逐项结论、映射表、状态转换图、方案 A/B/C、实施/验证/回滚、待人工决策）

## 调查摘要（全部结论以 file:line 或实测为证）

- **正式知识资产权威 Schema 不存在**：唯一知识记录是 `rag/knowledge_base.py:34-255,261-350` 的 DISEASE_DB（7 病害）/FARMING_GUIDE（4 作物）硬编码 Python 字典，无版本/来源/证据/状态字段。
- 候选字段→正式字段几乎全不兼容（quantitative→hard_constraints 五字段是唯一结构化可映射点且本轮全部 value=null 无可导出）；`CROP_MAP` 无小麦，属入库硬阻塞。
- 写入机制仅两处：`kg_adapter.propose_triple`→`data/kg_drafts.json` 草稿 JSONL（无审核消费者，`agents/judge_agent.py:146` 存在自动提议），`storage/db.py` 决策日志（agri.db 33 行/eval.db 285 行，实测）；均非知识资产通道。
- 未合并实现：`utils/judge_runtime.py`/`decision_semantics.py` 仅在 `work/20261017-phase4-eval-reliability`（340857f）与 docs-sync 分支；候选入库方案不依赖。
- 唯一迁移机制实例：`storage/db.py:40-45 _ensure_columns`（决策日志域）。
- T2A 报告两处事实勘误已登记：agri.db 非空库；"无任何写入接口"应限定为知识资产层。

## 推荐方案

- A（推荐）：独立候选层（v2 结构）+ 人工门禁 diff 提案导出器（只读候选→生成正式层 diff 提案，不写源码/库）+ 最小契约文档；不扩正式 Schema、不重建。
- B（否，备用）：正式层外置 JSON+loader（改动面大）。
- C（否）：kg_drafts 通道承载候选（无审核器+自动提议风险）。

## 验证结果

- 本轮只读；结论均附行级或命令实测证据（报告 §13 证据索引）；无代码/数据修改。

## 分支与提交

- 分支：`work/20261019-t2c-t2d-wheat-fhb`（与 T2C 同轮）
- 提交：`889462d` docs(AG-DISTILL-T2D): schema/ingestion contract survey

## 状态与下一步（待用户指示）

- 等待人工决策：方案 A 批准与否、小麦进 CROP_MAP/DISEASE_DB 时机、propose_triple 通道处置、P1 证据责任人、T2C v2 验收。
