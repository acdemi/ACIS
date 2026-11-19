# 盘点 C：文档 / Git / 历史垃圾 / 冗余

> 盘点员：inv-docs-git｜时间：2026-11-01｜工作目录：`E:\knowledge_database\ACIS`
> 约束：全程只读（未改/删/移动任何既有文件，未执行任何 git 写操作，未执行 `git config`）。
> 唯一产出：本文件（`reports/_parts/inventory_docs_git.md`）。所有 git 命令均以 `git -c safe.directory=E:/knowledge_database/ACIS <sub>` 形式执行。
> 方法限制：沙箱禁止捕获子进程 stdout（`git ... | cmdlet` 会报 `StandardOutputEncoding is only supported when standard output is redirected` / 拒绝访问），故需计数的项改用 git 原生计数参数、`.git/index` 头部解析、`Select-String` 等替代路径；逐字不可得的少数项在 C8 标注 `[待确认]`。

---

## C1 文档清单与时效

规模：`docs/**` 共 29 个文件 0.2 MB；根文档 2 份；`context/` 2 份；`reports/README.md` 1 份。Archive 内 9 份 RFC + 10 份 Sprint 报告与描述一致。

| # | 文档 | 主题 / 规模 | 最后修改（git 提交 / 工作树 mtime） | 时效判断 | 证据 |
|---|---|---|---|---|---|
| 1 | `README.md` | 项目入口：边界、架构、技术栈、快速开始、测试与评测、文档导航 | 提交 `d2fa727` 2026-10-24；mtime 2026-10-30 12:25 | **现行事实源**（RFC001 明示）；但工作树有未提交修改 | `README.md:1-216`；HEAD 版 9,018 B vs 工作树 13,467 B（`git ls-tree -r -l HEAD`）；RFC001:39 |
| 2 | `MODEL_AGENT_ORCHESTRATION.md` | 小模型/Agent 编排设计说明（181 行） | 提交 `f1c7e98` 2026-10-24 | 设计说明，非实现清单（自述），部分脱节 | `MODEL_AGENT_ORCHESTRATION.md:3-5,181` |
| 3 | `docs/ARCHITECTURE_DECISIONS.md` | ADR-001~005（248 行），架构决策 | 提交 `18abe26` 2026-10-24 | 现行，但 front matter 过期 | `:11` 仍写 `last_updated: 2026-07-10`；ADR-005 日期 `:163` 为 2026-10-23 |
| 4 | `docs/DEMO_RUNBOOK.md` | 3–5 分钟演示脚本与故障注入（168 行） | 提交 `f1c7e98` 2026-10-24；mtime 2026-10-30 12:28 | 现行；工作树未提交（HEAD 9,245 B vs 11,586 B） | `docs/DEMO_RUNBOOK.md:1-168` |
| 5 | `docs/rfc/RFC001-System Architecture.md` | 架构规格（351 行，10 层 + 实施状态） | 提交 `f1c7e98` 2026-10-24 | **现行架构权威**（ADR-001 Accepted），自带实现边界表 | `:4-11` status Accepted v2.1.1；`:36-49` Implementation Status |
| 6 | `docs/archive/README.md` | 归档索引（19 行） | `f1c7e98` 2026-10-24 新增 | 现行索引 | `:3-5,9-16` |
| 7 | `docs/archive/architecture-principles.md` | 6 条架构原则（8 行） | mtime 2026-08-01 | **历史/已被取代**（原则并入 vision §3、ADR） | `:1-8`；`archive/README.md:12` |
| 8 | `docs/archive/architecture-state.md` | 模块冻结状态（36 行） | mtime 2026-10-23 20:49 | **历史且自相矛盾**：自称唯一事实源、Judge 已 Frozen | `:4`；`:11`；与 ADR-005 冲突（见 C2-D7） |
| 9 | `docs/archive/changelog.md` | 变更记录（222 行，末条 2026-10-24） | mtime 2026-10-24 13:03 | 历史，但内容最新；与 ADR-005 结果重复 | `:3-25` vs `ARCHITECTURE_DECISIONS.md:207-224` |
| 10 | `docs/archive/current-sprint.md` | 旧 Sprint 状态（70 行，截至 10-19 + Phase 6 声明） | mtime 2026-10-24 13:03 | **已过期**：引用 3 个已删脚本 / 4 个已迁移报告路径 | `:5`；`:41-46,53-54` vs 实际 `scripts/` 仅 7 文件 |
| 11 | `docs/archive/roadmap.md` | 版本路线图（189 行） | front matter `status: Archived, last_updated: 2026-08-08` | 历史；指向的“唯一事实源”已不存在 | `:4-7,14-15,26`（`context/CURRENT_SPRINT.md` 已删） |
| 12 | `docs/archive/vision.md` | 早期 ACIS 宪章（456 行，含文档治理 §5） | mtime 2026-08-08 | 历史；治理章节引用的 `ACIS.md` 已不存在 | `:320-387`（`:328` ACIS.md；`:382-387` Read-Before-Implement） |
| 13 | `docs/archive/rfc/RFC-002 ~ RFC-010` | 9 份子系统规格（18,518 B ~ 6,432 B） | mtime 2026-07-16 / 08-08 | **历史设计**，多数未实现 | `archive/README.md:10`“多数未完整实现”；ADR-002 将 RFC-010 World Model 定为预留 |
| 14 | `docs/archive/sprints/*` | 10 份 Sprint 报告（6,613 B ~ 9,815 B，Phase 2.1E） | mtime 2026-08-01 ~ 08-08 | **历史**（Trace/Eval/Benchmark/Ablation/Capability/Experiment/Research） | `docs/archive/sprints/` 文件清单 |
| 15 | `context/EVIDENCE_LEDGER.md` | 证据台账 E007–E020（41 行） | 提交 `f1c7e98` 2026-10-24 | 现行，但与 README §8 重叠 | `:10-25`；`:17` E012 Untested |
| 16 | `context/KNOWN_DEBT.md` | 已知债务（46 行） | 提交 `f1c7e98` 2026-10-24 | 现行，但测试状态与 README 冲突（C2-D1） | `:8-10` |
| 17 | `reports/README.md` | 报告索引/口径提醒（37 行） | 提交 `f1c7e98` 2026-10-24 | 现行，但 `:36` 与实况不符（C2-D6） | `:3-4,24-26,36` |

