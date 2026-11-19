# ACIS 整理合并方案（阶段 3：Consolidation Plan）

> **基线**：`main @ d2fa727`（2026-10-24 21:19 +0800）｜ **工作区**：3 个已修改未提交（`README.md`、`docs/DEMO_RUNBOOK.md`、`tests/test_planner.py`）
> **输入**：[PROJECT_INVENTORY.md](PROJECT_INVENTORY.md)（阶段 1）+ [PROJECT_HEALTH.md](PROJECT_HEALTH.md)（阶段 2，H-01～H-38）
> **性质**：**待批准清单**。本文件所有动作**均未执行**，逐项由人类勾选批准后方可落地。
> **已确认的前置决策**（不再讨论）：① 定位=长期维护的工程基线；② `logs/p6-wt` 先存档 diff → 再 `worktree remove` → 再清目录；③ `.git` 历史重写暂缓（C 档）；④ `data/Agriculture_KnowledgeGraph-master` 保留原址，仅补 `data/README.md`；⑤ 3 个未提交改动以工作树为准，先跑测试再提交。
> **证据约定**：每项标注对应 `H-xx`（诊断编号）与 `路径:行号`；`[待确认]`=证据不足，`[推测]`=推断。

---

## 0. 方案总览

| 档 | 项数 | 合计工作量 | 性质 | 前置条件 |
|---|:--:|---|---|---|
| **A 低风险快赢** | 18 | 约 2–3 人日 | 机械、可逆、无架构判断 | 仅需批准；A 链内部严格串行 |
| **B 需讨论** | 10 | 约 8–12 人日 | 涉及架构/接口/对外契约 | 需人类先答每项的决策问题 |
| **C 暂缓** | 11 | — | 依赖外部条件或证据保全 | 需触发条件达成 |

**A 档核心是一条不可换序的串行链**：

```
A1 存档 → A2 worktree remove → A3 清整仓副本 → A4 清探针与散落脚本
```

理由：`logs/p6-wt/` 是**被 `.git` 登记的工作树**（`git worktree list` → `18abe26 [work/20261023-phase6-arch-redesign]`），且含 3 处未提交修改（`git -C logs/p6-wt status --porcelain`）。跳过 A1/A2 直接删目录 → 留下 `.git/worktrees/p6-wt` 悬挂注册 + 丢失 3 处状态（H-26）。

---

## 1. A 档：低风险快赢

### 1.1 A 链（**必须按 A1→A2→A3→A4 顺序执行，不可并行**）

| 编号 | 动作 | 目标 | 对应 H | 理由 | 影响范围 | 风险 | 工作量 | 验证方式 | 回滚方式 |
|---|---|---|---|---|---|---|---|---|---|
| **A1** | 存档工作树状态：在 `reports/_archive/p6-wt_20261023/` 下写入 ①`git -C logs/p6-wt diff` 完整 patch ②3 个改动文件的原始快照 ③`README.md` 说明（来源分支 `work/20261023-phase6-arch-redesign`、基提交 `18abe26`、改动清单、恢复命令） | `logs/p6-wt/` → `reports/_archive/` | H-26 | 该 worktree 有 3 处未提交修改（`context/CURRENT_SPRINT.md`、`docs/ARCHITECTURE_DECISIONS.md`、`reports/phase6_redesign_20261023/final_evidence.md`），必须先于任何删除动作保全 | 新增 1 个目录（约 50 KB）；不改动被跟踪文件 | 低 | **S** | `Get-Content` 打开 patch 确认含 3 个 `diff --git` 段；`git apply --check` 在干净临时树验证 patch 可应用（**只 check 不 apply**） | 删除 `reports/_archive/p6-wt_20261023/` |
| **A2** | 注销工作树：`git worktree remove logs/p6-wt --force`（dirty 必须加 `--force`；A1 已保全） | `logs/p6-wt/` | H-26 | 该分支已 **0 提交领先 main**（`git rev-list --count main..work/20261023-phase6-arch-redesign` = 0），技术上无条件保留价值；但注册必须在目录删除前解除 | `.git/worktrees/` 少 1 项；`logs/p6-wt/` 目录被移除 | 低 | **S** | `git worktree list` 只剩主树；`.git/worktrees/` 为空 | `git worktree add logs/p6-wt work/20261023-phase6-arch-redesign` + 用 A1 的 patch 恢复改动 |
| **A3** | 清理 `logs/` 内 **3 份整仓源码副本**：删 `logs/p6-exp/`、`logs/delivery_audit_20261024/env/clean/`（`p6-wt/` 已在 A2 移除） | `logs/` | H-25 | 这三处是完整仓库拷贝（122/125/120 个 `.py`），会让全仓 grep 与静态统计失真（实测 `mcp` 词匹配 185 次 vs 源码真实 import 3 次）；合计约 13 MB | 仅 `logs/`（`.gitignore:41` 已忽略，不触版本库） | 低 | **S** | 全仓 `Get-ChildItem -Filter *.py -Recurse`（排除 .venv/.git/cache）计数从 483 回落到 ≈119；`rg` 抽查不再有 `logs/p6-exp` 命中 | 无（副本无独有信息；若需恢复，从 A1 存档或从 `main` 重建） |
| **A4** | 清理 ACL 探针与一次性脚本：删 `logs/eng_audit_tmp{,2,3,4,5,6,_cleanup,_planner}/`（约 1.1 MB）、`logs/` 根下 82 个一次性 `.py`（`_manifest_check.py`、`_stats.py`、`_schema*.py` 等）+ 11 个 `.ps1` + 3 个 `status_z*.bin`/`status_*.txt` 快照 + `_wip.diff`. **保留** `logs/phase4_2*/`、`logs/phase6_*/`、`logs/phase4_judge_recovery_*/`、`logs/phase4_2_r*_preflight/`（原始 run 产物，属证据保全，见 C6） | `logs/` | H-25、H-30 | 探针目录与 82 个脚本是历史调试残留，无引用者；`status_*.bin` 是 `git status` 二进制快照，信息已被本报告取代 | 仅 `logs/` | 低 | **S** | `logs/` 文件数从 4,177 降到约 1,000；`git status --porcelain` 无新增项（`logs` 本被忽略） | 无独有信息，不可恢复 `[推测]`；若需保留，先整目录压缩到仓库外 |

