# ACIS 项目健康诊断（阶段 2：Diagnosis）

> **诊断对象**：`E:\knowledge_database\ACIS` ｜ **基线**：`main @ d2fa727`（2026-10-24 21:19 +0800）｜ **日期**：2026-11-01
> **输入**：阶段 1 盘点结果 → [PROJECT_INVENTORY.md](PROJECT_INVENTORY.md)（证据附录 `reports/_parts/*.md`）
> **只读声明**：本轮未修改/删除/移动任何项目文件，未执行 git 写命令、未安装依赖、未构建。本文件与 `PROJECT_INVENTORY.md` 为唯一写入。
> **判定口径**：`状态` = KEEP / MERGE / DELETE / REFACTOR / UNCLEAR；`风险` = 高 / 中 / 低（高 = 影响可复现性、数据安全或 30 天内会咬人）。
> **标注**：`[待确认]` 证据不足；`[推测]` 启发式推断。

---

## 0. 总裁决（一页）

**评级：B−（可演示、可审计，但尚不可维护）**

| 判断 | 结论 |
|---|---|
| **它是什么** | 一个**完成度很高的工程原型**：决策链路真实可跑（CLI/TUI/API 三入口共用单一编排器），可解释性与证据留痕（10 阶段 Trace + SQLite 审计 + EVIDENCE_LEDGER）明显高于同类原型。 |
| **它缺什么** | 缺的是**工程基线与仓库收口**，不是业务代码：无打包（19 处 `sys.path` 打补丁）、依赖与配置声明漂移、Git 与磁盘卫生失管（95.9% 文件未跟踪、`.git` 255 MB）、文档 9 处硬冲突且无单一事实源。 |
| **最危险的一件事** | `logs/`（被 `.gitignore` 忽略、90.5 MB）内部藏着**一个被版本库登记的 git worktree**，且带 3 处未提交修改。任何"清理磁盘"的直觉操作都会留下悬挂 worktree 并丢失那 3 处状态。 |
| **最该先做的一件事** | **不是重构代码**，而是把三件事钉死：①事实源唯一化（文档/测试数字）②仓库卫生与 entry 顺序可控（worktree → logs → data）③打包与测试可复现（`pyproject.toml` + `pytest` 进依赖）。这三件做完，其余重构才有稳定基线。 |
| **是否该继续投入** | **是**，但前提是先做一次"收口"，而不是继续加功能。当前新增功能的边际收益会被债务稀释。 |

**一句话**：业务侧是"可交付演示"，工程侧是"沙盒"，两者之间的落差就是本轮要做的事。

---

## 1. 健康度评分卡

| 维度 | 等级 | 依据（证据见 §2） | 趋势判断 |
|---|:--:|---|---|
| 核心链路可运行性 | **A−** | 三入口真实存在且共用 `AgentOrchestrator`（`orchestrator.py:112`）；规则链路离线可跑（`tests/test_cli_smoke.py:40-48` subprocess 实跑） | 稳定 |
| 可解释性 / 可审计性 | **A** | 固定 10 阶段 Trace（`trace/types.py:36-47`）+ `decisions` 表（`storage/db.py:16`）+ 故障留痕 `fallback_reason_code`（`agents/judge_agent.py:73`） | 稳定 |
| 降级鲁棒性 | **A−** | 可选依赖全部 `try/except` 降级并记录原因（视觉/异常检测/校准/LLM Judge 四类） | 稳定 |
| 结构清晰度 | **C** | 两套布局并存（扁平根 + 20 余个包）、`src/` 半迁移、`agents/` 唯一缺 `__init__.py` | 缓慢恶化 |
| 打包与可安装性 | **D** | 无 `pyproject.toml`/`setup.py`；**19 处 `sys.path.insert`** 是唯一模块解析手段 | 未动 |
| 依赖与配置卫生 | **C−** | 5 个在用依赖未声明；`pillow` 声明未用；`.env.example` 缺 10 键；`.dockerignore` 缺 `logs`（构建上下文 90.3 MB） | 缓慢恶化 |
| 测试有效性 | **B−** | 26 文件 / 316 `def test_` / 342 collected；但 `rag/ kg/ rule_engine/ ui/` **零覆盖**；2 个永久 skip 指向已删脚本 | 尚可但盲区集中 |
| 文档可信度 | **B** | README 22 项机械核对 **18 ✅ / 2 ❌ / 2 ⚠️**（自述诚实度高）；但 9 处文档间硬冲突、单一主题平均 3.2 份承载 | 有漂移风险 |
| 仓库 / 磁盘卫生 | **D** | 95.9% 文件未跟踪；`.git` 255 MB 与 235 个跟踪文件严重不匹配；`xx` 误入库；90.5 MB `logs/` 含 3 份整仓副本 + 1 个 worktree | 持续恶化 |
| 变更流程与规范 | **D** | 根 `AGENTS.md` 已被删除（`f1c7e98`），其规定的归档目录同批删除；23 个本地分支残留 | 规范已失效 |
| 债务可见性 | **A** | `context/KNOWN_DEBT.md`（12 项）+ `context/EVIDENCE_LEDGER.md`（E007–E020，含 `Untested`/`Superseded` 状态）——**这是本项目最被低估的资产** | 稳定 |

