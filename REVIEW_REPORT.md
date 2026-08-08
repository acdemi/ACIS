# ACIS 项目审阅报告

**审阅日期:** 2026-08-08
**审阅范围:** 文档重复、代码冗余、项目组织、潜在问题（只读审阅，未修改任何文件）
**项目规模:** 469 个 git 跟踪文件，222 个 pytest 用例，约 12k 行 Python 代码

---

## 1. 项目概况

- **性质:** 农业认知智能体系统（ACIS 2.1E Evidence Platform），包含 agents（专家辩论层）、evals/experiments（评估与实验层）、planner/tool_router/rule_engine（规划与路由）、rag/kg（知识层）、trace/storage（可观测性）。
- **优点:** 模块分层清晰（perception → planning → memory → experts → debate → critic → judge）；测试覆盖较完整（222 个用例，2.6s 完成收集）；trace/evals/experiments 三层形成了完整的研究评估闭环（ablation、multiseed、能力矩阵）。
- **总体评价:** 架构方向健康，主要问题集中在**文档失控、代码复制、工程卫生**三方面。

---

## 2. 文档重复（6 组，按严重度排序）

### D1. Sprint 04.5 双份报告 — 同一 sprint 记录两次
- `docs/BENCHMARK_ENRICHMENT_SPRINT_04_5_REPORT.md` 与 `docs/BENCHMARK_ENGINEERING_SPRINT_04_5_REPORT.md`（均为 129 行，均称 "Sprint 04.5 Report (Phase 2.1E)"，内容高度重叠）。
- 且两者都已被 04.5B / 04.5C 报告取代。→ 应合并为一份并归档。

### D2. 路线图三处并存且互相矛盾
- `docs/roadmap.md`（187 行）、`context/ROADMAP.md`（18 行）、`README.md` §版本演进、`context/CURRENT_SPRINT.md` 四处描述同一版本路线。
- 矛盾点：`context/ROADMAP.md` 称 Sprint 05/06 未运行，但 `docs/EXPERIMENT_MANAGER_SPRINT_05_REPORT.md` 与 `docs/RESEARCH_EVAL_SPRINT_06_REPORT.md` 均标记 Complete；ROADMAP 说 "Sprint 06 → Dashboard"，CURRENT_SPRINT 说 Sprint 06 = 研究评估基础设施。
- → 以 `context/CURRENT_SPRINT.md` 为唯一事实源，ROADMAP 更新后降为指针。

### D3. 架构文档 3 份活跃副本 + 2 份陈旧副本
- RFC-001 已声明取代 `docs/architecture.md`（后者也正确声明自身已并入 RFC-001）——但 **`docs/architecture/architecture.md` 是第三份仍在维护的分层架构副本**，且是 CURRENT_SPRINT.md Read Order 第一项。
- `docs/architecture/vision.md`（10 行）复述 ACIS.md 使命；`docs/audit/IMPLEMENTATION_ARCHITECTURE.md`（"status: Proposed v0.1"）复述 RFC-008/009 + ADR。
- → 保留 RFC-001，删除/重定向 architecture.md 与 vision.md，修正 CURRENT_SPRINT.md 引用。

### D4. 实施计划 vs 审计 — 计划是"虚构的未来"文档
- `docs/IMPLEMENTATION_PLAN.md`（Draft，2026-07-16）描述的 Executive/Execution/Tool Layer/World Model/IoT 分层**在代码中不存在**；`IMPLEMENTATION_AUDIT.md`（2026-08-07）描述的是真实链路（planning → debate → critic → judge）。
- → 将 IMPLEMENTATION_PLAN.md 标记为历史 RFC 期规划并归档，或删除。

### D5. RFC 系列：格式分裂 + 前瞻性重复 + 规格落后于实现
- 格式三套并存：RFC-001/002 用 YAML front-matter，RFC-003~005 用 `**Status:**`，RFC-006~014 用 `- **Status:**` 列表。
- 内容重叠：RFC-008（Planner）与 RFC-006（Decision Pipeline）描述同一决策流；RFC-011~014（Self-Model/Goal/Agent-Ecosystem）是明确不实施的 4.x/5.x 前瞻规格（IMPLEMENTATION_PLAN.md L17 自认）。
- 状态滞后：RFC-004 记忆系统已实现并 Frozen 2.1，但状态仍是 Draft 1.0.0；RFC-003 agent 协议（lifecycle/capability declaration）在代码中**完全没有实现**，应标记为 Draft/未实施。