> ⚠️ **A 链唯一不可逆点**：A2/A3/A4 删除的目录不在版本库内（`.gitignore:41` 忽略 `logs/`），**删除后无法用 git 恢复**。因此 A1 的存档是硬前置；建议在执行 A2 前把 `logs/` 关键目录整体压缩一份到仓库外。

### 1.2 A 档独立项（可并行，互不冲突）

| 编号 | 动作 | 目标 | 对应 H | 理由 | 影响范围 | 风险 | 工作量 | 验证方式 | 回滚方式 |
|---|---|---|---|---|---|---|---|---|---|
| **A5** | `git rm xx` 删除根目录 15 KB 误入库文件（内容为 `git diff --stat` 终端转储，含 ANSI 色码与末行 `xx \| 214 +` 自引用） | `xx` | H-23 | 无意义文件在版本库里，且把一次大清理的删除清单留在根目录 | 1 个跟踪文件 | 低 | **S** | `git ls-files \| grep -x xx` 无输出；`ls xx` 报不存在 | `git checkout HEAD -- xx`（提交前）；`git revert`（提交后） |
| **A6** | 固化 3 个未提交改动：先 `python -m pytest tests/test_planner.py -q` 全绿，再 `git add README.md docs/DEMO_RUNBOOK.md tests/test_planner.py && git commit -m "docs: sync delivery notes and planner tests"` | `README.md`、`docs/DEMO_RUNBOOK.md`、`tests/test_planner.py` | H-24 | 工作树 ≠ HEAD，`README.md` 差 4,449 B，导致"以 README 为证据"的所有结论必须声明口径；`test_planner.py` 未提交会影响测试可复现性（人类决策 5 已定为"以工作树为准"） | 1 个提交；3 个文件 | 低 | **S** | 提交后 `git status --porcelain` 无 ` M`；`git show --stat HEAD` 恰为 3 文件 120 增 28 删 | `git reset --soft HEAD~1`（未推送时，不改工作树） |
| **A7** | 测试基线实跑定案：`python -m pytest -q` 全量执行，输出存档到 `reports/_archive/pytest_baseline_20261101.txt`；记录 collected/passed/skipped/failed 与耗时 | 全仓测试 | H-20 | 现有 3 个互斥数字：README「344 用例 / 342 passed + 2 skipped」、`context/KNOWN_DEBT.md:8-10`「340 passed / 3 failed」、实测「342 collected」。**这是文档可信度的锚点**，必须先有唯一数字 | 写 `.pytest_cache`、`reports/_archive/` 1 个文件 | 低 | **M** | 输出中 `collected`/`passed`/`skipped` 三数自洽；与 `342 collected` 对照，差额归因写进 A8 | 删除存档文件（测试本身无副作用；`data/*.db` 若有写入用 `git status` 确认——本项目 `data/` 已 gitignore） |
| **A8** | 数字统一回写：依 A7 结果，把 `README.md:78,169,171,198` 与 `context/KNOWN_DEBT.md:8-10` 的测试数字改为**同一唯一表述**（其余位置只保留指向，不重复数字） | `README.md`、`context/KNOWN_DEBT.md` | H-20、H-31(D1) | 消除最刺眼的一处硬冲突（D1）；后期所有引用以改后文本为准 | 2 个文件、约 4–6 行 | 低 | **S** | 全文 `rg "344 个用例\|340 passed\|342 passed"` 只命中 A8 指定的一处 | `git checkout HEAD -- README.md context/KNOWN_DEBT.md`（若 A6 已提交，则 revert 该文件改动） |
| **A9** | `.dockerignore` 补 `logs/`、`pytest-of-*/`、`torchinductor_lkl/`（与 `.gitignore:41,45-46` 对齐） | `.dockerignore` | H-15 | 现构建上下文 **4,209 文件 / 90.3 MB**，其中 `logs/` 占 90.5 MB；`.dockerignore` 注释自称与 `.gitignore` 同步却漏项 | 构建上下文体积 | 低 | **S** | `docker build` 上下文从 90.3 MB 降到 <2 MB（若本环境仍无 Docker，则用 `Get-ChildItem` 按 `.dockerignore` 规则静态模拟核对）`[待确认]` | `git checkout HEAD -- .dockerignore` |
| **A10** | 新增 `agents/__init__.py`（一行 docstring，声明感知/记忆/专家/Judge 四层） | `agents/` | H-08 | 15 个包中唯一缺 `__init__.py`；隐式命名空间包在 `site-packages` 出现同名 `agents` 时会被遮蔽 | 新增 1 文件；`orchestrator.py:55-68` 的 import 不变 | 低 | **S** | `python -c "import agents; print(agents.__file__)"` 指向仓内；`pytest -q` 不回归 | 删除该文件 |
| **A11** | 新增 `requirements-dev.txt`（`pytest>=8`、`matplotlib>=3.8`、`PyYAML>=6`），并在 `README.md` §6 快速开始加一行"开发/测试额外安装" | 根目录 + `README.md` | H-13 | 现在按 `README.md:99-101` 装完依赖**不能跑测试**（pytest 未声明）；`experiments/figures.py:22`、`experiments/schema.py:21` 同样在用未声明包 | 新增 1 文件；`README.md` 2 行 | 低 | **S** | 新建干净 venv 后 `pip install -r requirements.txt -r requirements-dev.txt` 再 `python -m pytest -q` 可跑通 `[需实跑验证]` | 删除新文件、revert README |
| **A12** | 删除 2 个永久 skip 的测试文件：`tests/test_phase4_harness_runtime.py`、`tests/test_phase4_reliability.py`（均以 `pytest.importorskip` 指向已删除的 `scripts/run_phase4_2*.py`） | `tests/` | H-22 | 永久跳过 = 永久噪音，且是"344 vs 342"混乱来源之一；所测对象已不存在 | 少 2 个测试文件（−6 个用例） | 低 | **S** | `pytest --collect-only -q` 无 skip 项、无导入告警 | `git checkout HEAD -- tests/test_phase4_*.py` |
| **A13** | 删除可再生缓存：`.mypy_cache/`（**153.1 MB**）、根与各包 `__pycache__/`（57 处）、`.ruff_cache/` | 缓存目录 | H-30 | 纯生成物、可再生；`.mypy_cache` 单文件达数十 MB，体积异常 | 回收约 153 MB | 低 | **S** | 目录不存在；`python -c "import orchestrator"` 正常（会重建 pycache） | 重跑 `mypy` 即可重建（无信息损失） |
| **A14** | `.env.example` 补齐 **10 个**代码实际读取的键：`AGRI_AI_ABSTAIN_MIN_SUFFICIENCY`、`AGRI_AI_CALIB_ALPHA`、`AGRI_AI_CALIBRATION`、`AGRI_AI_COHERENCE_MODEL`、`AGRI_AI_JUDGE_SESSION_ID`、`AGRI_AI_KG_DRAFTS_LOAD`、`AGRI_AI_KG_DRAFTS_PATH`、`AGRI_AI_KG_DRAFTS_PROPOSE`、`AGRI_AI_PLANNER_MODEL`、`PYTHONIOENCODING`（只写键名+默认值+注释，**不写任何真实密钥**） | `.env.example` | H-18 | 新环境按模板配置会静默落到默认行为，`AGRI_AI_KG_DRAFTS_*` 这类开关完全不可发现 | 1 个模板文件、约 20 行 | 低 | **S** | 用 `rg "os.environ.get\|os.getenv"` 提取的键集合与模板键集合做 diff，差集为空 | `git checkout HEAD -- .env.example` |
| **A15** | 新增 `data/README.md`：记录 `Agriculture_KnowledgeGraph-master/`（245.4 MB）的来源仓库、获取日期、文件清单与 SHA-256（`hudong_pedia.json` 110.9 MB 等 5 个大文件），并注明"不参与构建、仅 `scripts/import_agrikg.py` 消费" | `data/` | H-27（人类决策 4） | 体积最大的未跟踪目录无任何出处记录；将来无人能判断它是否过期、能否重建 | 新增 1 个文件（`data/` 已被 `.gitignore:40` 忽略 → **该文件默认不入库**，需 `!data/README.md` 例外规则） | 低 | **S** | 文件存在；`git check-ignore -v data/README.md` 显示被忽略 → 需在 `.gitignore` 加 `!data/README.md`（属本项范围内） | 删除该文件 + revert `.gitignore` |
| **A16** | 剪除 22 个已并入 main 的本地分支（`git branch -d <b>`，`-d` 只删已合并的，安全阀）+ `git remote prune origin`（清 `sprint-04.5B-capability-contract` 的 gone 上游） | 本地分支 | H-29 | 24 个分支里 22 个是会话遗留；`-d` 天然拒绝未合并分支，零误删风险 | 本地引用（不动 remote） | 低 | **S** | `git branch` 剩 2 条（`main` + `codex/acis-implementation-plan`） | 分支对象仍可由 reflog 找回：`git branch <name> <sha>` |
| **A17** | 删除 `data/.fuse_hidden*` 2 个残留文件（各 32 KB，FUSE 挂载遗留） | `data/` | H-30 | 无引用、无意义；`.gitignore:49` 已显式忽略该类文件 | 64 KB | 低 | **S** | 文件不存在；`agri.db`/`eval.db` 可正常打开 | 不可恢复，但内容为已删除文件的悬挂句柄残留 `[推测]` |
| **A18** | `.gitignore` 增防复发规则：`/xx`、`status_*.bin`、`status_*.txt`、`_wip.diff`、`*.orig`、`*.rej`（与 A5/A4 配套，防止同类转储再次误入库） | `.gitignore` | H-23、H-30 | `xx` 之所以能进版本库，是因为 `.gitignore` 没有拦截终端转储类文件；只删不防 → 会复发 | 1 个配置文件、5 行 | 低 | **S** | 造一个 `xx`/`status_test.bin` 的临时文件，`git check-ignore -v` 能命中 | `git checkout HEAD -- .gitignore` |