**综合**：**B−**。"能力维度"集中在 A 区，"基线维度"集中在 C/D 区——典型的**单点强、底盘弱**结构。修复优先级应压在 D 区（便宜、可逆、收益确定），而不是动 A 区。

---

## 2. 诊断明细（34 项）

### 2.1 核心运行时 —— 应当保护，不要动

| 编号 | 对象 | 状态 | 风险 | 证据 | 判定说明 |
|---|---|:--:|:--:|---|---|
| **H-01** | 编排主干与三入口（`orchestrator.py` + `workflow.py` + `gateway/app.py` + `ui/tui.py`） | **KEEP** | 低 | `orchestrator.py:112,138-146,165-182`；`gateway/app.py:20,25`；`ui/tui.py:46,518` | 三入口复用同一 `AgentOrchestrator`，不存在两套业务实现（`README.md:89` 的声称成立）。这是本仓最值钱的部分 |
| **H-02** | LangGraph 主图 → 规则编排的回退，以及 LLM 故障分类留痕 | **KEEP** | 低 | `orchestrator.py:165-182`（异常→`run_rules` 并写入 `missing_evidence`）；`agents/judge_agent.py:73`（`fallback_reason_code`）、`:146`（脱敏日志）；`utils/judge_runtime.py` | "回退对调用方透明"且回退原因可区分（`judge_mode=rules` vs `deepseek`），避免把规则结果当模型结果上报 |
| **H-03** | 10 阶段统一 Trace + SQLite 决策审计 | **KEEP** | 低 | `trace/types.py:36-47`（STAGE_ORDER 恰 10 项）、`trace/exporter.py:37`；`storage/db.py:16`；`gateway/app.py:62,68` | 可解释性基础设施齐全，CLI 一条命令导出（`--trace-out`） |
| **H-04** | 可选依赖的降级边界（视觉 / 异常检测 / 校准 / LLM） | **KEEP** | 低 | `agents/vision_agent.py:13-17`、`agents/vision.py:114-120`；`rule_engine/sensor_anomaly.py:89-101,104-134`；`utils/confidence_calibration.py:73-80` | 缺库/缺 key 时不崩、可降级、并把降级状态写进证据（`_IF_STATUS`/`_CHRONOS_STATUS`）。这使 `requirements.docker.txt` 的裁剪才是安全的 |
| **H-05** | 债务与证据台账（`context/KNOWN_DEBT.md`、`context/EVIDENCE_LEDGER.md`） | **KEEP** | 低 | `KNOWN_DEBT.md:1-46`（12 项）；`EVIDENCE_LEDGER.md:10-25`（E007–E020，含 `Untested`/`Superseded by E015`） | 罕见的负分自述文化：明确写"架构收益未证明""1 例×2 seed 不足以外推"。**不要为了"整洁"删掉** |

### 2.2 结构 —— 最需要人类拍板的地方

