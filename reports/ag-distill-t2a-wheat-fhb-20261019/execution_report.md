# AG-DISTILL-T2A 执行报告 — WHE-02 小麦赤霉病与毒素管理深度提取

- 执行日期：2026-10-19
- 分支：`work/20261019-t2a-wheat-fhb`
- 任务标识：`AG-DISTILL-T2A`；Prompt 版本：`t2a-p1`
- 性质：候选知识生成轮。产出**尚未进入**正式知识库资产，等待人工审查。

## 1. 执行前检查结果（任务 Section 一）

| 检查项 | 结果 |
|---|---|
| 阅读 AGENTS.md 与工作约定 | 已读；本轮按"独立分支 + 归档 + 等待指示"执行 |
| 阅读 T1 域探测地图 WHE-02 章节 | 已读；WHE-02 定位为 P1/全新域/时窗型规则，本轮范围 A-I 按其展开 |
| 现有 Schema、知识记录格式、证据字段 | 现状：库内唯一知识记录格式是 `rag/knowledge_base.py` 的 `DISEASE_DB`（作物病害诊断条目）与 `FARMING_GUIDE`；`kg_adapter.py` 从中派生 triples/rules/hard_constraints。**仓库不存在候选知识入库的正式 Schema 或证据元数据结构**（EVIDENCE_LEDGER.md 是台账文档，非数据结构） |
| 存储与检索接口现状（未修改） | 检索接口：`kg_adapter.query_kg(crop, query, top_k)`（neo4j/memory/fallback 三态）与 `rag` MCP 工具（search_disease/get_disease_info/get_farming_guide/get_optimal_conditions）。**无任何写入/入库接口**；`data/agri.db` 空库；Neo4j 依赖 docker-compose |
| 要求与项目约定的冲突 | 见 §7 冲突清单（共 4 项，均按项目约定处理并登记） |

## 2. 教师模型 API 可用性核验（Section 七前置）

- `DEEPSEEK_API_KEY` 经 `.env` 存在；最小预检（GET /models）返回 **HTTP 200**，模型列表 2 个。
- 对比：`reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md` 时为 401。**当前凭证已有效**，停止条件"无法访问教师模型 API"不触发。
- 注意：未修改 `.env` 与任何既有运行配置。

## 3. 管线执行（Section 三，8 阶段）

运行器：`scripts/extract_ag_distill_t2a_wheat_fhb.py`（本轮新增；ruff/mypy 通过）。
每阶段落盘 `reports/ag-distill-t2a-wheat-fhb-20261019/stage_logs/<stage>/{prompt.txt, raw_response.txt, parsed.json, meta.json}`。

| 阶段 | 内容 | 请求模型 | 实际服务模型 | 次数 | 耗时 | tokens(in/out) |
|---|---|---|---|---|---|---|
| S1 | 主题分解与缺口识别 | deepseek-chat | **deepseek-flash** | 1 | 7.7s | 832/907 |
| S2 | 核心概念与机制 | deepseek-chat | deepseek-flash | 1 | 15.4s | 804/2951 |
| S3 | 条件规则与时间窗口 | deepseek-chat | deepseek-flash | 1 | 19.1s | 832/3099 |
| S4 | 病害风险×毒素风险关系 | deepseek-chat | deepseek-flash | 1 | 10.9s | 819/1758 |
| S5 | 失败模式/反例/边界 | deepseek-chat | deepseek-flash | 1 | 14.9s | 806/2402 |
| S6 | 定量知识与证据需求 | deepseek-chat | deepseek-flash | 1 | 18.8s | 834/3928 |
| S7 | 独立审计（机器初筛） | deepseek-reasoner | deepseek-flash | 1 | 33.6s | 5930/7015 |
| S8 | 候选包组装与结构自检 | 本地脚本（无 API） | — | — | — | — |

合计约 10.9k 输入 / 22.1k 输出 tokens。

**重要诚实性发现**：服务端对所有请求模型统一返回 `served_model="deepseek-flash"`（`DEEPSEEK_BASE_URL` 网关映射）。含义：
- 提取与审计实际由同一服务模型完成；
- S7"独立审计"的**独立性降级**为"同模型机器初筛"，不能替代人工审查；
- 该收敛性已写入候选包 `audit_summary.independence_note`，并列入待人工决策。

## 4. 已执行 / 未执行清单（Section 五必答）

- **实际调用的模型**：deepseek-flash（经网关；请求模型见上表）。无非提取用途调用。
- **实际核验的来源**：仅教师 API 认证本身（HTTP 200）。**零文献/标准/规程文本核验**——本轮未获得任何检索或文献材料，因此：
  - 候选包 **0 条 `source-supported`** 知识；40 个单元全部为 model-candidate（16）/ model-inference（15）/ needs-verification（9）；
  - 所有定量 value=null 且 value_status=needs-verification（含 DON/ZEN 限量、安全间隔期、流行阈值等）；
  - 未录入任何农药名称-剂量组合；未录入任何标准编号数值。
- **未执行的环节**：真实独立模型审计（受网关映射限制，见 §3）、人工证据核验（需外部材料）、知识入库（无接口）、其余 4 个 Top5 主题（任务明示不做）。

## 5. 产物索引（Section 五 1-8 对应）