### 1.3 A 档中的 **git 写操作**（需人类逐项勾选）

> 以下 4 项会改变版本库状态（不是纯文件操作），单独列出供逐项批准。

- [ ] **A2** `git worktree remove logs/p6-wt --force` — 注销一个附属工作树；**依赖 A1 完成**
- [ ] **A5** `git rm xx` — 删除一个误入库文件
- [ ] **A6** `git add … && git commit` — 固化 3 个未提交改动（前置：`pytest tests/test_planner.py` 全绿）
- [ ] **A16** `git branch -d <22 条已合并分支>` + `git remote prune origin` — 仅本地分支引用

**建议的执行顺序（已考虑依赖）**：

```
A1 → A2 → A3 → A4 → A5 → A6 → A7 → A8 → A18 → A16(须在 A2 之后)
并行：A9、A10、A11、A12、A13、A14、A15、A17
```

> `A16` 必须在 `A2` 之后：`work/20261023-phase6-arch-redesign` 正被 `logs/p6-wt` 检出，**检出中的分支无法删除**。
> `A7` 建议在 `A6` 之后：避免把"未提交改动"混进基线记录。

---

## 2. B 档：需讨论

> 每项**不能**在未回答"需人类决策的问题"前开工，否则方案会自相矛盾。

| 编号 | 动作 | 目标 | 对应 H | 理由 | 影响范围 | 风险 | 工作量 | 验证方式 | 回滚方式 |
|---|---|---|---|---|---|---|---|---|---|
| **B1** | 打包落地：新增 `pyproject.toml`（声明 5 个根模块 + 各包），逐个消除 **19 处** `sys.path.insert`，改为 `pip install -e .` | 根目录 + 19 个文件 | H-07 | **结构债的根**：无打包导致每个入口自己垫路径、E402 常态、`src/` 只能靠测试注入、IDE/CI 静态分析不可靠。修它**不需要动业务逻辑**，杠杆最高 | 19 个文件 + 所有入口的运行方式；测试/CI 全量 | 中 | **M–L** | `pip install -e .` 后，在**仓库外**目录 `python -c "import orchestrator, gateway.app, ui.tui"` 全成功；`pytest -q` 无回归；`rg "sys.path.insert"` 归零 | 删除 `pyproject.toml`、恢复 19 处 import（走 A6 之后的干净基线做 `git revert`） |
| **B2** | 布局决策与迁移：扁平根（现状）vs `src/acis/` 布局 | 全仓 | H-06 | 三种布局并存（根扁平 + 20 余包 + `src/`）；但迁移是 L/XL 且高回归风险，**是否值得取决于项目 3 年内的维护强度** | 全仓 import、测试、脚本、Docker | 高 | **L–XL** | 迁移后 `pytest -q` 全绿 + 三入口冒烟 | 分阶段提交，逐批 revert |
| **B3** | `src/openmetaphysics/` 归宿：①并入 `benchmarks/`/`evals/` ②随 B1 纳入打包 ③保持现状但加显式说明 | `src/` | H-09 | 它只有 4 个文件，却引入第三种布局；`KNOWN_DEBT.md:21-23` 仍在引用它，说明尚未退役 | 4 文件 + `tests/conftest.py:10-11` + `scripts/generate_stability_report.py:41` | 中 | **M** | 归并后 `rg "openmetaphysics"` 只剩打包声明处；相关测试通过 | `git revert` |
| **B4** | **双 MCP Server 归一**：确定权威实现（`kg/mcp_server.py` 9 tool vs `rag/knowledge_base.py` 5 tool），统一 `search_disease` 与 `knowledge://diseases` 的语义与返回结构 | `kg/`、`rag/` | H-10 | 两个 server 暴露**同名工具与资源**，各自演进 → 对外契约静默漂移；且 MCP 侧**零测试**。`kg/mcp_server.py:41` 还在注释里引用已删除的 `knowledge_mcp_server.py` | 对外 MCP 契约（可能已有外部调用方） | **高**（契约破坏不可见） | **M** | 单测覆盖两个工具的输入/输出 schema；一次"同输入两 server 输出 diff"的对照测试 | 保留双实现 + 版本号切换；或 revert |
| **B5** | 拆分 `rag/knowledge_base.py`：拆为"领域数据/函数"（`DISEASE_DB`/`CROP_MAP`/`diagnose_and_advise`）与"MCP 适配层"（`FastMCP`）；使生产链路不再顶层依赖 `mcp` 包 | `rag/` | H-12 | 核心诊断链路硬依赖一个 MCP server 模块（`from mcp.server.fastmcp import FastMCP` 为顶层 import）；数据与协议无法分别演进 | `kg_adapter.py:34`、`rag/retriever.py:18`、`agents/{pathology,cultivation,kg}_agent.py:4` | 中 | **M** | 拆除后在不安装 `mcp` 的环境里 `import agents.pathology_agent` 成功；`pytest -q` 全绿 | 保留旧模块作为 re-export shim，先兼容后删除 |
| **B6** | 双能力矩阵生成器归一（`benchmarks/taxonomy.py` vs `capability_matrix.py` 同写 `CAPABILITY_MATRIX.md` + `COVERAGE.md`），并将 5 份生成/报告 md 移出代码目录 | `benchmarks/` | H-11、H-34 | 谁后跑谁生效，无权威标注；生成物与代码混放 | 2 个脚本、5 个 md、`tests/test_capabilities.py` 等引用 | 中 | **M** | 只保留一个 `__main__` 生成入口；生成物落到 `reports/`；测试通过且产物 diff 稳定 | `git revert` + 恢复旧 md |
| **B7** | 文档单一事实源改造：按 D1–D9 逐条修（ADR front matter 与 Proposed 表述、`MODEL_AGENT_ORCHESTRATION.md:146,181`、`reports/README.md:36` 的 raw JSON 声明、`archive/architecture-state.md` 的自称、`current-sprint.md` 失效路径），并在 archive 统一加 "Superseded by …" 头 | `docs/`、`README.md`、`context/`、`reports/` | H-31、H-32 | 9 处硬冲突 + 同一主题平均 3.2 份承载；**侵蚀项目最值钱的"可审计性"资产** | 约 8 份文档 | 中 | **M** | 建立"事实源地图"（RFC001=WHAT / ADR=WHY / README=现状 / `experiment_audit`=数字），逐条核对指向存在性 | `git revert`（纯文档） |
| **B8** | 恢复或重写工程规范 `AGENTS.md`：①恢复旧 3 条（每轮独立分支 / 结束 5 字段归档 / 用户控合并）②按"工程基线"定位重写（加包管理、测试门禁、清理规则、禁止再往根目录扔临时文件） | 根目录 + `context/archive/` | H-33 | 规范已被 `f1c7e98` 删除但遗迹仍在执行（20 个 `work/<日期>-<主题>` 分支即其产物）；后来者/Agent 无法发现约定 → 行为不可预期 | 全部后续协作流程 | 低 | **S–M** | 新规范与 `git branch` 实际命名一致；一次演练（新建分支→归档→报告）走通 | `git revert` |
| **B9** | 测试覆盖补齐优先级与门禁：先补哪块（`kg_adapter` Neo4j 路径 / `rag/retriever` / `rule_engine` 三层降级 / `gateway`），是否引入 coverage 门槛与 CI | `tests/`、CI | H-21 | `rag/ kg/ rule_engine/ ui/` **零覆盖**，而这四块恰是"外部依赖多、最易静默失败"的部分；它们是下次改动的最大回归风险源 | 新增测试与可能新增 CI 配置 | 中 | **M–L** | 目标模块行覆盖 ≥60%；降级路径（缺 Neo4j/Qdrant/模型）有显式断言 | 新测试可独立 revert，不影响生产代码 |
| **B10** | Docker 基线统一：①目标 Python 版本（3.11 vs 3.13）②是否弃 `.:/app` bind mount 改纯镜像 ③`NEO4J_PASSWORD` 走环境/secret ④补 `HEALTHCHECK` + CI build 验证 | `Dockerfile`、`docker-compose.yml` | H-16、H-17 | 版本双轨、密钥入库、挂载遮蔽镜像使构建物在运行期失效；`KNOWN_DEBT.md:13-14` 自述从未构建验证 | 部署形态 | 中 | **M** | 本机或 CI 成功 `docker compose up` 且 `/health` 200；`docker image inspect` 里 Python 版本符合决策 | `git revert`；compose 保留旧文件备份 |