| 编号 | 对象 | 状态 | 风险 | 证据 | 判定说明 |
|---|---|:--:|:--:|---|---|
| **H-06** | 扁平根布局：5 个核心模块平铺在根（`orchestrator/workflow/kg_adapter/decision_semantics/_env`）与 20 余个包同级 | **UNCLEAR** | 中 | `git log` `6a74817 "refactor: agri-ai 铺平至仓库根目录"`；10 处 import 指向根模块（见盘点 §9.1） | **这是有意重构的结果，不是事故**。迁移到 `src/acis/` 布局收益真实但成本 L/XL（要动 10 处 import + 19 处 `sys.path` + 全部测试）。是否值得取决于项目下一步定位，需人决策 |
| **H-07** | **无打包**：无 `pyproject.toml`/`setup.py`/`setup.cfg`；模块解析靠 **19 处 `sys.path.insert`** | **REFACTOR** | **高** | 文件存在性验证；注入点：`tests/conftest.py:8,11`、`gateway/app.py:9`、`ui/tui.py:17`、`ui/web_app.py:15`、`kg/mcp_server.py:27`、`evals/` 4 处、`scripts/` 4 处、`utils/generate_calibration.py:19`、`src/…/challenge_report.py:50` | **结构债的根**：它导致 E402 告警、导致每个入口都得自己垫路径、导致 `src/` 只能靠测试注入、导致 IDE/CI 静态分析不可靠。修它收益最大、且**不需要动业务代码** |
| **H-08** | `agents/` 是唯一缺 `__init__.py` 的包（隐式命名空间包） | **REFACTOR** | 低 | 目录实测缺失；`orchestrator.py:55-68` 仍能 import；其余 15 个包均有 `__init__.py` | 当前可用，但若 `site-packages` 出现同名 `agents` 会被遮蔽；一致性上也说不通 |
| **H-09** | `src/openmetaphysics/` 半迁移包（仅 4 文件，Phase 4 评测工具；`openmetaphysics` 仅经 `conftest.py` 注入才可 import） | **UNCLEAR** | 中 | `src/openmetaphysics/__init__.py:1`；`tests/conftest.py:10-11`；`scripts/generate_stability_report.py:41`；`KNOWN_DEBT.md:21-23` 仍在引用它 | 第三种布局（根扁平 + 包目录 + src 包）并存。要么并入 `benchmarks/`/`evals/`，要么真正纳入打包；现状"半挂载"最差 |
| **H-10** | **两套 MCP Server 暴露同名工具与资源**：`kg/mcp_server.py`（9 tool）与 `rag/knowledge_base.py`（5 tool）都有 `search_disease` 与 `knowledge://diseases` | **MERGE** | **高** | `kg/mcp_server.py:144-145,428-429` vs `rag/knowledge_base.py:371-372,535-536`；`kg/mcp_server.py:41` 还引用**已不存在**的 `knowledge_mcp_server.py` | 两个 server 各自独立演进 → 同名工具的语义/返回结构必然漂移；对外部调用方是**不可见的破坏性风险**。必须先定"哪个是权威" |
| **H-11** | 两套能力矩阵生成器写同一对产物 `CAPABILITY_MATRIX.md` + `COVERAGE.md` | **MERGE** | 中高 | `benchmarks/taxonomy.py:258-262,271-275,300-301` vs `benchmarks/capability_matrix.py:277-284,447,563-567`；两者都有 `__main__` | **谁最后跑谁生效**，无文档说明权威；产物已入库（`benchmarks/CAPABILITY_MATRIX.md` 等），一旦不一致无法判真 |
| **H-12** | `rag/knowledge_base.py` 混装"MCP Server + 领域知识库（DISEASE_DB/CROP_MAP/诊断函数）" | **REFACTOR** | 中高 | 文件头 `:1-7` 自述 MCP Server；但 `kg_adapter.py:34`、`rag/retriever.py:18`、`agents/{pathology,cultivation,kg}_agent.py:4` 都从它 import 领域函数 | 生产诊断链路**依赖一个 MCP server 模块**：`from mcp.server.fastmcp import FastMCP` 是顶层 import，意味着核心链路隐式硬依赖 `mcp` 包。职责应拆成"知识数据"与"MCP 适配层"两部分 |

### 2.3 依赖与配置

| 编号 | 对象 | 状态 | 风险 | 证据 | 判定说明 |
|---|---|:--:|:--:|---|---|
| **H-13** | 依赖声明缺口：`pytest`(18 处)、`matplotlib`、`PyYAML`、`chronos`、`huggingface_hub` | **REFACTOR** | 中 | `requirements*.txt` 三份均无；使用点：`tests/*`、`experiments/figures.py:22`、`experiments/schema.py:21`、`rule_engine/sensor_anomaly.py:113-114` | 直接后果：按 `README.md:99-101` 装完依赖**不能跑测试**（pytest 不在依赖里）。chronos 未声明 → 该预测层**必然降级**（`.venv` 内也没有） |
| **H-14** | `pillow` 声明但全仓零 import | **DELETE** | 低 | `requirements.txt:23`；`import PIL` 命中 0 | 疑似历史遗留 `[推测]`；删除前需确认非常规路径间接使用（如 streamlit 运行期） |
| **H-15** | `.dockerignore` 缺 `logs`（与 `.gitignore:41`、自身"保持同步"注释矛盾） | **REFACTOR** | 中 | `.dockerignore:1-20` 无 `logs`；实测构建上下文 **4,209 文件 / 90.3 MB**，其中 `logs/` 4,177 文件 / 90.5 MB | 每次 `docker build` 都要搬运 90 MB 无用上下文，且其中含 3 份整仓源码副本 —— 构建慢 + 泄漏面扩大 |
| **H-16** | Python 版本双轨：`README.md:71,95` 称 3.13，`Dockerfile:2` 固定 `python:3.11-slim` | **UNCLEAR** | 中 | `.venv/pyvenv.cfg` `version_info = 3.13.3`；`Dockerfile:2` | 哪个是目标运行时要人定；若 3.13 是事实，则容器已落后两个 minor（且 `context/KNOWN_DEBT.md:13-14` 自述 Docker 从未构建验证） |
| **H-17** | compose 硬编码 `NEO4J_PASSWORD=agriai2026`（`:23,58`）+ `.:/app` 绑定挂载（`:10`）遮蔽镜像并让宿主 `.env` 进入容器 | **REFACTOR** | 中 | `docker-compose.yml:10,23,27-29,58`；`.env.example:58` 默认值为 `neo4j` | 密钥入库（compose 被跟踪）；凭据与模板不一致；挂载使镜像构建物在运行期失效，`docker build` 白做 |
| **H-18** | 配置双向漂移：`.env.example` 缺 **10** 个代码实际读取的键；`.env` 含 **2** 个源码不读的键（`OPENCODE_*`） | **REFACTOR** | 低 | 缺失键见盘点 §4.2 C-1；`utils/judge_runtime.py:147-156` 只用 host 推断 provider | 新环境按模板配置会得到"默认行为"，且 `AGRI_AI_KG_DRAFTS_*` 这类开关完全不可发现 |
| **H-19** | 无 lint / type / 格式化配置（无 `pyproject.toml`/`setup.cfg`/`tox.ini`/`.pre-commit-config.yaml`） | **REFACTOR** | 中 | 文件存在性验证；`KNOWN_DEBT.md:42-45` 自认存在 ruff/mypy 告警但"未在 MVP 中扩大修复" | 无配置 → `ruff`/`mypy` 只能跑默认规则 → 告警长期悬挂、无法作为门禁。与 H-07 同根，可一并解决 |