### D6. 自动生成的矩阵文档重叠（设计性重复）
- `benchmarks/CAPABILITY_MATRIX.md` 与 `benchmarks/COVERAGE.md` 由 `capability_matrix.py` 同时生成，行内容相同。
- → 保留其一，或让两份文档各有明确视角（如 CAPABILITY_MATRIX=能力×数据集，COVERAGE=数据集覆盖明细）。

---

## 3. 代码冗余

### 3.1 高度重复（应合并）

| 集群 | 位置 | 问题 |
|---|---|---|
| **Neo4j 客户端双份** | `kg_adapter.py:210-257` vs `kg/mcp_server.py:36-143` | `_get_driver`/`_neo4j_available`/`_query_neo4j`/`_parse_base_info` 四个函数几乎逐字节相同 |
| **决策形状断言双份** | `evals/fixture_eval.py:25-38` vs `evals/smoke_eval.py:30-42` | 相同的断言序列 |
| **trace 载荷提取器双份** | `evals/metrics.py:140-197` vs `evals/capability_metrics.py:166-190` | `_judge_payload`/`_memory_hits`/`_counterfactual_count` 重复实现而非 import |
| **能力矩阵生成器双份** | `benchmarks/taxonomy.py:126-260` vs `benchmarks/capability_matrix.py:124-442` | 同一 matrix+coverage 概念实现两遍 |
| **检查脚本双份** | `phase0_check.py` vs `scripts/phase0_check.py` | 同一脚本两份，已发生漂移（suite 加载方式不同），需手动同步 |
| **Sensor MCP 双份** | `rule_engine/sensor_simulator.py:85-125` vs `sensor_anomaly.py:416-431` | 同名 API、相同异常偏移量，后者质量更高 |

### 3.2 中等重复

- `_normalize_crop` 三份相同实现：`kg_adapter.py:41`、`rag/knowledge_base.py:23`、`rag/retriever.py:27`（后两处明明 import 了同一 CROP_MAP 却不复用函数）。
- `_read_manifest` 三个变体：`experiments/analysis.py:232` / `fingerprint.py:109` / `report.py:54`（一个 raise、一个返回 None、一个返回 {}）。
- `_fmt` 四份：`analysis.py:458` / `catalog.py:145` / `manager.py:134` / `report.py:48`。
- 能力平均值获取器两份：`catalog.py:137` `_cap_average` vs `manager.py:142` `_cap_avg`。
- 开关配置 schema 四份镜像：`evals/config.py` 的 EvalConfig/AblationConfig vs `experiments/schema.py` 的 RunSpec/AblationSpec（6 个开关布尔量重复定义，靠 `runner_adapter.py` 桥接）；`evals/ablation.py:140` 还有第 4 份 combo_config 映射。
- `_combo_name`/`_toggles_key` 在 `experiments/analysis.py:260` 重新推导 `evals/ablation.py:118` 已产生的命名。
- 数据集加载：`evals/config.py:83-100` 与 `benchmarks/loader.py:47-56` 并行实现。
- `workflow.py` 的 `compile_workflow` 是与 orchestrator 平行的备用管道，仅被 `orchestrator.py:198` 惰性引用。

### 3.3 死代码 / 孤儿文件

| 文件 | 状态 |
|---|---|
| `rule_engine/router.py` | **死代码**，无任何导入，已被 planner + tool_router 取代 |
| `rule_engine/sensor_simulator.py` | **死代码**，已被 sensor_anomaly 取代 |
| `scripts/phase0_check.py` | 死副本 |
| `phase0_5_single_case.py`（根目录） | 一次性孤儿脚本，已被 evals/runner 取代 |
| `phase0_check.py`（根目录） | 独立入口，未纳入 tests/CI |
| `src/` | **空目录（幽灵包）**，无任何文件 |

### 3.4 导入方式问题

- 无 `conftest.py` / `pytest.ini` / `pyproject.toml`，`sys.path.insert(0, ROOT)` 引导代码在 **21 个文件**（8 个入口 + 13 个测试）中复制粘贴。
- 无 installable package 配置，`_env.py` + sys.path 是事实上的打包替代品。

---

## 4. 项目组织问题