### 2.1 B 档需人类决策的具体问题（逐项）

| 编号 | 需人类决策的问题 |
|---|---|
| **B1** | ① 发行包名用什么（`acis` / `acis-core`）② 采用 setuptools 还是 hatchling ③ 是否连 `src/openmetaphysics` 一起纳入打包（与 B3 联动）④ 是否要求 `pip install -e .` 成为唯一启动方式（会改变 README 的快速开始） |
| **B2** | ① 是否迁移到 `src/` 布局 ② 若迁，可否接受"分批迁移 + 每批一次完整回归"（预计 2–3 批）③ 迁移期间是否冻结新功能 |
| **B3** | 并入 `benchmarks/` 还是 `evals/`？还是作为独立可安装包 `openmetaphysics`？`KNOWN_DEBT.md:21-23` 的引用是否需要同步改？ |
| **B4** | ① 哪个是权威 server（建议 `kg/mcp_server.py`，9 tool 覆盖面更大，但是 `rag` 侧被生产链路依赖）② 是否需要**保留两个对外入口**（若已有外部调用方）③ 兼容期多长、是否要双版本号 |
| **B5** | ① 拆分粒度（数据 vs 适配层 二分，还是再拆"诊断算法"）② 是否保留旧导入路径 shim 及其保留期限 ③ 是否允许 `mcp` 变成可选依赖（会影响 `requirements.docker.txt`） |
| **B6** | ① 哪个生成器权威（`capability_matrix.py` 功能更全、`taxonomy.py` 更早）② 生成物是否从 `benchmarks/` 移到 `reports/` ③ 被跟踪的 2 份生成物是否从版本库移除 |
| **B7** | ① 是否接受"事实源地图"这一分工（RFC001=WHAT / ADR=WHY / README=现状 / `experiment_audit`=数字）② `docs/archive/` 是保留并加 superseded 头，还是整体移出仓库 ③ `MODEL_AGENT_ORCHESTRATION.md` 保留还是归档 |
| **B8** | ① 恢复旧 3 条，还是在"工程基线"定位下重写 ② 若重写，是否包含"禁止在根目录产生临时文件""提交前必跑 `pytest -q`""分支命名与归档模板" ③ 是否重建 `context/archive/` 目录 |
| **B9** | ① 四块未覆盖模块的补齐顺序（建议 `kg_adapter` → `rule_engine` → `rag` → `gateway`）② 用 fake/stub 还是起真实 Neo4j/Qdrant 容器 ③ 是否引入 coverage 门槛与 CI（若无 CI，门禁只能靠本地约定） |
| **B10** | ① 目标 Python 版本定为 3.11 还是 3.13（`.venv` 是 3.13.3）② 是否弃 `.:/app` bind mount（开发热更新会变麻烦）③ 密钥用 compose `${VAR}` 还是 `secrets:` ④ 是否本轮就把 Docker 构建纳入验收 |