### 2.4 测试

| 编号 | 对象 | 状态 | 风险 | 证据 | 判定说明 |
|---|---|:--:|:--:|---|---|
| **H-20** | 测试数字三处口径冲突：README「344 用例 / 342 passed + 2 skipped」、`KNOWN_DEBT`「340 passed / 3 failed」、实测「342 collected」 | **REFACTOR** | 中 | `README.md:78,169,171,198`；`context/KNOWN_DEBT.md:8-10`；`pytest --collect-only` = 342 | 差额 2 恰等于 2 个模块级 skip `[推测]`。**这是文档可信度的锚点问题**：连"多少测试通过"都无法唯一回答，其他数字的引用都会打折扣。需一次实跑定案并回写单一处 |
| **H-21** | 覆盖盲区：`rag/`、`kg/`、`rule_engine/`、`ui/` **零测试覆盖** | **REFACTOR** | 中高 | 按 import 映射（盘点 §5）；`kg_adapter.py` 的 Neo4j 路径、`rag/knowledge_base.py`、`rule_engine/sensor_anomaly.py` 三层检测全部无测试 | 这四块恰好是"外部依赖多、最容易静默失败"的部分（Neo4j/Qdrant/模型缓存）。它们是**下次改动的最大回归风险源** |
| **H-22** | 2 个永久 skip：测试指向已删除的 `scripts/run_phase4_2*.py` | **DELETE** | 低 | `tests/test_phase4_harness_runtime.py:9-13`、`tests/test_phase4_reliability.py:11-16`（注释明写 "removed in f1c7e98"） | 永久跳过 = 永久噪音；且它们是"344 vs 342"混乱的来源之一 |

### 2.5 Git 与仓库卫生 —— 风险最集中区

