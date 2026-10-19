# 工程调查报告 — 现有知识资产 Schema 与入库契约（AG-DISTILL-T2D）

- 日期：2026-10-19；分支：`work/20261019-t2c-t2d-wheat-fhb`（与 T2C 同轮，只读调查）
- 方法：以实现与调用关系为准（不以文件名推断功能）；结论均给出 file:line 或实测命令证据。
- 范围：正式知识资产的格式/归属/ID/约束/写入接口/发布流，及 WHE-02 候选包的适配路径。未修改任何代码与正式数据。

## 0. 结论速览

| 问题 | 结论 |
|---|---|
| 正式知识资产权威 Schema | **不存在**。唯一知识记录载体是 `rag/knowledge_base.py` 两个硬编码 Python 字典 |
| 候选→正式转换 | 任务文档定义了"知识资产"（`kg_adapter` 契约），但**无**任何状态转换或入库流程的实现或文档规范 |
| 写入接口 | 知识层无写入接口；仅存在：①`propose_triple`→`data/kg_drafts.json` 草稿通道（无审核消费者）；②`storage/db.py` 决策日志写入 |
| 未合并实现 | `utils/judge_runtime.py`/`decision_semantics.py` 仅存在于未合并分支（340857f），main 与当前谱系不可用 |
| 推荐 | **独立候选层 + 人工门禁 diff 提案导出器**（不扩建正式 Schema、不重建知识库） |

## 1. Q1：正式知识资产的权威 Schema —— **不存在**

- 仓库无任何"知识资产"专用数据模型文件、JSON Schema、验证器或迁移文件（全树检索与目录核对：`rag/`、`scripts/`、`data/`、`docs/` 均无 schema/validator/migration 命名文件）。
- 唯一知识记录格式（事实标准）：
  - `rag/knowledge_base.py:34-255` `DISEASE_DB`（7 个病害条目；字段 name/crop/pathogen/symptoms/conditions/prevention/treatment/severity_indicators）；
  - `rag/knowledge_base.py:261-350` `FARMING_GUIDE`（4 个作物：optimal_conditions/growth_stages/irrigation）。
- 两者数据即 Python 源码字面量；**无版本、无来源、无证据状态、无生命周期字段**。
- 对话历史提到的 "AG-KA-v1" Schema 在仓库中**不存在**（全库 grep `AG-KA|AG_KA` 零命中；`work/20261019-t2-wheat-fusarium-head-blight` 分支为空壳，T2A 归档有记录）。

## 2. Q2：现有资产存储位置与序列化格式

| 载体 | 位置/格式 | 证据 |
|---|---|---|
| 诊断/农事知识（正式） | Python 源码字典（in-code literals） | `rag/knowledge_base.py:34,261` |
| 外部知识图谱 AgriKG | Neo4j（docker），节点 `:HudongItem/:NewNode`，关系 `:RELATION{type}`；数据源 `qq547276542/Agriculture_KnowledgeGraph`，本地副本 `data/Agriculture_KnowledgeGraph-master/` | `scripts/import_agrikg.py:8-16`、`kg_adapter.py:13-16` |
| RAG 向量层 | Qdrant collection `agri_knowledge_v1`（可选，offline fallback 到 DISEASE_DB） | `rag/retriever.py:1-6,18-24` |
| 决策审计库 | SQLite `data/agri.db`（默认，`AGRI_AI_DB_PATH` 可改；`data/eval.db` 为评测库）。**实测行数：agri.db decisions=33 行，eval.db=285 行** | `storage/db.py:13-37`；本报告调查实测 |
| 草稿三元组 | JSONL `data/kg_drafts.json`（append-only）；**该文件当前不存在**（从未写入） | `kg_adapter.py:449-492`；实测 `Test-Path data/kg_drafts.json`→False |
| 候选知识层 | JSON 文件包（`reports/**/candidate_knowledge*.json`，本轮 v2 含 revision 元数据） | `reports/ag-distill-t2c-wheat-fhb-revision/candidate_knowledge_v2.json` |

- T2A 报告两处表述勘误（不改结果，修正事实）：
  1. "`data/agri.db` 空库"不准确——含 decisions 表 33 行（决策日志，非知识资产）；
  2. "无任何写入/入库接口"应限定为"**知识资产层**无写入接口"——决策日志写入（`storage/db.py:get_connection`）与草稿三元组写入（`kg_adapter.propose_triple`）实际存在。

## 3. Q3：ID / 版本 / 来源 / 证据 / 条件 / 关系 / 状态的表达现状

| 维度 | 正式层现状 | 证据 |
|---|---|---|
| ID | DISEASE_DB/FARMING_GUIDE 字典 key（snake_case，如 `tomato_leaf_mold`） | `rag/knowledge_base.py:35` |
| 版本 | 无 | 同上（条目无 version 字段） |
| 来源 | 无来源字段；仅运行时合成 hard_constraints 带 `source:"memory"` | `kg_adapter.py:146` |
| 证据 | 无 | 同上 |
| 条件 | 自由文本，如 `"20-25°C"`、`">85%"`；`_parse_threshold` 运行时正则解析为 (operator, float) | `knowledge_base.py:46-49`、`kg_adapter.py:52-65` |
| 关系 | 非存储字段：`_disease_triples` 运行时从条目合成 triples | `kg_adapter.py:111-126` |
| 状态 | 无任何状态字段/状态机 | 全条目观察 |