时效口径说明：多数 archive 文件的 git 提交日期都是 `f1c7e98`（2026-10-24 “更换线程”，一次性搬迁 222 个文件），因此**以 mtime / front matter / 内容日期判断真实时效**，不能以“最后提交=10-24”当作“内容最新”。

---

## C2 文档冗余与单一事实源建议

### C2.1 重叠主题矩阵（●=主要承载，○=重复提及）

| 主题 | README | MODEL_AGENT_ORCH | RFC001 | ADR | DEMO_RUNBOOK | vision | arch-principles | arch-state | roadmap | current-sprint | changelog | EVIDENCE_LEDGER | KNOWN_DEBT | reports/README |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 系统分层/组件职责 | ● | ● | ● | ○ | | ○ | ○ | | | | | | | |
| 能力边界（真实/模拟/未实现） | ● | ● | ● | | ○ | | ○ | | | | | | ● | |
| 测试与评测数字 | ● | | ○ | ○ | ● | | | | | ○ | ● | ● | ● | ● |
| accuracy=factor coverage 口径 | ● | | | | | | | | | | | ● | ● | ● |
| 指标/实验证据 | ○ | | | ● | | | | | | ● | ● | ● | ○ | ● |
| 架构决策为何如此 | ○ | ○ | ○ | ● | | | ○ | | | | | | | |
| 模块冻结/项目状态 | ○ | | | | | | | ● | ● | ● | ● | | ● | |
| 文档治理/优先级 | ○ | | ● | ● | | ● | | | | | | | | |
| 目录/入口/运行方式 | ● | ● | ○ | | ● | | | | | | | | | |

结论：**同一主题平均有 3.2 份文档承载**；`能力边界` 有 5 份、`测试数字` 有 8 份、`accuracy 口径` 有 4 份，属于典型“多点声明”。

### C2.2 已定位的文档间冲突（可机械核对）

| ID | 冲突 | 证据 |
|---|---|---|
| D1 | 测试状态不一致：README 称“本机复跑 342 passed / 2 skipped”；KNOWN_DEBT 称“受限沙箱 340 passed / 3 failed，普通环境未复跑” | `README.md:171,198` vs `context/KNOWN_DEBT.md:8-10` |
| D2 | 支持作物数量：README=4 作物/7 病害；MODEL_AGENT_ORCH=“番茄/甜菜/棉花三种” | `README.md:25-26` vs `MODEL_AGENT_ORCHESTRATION.md:181`；代码为 4 作物（`rag/knowledge_base.py:12-19`）、7 病害（`:35,67,99,131,162,193,224`） |
| D3 | ADR 状态自相矛盾：ADR-005 标 Accepted，但结尾“决策生效与后续”称 ADR-002~005 均为 Proposed | `docs/ARCHITECTURE_DECISIONS.md:162` vs `:240` |
| D4 | 谁是对事实源：RFC001 说“README is the current fact source”；vision §5.2 把 README 排 Priority 5、RFC 高于 README；archive/README 说归档非事实源；roadmap 说以 `context/CURRENT_SPRINT.md` 为唯一事实源 | `docs/rfc/RFC001…:39`；`docs/archive/vision.md:362-366`；`docs/archive/README.md:3-5`；`docs/archive/roadmap.md:15` |
| D5 | ADR-001 规定 `architecture.md` 降级为指向 RFC-001 的指针，但该文件已被删除 | `docs/ARCHITECTURE_DECISIONS.md:43,239` vs `f1c7e98` name-status `D docs/architecture.md` |
| D6 | reports/README 称“原始 raw JSON 不在此目录，已移出公开仓库”，实际仍有 5 份 `raw_results*.json` 被跟踪（合计约 0.58 MB） | `reports/README.md:36` vs `git ls-files`：`phase6_baseline_20261023/raw_results.json`(228,607 B)、`phase6_ablation_20261024/…`(133,191 B)、`phase4_real_agent_consistency_20261017/…json`(94,582 B)、`phase6_sc43…`(73,894 B)、`phase6_sc_…`(66,016 B) |
| D7 | architecture-state 自称“模块稳定性唯一事实源”“Judge Frozen”，但 ADR-005 已在 Phase 6 重构 Judge 置信度链路 | `docs/archive/architecture-state.md:4,11` vs `docs/ARCHITECTURE_DECISIONS.md:160-235`、commits `575b24e/65fe42c/e912d80` |
| D8 | current-sprint 引用的脚本/报告路径均已不存在 | `docs/archive/current-sprint.md:46,53-54`（`scripts/run_phase4_2.py`、`scripts/run_phase4_2_real_agent.py`、`scripts/stress_test_judge.py`、`reports/phase4_evaluation_pilot.md` 等均为 MISSING） |
| D9 | 实际工程规范 `AGENTS.md` 已从根目录删除，只在 `logs/` 留下 3 份副本；其规定的归档路径 `context/archive/` 也已被删除 | `f1c7e98` 删除 `AGENTS.md`；`xx:4`（`AGENTS.md | 28 -`）；`xx:21-40`（`context/archive/*` 全删） |