| 编号 | 对象 | 状态 | 风险 | 证据 | 判定说明 |
|---|---|:--:|:--:|---|---|
| **H-25** | `logs/`（4,177 文件 / 90.5 MB）含 **3 份整仓源码副本** + 82 个一次性脚本 + git status 二进制快照 | **DELETE** | **高** | 盘点 §11.2 逐目录表；`logs/delivery_audit_20261024/env/clean`(125 py)、`p6-exp`(122 py)、`p6-wt`(120 py) | 危害不只是占空间：它**污染全仓 grep/静态统计**（实测 `mcp` 词匹配 185 次 vs 源码真实 import 3 次）。任何基于"全仓搜索"的判断都会被误导 |
| **H-26** | `logs/p6-wt/` 是**被版本库登记的 git worktree**，且带 3 处未提交修改 | **DELETE** | **高** | `git worktree list` → `18abe26 [work/20261023-phase6-arch-redesign]`；`git -C logs/p6-wt status --porcelain` = 3 项；该分支 0 提交领先 main | **顺序强依赖**：必须先 `git worktree remove`（写操作）再删目录；直接删会留悬挂注册并丢状态。分支已全并入 main，技术上可弃，但 3 处未提交修改**必须先人看** |
| **H-27** | `data/` 266 MB，其中 245.4 MB 是 **vendored 第三方 GitHub 仓库**（`Agriculture_KnowledgeGraph-master`，含 110.9 MB 单 JSON + 4 个 zip） | **UNCLEAR** | 中 | `data/…/hudong_pedia.json` 110.9 MB 等；`scripts/import_agrikg.py` 消费它 | 它是 AgriKG 导入的源数据，删了就得重下；但"把第三方仓库整个塞进 data/"不是好形态。是 Move-out（仓库外归档）还是保留，取决于是否还要重跑 `import_agrikg` |
| **H-28** | `.git` **255.2 MB**（`size-pack` 253.34 MiB，两个 130+ MB pack），而当前树只有 235 个文件、最大单文件 0.22 MB | **UNCLEAR** | **高** | `git count-objects -vH`；`git ls-tree -r -l HEAD` 最大值 228,607 B | 大对象在**历史**里（`[推测]` 早期上游/合并携带）。清理需 `filter-repo` 类**历史重写**（破坏性、需全员协调），必须人决策；不清理则 clone/备份成本持续 |
| **H-23** | 根 `xx`（15,082 B）**被 git 跟踪**，内容是 `git diff --stat` 终端转储（含 ANSI 颜色码） | **DELETE** | 低 | `git ls-files` 含 `xx`；`xx:1-40`；末行 `xx | 214 +` 自引用 | 无意义文件进了版本库，且把一次大清理的删除清单留在根目录。删除需 `git rm`（写操作），并顺手加 `.gitignore` 族规则防复发 |
| **H-24** | **3 个已修改未提交**的跟踪文件：`README.md`(+87)、`docs/DEMO_RUNBOOK.md`(+30)、`tests/test_planner.py`(−17/+14) | **UNCLEAR** | 中 | `git status --porcelain`、`git diff --stat` | 工作树 ≠ HEAD。`README.md` 工作树版比 HEAD 大 4,449 B ⇒ **所有以 README 为证据的结论都需声明口径**。`tests/test_planner.py` 的改动还会影响"测试全绿"的可复现性。归属与意图必须人来定 |
| **H-29** | 23 个本地分支中 22 个已并入 main（大量 `work/<日期>-<主题>` 会话分支残留）；另 1 个未合并 `codex/acis-implementation-plan`（领先 1 提交 `6de83b2 Save changes to tui.py`） | **DELETE**（已并入部分）/ **UNCLEAR**（未合并部分） | 低 / 中 | `git branch -a -vv`；`git rev-list --count main..…` | 已并入分支可批量剪除（低风险，纯本地）。未合并那条只领先 1 个 `tui.py` 提交，需人判断是要还是丢 |
| **H-30** | 95.9% 的磁盘文件未跟踪（5,681 vs 235），全部由 `.gitignore` 覆盖 | **KEEP**（策略正确）/ 需收口 | 中 | `.git/index` vs 磁盘实测；`.gitignore:38-46` 明确忽略 `data/logs/results` | 忽略策略本身是**对的**（本地数据不该入库）。问题在**没人清理**，导致"本地状态"成为不可复现的黑箱 |

### 2.6 文档

| 编号 | 对象 | 状态 | 风险 | 证据 | 判定说明 |
|---|---|:--:|:--:|---|---|
| **H-31** | **9 处文档间硬冲突**（D1–D9）：测试数字、作物数量、ADR 状态、谁是事实源、已删文件指针、raw JSON 是否移出、architecture-state 自称唯一源、失效路径、AGENTS.md 被删 | **MERGE** | 中 | 盘点 §7.3 全表（D1–D9 逐条带行号） | 单看每条都不致命，合起来构成"**任何引用都可能踩到已失效声明**"。其中 D3（ADR-005 Accepted vs 文末称 Proposed）、D6（声明已移出但 5 份仍在库）是硬伤 |
| **H-32** | 无单一事实源：同一主题平均 **3.2 份**文档承载（测试数字 8 份、能力边界 5 份、accuracy 口径 4 份） | **MERGE** | 中 | 盘点 §7.2 矩阵 | 与 H-31 同因：多点声明必然漂移。README 的可核对项准确率其实很高（18/22），说明**问题不是不诚实，而是复述层太多** |
| **H-33** | 工程规范 `AGENTS.md` 已被删除（`f1c7e98`），其规定的归档目录 `context/archive/` 同批删除；现仅存 3 份 `logs/*/AGENTS.md` 副本（同一 blob `962ae16`） | **REFACTOR** | 中 | `xx:4`；3 份副本 `git hash-object` 同 hash；规范内容 3 条（每轮独立分支、结束时 5 字段归档、用户控合并） | **规范实际已失效但遗迹仍在执行**：20 个 `work/<日期>-<主题>` 分支正是它塑造的。后来者/Agent 无法发现该约定 → 行为不可预期。恢复或重写都需要人定 |
| **H-34** | `benchmarks/` 目录混放 5 份能力报告 md（`CAPABILITY_MATRIX.md`、`COVERAGE.md`、`CAPABILITY_CONSISTENCY_REPORT.md`、`CAPABILITY_ANNOTATION_SUGGESTIONS.md`、`CHALLENGE_SET_V1_REPORT.md`） | **MERGE** | 低 | `benchmarks/` 文件清单；其中 2 份是 `__main__` 生成物 | 代码目录承担文档职责；且生成物（`CAPABILITY_MATRIX.md`/`COVERAGE.md`）被跟踪，与 H-11 的"双写"叠加后更难判真 |

### 2.7 规模与坏味道