候选层（WHE-02 v2）已具备：unit_id、knowledge_layer、provenance/provenance_note、conditions、failure_modes/side_effects、applicability、quantitative（metric/value/unit/operator/value_status）、verification_methods、related_units、uncertainties、audit 记录——证据元数据结构见 `candidate_knowledge_v2.json`（T2A 组包脚本同样固定该结构，`scripts/assemble_ag_distill_t2a_wheat_fhb.py:137-138`）。

## 4. Q4：校验器 / 迁移 / 写入接口 / 发布审批 —— 除决策库自迁移外均不存在

| 机制 | 结论 | 证据 |
|---|---|---|
| 知识校验器 | **不存在**（tests/ 19 个测试文件无 knowledge_base/kg_adapter 专项；`tests/test_collective_omission.py:104` 使用自造 kg dict） | tests/ 目录核对 |
| 迁移机制 | 仅决策日志有（`storage/db.py:40-45 _ensure_columns` 幂等 ALTER；`executescript` 幂等建表） | `storage/db.py:48-57` |
| 知识写入接口 | **不存在**（正式层=源码，写=改代码）；草稿级仅有 `propose_triple`（幂等 append，`AGRI_AI_KG_DRAFTS_PROPOSE` 开关，带 confidence/evidence/created_at） | `kg_adapter.py:452-477` |
| 草稿审核消费者 | **不存在 promote/审核流程**；唯一消费点 `agents/judge_agent.py:152` 只读取草稿供上下文，`146` 自动提议"易感"三元组 | `agents/judge_agent.py:146,152`、README.md:65 |
| 发布审批 | 无机制；正式层变更仅靠 Git PR 人工流程（AGENTS.md 约定） | AGENTS.md；文档无发布规范 |

## 5. Q5：候选包 → 现有资产字段不兼容清单

| 候选字段 | 正式层对应 | 映射性 |
|---|---|---|
| unit_id | DISEASE_DB key | 需命名规范转换（`WHE02-D-xx`→`wheat_fhb_*` 风格） |
| title / statement | `name`/`symptoms[]` | 无 1:1；需按 knowledge_layer 拆写 |
| provenance/audit/verification_methods | 无对应 | 需新增 evidence 元数据（承载于候选层或契约文档） |
| main_triple | 运行时合成 triples；Neo4j 可存 但正式层无三元组实体 | 声明级可用；持久化需走 Neo4j 或 drafts 通道 |
| conditions[]（中文文本） | `DISEASE_DB.conditions{温度/湿度:">85%"}` 需可被 `_parse_threshold` 解析 | 需人工改写为结构化键+规范化串 |
| quantitative | `hard_constraints`（metric/operator/threshold/raw/description） | 结构可映射；**但本轮全部 value=null，无任何可导出数值** |
| failure_modes/side_effects/uncertainties/related_units/applicability | 无对应 | 不导出，保留候选层 |
| **作物覆盖** | `CROP_MAP`（`knowledge_base.py:12-20`）**不含小麦**；crop 过滤按中文子串（`_normalize_crop("wheat")`→原样 `"wheat"`，与条目 `crop:"小麦"` 不命中） | 硬阻塞：入库须同时改 CROP_MAP，否则检索不可达 |

## 6. Q6：是否需要新增字段/映射层/独立候选层

**需要独立候选层（已事实存在）+ 人工门禁映射层；不需要扩展正式 Schema。**

- 候选层保持 v2 结构（字段自足、含 provenance/状态验证门禁），作为唯一"真源"；
- 正式层改动只以"diff 提案"形式生成（改 `knowledge_base.py` 源码的补丁建议），人工审阅合入；
- 不引入新字段进正式层（severity_indicators 等现状字段不动）。

## 7. Q7：防重复入库 / 覆盖历史 / needs-verification 误升

- **重复防护**：候选 side dedupe key = package_id + unit_id + base_sha256（v2 已内置 base_sha256 追溯，`candidate_knowledge_v2.json.revision`）；正式层重复检测靠人工 diff 审阅.
- **覆盖防护**：候选文件不可变策略（v1/v2 分目录、append 式版本号）；正式层=Git 源码，禁止程序化改写，防覆盖.
- **误升防护（关键）**：**`needs-verification` 单元不得通过任何自动流程进入 `DISEASE_DB`/`har d_constraints`**。当前五条 P1 合规门禁（R-07/K-02/Q-04/Q-05/Q-06）在标准文本/登记标签核验完成前，映射导出器一律不产出其数值. 升级点唯一：证据登记（ref/verified_by/retrieved_at）→ 人工批准.

## 8. Q8：回滚 / 审计 / 增量更新