### C2.3 单一事实源建议（[推测]，供 Lead 决策）

| 主题 | 建议唯一事实源 | 处理动作（建议，不在本次执行） |
|---|---|---|
| 架构 WHAT（分层/边界/职责） | `docs/rfc/RFC001` | 保持；删除 `architecture-principles.md`/`architecture-state.md` 或降为一行指针 |
| 决策 WHY（为何这样改） | `docs/ARCHITECTURE_DECISIONS.md` | 修 front matter（`:11`）、修 `:240` Proposed 表述；ADR 是权威解释，不再在 changelog 复述结论 |
| 项目现状/能力边界/入口 | `README.md` | 保留为现状唯一源；RFC001 只留 Implementation Status 摘要并回链 README |
| 实验数字与指标口径 | `reports/experiment_audit_20261024.md` + `reports/README.md` | 其余位置（README §8、KNOWN_DEBT、EVIDENCE_LEDGER、DEMO_RUNBOOK）只引用不复述 |
| 证据台账 | `context/EVIDENCE_LEDGER.md` | 建议合并进 reports 或 README §8；否则与 experiment_audit 双写 |
| 工程规范 | 恢复仓库根 `AGENTS.md`（内容取 `logs/*/AGENTS.md` 的 blob `962ae16`） | 这是当前唯一可查到的真实工作约定（C7） |
| 历史 | `docs/archive/**` | 保留，但在文件头统一加 “Superseded by …” 指针，避免被误引 |

---

## C3 文档 vs 实现脱节核对（只做可机械验证项）

| # | 声称（含行号） | 实际证据 | 判定 |
|---|---|---|---|
| 1 | README：26 个测试文件 | `tests/test_*.py` = **26** | ✅ 一致 |
| 2 | README：344 个用例 | 静态 `def test_` = **316**，`@pytest.mark.parametrize` = **9** | ⚠️ `[待确认]`（未跑 pytest，参数化展开数无法静态确定） |
| 3 | README：342 passed / 2 skipped | 未运行（pytest 会写 `.pytest_cache`，越界）；KNOWN_DEBT 记 340/3 | ⚠️ `[待确认]` + 文档冲突（D1） |
| 4 | README：4 作物 / 7 类病害 | `CROP_MAP` 4 项（`:12-19`）、`DISEASE_DB` 7 项（`:35,67,99,131,162,193,224`） | ✅ 一致 |
| 5 | README：Python 3.13.3 | `.venv/pyvenv.cfg` `version_info = 3.13.3` | ✅ 一致 |
| 6 | README:72 `workflow.py:37` LangGraph StateGraph | `workflow.py:37` `from langgraph.graph import END, StateGraph`，`:39` 建图 | ✅ 一致 |
| 7 | README:85 `orchestrator.py:172-178` 回退 | `orchestrator.py:172` 回退日志、`:176` `run_rules(...)` | ✅ 一致 |
| 8 | README:73 `gateway/app.py:25` FastAPI | `gateway/app.py:25` `app = FastAPI(...)` | ✅ 一致 |
| 9 | README:86 `judge_agent.py:73` fallback_reason_code | `agents/judge_agent.py:73` | ✅ 一致 |
| 10 | README:87 `trace/types.py:36-47` 10 阶段 / `exporter.py:37` | `trace/types.py:36-47` STAGE_ORDER 恰 10 项；`trace/exporter.py:37` `export_trace_json` | ✅ 一致 |
| 11 | README:88 `storage/db.py:16` decisions 表 | `storage/db.py:16` `CREATE TABLE IF NOT EXISTS decisions (` | ✅ 一致 |
| 12 | README:109 TUI「6 个演示场景」 | `ui/tui.py:73` `DEMO_SCENARIOS`，`"title"` 计数 = **6** | ✅ 一致 |
| 13 | README:79 streamlit/transformers/torch/scikit-learn“已声明未验证” | `requirements.txt:18,21,22,27`；`ui/web_app.py:20 import streamlit as st` | ✅ 一致 |
| 14 | README:174 离线评测 12/12、平均置信度 0.6583、2 例 Critic | `reports/delivery_eval/summary.md`：12 行 PASS、`平均置信度：0.6583`、`Critic 触发：2 例` | ✅ 一致 |
| 15 | README:179-181 Phase 6：72/72、C0 20/24、C1 19/24、C2 24/24 | `reports/phase6_baseline_20261023/baseline_analysis.md:6,12-14` | ✅ 一致 |
| 16 | README:185-186 Phase 4.2-R 191/216 规则回退 | `docs/archive/current-sprint.md:14` “judge 191/216 回退” | ✅ 一致 |
| 17 | README:187-190 历史 accuracy 实为 factor coverage | `reports/README.md:24-26`；`context/KNOWN_DEBT.md:18-20` | ✅ 一致 |
| 18 | README:204-213 文档导航 6 个链接 | 6 个目标文件/目录全部存在 | ✅ 一致 |
| 19 | README:130 示例置信度 72% | `reports/delivery_eval/summary.md` 同案（tomato_leaf_mold, seed 7）= 74% | ⚠️ 小差异 `[待确认]`（RAG/KG/持久化开关不同，非同一配置） |
| 20 | MODEL_AGENT_ORCH:181 “三种作物” | 代码 4 作物（含黄瓜，`knowledge_base.py:14,99`） | ❌ 脱节（D2） |
| 21 | MODEL_AGENT_ORCH:146 `agri-agent-mvp/scripts/import_agrikg.py` | 实际为根下 `scripts/import_agrikg.py`（无 `agri-agent-mvp/` 子目录） | ❌ 路径失效 |
| 22 | README:213 指向 `LICENSE` | 根目录存在 `LICENSE`（1,063 B，tracked） | ✅ 一致 |