- `reports/ag-distill-t2a-wheat-fhb-20261019/execution_report.md`（本报告=产物 1+8）
- `reports/ag-distill-t2a-wheat-fhb-20261019/candidate_knowledge.json`（产物 2：40 单元候选包；**adaptation_status="待适配"**，对齐结构说明见包内 `existing_schema_alignment`）
- 产物 3（候选↔证据对应清单）：包内 `candidate_evidence_map` + 每单元 `provenance/provenance_note`
- 产物 4（定量待核验清单）：包内 `quantitative_verification_list`（40 单元相关条目全部 null；核验方向 topic 级已登记）
- 产物 5（知识关系清单）：包内 `knowledge_relations`（来自单元 related_units；本轮无悬空引用）
- 产物 6（独立审计结果）：包内 `audit_summary` + 每单元 `audit`（29 pass / 11 revise / 0 reject；独立性降级说明见 §3）
- 产物 7（冲突/缺口/待人工决策）：§7 + 包内 `coverage_gaps_and_next_questions`（S1 缺口 + 审计开放修订）、`pending_human_decisions`
- `reports/ag-distill-t2a-wheat-fhb-20261019/stage_logs/`（原始响应与逐阶段元数据，可追溯）
- `reports/ag-distill-t2a-wheat-fhb-20261019/validation_report.json`（结构自检：全绿）
- 脚本：`scripts/extract_ag_distill_t2a_wheat_fhb.py`、`scripts/assemble_ag_distill_t2a_wheat_fhb.py`

## 6. 审计与质量信号（结构自检 + 机器审计）

- 结构自检（`validation_report.json`）：unit_id 唯一与前缀一致（D10/R8/K5/F7/Q10）、枚举合法、statement 无未登记数字、定量纪律无违例、rule 单元 conditions 非空、审计覆盖 40/40。
- 机器审计（S7）：29 pass / 11 revise / 0 reject；全局发现 7 条。**有效修订意见**（保留 open）：D-03 病原复合体表述过宽、D-09 条件缺失表述绝对化、R-03 补治间隔按标签核验、R-05 排水降湿仅配套不替代、R-06 区域性绑定、R-07 安全间隔按标签核验、F-02 判定边界。
- **浓缩视图假象更正**：审计员只见浓缩清单，其"rule 单元缺 conditions/failure_modes"意见经对完整单元结构复核不成立（0 缺失）；该类修订项在包内标注 resolution=verified_in_full_unit 并保留原文以供追溯。

## 7. 冲突、缺口与待人工决策（Section 五 7）

冲突/偏差（按项目约定处理）：

1. **分支来源偏离**：AGENTS.md 要求"从 main 建新分支"，但 T1 地图只存在于未合并的 `work/20261019-ag-distill-domain-scan`，main 无法满足前置检查"阅读 T1 地图"。本轮分支从 domain-scan 派生；登记为对约定的显式偏离，待你确认合并路径。
2. **解码偏差**：上一轮 T2 约定"采用我定义的 schema"；本任务改为"符合现有 Schema 或明确标记为待适配"。因仓库无正式候选 Schema 且上轮 schema 未落盘，本包按后者输出（adaptation_status="待适配"），并把 Schema 定义归属列为待决策。
3. **文档-代码偏差**：`context/CURRENT_SPRINT.md` 称 `utils/judge_runtime.py`/`decision_semantics.py` 已落地（2026-10-17），实际 commit `340857f` 仅在未合并分支 `work/20261017-phase4-eval-reliability`，main/当前分支不可用。本轮未依赖该模块（另行直连 API），不影响产物，但影响后续评测链路复用。
4. **服务模型映射**：请求模型与实际服务模型不一致（§3），影响"独立审计"语义；不做未授权的端点配置修改。

知识缺口（节选，完整见候选包）：
- 病穗率→DON 的本地定量关系、区域流行阈值、病粒率收购分类挂钩、储粮安全水分界限：全部待核验。
- 农药标签合规层（登记/用量/间隔）需人工按现行标签核对，模型层不得代填。

## 8. 验收条件对照（Section 六）

| 条件 | 状态 |
|---|---|
| 稳定候选标识+知识类型 | ✓（unit_id 唯一 + knowledge_layer 枚举） |
| 重要结论有适用条件与不确定性 | ✓（conditions/uncertainties 字段强制） |
| 定量结论可追溯或明确待核验 | ✓（全部 null + needs-verification + verify_direction） |
| 病害风险与毒素风险未合并 | ✓（risk-chain 层专门拆分，K-04 解耦单元） |
| 证据不足/高风险知识不直接发布 | ✓（status=candidate；quarantined_units 空=无单元被直接采纳） |
| 未擅自修改现有知识库/Schema | ✓（仅新增文件；未改 rag/kg_adapter/接口） |
| 原始响应可追溯 | ✓（stage_logs 全套） |
| 格式与结构检查通过 | ✓（validation_report 全绿） |

## 9. 停止条件评估（Section 七）

未触发：API 可达、管线 8 阶段全部完成、结构检查通过。未合并分支、未启动其他主题、未将候选升级为正式资产。

## 10. 结论

按任务要求**等待人工审查**。可审查入口：`candidate_knowledge.json`（重点：audit_summary.independence_note、quantitative_verification_list、pending_human_decisions）。