- 回滚：候选层=Git 版本化 JSON（v1/v2 各自完整、按 sha 引用）；正式层=Git revert；SQLite 决策库日志 WAL+idempotent schema（`storage/db.py:53-55`），无需知识层回滚耦合.
- 审计：T2A stage_logs（raw/prompt/meta）+ T2B claim_audit.csv + T2C revision_status.csv/diff_report.json 已形成链条的性能良好的 audit trail.
- 增量：按 unit_id 逐单元处理（本链已实践）；正式层增量=每提案一个 PR（最小 diff）.

## 9. Q9：文档引用的不可用实现影响

- `utils/judge_runtime.py`/`decision_semantics.py` **仅存在**于未合并分支 `work/20261017-phase4-eval-reliability`（提交 340857f，同时被 `work/20261019-docs-sync-reliability` 包含）；main 与当前谱系**没有**（`git ls-tree main` 无 utils/ 下该文件；实测 `Test-Path` 均不工作).
- 引用它们的 `context/CURRENT_SPRINT.md` 是 docs-sync 分支版本；main/当前谱系的 CURRENT_SPRINT.md（Phase 4.2-R 待架构决策）不含该条目.
- **影响评估**：候选→正式入库方案不依赖这两个模块（它们属评测语义层）；若未来评估链复用，须先合并并移植后再定契约。当前结论不受其缺席影响.

## 10. 状态转换图（候选 → 正式）

```
candidate v1 (T2A)
   │ T2B 审计(48行, agent复核≠独立模型审计)
   ▼
audited v2 (T2C 最小修订: 34 closed / 6 open / 8 deferred)
   │ ① 人工验收本轮产物
   ▼
adopted ──(5项P1合规门禁: 标签/限量/条款证据)──▶ evidence-verified   [provenance 唯一允许升级点]
   │ ② 人工批准映射导出
   ▼
adaptation-proposal (正式层 diff 提案: DISEASE_DB新增条目 + CROP_MAP小麦 + hard_constraints)
   │ ③ 人工 PR 合入 rag/knowledge_base.py (Git 历史=审计轨迹)
   ▼
published (正式知识; needs-verification 永不经①②③直达)
```

## 11. 方案与替代

### 方案 A（推荐）：独立候选层 + 人工门禁 diff 提案导出器

- 复用：候选包结构（事实标准）、V2 sha256 追溯、`hard_constraints` 五字段结构（作为 quantitative 目标契约）、AGENTS.md 人工审查流、Git 全历史审计。
- 新增最小件（批准后才做）：①契约文档（状态转换图+字段映射表+evidence 元数据最小集 ref/status/verified_by/retrieved_at）；②只读导出器 `scripts/export_candidate_diff.py`（候选包→正式层 diff 提案，**不写源码、不写库**）。
- 约束对照：不扩 Schema✓、不重建知识库✓、needs-verification 不进正式层✓、迁移有备份/diff/幂等/回滚✓（提案式=零迁移）。

### 方案 B（否，备用）：正式层外置为 JSON 数据文件 + loader

- 改动面大（所有 import 语义变化），违反"不因格式不理想而重建"；仅在知识规模显著增长时重新评估。

### 方案 C（否）：以 `kg_drafts.json` JSONL 承载候选

- 该通道无审核消费者，且 `agents/judge_agent.py:146` 存在**自动提议**路径——用它承载候选会弱化人工门禁；若远期采用必须先建审核器并默认 `AGRI_AI_KG_DRAFTS_PROPOSE=0`。

## 12. 待人工决策事项

1. 批准/否决方案 A（含 2 个最小新增件）。
2. 小麦进入 `CROP_MAP`/`DISEASE_DB` 的时机与审校人选（涉及正式代码双点修改，硬阻塞见 §5）。
3. `propose_triple` 草稿通道处置：冻结 / 限流默认关闭 / 补建审核器。
4. T2B/T2C 遗留：五条 P1 证据责任人、AUD-T2B-048 审计独立性处置。
5. T2C v2 候选包的人工验收。

## 13. 证据索引

- 实现：`rag/knowledge_base.py:12-20,34-255,261-350,371-442,535-544`；`kg_adapter.py:34,52-65,111-149,396-442,449-506`；`agents/judge_agent.py:15,40,66,73,146,152`；`rag/retriever.py:1-24`；`storage/db.py:13-57`；`scripts/import_agrikg.py:8-16,39-46,61-89`；`agents/` 13 agent+types.py；tests/ 19 测试文件清单。
- 数据：`data/agri.db`(decisions=33 行)/`data/eval.db`(285 行) 实测；`data/kg_drafts.json` 不存在实测；`data/Agriculture_KnowledgeGraph-master/` 存在。
- 分支事实：340857f stat（judge_agent +199 / decision_semantics 新增 / test_judge_runtime 新增 302 行）；ls-tree reliability 分支含 `utils/judge_runtime.py`；docs-sync 分支 CURRENT_SPRINT 摘录引用两实现。
- 文档：`MODEL_AGENT_ORCHESTRATION.md:131`（query_kg 契约）、`README.md:65`（KG 进化描述）、AGENTS.md（人工审查流）、`context/CURRENT_SPRINT.md`（当前 Sprint 无知识入库事项）。