技术栈层面无夸大：`requirements.txt`(694 B)/`requirements-lock.txt`(2,794 B)/`.venv` 均存在，`pytest.ini` 限定 `testpaths = tests` 且显式排除 `logs results data neo4j pytest-of-lkl torchinductor_lkl`（`pytest.ini:1-6`）。

---

## C4 Git 状态与活跃度

### C4.1 基本状态

| 项 | 值 | 证据 |
|---|---|---|
| 当前分支 | `main`（HEAD `d2fa727`，与 `origin/main` 同点） | `git rev-parse --abbrev-ref HEAD`、`git branch -a -vv` |
| 提交总数 | HEAD 可达 **96**；`--all` **97**；**2 个根提交**（`3542e6c` lkl “Initial agri agent MVP”、`74f92b4` acdemi “Initial commit”，均 2026-07-02） | `git rev-list --count HEAD/--all`、`git log --max-parents=0 --all` |
| 时间跨度 | 2026-07-02 → 2026-10-24 21:19（+0800），约 115 天 | `git log -1 --date=iso` |
| 近 30 天提交 | **50** | `git rev-list --count --since=30.days HEAD` |
| 近 90 天提交 | **80** | `git rev-list --count --since=90.days HEAD` |
| 按月 | 7 月 11 / 8 月 29 / 9 月 6 / **10 月 50** | `git rev-list --count --since/--until` |
| 最近活动 | 2026-10-25 ~ 11-01 提交数 **0**（已静默 8 天） | `git rev-list --count --since=2026-10-25 --until=2026-11-02` |
| stash | **空** | `git stash list`（无输出） |
| tag | **无** | `git tag -l`（无输出） |
| worktree | **2 个**：主工作树 `E:/…/ACIS` [main]；`E:/…/ACIS/logs/p6-wt` [work/20261023-phase6-arch-redesign @ 18abe26] | `git worktree list` |
| 未提交改动 | **3 个已修改、0 个未忽略未跟踪**：`README.md`、`docs/DEMO_RUNBOOK.md`、`tests/test_planner.py` | `git status --porcelain=v1` |
| 被忽略目录（摘录） | `.venv/ .mypy_cache/ logs/ results/ data/ pytest-of-lkl/ torchinductor_lkl/ neo4j/{import,logs,plugins}/ .env .claude/ .vscode/ reports/document_cleanup_manifest.csv` | `git status --porcelain --ignored=matching`（35 条） |
| 跟踪文件数 | **235**（`.git/index` 头部 uint32 BE @offset 8；与 `HEAD` 树 235 项一致） | `.git\index` 解析 + `git ls-files` |
| 磁盘实际文件数 | 全盘 **51,736**；排除 `.git/.venv/__pycache__/.mypy_cache/.ruff_cache/.pytest_cache` 后 **5,681** | `Get-ChildItem -Recurse -File` |
| 未跟踪占比 | 5,681 − 235 ≈ **5,446 个（95.9%）未跟踪**（全部被 .gitignore 覆盖：logs 4,006 / results 1,239 / data 191 / 其它缓存与临时） | 同上 |

### C4.2 最近 20 条提交（`git log --oneline -20`）