| 编号 | 对象 | 状态 | 风险 | 证据 | 判定说明 |
|---|---|:--:|:--:|---|---|
| **H-35** | 12 个 >500 行文件（最大 `benchmarks/capability_matrix.py` 987 行）；`agents/judge_agent.py` 单类 575 行；`_run_llm_judge` 121 行 | **REFACTOR** | 中 | 盘点 §10.1；`agents/judge_agent.py:86,340` | 集中在"评测/矩阵"与"Judge"两块。Judge 是决策核心，575 行单类已到"改一处要读全文"的程度 |
| **H-36** | `except Exception` 45 处（多数带 `# noqa: BLE001` 且属有意降级边界）；静默吞异常 2 处（`ui/web_app.py:148` `pass`、`debate/engine.py:16` `return None`） | **KEEP**（45 处）/ **REFACTOR**（2 处静默） | 低 | 盘点 §10.3 | 45 处不是债而是**设计**（降级边界应宽）。真正要修的是 2 处真静默——尤其 `debate/engine.py:16` 在核心链路里 |
| **H-37** | 魔法数（置信度阈值/降权系数）散落：`workflow.py:178`、`judge_agent.py:264,295,542-595`、`debate/critic.py:151-152,189`、`planner/planner.py:94` | **REFACTOR** | 低 | 同上 | 部分已可经环境变量覆盖（`AGRI_AI_MEMORY_GATE_MIN_CONF` 等），其余写死 → 调参即改代码 |
| **H-38** | `bare except:` **0 处**；硬编码绝对路径 **0 处**；注释掉的大段代码 **0 处**；代码内 TODO 仅 **3 处** | **KEEP** | — | `rg` 全仓验证 | **正面结论**：历史 lint 清偿（`0111465`）有效，没有"注释掉旧实现"的常见腐化模式。这条要写进报告，避免误判项目"很脏" |

---

## 3. 高风险深潜（Top 5，按"何时会咬人"排序）

### R1 — `logs/` 里的 git worktree（H-26 + H-25）
- **事实**：`git worktree list` 显示第二个工作树在 `logs/p6-wt`，分支 `work/20261023-phase6-arch-redesign @ 18abe26`，且 `git -C logs/p6-wt status --porcelain` 有 3 项未提交（`context/CURRENT_SPRINT.md`、`docs/ARCHITECTURE_DECISIONS.md`、`reports/phase6_redesign_20261023/final_evidence.md`）。
- **为什么危险**：`logs/` 被 `.gitignore:41` 忽略 ⇒ 任何"磁盘瘦身/清仓"直觉都会直接删它 ⇒ 留下 `.git/worktrees/p6-wt` 悬挂注册、丢失 3 处未提交状态、`git worktree list` 长期报错。
- **处置顺序不可交换**：先 `git worktree remove`（写操作，需批准）→ 再删目录。分支本身已 0 提交领先 main，技术风险低；**但 3 处未提交修改必须先人读**。

### R2 — 无打包 + 19 处 `sys.path`（H-07）
- **事实**：无 `pyproject.toml`/`setup.py`；19 个文件手工 `sys.path.insert`；`src/openmetaphysics` 只能靠 `tests/conftest.py:10-11` 注入才可 import。
- **为什么危险**：这是**所有其他结构问题的根**。它让"能否 import"取决于 CWD 和谁先跑、让静态分析不可信、让 E402 成为常态、让 `src/` 无法被正常消费。任何"加个模块/换个入口/上 CI"的动作都会再次踩它。
- **特点**：修复**不需要动业务逻辑**（加 `pyproject.toml` + 打包声明 + 清理 `sys.path`），是"高杠杆、低业务风险"的典型。

### R3 — 双 MCP Server 同名工具（H-10）
- **事实**：`kg/mcp_server.py:144-145,428-429` 与 `rag/knowledge_base.py:371-372,535-536` 都定义 `search_disease` 与 `knowledge://diseases`；后者还被生产诊断链路 import 领域函数。
- **为什么危险**：同名 ≠ 同语义。任一改动都会造成**对外契约的静默漂移**，而 MCP 侧零测试（H-21）。`kg/mcp_server.py:41` 还在注释里引用已删除的 `knowledge_mcp_server.py`，说明这块已经发生过一次"文件消失但引用留存"。

### R4 — `rag/knowledge_base.py` 混装职责（H-12）
- **事实**：它既是 `FastMCP("agri-knowledge")` 服务（`:5-7`），又是 `DISEASE_DB`/`CROP_MAP`/`diagnose_and_advise` 的唯一来源（`kg_adapter.py:34`、`rag/retriever.py:18`、3 个 agent 模块）。
- **为什么危险**：核心链路对一个 **MCP server 模块**形成硬依赖（`from mcp.server.fastmcp import FastMCP` 是顶层 import）。一旦想做"纯诊断库"或"关掉 MCP"，就会牵动整个链路；也让"数据"与"协议适配"无法分别演进。