---

## 3. C 档：暂缓

> 暂缓 ≠ 放弃。每项注明**暂缓理由**与**触发条件**（条件达成即升级为 B 档）。

| 编号 | 动作 | 目标 | 对应 H | 暂缓理由 | 触发条件（达成即重启） | 风险 | 工作量 | 验证方式 | 回滚方式 |
|---|---|---|---|---|---|---|---|---|---|
| **C1** | `.git` 历史重写（`git filter-repo` 清除 253 MB pack 中的历史大对象） | `.git/` | H-28 | **人类已定暂缓**；这是唯一不可逆动作，需全员协调与全量备份 | 仓库需对外发布 / 新机器 clone 时间成为痛点 / 需要与外部协作者协同前 | 高（不可逆） | **L** | 重写后 `git count-objects -vH` 显著下降 + 235 个跟踪文件内容哈希不变 | **只能靠备份**：执行前完整 `git clone --mirror` 到仓库外 |
| **C2** | `data/` 266 MB（含 245.4 MB vendored 第三方仓库）移出仓库 | `data/` | H-27 | **人类已定保留原址**（A15 只补来源记录） | 需要 CI/新机器快速拉起 / `import_agrikg` 不再需要时 | 中 | **M** | 移出后 A15 的 README 指向新位置且可访问 | 移回原路径 |
| **C3** | 超长文件拆分（`agents/judge_agent.py` 575 行单类、`benchmarks/capability_matrix.py` 987 行、另 10 个 >500 行文件） | 12 个文件 | H-35 | Judge 是决策核心且**无专门回归测试**；先拆等于裸奔 | B9 完成、Judge 有行为级测试后 | 中 | **L** | 拆分前后对同一批固定案例输出 diff 为空 | 分文件提交，逐个 revert |
| **C4** | `pillow` 去留（声明但全仓零 `import PIL`） | `requirements.txt:23` | H-14 | 删除与否取决于 web/streamlit 路线是否保留（`ui/web_app.py:20` 仍 import streamlit）；且 streamlit 生态对 pillow 有间接需求 `[待确认]` | B10 或 web UI 定位确定后 | 低 | **S** | 删除后 `pip check` 无缺失；streamlit 路径可启动 | 恢复该一行 |
| **C5** | 为 Chronos 预测层补依赖声明（`rule_engine/sensor_anomaly.py:114` 用 `chronos`，三份清单均无、`.venv` 也无） | `requirements*.txt` | H-13 | 该层当前**必然降级**为线性回归，且代码有 `try/except` 保护；补依赖会引入 torch 权重下载，与"离线优先"冲突 | 需要真实 Chronos 预测能力 / 评测口径要求该层启用 | 中 | **S–M** | 装上后 `_CHRONOS_STATUS` 显示 `chronos-t5-small` 而非 `linear_regression_fallback` | 移除依赖声明 |
| **C6** | 清理 `logs/phase4_2*/`、`logs/phase6_*/` 原始 run 产物（约 60 MB，A4 特意保留） | `logs/` | H-25 | 它们是 `E017`/`E019` 的证据原始材料，且 `EVIDENCE_LEDGER.md:24` 记载 Phase 4.2-R 的 raw 已"保存在仓库外本地归档"——删除前须确认归档完整 | 证据台账改为"哈希 + 仓库外归档"引用后 | 中 | **S** | 删除后 `EVIDENCE_LEDGER` 中对应条目的引用仍可解析 | 从仓库外归档恢复 |
| **C7** | 清理 `results/` 56.8 MB 历史实验输出（1,239 文件） | `results/` | H-30 | 是 `E007`/`E009`（Phase 2 数据）的原始材料，`EVIDENCE_LEDGER.md:29` 明确其"不公开"地位 | Phase 2 证据完成归档与哈希化后 | 中 | **S** | 台账引用可解析 | 从归档恢复 |
| **C8** | 处理未合并分支 `codex/acis-implementation-plan`（领先 main 1 提交 `6de83b2 Save changes to tui.py`） | 本地分支 | H-29 | 需人先判断那 1 个 `tui.py` 提交是否有价值；`-d` 会拒绝删除，必须 `-D` 强制 | 人审该提交内容后 | 低 | **S** | 审阅 `git show 6de83b2` 后决定 merge 或 `-D` | `git branch` 重建（reflog 可找回） |
| **C9** | 5 份 `raw_results*.json`（≈596 KB）出库，使 `reports/README.md:36` 的"已移出"声明成立 | `reports/` | H-31(D6) | 它们是 `E017` 的复算依据（`EVIDENCE_LEDGER.md:22` 明确引用），出库即削弱可复算性 | 台账改为"仓库外归档 + SHA-256"引用后 | 低 | **S** | 引用链可解析 | `git revert` |
| **C10** | 魔法数集中化（置信度阈值/降权系数散落 10+ 处：`workflow.py:178`、`judge_agent.py:264,295,542-595`、`debate/critic.py:151-152,189`） | 多文件 | H-37 | 当前无调参需求；集中化会改变既有行为，需回归验证 | 需要系统性调阈值做实验时 | 低 | **M** | 集中后同 seed 输出与现状一致 | `git revert` |
| **C11** | 收敛 45 处 `except Exception`（多数为有意的降级边界，附 `# noqa: BLE001`） | 多文件 | H-36 | **多数不是债而是设计**；收敛需先有 lint 门禁与白名单机制，否则会把正常降级改坏 | B1/B8 落地 lint 门禁后，按 `BLE001` 白名单逐项收敛 | 中 | **M** | 每处收敛后其降级路径测试仍通过 | `git revert` |