```
d2fa727 fix: finalize ACIS offline delivery validation
f1c7e98 更换线程                       ← 一次性删除 222 文件、-58,184 行（含根 AGENTS.md、archive 搬迁、xx 入库）
828e0da merge: work/20261024-acceptance-portfolio (audit, plan, MVP, acceptance materials)
0d3f288 docs(portfolio): acceptance, experiment audit and resume materials
3b5cc99 docs: correct test counts after delivery contracts
10df9c1 docs(archive): 20261024 mvp delivery round
059fc0b feat(mvp): runnable delivery baseline - pytest/trace/API/vision fixes + deterministic eval
39df292 docs(archive): 20261024 resume delivery plan round
166da76 docs(plan): read-only inventory and minimal resume-delivery path (mode switch)
d4197f3 docs(archive): 20261024 delivery checklist audit round
750886c docs(audit): delivery checklist audit for ACIS 2.1E/Phase 6 (6-item evidence review + 3-min demo runbook)
6420e34 docs: archive 20261024 merge round
81d63ed Merge branch 'work/20261023-phase6-arch-redesign'
26b2133 Merge branch 'work/20261019-judge-provenance-verify'
b9c6ae2 Merge branch 'work/20261019-t2e-t2f-release-readiness'
18abe26 docs: record ADR-005 acceptance and phase 6 findings
042e1a2 analysis(phase6): agreement-based confidence meets ADR-005 on two seeds
e912d80 feat(judge): agreement-dominant confidence, unscored when signal missing
65fe42c feat(judge): self-consistency sampling as the discriminative confidence signal
575b24e feat(judge): derive and calibrate decision confidence (ADR-005)
```

### C4.3 分支（本地 24 = main + 23）

- 已并入 main：**22 条**（`claude/amazing-bardeen-551868`、`sprint-04.5B-capability-contract`、20 条 `work/<日期>-<主题>`，其中 `work/20261023-phase6-arch-redesign` 仍被 `logs/p6-wt` 检出）。
- **未合并：1 条** `codex/acis-implementation-plan`（领先 main **1** 个提交：`6de83b2 Save changes to tui.py`；本地领先 origin 1；其父提交 `6a74817 refactor: agri-ai 铺平至仓库根目录 + .gitignore 清理` 已通过 PR #1 进入 main）。
- 远程仅 3 个引用：`origin/main`、`origin/codex/acis-implementation-plan`、`origin/HEAD`；`sprint-04.5B-capability-contract` 上游已 `gone`。
- 结论：**95% 的本地分支是已合并的会话分支残留**；`logs/p6-wt` 是唯一登记的额外工作树，其分支已 0 提交领先 main → 可安全剪除（[推测]）。

### C4.4 仓库体积与最大跟踪文件

| 项 | 值 |
|---|---|
| `.git` 目录 | **255.2 MB / 758 文件** |
| `git count-objects -vH` | 松散对象 667（1.55 MiB）；**5 个 pack，size-pack 253.34 MiB**；garbage 0 |
| 最大 pack | `pack-255cd6b…` **133.6 MB**、`pack-e3f3105…` **130.8 MB**；其余 3 个合计 <1.2 MB |
| 体积异常 | 工作树 HEAD 树 235 个文件、最大单文件仅 228,607 B（≈0.22 MB），与 253 MB pack 严重不匹配 → 大对象存在于历史而非当前树 [推测：早期上游/合并历史携带大二进制；`git log -- data/ results/ *.db .venv logs/` 均无大目录入库记录] |

最大 10 个跟踪文件（`git ls-tree -r -l HEAD`，按字节）：

| # | 路径 | 字节 |
|---|---|---:|
| 1 | `reports/phase6_baseline_20261023/raw_results.json` | 228,607 |
| 2 | `reports/phase6_ablation_20261024/raw_results_c0c2_seed43.json` | 133,191 |
| 3 | `reports/phase4_real_agent_consistency_20261017/stop_probe_logs/precheck_seed42/c1_all_on/runner/traces/d432f0d4….json` | 94,582 |
| 4 | `reports/phase6_sc43_20261024/raw_results_c1_seed43.json` | 73,894 |
| 5 | `reports/phase6_sc_20261023/raw_results_c1_seed42.json` | 66,016 |
| 6 | `benchmarks/capability_matrix.py` | 37,387 |
| 7 | `agents/judge_agent.py` | 34,288 |
| 8 | `ui/tui.py` | 21,992 |
| 9 | `docs/rfc/RFC001-System Architecture.md` | 21,933 |
| 10 | `src/openmetaphysics/evaluation/challenge_report.py` | 21,468 |

---

## C5 历史垃圾与临时产物规模

### C5.1 `logs/`（被 gitignore，4,178 文件 / 90.5 MB）