### R5 — 事实源与数字不可唯一回答（H-31 + H-20 + H-32）
- **事实**：测试通过数有 3 个互斥版本；同一主题平均 3.2 份文档承载；9 处硬冲突；`README.md` 工作树版与 HEAD 版差 4,449 B。
- **为什么危险**：本项目最值钱的资产是**可审计性**（EVIDENCE_LEDGER/Trace/KNOWN_DEBT）。而"数字无法唯一回答"会直接侵蚀这个资产——审阅者一旦发现 344/342/340 三个数并存，就会对 E017、E019 等证据打个折扣。**这是对核心竞争力的伤害，不是排版问题**。

---

## 4. 一致性检查

### 4.1 命名一致性 —— 基本一致，例外可解释
- Agent 命名：15 个 Agent 中 13 个遵循 `<domain>_agent.py`；例外是 `vision.py`/`weather.py`（底层实现，非 Agent）与 `vision_agent.py`/`weather_agent.py`（薄包装）——`agents/vision_agent.py:14` 函数内延迟 import 证明这是**有意的包装模式**，不是命名混乱。
- 模块撞名：`types.py`×4、`report.py`×2、`schema.py`×2 —— 当前 import 路径唯一（`agents/types.py`、`planner/types.py`、`tool_router/types.py`、`trace/types.py`），**无实际冲突**，但增加误导入/误读成本。
- 包名：全部小写单数，一致。唯一例外 `src/openmetaphysics`——非 ACIS 领域命名，来自 Phase 4 外包工具包（H-09）。
- **判定**：命名层面 `KEEP`，无需大动；仅 `src/` 命名与归属需随 H-09 一并决策。

### 4.2 目录结构一致性 —— 规则不统一（唯一硬伤）
- 两套布局并存：**扁平根模块**（5 个）+ **顶层包**（20 余个）；再加第三种 `src/<pkg>/`。
- `agents/` 是**唯一没有 `__init__.py` 的包**（H-08），其余 15 个包都有 ⇒ 同一仓库内包定义规则不一致。
- **判定**：`REFACTOR`（低风险部分：补 `__init__.py`；中高风险部分：H-07/H-09 需人决策）。

### 4.3 代码风格一致性 —— 事实上统一，但无强制
- 127 个 `.py` 中 **99 个**使用 `from __future__ import annotations`（缺省 28 个分散在各包，每包 1–2 个）；**114 个**有模块 docstring；含 Tab 的文件 7 个。
- `bare except:` 0 处、硬编码绝对路径 0 处、注释掉的大段代码 0 处 ⇒ 风格**没有被腐化**。
- 但没有 ruff/mypy 配置（H-19）⇒ 一致性靠自觉维持，无门禁。
- **判定**：`KEEP` 现状 + `REFACTOR` 补门禁。

### 4.4 文档与实现一致性 —— 自述诚实，复述层漂移
- 22 项可机械核对：**18 ✅ / 2 ❌ / 2 ⚠️**。❌ 是 `MODEL_AGENT_ORCHESTRATION.md:181`「三种作物」（代码 4 作物）与 `:146` 失效路径 `agri-agent-mvp/scripts/...`。
- 正面：`README.md` 明确自曝"图片识别默认 mock、真实视觉效果未验证""Docker 未验证""不能证明完整架构优于裸基线"——**没有夸大**。
- 负面：`README.md` 的自我限制仍在多份文档被复述并走样（D1/D4/D6/D7）。**判定**：实现的 `KEEP`，复述层 `MERGE`。

### 4.5 配置与代码一致性 —— 双向漂移
- 代码读取 35 个环境变量键，`.env.example` 只覆盖 25 个（缺 10）；`.env` 有 2 个代码不读的键。
- `NEO4J_PASSWORD` 三处默认值不一致（compose `agriai2026` vs `.env.example` `neo4j` vs `.env` 实际值未读取）。
- **判定**：`REFACTOR`（H-18）。

---

## 5. 与 `context/KNOWN_DEBT.md` 的对账

**已登记 12 项 → 本轮独立核实：11 项成立、1 项需实跑定案。**