---

## 4. 与阶段 2 诊断的覆盖度对照

| 诊断编号 | 覆盖动作 | 备注 |
|---|---|---|
| H-01～H-05（核心运行时 / 台账） | **无动作（KEEP）** | 明确不动，避免"顺手重构" |
| H-06 | A—（B2） | 需人决策 |
| H-07 | **B1** | 最高杠杆的 B 档项 |
| H-08 | **A10** | — |
| H-09 | **B3** | — |
| H-10 | **B4** | — |
| H-11 | **B6** | — |
| H-12 | **B5** | — |
| H-13 | **A11**（pytest/matplotlib/PyYAML）+ **C5**（chronos） | 拆分处理：能立即补的进 A，涉及权重的进 C |
| H-14 | **C4** | 依赖路线未定 |
| H-15 | **A9** | — |
| H-16、H-17 | **B10** | — |
| H-18 | **A14** | — |
| H-19 | 并入 **B1**（`pyproject.toml` 同时承载 lint/type 配置） | 不单列，避免重复建文件 |
| H-20 | **A7 + A8** | 先测后写 |
| H-21 | **B9** | — |
| H-22 | **A12** | — |
| H-23 | **A5 + A18** | — |
| H-24 | **A6** | 人类已决策 |
| H-25 | **A3 + A4** + **C6** | A 清副本/探针，C 保留证据 |
| H-26 | **A1 → A2** | 严格串行 |
| H-27 | **A15** + **C2** | — |
| H-28 | **C1** | 人类已定暂缓 |
| H-29 | **A16** + **C8** | 已合并可删，未合并待审 |
| H-30 | **A13 + A17 + A18** + **C7** | — |
| H-31 | **A8**（D1）+ **B7**（其余 8 条）+ **C9**（D6） | 拆分处理 |
| H-32 | **B7** | — |
| H-33 | **B8** | — |
| H-34 | **B6** | — |
| H-35 | **C3** | 等测试保护 |
| H-36 | **A—**（45 处 KEEP）+ **C11**（2 处静默需在 B9 中一并覆盖） | — |
| H-37 | **C10** | — |
| H-38（正面项） | **无动作（KEEP）** | 0 bare except / 0 硬编码路径 / 0 注释死代码，保持 |

**未覆盖检查**：H-01～H-38 全部有归属，无遗漏；**无新增问题**——本方案所有动作均可回溯到阶段 2 已编号的诊断项。

---

## 5. 执行前提与纪律

1. **全部未执行**：本文件是清单，不是变更记录。批准前不得做任何写操作。
2. **A 链不可换序**：A1（存档）是所有删除动作的硬前置；`A2` 之后才能做 `A16`；`A6` 之后再做 `A7`。
3. **不可逆动作只有 3 个**：A2/A3/A4（删除被 gitignore 的本地目录）+ A17。执行前建议把 `logs/` 整体压缩到仓库外一份。
4. **B 档禁止"边讨论边动手"**：每项必须先回答 §2.1 的对应问题，否则会产出互相矛盾的实现。
5. **验证优先**：每批动作完成后跑 `python -m pytest -q` + 三入口冒烟（`orchestrator.py --rules-only --seed 7`、`python -m ui.tui`、`uvicorn gateway.app:app`）。

---

*下一步动作与批次编排见 [NEXT_ACTIONS.md](NEXT_ACTIONS.md)。*