| 子目录 | 文件数 | 体积 | 性质（判断依据） |
|---|---:|---:|---|
| `phase4_2_real_agent/` | 469 | 15.4 MB | Phase 4.2-R 整轮运行产物（mtime 2026-09-01） |
| `phase4_2_r2/` | 459 | 15.2 MB | 同族运行产物 |
| `phase4_2_r3/` | 459 | 14.9 MB | 同族运行产物 |
| `phase4_2_r3_stress/` | 120 | 2.7 MB | 压力测试产物 |
| `phase4_2/` | 217 | 0.6 MB | Phase 4.2 运行产物 |
| `phase4_2_r2_diag/`・`_r2_preflight/`・`_r4_preflight/` | 4/4/10 | ~0.3 MB | 预检小样 |
| `delivery_audit_20261024/` | 736 | 13.1 MB | 交付审计：`env/` 448 文件 10.1 MB（含 `env/clean` **整仓副本** 125 py/115 md）、`eval/` 70、`flow/` 82、`tmp/` 130 |
| `phase6_baseline_20261023/` | 155 | 5.4 MB | Phase 6 基线 run 产物 |
| `phase6_ablation_20261024/` | 103 | 3.4 MB | Phase 6 消融 run |
| `phase6_ab_seed42_20261024/` | 103 | 3.5 MB | 同上（seed42 重复轮次） |
| `phase6_sc_20261023/`・`sc43_20261024/` | 53/52 | 1.9/1.8 MB | 自一致性采样 run |
| `phase6_redesign_20261023/`・`phase6_gateoff_20261024/` | 3/1 | ~0 MB | 小样 |
| `phase4_judge_recovery_20261019/` | 24 | 0.6 MB | Judge 恢复验证 |
| `p6-wt/` | 277 | 3.6 MB | **已登记 git worktree**（含 `.git` 文件），整仓检出 + AGENTS.md |
| `p6-exp/` | 384 | 6.0 MB | **整仓副本**（有 `README.md`/`AGENTS.md`/`orchestrator.py`/`context/KNOWN_DEBT.md`；122 py / 92 md） |
| `eng_audit_tmp*/`（tmp, tmp2, tmp3, tmp4, tmp5, tmp6, tmp_cleanup, tmp_planner） | 1/130/9/0/139/139/9/3 | ~1.1 MB | **沙箱/ACL 探针副本**：内容为 `pytest-of-lkl/pytest-0/...` 与 `torchinductor_lkl` 空目录骨架 + pytest 生成物（如 `test_write_capability_docs0/CAPABILITY_MATRIX.md`），用于复现 `tmp_path` ACL 问题 |
| `logs/` 根散落文件 | 114 | ~0.5 MB | **82 个一次性 `.py` 审计/重算脚本**（`_manifest_check.py`、`_stats.py`、`_schema` 系列、`analyze_baseline.py`…）+ 11 `.ps1` + 8 `.txt` + 7 `.json` + 3 `.bin`（`status_z*.bin` = git status 二进制快照）+ `_wip.diff` + `gitconfig.local` |

关键事实：
- `logs/` 下共 **483 个 `.py` / 489 个 `.md`**，其中多数来自上述**整仓副本**而非独立文件（`p6-exp`+`p6-wt`+`delivery_audit/env/clean` 各含 120~125 个 py）。
- **3 份 `AGENTS.md`**（各 1,340 B / 28 行）位于 `logs/p6-wt/`、`logs/p6-exp/`、`logs/delivery_audit_20261024/env/clean/`，与已删除的根 AGENTS.md **字节级同一 blob**（详见 C7）。
- `logs/gitconfig.local`（93 B）内容是 `[safe] directory = E:/knowledge_database/ACIS` + `[user] lkl/1605321557@qq.com` —— 说明项目侧曾用 `safe.directory` 规避 dubious ownership（本次盘点未修改任何 git 配置）。

### C5.2 根目录与其它垃圾

| 目标 | 规模 | 性质 | 证据 |
|---|---|---|---|
| `data/` | **266.0 MB / 191 文件** | 未跟踪数据：`Agriculture_KnowledgeGraph-master/` 245.4 MB/30 文件（`hudong_pedia.json` **110.9 MB**、47.0 MB、44.3 MB zip、16.0 MB zip、11.1 MB csv）、`evaluation/` 12.4 MB/155 文件、`agri.db` 1.79 MB、`eval.db` 6.7 MB、`.fuse_hidden0000*` 32 KB×2 | `Get-ChildItem data` |
| `results/` | **56.8 MB / 1,239 文件** | 历史实验运行输出（`ablation/ experiments/ suites/ traces/`+`metrics.csv`），被 gitignore | 目录统计 |
| `.mypy_cache/` | **153.1 MB / 155 文件** | mypy 缓存（体量异常大，单文件可达数十 MB） | 目录统计 |
| `.ruff_cache/`・`.pytest_cache/` | 162 / 6 文件 | 工具缓存 | 目录统计 |
| `__pycache__/`（根+各包） | **57 个目录**（0.2 MB 见于根） | 字节码缓存 | 目录计数（排除 .venv） |
| `pytest-of-lkl/`・`torchinductor_lkl/` | 0 可视文件，**枚举被拒绝访问（ACL）** | pytest `tmp_path` 遗留（`pytest.ini:4-6` 明确点名 `stray pytest-of-lkl/`） | `Get-ChildItem` 报 “Access to the path … is denied” |
| `.claude/` | `pytest_tmp_base`（拒绝访问）+ `worktrees/amazing-bardeen-551868/.claude/settings.local.json`(243 B) | **Claude 工作树残留**（分支 `claude/amazing-bardeen-551868` 已并入 main） | 目录列出 |
| `xx`（根） | 15,082 B / 214 行，**已被跟踪**（HEAD blob `f68e71e`） | **误入库的 `git diff --stat` 终端转储**：首行 `warning: in the working copy of '.gitignore', LF will be replaced…`，随后为 `文件 | +-` 统计与 ANSI 颜色码；末行含 `xx | 214 +` 自引用 | `xx:1-40`；`git ls-tree -r -l HEAD` 末行 |