| 登记项 | 本轮核实 | 结论 |
|---|---|---|
| 全量测试未在普通环境验证（`:8-10`） | 与 `README.md:171` 直接冲突；实测 342 collected | **成立，且冲突未被登记** |
| 依赖锁平台绑定（`:11-12`） | `requirements-lock.txt:1-6` 自述一致 | 成立 |
| Docker 未验证（`:13-14`） | 本环境无 Docker；配置层另有 3 处问题（H-15/H-16/H-17） | 成立，但**低估了** |
| accuracy=factor coverage 字段未改名（`:18-20`） | `scripts/generate_stability_report.py:66-75` 确仍用历史字段 | 成立 |
| ECE 分箱浮点误差（`:21-23`） | `challenge_scorer.py:154` `int(conf/bin_size)` 仍在 | 成立 |
| SC 依赖 trace.agreement（`:24-25`） | 与 `EVIDENCE_LEDGER.md:23` 一致 | 成立 |
| Phase 6 覆盖不足（`:26-29`） | 与 `README.md:177-190` 一致 | 成立 |
| LLM Judge 端点/重试未统一（`:32-33`） | `utils/judge_runtime.py` 存在但 `AGRI_AI_JUDGE_*` 键未入模板（H-18） | 成立 |
| Harness vs 真实 Agent 一致性（`:34-35`） | — | 成立（未复核细节） |
| 静默失败路径（`:36-37`） | 实测静默吞异常 2 处 | 成立，且**可定位到 2 处具体行号** |
| 视觉/传感器为模拟（`:38-39`） | `README.md:33-34` 一致 | 成立 |
| 能力标注 52/64 未冻结（`:46-47`） | `benchmarks/capability_matrix.py:415-441` | 成立 |

**本轮新增、`KNOWN_DEBT.md` 未登记的债务（12 项）**：无打包 + 19 处 `sys.path`（H-07）；双 MCP Server 同名工具（H-10）；双能力矩阵生成器（H-11）；`rag/knowledge_base.py` 混装职责（H-12）；5 个在用依赖未声明（H-13）；`pillow` 未用（H-14）；`.dockerignore` 缺 `logs`（H-15）；git worktree 藏在 `logs/`（H-26）；`xx` 误入库（H-23）；95.9% 文件未跟踪且无清理（H-30）；`.git` 255 MB 与树不匹配（H-28）；`AGENTS.md` 规范被删（H-33）；文档 9 处硬冲突（H-31）。

> 评价：`KNOWN_DEBT.md` 的**研究/指标类债务记录质量很高**（口径混乱、样本不足都如实写），但**工程/仓库类债务几乎空白**——这正说明项目的注意力长期在"结果可信"而非"工程可维护"。

---

## 6. 证据可信度分级

| 等级 | 含义 | 本文中的例子 |
|---|---|---|
| **强**（可复现命令/精确行号） | 任何人重跑可得到同一结果 | 目录体积与文件数、`git count-objects -vH`、`git worktree list`、`git status --porcelain`、`git ls-files` 计数、行号引用、`pytest --collect-only` = 342、`rg` 计数（0 bare except / 45 except Exception / 3 TODO） |
| **中**（静态启发式） | 结论方向可靠，数值可能有 ± 偏差 | 超长函数行数（dedent 边界）、魔法数清单、覆盖率映射（按 import 粗判）、跨单元 import 边计数、文档重叠主题计数 |
| **弱**（推断） | 仅作假设，不可作为决策唯一依据 | `.git` 253 MB pack 的历史构成 `[推测]`；`344 vs 342` 差额成因 `[推测]`；`logs/` 各目录精确用途 `[推测]`；`fit_decision_calibration.py` 为一次性工具 `[推测]` |

**未确认清单（12 项）** 见 [PROJECT_INVENTORY.md §13](PROJECT_INVENTORY.md)。其中**不影响本轮结论**的 8 项（pack 构成、ACL 目录内容、logs 精确用途等）；**影响结论可信度的 4 项**为：测试真实通过数、344 口径、双 MCP 是否有意部署、未提交改动归属。

---

## 7. 转入阶段 3 前必须先由人类回答的问题（5 条，按阻塞程度）

> 本节**不属于阶段 2 交付物**（阶段 3 的待批准清单尚未产出），仅列出会决定"合并方案形态"的前置决策；否则阶段 3 会写出自相矛盾的清单。

1. **项目定位**：这是"要长期维护的工程基线"，还是"交付用的一次性演示原型"？——决定 H-06/H-07/H-09（布局与打包）是"必须做"还是"记录即可"。**阻塞面最大**。
2. **`logs/p6-wt` 里那 3 处未提交修改**（`context/CURRENT_SPRINT.md`、`docs/ARCHITECTURE_DECISIONS.md`、`reports/phase6_redesign_20261023/final_evidence.md`）要不要保留？——决定 H-26 的执行顺序与是否可整体清空 `logs/`。
3. **`.git` 255 MB 是否允许历史重写**（`filter-repo`）？——这是**唯一不可逆**的动作，必须显式授权或明确放弃。
4. **`data/Agriculture_KnowledgeGraph-master`（245 MB）** 是否还要用于重跑 AgriKG 导入？——决定它是"仓库外归档"还是"保留原址"。
5. **3 个未提交改动**（`README.md` / `docs/DEMO_RUNBOOK.md` / `tests/test_planner.py`）以工作树为准还是以 HEAD 为准？——决定后续所有文档结论的基准版本。

---

*阶段 1 盘点见 [PROJECT_INVENTORY.md](PROJECT_INVENTORY.md)；详细证据附录见 `reports/_parts/`。*