1. **`results/` 被 git 跟踪**：288 个实验产物文件已提交（2026-08-08 之前），`.gitignore` 虽新增 `results/` 但对已跟踪文件无效——后续每次实验都会产生脏工作区/无意义 diff。`data/`（245MB，vendored 第三方仓库 Agriculture_KnowledgeGraph-master）已在 .gitignore 中，处理正确。
2. **分支管理混乱**：本地 4 条陈腐分支（`0.45C-Capability_Evaluation_Engine`、`0.45C-CapabilityEvaluationEngine`、`claude/amazing-bardeen-551868`、`codex/acis-2.0`），远端也有 `0.45C-Capability_Evaluation_Engine` / `codex/acis-implementation-plan` / `sprint-04.5B-capability-contract` 未合并分支。分支命名也风格不一（大小写、下划线/连字符混用）。
3. **工作区未提交**：8 个文件已修改、4 个新文件未跟踪（含 `experiments/definitions/phase2_multiseed.yaml`、两个 phase0 脚本）。
4. **`codex/` 目录（AI 会话产物）被提交进仓库**，且其中 `IMPLEMENT.md`、`PATCH.md` 是 0 字节空文件。
5. **`.gitignore` 注释编码损坏**（GBK 中文写入 UTF-8 文件，显示为乱码），且缺少 `*.json` 类数据忽略规则。
6. **`context/README.md` 格式损坏**（有序列表被空行打断）。
7. **`context/CURRENT_SPRINT.md` 引用不存在的文件** `docs/ACIS_2.1E_ARCHITECTURE_FREEZE.md`（悬空引用）。

---

## 5. 其他发现

- **安全（低危）**: `_env.py` 被提交（`git ls-files` 确认），内容仅 `.env` 加载器、无密钥，属无害但应明确处理（保留或删除并改用统一加载方式）。`.env` 未被提交，`git grep` 确认 API key 未进入 git 历史。**状态正常。**
- **文档数字过期**: `IMPLEMENTATION_AUDIT.md` 声称 189 个测试，实际已收集 222 个；README 声称 "Evidence Review Gate / Sprint 05 未启动"，与 Sprint 05/06 报告及 `results/experiments/` 中已完成的多组实验矛盾。
- **`_env.py` 是唯一的 .env 加载入口**，删除前需确认 orchestrator/kg_adapter 的替代加载路径。

---

## 6. 建议优先级

### P0（低风险高收益，立即做）
1. 删除 `src/` 空目录、`rule_engine/router.py`、`rule_engine/sensor_simulator.py`、`scripts/phase0_check.py`（保留根 `phase0_check.py` 或统一其位置）。
2. 合并 `phase0_check.py`（根 vs scripts）为单份。
3. 为 tests 添加 `conftest.py`，删除 13 个测试文件中的 sys.path 样板。
4. 合并 `kg_adapter.py` 与 `kg/mcp_server.py` 的 Neo4j 客户端为单一模块。

### P1（清理冗余）
5. 合并 `evals/metrics.py` 与 `evals/capability_metrics.py` 的载荷提取器；统一 `_fmt`/`_read_manifest`/`_normalize_crop` 到 utils。
6. 统一两个能力矩阵生成器（taxonomy.py vs capability_matrix.py）。
7. 归档 Sprint 04.5 双份报告中的一份；更新 `context/ROADMAP.md` 与 README 现状。

### P2（文档治理）
8. 架构文档收敛到 RFC-001 + ACIS.md，删除 `docs/architecture/architecture.md`、`vision.md`、`docs/audit/IMPLEMENTATION_ARCHITECTURE.md`；修正 CURRENT_SPRINT.md 悬空引用与 Read Order。
9. 统一 RFC 状态格式；将 RFC-004/005 标记 Accepted，RFC-003 保留 Draft 并注明未实现；归档 RFC-011~014 为前瞻规格。
10. 标记 `docs/IMPLEMENTATION_PLAN.md`、`docs/acis_assessment.md` 为历史文档。

### P3（仓库卫生）
11. 从 git 移除已跟踪的 `results/`（`git rm -r --cached results/`），保持 .gitignore 生效。
12. 删除陈腐分支（本地 4 条 + 远端 3 条）或至少归档合并。
13. 决定 `codex/`、`context/`、`.claude/` 是否应进入版本库（建议仅保留 docs 化结论）。
14. 修复 `.gitignore` 编码与 `context/README.md` 格式。

---

## 结论

ACIS 2.1E 的**架构分层与评估闭环设计良好，测试体系健壮**（222 用例，收集 2.6s）。主要债务不在架构而在**维护面**：约 6 组文档重复/矛盾、8 个高冗余代码集群、4 个死文件、21 处 sys.path 样板、288 个误提交的实验产物。上述问题均为机械性清理工作，无架构性重构需求；建议按 P0→P3 顺序执行，预计可减少 10~15% 代码量并使文档事实源从 6 处收敛到 2 处。