可回收量估算 `[推测]`：logs 90.5 + results 56.8 + data 266.0 + .mypy_cache 153.1 + 缓存 ≈ **570 MB 工作区**；`.git` 再 repack/filter 后最多可再省 ~250 MB（取决于是否保留历史上游大对象）。

---

## C6 根目录污染与 `reports/` 分类

### C6.1 根目录（21 个文件 + 30 个目录）

| 文件 | 字节 | 判定 |
|---|---:|---|
| `orchestrator.py` | 14,759 | ✅ CLI 入口（README 三入口之一） |
| `workflow.py` | 7,861 | ✅ LangGraph 主图（README:72 引用） |
| `kg_adapter.py` | 20,549 | ⚠️ 合法模块但在根（`MODEL_AGENT_ORCH:177` 提及；属“铺平到根”遗留布局 `6a74817`） |
| `decision_semantics.py` | 3,781 | ⚠️ 同上（共享决策语义，`:49` 被 ADR-005 引用） |
| `_env.py` | 1,021 | ⚠️ 私有 helper 放根目录，语义不清 |
| `MODEL_AGENT_ORCHESTRATION.md` | 10,669 | ✅ 设计文档（但部分脱节，C3-20/21） |
| `README.md` | 13,467 | ✅ 现行事实源 |
| `xx` | 15,082 | ❌ **垃圾**（`git diff --stat` 转储，见 C5.2） |
| `LICENSE`・`Dockerfile`・`.dockerignore`・`docker-compose.yml`・`start.ps1`・`start.sh`・`pytest.ini`・`requirements*.txt`(3)・`.gitignore`・`.env.example` | — | ✅ 常规工程文件 |
| `.env` | 631 | ⚠️ 未跟踪本地密钥文件（gitignore 覆盖，本次未读取内容） |

其它：根目录**无 `AGENTS.md` / `CONTRIBUTING.md` / `pyproject.toml` / `setup.py` / `tox.ini`**（`Get-ChildItem` 与 `git ls-files` 双重确认）；`.claude/`、`.vscode/`（各 1 文件）与 3 个工具缓存目录未跟踪。

结构判断：项目是**扁平根布局**（`agents/`、`gateway/`、`rag/`… 与 `orchestrator.py`、`workflow.py`、`kg_adapter.py` 同级），因此根级 `.py` 不全是“污染”，真正的问题是 `xx` 与缺少 `pyproject.toml`。

### C6.2 `reports/`（36 文件 / 0.8 MB）分类

| 类别 | 文件 | 说明 |
|---|---|---|
| **最终证据（README/reports-README 引用）** | `acceptance_20261024.md`(7,180)、`experiment_audit_20261024.md`(10,276)、`delivery_eval/summary.{md,json}`、`phase6_baseline_20261023/{baseline_analysis.md, raw_results.json}`、`phase6_redesign_20261023/{final_evidence,implementation_status}.md`、`phase6_sc_20261023/raw_results_c1_seed42.json`、`phase6_sc43_20261024/raw_results_c1_seed43.json`、`phase6_ablation_20261024/raw_results_c0c2_seed43.json`、`phase4_evaluation_metric_contract_audit.md`、`phase4_evaluation_reliability_repair.md`、`phase4_judge_recovery_20261019/{judge_recovery_report,provenance_addendum}.md`、`phase4_2_real_agent/diagnosis_judge_fallback.md` | 共 ~19 份，均在 `reports/README.md:8-20` 有索引 |
| **归档** | `archive/phase4/`(7)、`archive/phase4_2/`(3)、`archive/phase4_judge_recovery/`(6) | 历史摘要，`reports/README.md:22-26` 声明 accuracy=factor coverage |
| **一次性中间产物 / 未登记** | `document_cleanup_manifest.csv`(87,539 B，**未跟踪且被 ignore**)、`public_docs_cleanup_20261024.md`(12,206)、`phase4_real_agent_consistency_20261017/stop_probe_logs/…/traces/d432f0d4….json`(94,582，单条 trace 放在 7 层深目录) | 建议移入 logs 或删除（[推测]） |
| **原始大 JSON** | 上述 5 份 `raw_results*.json`，合计 ≈ 596 KB | 与 `reports/README.md:36` 的“已移出”声明冲突（D6） |

---

## C7 工程规范现状（logs 内 AGENTS.md 内容要点）

现状：**根目录没有任何工程规范文件**（无 `AGENTS.md`、`CONTRIBUTING.md`、`pyproject.toml`、`setup.cfg`、`.pre-commit-config.yaml`）；唯一可执行的规范只存在于 `logs/` 副本中。

证据链（完整）：
1. `3cd33ca docs: establish per-session branch + archive conventions (AGENTS.md)` —— 规范首次建立（2026-08-10）。
2. `f1c7e98 更换线程`（2026-10-24）删除根 `AGENTS.md`：`xx:4` 即该 diff 的统计 `AGENTS.md | 28 -`，`git show --name-status f1c7e98` 中为 `D AGENTS.md`。
3. 历史 blob `3cd33ca:AGENTS.md` = `962ae16352ed2b8d615eee93e6b3c40b7f39c285`，**1312 B**；
   `logs/p6-wt/AGENTS.md`、`logs/p6-exp/AGENTS.md`、`logs/delivery_audit_20261024/env/clean/AGENTS.md` 的 `git hash-object` **全部返回同一 hash `962ae16…`**（磁盘 1,340 B = LF→CRLF 后 28 行各 +1 B）。→ 三份副本就是被删除的根规范的逐字节副本。

该规范（28 行，3 条约定）实际规定了：

| # | 规则 | 要点 |
|---|---|---|
| 1 | 每轮对话在独立分支上进行 | 开始前 `git checkout main && git pull && git checkout -b work/<日期>-<主题>`；本轮所有代码/文档只在该分支；不得直接提交/推送 `main`，不得自行 merge |
| 2 | 每轮对话结束时归档 | 提交后在 `context/archive/<YYYYMMDD>-<主题>.md` 写归档记录，固定 5 字段：主题与目标 / 变更文件清单（增删改）/ 变更摘要 / 验证结果（pytest、ruff、mypy）/ 分支名与提交号；中途被打断也要提交并注明“未完成” |
| 3 | 用户把控合并与下一步 | 合并、删分支、进入下一步均由用户决定；完成后报告分支名、提交内容、归档位置并等待指示，不主动推进 |

规范的执行痕迹与失效点：
- **规则 1 执行良好**：本地 20 条 `work/<日期>-<主题>` 分支、命名完全符合规范（C4.3）。
- **规则 2 曾执行**：历史提交大量 `docs: archive <日期> <主题>` / `docs(archive):`（如 `10df9c1`、`39df292`、`d4197f3`、`6420e34`）。
- **规则 2 现已失效**：归档目标 `context/archive/` 连同 `context/template/` 在 `f1c7e98` 被整体删除（`xx:21-40`），规范文件本身也被删 → 后来者/Agent 无法发现该约定（本次盘点只能在 `logs/` 残片中找到）。
- 其它缺失规范：无 lint/type 配置（`pyproject.toml` 缺失，ruff/mypy 只能跑默认规则）；KNOWN_DEBT 自认 `judge_agent.py` 有 I001/BLE001/S110 告警、`orchestrator.py` E402（`context/KNOWN_DEBT.md:43-45`）——与“无统一配置”一致。

---

## C8 未经确认事项 `[待确认]`

| # | 事项 | 为什么未确认 |
|---|---|---|
| 1 | README 的 **344 用例 / 342 passed / 2 skipped** | 未运行 pytest（会写 `.pytest_cache`，越过只读约束）；静态只能数到 316 个 `def test_` + 9 处 `parametrize`；且 KNOWN_DEBT 记 340/3，两份现行文档本身冲突（D1） |
| 2 | `.git` **253 MB pack 的构成** | 工作树最大跟踪文件仅 228 KB；两次根提交历史大对象无法在不落地索引/不捕获输出的前提下逐项排序，故仅能判定“历史大二进制” [推测] |
| 3 | `pytest-of-lkl/`、`.claude/pytest_tmp_base/` 的内容与体积 | 目录枚举被 ACL 拒绝（`Access … denied`），可见文件数为 0；`pytest.ini:4-6` 仅说明它是遗留目标 |
| 4 | `logs/eng_audit_tmp1..6` 与 `phase4_2_*` 各目录的精确用途 | 仅按命名、内含物（`pytest-of-lkl/pytest-0/…` 输出）与 mtime 推断为“沙箱 ACL 探针/历史 run 产物”，未逐目录读日志正文（含巨型 JSON，按要求折叠） |
| 5 | README:130 示例置信度 72% vs `reports/delivery_eval` 同案 74% | 两处运行配置（RAG/KG/持久化开关）不同，无法判定是否同一条件 |
| 6 | `MODEL_AGENT_ORCHESTRATION.md` 的最终定位（设计参考 vs 应归档） | 无任何现行文档明示其状态；`README.md:204-213` 文档导航**未列出**它 |
| 7 | `docs/ARCHITECTURE_DECISIONS.md:11` 的 `last_updated: 2026-07-10` 是否为有意（ADR 追加不改 front matter） | 无法从仓库判断作者意图 |
| 8 | 未提交改动（`README.md`、`docs/DEMO_RUNBOOK.md`、`tests/test_planner.py`）的意图 | 只读盘点不判断工作树改动归属；它们使 README 与 HEAD 版相差 4,449 B，评审时需注意以工作树为准还是以 HEAD 为准 |
