# ACIS 下一步动作与路线图（阶段 4：Next Actions）

> **基线**：`main @ d2fa727`｜**日期**：2026-11-01｜**定位（人类已确认）**：**长期维护的工程基线**，当前处于"原型 → 基线"过渡期
> **输入**：[PROJECT_INVENTORY.md](PROJECT_INVENTORY.md) + [PROJECT_HEALTH.md](PROJECT_HEALTH.md)（H-01～H-38）+ [CONSOLIDATION_PLAN.md](CONSOLIDATION_PLAN.md)（A1–A18 / B1–B10 / C1–C11）
> **状态**：**全部未执行**。本文件是路线图与勾选依据，不是变更记录。

---

## 0. 一句话路线

**先花 2–3 人日"A 档收口"（把仓库变干净、让数字唯一、让测试能跑），再花 8–12 人日按决策顺序做 B 档（打包 → 契约归一 → 文档事实源），C 档全部等触发条件。**

**排序依据（三条硬规则）**：
1. **先做"让后续判断可信"的事**（A1/A6/A7/A8 —— 存档、基线、唯一数字），否则后面每个决策都建在流沙上。
2. **不可逆动作必须被可逆动作包住**（A1 存档在 A2 删除之前；备份在 A3/A4 之前）。
3. **高价值但被决策阻塞的项，排在"解阻塞"之后**（B 档按 §2.1 问题逐项解锁，不抢跑）。

---

## 1. 优先级矩阵（价值 / 成本 / 风险）

**评分口径**：价值 3=直接消除高/中风险或解锁后续工作；2=明显改善；1=锦上添花。成本 S=1 / M=2 / L=3 / XL=4（**实际耗时，含验证**）。比值 = 价值 ÷ 成本，**同等比值下低风险优先**。

### 1.1 A 档（全部可立即批准）

| 排名 | 编号 | 动作 | 价值 | 成本 | 风险 | 比值 | 排序依据 |
|:--:|---:|---|:--:|:--:|:--:|:--:|---|
| 1 | **A1** | 存档 `p6-wt` 未提交改动 | 3 | S(1) | 低 | **3.0** | 解锁整条 A 链，且保全唯一不可再生的 3 处工作状态 |
| 2 | **A2** | `git worktree remove` | 3 | S(1) | 低 | **3.0** | 解除 R1（最易踩的清理地雷），且分支 0 领先 main |
| 3 | **A6** | 提交 3 个未提交改动 | 3 | S(1) | 低 | **3.0** | 让"以 README 为证据"从双口径变成单口径；人类已决策 |
| 4 | **A11** | 新增 `requirements-dev.txt` | 3 | S(1) | 低 | **3.0** | 修掉"按 README 装完依赖不能跑测试"这一硬伤 |
| 5 | **A7** | 全量 pytest 实跑定案 | 3 | M(2) | 低 | **1.5** | 是 A8 的前置，也是所有"测试数字"争议的唯一解 |
| 6 | **A3** | 清 `logs/` 三份整仓副本 | 2 | S(1) | 低 | **2.0** | 消除 grep/静态统计失真（实测 `mcp` 词匹配 185 次 vs 真实 3 次） |
| 7 | **A4** | 清 ACL 探针与 82 个散落脚本 | 2 | S(1) | 低 | **2.0** | 同 A3；且 `status_*.bin` 已被本报告取代 |
| 8 | **A5** | `git rm xx` | 2 | S(1) | 低 | **2.0** | 移除误入库垃圾；成本近乎为零 |
| 9 | **A8** | 测试数字统一回写 | 2 | S(1) | 低 | **2.0** | 消除最刺眼的文档硬冲突 D1；**依赖 A7** |
| 10 | **A9** | `.dockerignore` 补 `logs` | 2 | S(1) | 低 | **2.0** | 构建上下文 90.3 MB → <2 MB，投入 1 行 |
| 11 | **A12** | 删 2 个永久 skip 测试 | 2 | S(1) | 低 | **2.0** | 去噪音、去"344 vs 342"来源之一 |
| 12 | **A13** | 删 `.mypy_cache` 等缓存 | 2 | S(1) | 低 | **2.0** | 纯回收 153 MB，零信息损失 |
| 13 | **A14** | `.env.example` 补 10 键 | 2 | S(1) | 低 | **2.0** | 修配置双向漂移的一半（模板→代码） |
| 14 | **A15** | 新增 `data/README.md`（AgriKG 出处） | 2 | S(1) | 低 | **2.0** | 让 245 MB 未跟踪数据有出处，人类决策 4 的落地 |
| 15 | **A16** | 剪除 22 个已合并分支 | 2 | S(1) | 低 | **2.0** | `git branch -d` 有安全阀；须在 A2 之后 |
| 16 | **A18** | `.gitignore` 防复发规则 | 2 | S(1) | 低 | **2.0** | 只删不防会复发（`xx` 就是这么进来的） |
| 17 | **A10** | 新增 `agents/__init__.py` | 1 | S(1) | 低 | **1.0** | 一致性修补，当前无实际故障 |
| 18 | **A17** | 删 `data/.fuse_hidden*` | 1 | S(1) | 低 | **1.0** | 64 KB，纯整洁 |

### 1.2 B 档中价值/成本最划算的 4 项（**均被决策阻塞，不能抢跑**）

| 排名 | 编号 | 动作 | 价值 | 成本 | 风险 | 比值 | 阻塞点 |
|:--:|---:|---|:--:|:--:|:--:|:--:|---|
| 1 | **B8** | 恢复/重写 `AGENTS.md` | 3 | S–M(1.5) | 低 | **2.0** | §2.1-B8 三问（恢复 vs 重写 / 内容范围 / 是否重建 `context/archive/`） |
| 2 | **B7** | 文档单一事实源改造（D1–D9） | 3 | M(2) | 中 | **1.5** | §2.1-B7 三问（事实源地图 / archive 去留 / MODEL_AGENT 定位） |
| 3 | **B4** | 双 MCP Server 归一 | 3 | M(2) | **高** | **1.5** | §2.1-B4 三问（权威 server / 是否保留双入口 / 兼容期）——**风险高于比值，需最谨慎** |
| 4 | **B1** | 打包（`pyproject.toml` + 清 19 处 `sys.path`） | 3 | M–L(3) | 中 | **1.0** | §2.1-B1 四问（包名 / 构建后端 / 是否含 `src/` / 是否强制 editable 安装） |

> 说明：**B8 的比值最高却仍列 B 档**——因为它需要人定"要不要恢复旧纪律"，不是技术难度问题。这正说明本轮瓶颈在**决策**而非**工时**。

---

## 2. 建议批次

### 批次 0：**本轮立即做**（批准 A 链 + 三个"让判断可信"的项）

| 顺序 | 项 | 为什么本轮必做 |
|:--:|---|---|
| 1 | **A1 → A2 → A3 → A4** | 严格串行。这是唯一有"不可逆 + 顺序依赖"的链路，必须一次做完；拖到下次会持续污染 grep 与静态统计 |
| 2 | **A6** | 让工作树与 HEAD 对齐，后续所有文档结论有单一基准 |
| 3 | **A7** | 产出唯一测试数字，喂给 A8 |
| 4 | **A8** | 消除 D1 硬冲突（**依赖 A7**） |

**验收标准（批次 0 完成即认为"仓库可判断"）**：
- `git worktree list` **只剩主树 1 项**
- 源码 `.py` 计数回到 **≈119**（不再被 `logs/` 三份副本污染）
- `git status --porcelain` **无 ` M`**（A6 已提交）
- 全仓 `rg "344 个用例|340 passed|342 passed"` **只命中一处**
- `logs/` 体积从 **90.5 MB 降到 ≤75 MB**（保留 phase run 证据）

### 批次 1：**本轮做完，同一次批准即可**（A 独立项，零争议）

**A5、A9、A10、A11、A12、A13、A14、A15、A16、A17、A18**

理由：全部是机械动作（删/补一行/补一个文件），彼此无冲突，且**不涉及任何架构或接口判断**。A16 放在 A2 之后、A18 放在 A5 之后即可。

**验收标准**：
- `python -m pytest -q` 全绿（数字与 A7 一致）
- 三入口冒烟通过：`python orchestrator.py --rules-only --seed 7 "温室A番茄叶片出现黄斑"` / `python -m ui.tui` / `uvicorn gateway.app:app` → `GET /health` 200
- `git branch` 剩 2 条（`main` + `codex/acis-implementation-plan`）
- 回收磁盘 ≥190 MB（`.mypy_cache` 153 + `logs` 约 15 + 缓存）

### 批次 2：**下个迭代（第 1–2 天）**——先解阻塞，再动结构

| 顺序 | 项 | 理由 |
|:--:|---|---|
| 1 | **回答 §3 的 Q1–Q5** | 不解这 5 个问题，批次 2 之后无一项能安全开工 |
| 2 | **B8** 工程规范 | 成本最低、价值最高；且它定义的纪律会约束后续 A/B 档执行方式 |
| 3 | **B7** 文档事实源 | 纯文档、可 revert；做完后"引用失真"风险归零，后续所有报告受益 |
| 4 | **B1** 打包 | 结构债的根；但**必须先有 Q1 的答案**（包名/布局） |
| 5 | **B10** Docker 基线 | 与 B1 共用"目标 Python 版本"决策，适合同批 |

**验收标准**：`pip install -e .` 后能在仓库外目录 import 全部入口；`rg "sys.path.insert"` 归零；文档"事实源地图"逐条指向存在；`pytest -q` 无回归。

### 批次 3：**下下个迭代**——契约与测试深度

| 顺序 | 项 | 理由 |
|:--:|---|---|
| 1 | **B9** 测试覆盖补齐（`kg_adapter` → `rule_engine` → `rag` → `gateway`） | 是 B4/B5/C3 的前置保护 |
| 2 | **B4** 双 MCP 归一 | **高风险、需在测试保护下做** |
| 3 | **B5** `knowledge_base` 拆分 | 与 B4 同一片区域，宜连续做 |
| 4 | **B6** 矩阵生成器归一 | 低耦合，可插空 |
| 5 | **B3** `src/openmetaphysics` 归宿 | 跟随 B1 的打包结论 |
| 6 | **B2** 布局迁移 | **仅在 Q1 明确"要迁"时启动**；否则长期挂起 |

### 暂不做（C 档全部 + B2 条件项）

| 项 | 暂缓理由（一句话） | 触发条件 |
|---|---|---|
| **C1** `.git` 历史重写 | 人类已定暂缓；唯一不可逆动作 | 需对外发布 / clone 成本成痛点 |
| **C2** `data/` 移出 | 人类已定保留原址（A15 补出处即可） | 需 CI 或新机器快速拉起 |
| **C3** 超长文件拆分 | Judge 无行为级测试，拆等于裸奔 | B9 完成 |
| **C4** `pillow` 去留 | 取决于 web/streamlit 路线 | B10 或 web UI 定位确定 |
| **C5** Chronos 依赖 | 当前必然降级且有 `try/except`，补依赖引入 torch 权重下载 | 需要真实 Chronos 预测能力 |
| **C6** `logs/phase*` 原始 run | E017/E019 的证据原始材料 | 证据改为"哈希 + 仓库外归档" |
| **C7** `results/` 清理 | E007/E009 的原始材料 | Phase 2 证据归档完成 |
| **C8** 未合并分支 | 需人审 `6de83b2` 那 1 个 `tui.py` 提交 | 人审后 |
| **C9** 5 份 `raw_results.json` 出库 | E017 的复算依据 | 台账改为哈希引用 |
| **C10** 魔法数集中化 | 无调参需求，改了要回归 | 需系统性调阈值做实验 |
| **C11** 45 处 `except Exception` 收敛 | **多数是设计而非债**，需 lint 白名单机制 | B1/B8 落地门禁后 |
| **B2** 全量布局迁移 | L–XL 且高风险 | Q1 明确"要迁"时才升级 |

---

## 3. 剩余需人类决策的问题（≤5，按阻塞程度排序）

### Q1 —— 包名与布局（阻塞 8–12 人日中的最大一块）
**要定的事**：发行包名（`acis` / `acis-core`）？构建后端（setuptools / hatchling）？**是否迁移 `src/` 布局**？是否要求 `pip install -e .` 成为唯一启动方式？
**阻塞**：B1（打包）、B2（布局）、B3（`src/` 归宿）、B10（Docker 版本对齐）。**这 4 项合计 4–6 人日，全部卡在这一个问题上。**
**为什么必须早答**：B1 是在"不迁布局"前提下做（只加 `pyproject.toml` + 清 `sys.path`，M 级）；一旦决定迁移，B1 的写法完全不同（会变成 L 级）。**先做 B1 再改主意 = 白做一遍。**

### Q2 —— 双 MCP Server 谁是权威（阻塞最高风险项）
**要定的事**：`kg/mcp_server.py`（9 tool）还是 `rag/knowledge_base.py`（5 tool）为权威？是否保留**两个对外入口**？兼容期多长？
**阻塞**：B4、B5、B6（同片区改造），以及 C11 中 MCP 侧相关部分。
**为什么最危险**：两个 server 现在都暴露 `search_disease` 与 `knowledge://diseases`，**且 MCP 侧零测试**——任何一方改动都可能是"看不见的契约破坏"。若已有外部调用方，必须先确认其依赖哪个入口。

### Q3 —— 文档事实源地图与 archive 去留（阻塞数字治理）
**要定的事**：是否接受"RFC001=WHAT / ADR=WHY / README=现状 / `experiment_audit`=数字"的分工？`docs/archive/`（26 文件）保留并加 superseded 头，还是整体移出？`MODEL_AGENT_ORCHESTRATION.md`（10.7 KB，README 导航未列）保留还是归档？
**阻塞**：B7、B6（生成物去向）、C9（raw JSON 是否出库）。
**为什么必须早答**：A8 只修 D1 一处冲突；剩下的 D3/D4/D6/D7 都取决于"哪份文档有权说话"。不定这个，改完还会再冲突。

### Q4 —— `AGENTS.md`：恢复旧纪律还是按"工程基线"重写（成本最低、价值最高）
**要定的事**：恢复被删的 3 条（每轮独立分支 / 结束 5 字段归档 / 用户控合并），还是重写为含**包管理、测试门禁、禁止根目录临时文件、清理规则**的新版？是否重建 `context/archive/`？
**阻塞**：B8，并影响后续所有批次"怎么做才算合规"。
**为什么优先**：S–M 成本、零代码风险，却能立刻把"行为不可预期"变成"有章可循"。**建议本轮就先答这一条**（它比 Q1 便宜得多）。

### Q5 —— 测试补齐的优先级与是否上 CI（阻塞"下迭代做什么"）
**要定的事**：四块未覆盖模块的顺序（建议 `kg_adapter` → `rule_engine` → `rag` → `gateway`）？用 fake/stub 还是起真实 Neo4j/Qdrant 容器？是否引入 coverage 门槛与 CI（当前仓库**无任何 CI 配置**）？
**阻塞**：B9、C3（超长文件拆分）、C11（异常收敛）——**没有测试保护，这三项都不能动**。
**为什么关键**：它决定"工程基线"是真基线还是口号——没有 CI 与门禁，A 档收口的成果会在 3 个月内重新腐化。

---

## 4. 验证方式（按批次，可直接复制执行）

### 4.1 批次 0 验证
```powershell
# 1) worktree 已注销
git -c safe.directory=E:/knowledge_database/ACIS worktree list      # 期望：仅主树 1 行

# 2) 源码计数不被副本污染（期望 ≈119）
(Get-ChildItem -Recurse -File -Filter *.py | Where-Object { $_.FullName -notmatch '\\(\.venv|logs|torchinductor_lkl|__pycache__)\\' }).Count

# 3) 工作树干净
git -c safe.directory=E:/knowledge_database/ACIS status --porcelain  # 期望：无 ' M' 行

# 4) 唯一测试数字
rg -n "344 个用例|340 passed|342 passed" --glob '!logs/**' --glob '!.venv/**'

# 5) logs 体积（期望 ≤75 MB）
[math]::Round((Get-ChildItem logs -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum/1MB,1)
```

### 4.2 批次 1 验证
```powershell
python -m pytest -q                                    # 期望：全绿，数字与 A7 存档一致
python orchestrator.py --rules-only --seed 7 "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"   # 期望：退出码 0 + 【Judge】rules
python -m ui.tui                                       # 期望：菜单 + 6 个演示场景
uvicorn gateway.app:app --port 8000                    # 另一终端：curl http://127.0.0.1:8000/health → 200
git -c safe.directory=E:/knowledge_database/ACIS branch          # 期望：main + codex/acis-implementation-plan
git -c safe.directory=E:/knowledge_database/ACIS check-ignore -v xx status_test.bin   # 期望：命中 A18 规则
```

### 4.3 批次 2/3 验证
- **B1**：在**仓库外**目录执行 `python -c "import orchestrator, gateway.app, ui.tui, agents, debate, rag"` 全成功；`rg "sys.path.insert"` 归零；`pip install -e .` 后 `python -m pytest -q` 无回归。
- **B7**：写一个一次性脚本核对"事实源地图"每条指向的文件存在且不含冲突数字；人工抽读 3 份。
- **B8**：按新规范走一次完整流程（建分支 → 改一处 → 归档 5 字段 → 报告分支/提交号），确认可执行。
- **B10**：`docker compose up -d --build` → `/health` 200；`docker image inspect` 的 Python 版本符合决策。
- **B4/B5/B6**：新增对照测试（同输入两实现输出 diff / 生成物 diff 稳定 / 不装 `mcp` 时能 import 生产链路）。

### 4.4 每个动作的通用回滚（与 [CONSOLIDATION_PLAN.md](CONSOLIDATION_PLAN.md) 逐项一致）
| 动作类型 | 回滚手段 |
|---|---|
| 文件删除（**被 gitignore**：`logs/`、缓存、`data/.fuse_hidden`） | **不能用 git 恢复** → 执行前 `Compress-Archive` 备份到仓库外（见 §5） |
| 跟踪文件删除/编辑（`xx`、`README.md`、`.dockerignore`…） | `git checkout HEAD -- <path>`（提交前）/ `git revert <sha>`（提交后） |
| `git worktree remove` | `git worktree add logs/p6-wt work/20261023-phase6-arch-redesign` + 用 A1 的 patch 恢复 |
| `git commit` | `git reset --soft HEAD~1`（未推送） |
| `git branch -d` | `git branch <name> <sha>`（reflog 可找回） |
| 新增 `pyproject.toml`（B1） | 删除文件 + revert 19 处 import 改动 |
| 不可逆项（只有 C1） | **只能靠执行前完整 `git clone --mirror` 备份** |

---

## 5. 风险登记与执行护栏

| 风险 | 触发场景 | 护栏 |
|---|---|---|
| **R-a 不可逆删除** | A3/A4/A17 删的是被 gitignore 的本地目录 | 执行前：`Compress-Archive -Path logs -DestinationPath <仓库外>\logs_20261101.zip`；确认压缩包可读再删 |
| **R-b 顺序颠倒** | 先删 `logs/` 再 `worktree remove` → 悬挂注册 | 硬性顺序 A1→A2→A3→A4；A16 在 A2 后；A7 在 A6 后 |
| **R-c 决策抢跑** | 未答 Q1 就开工 B1 → 若最终要迁 `src/` 则白做 | 批次 2 的第一件事是**回答问题**，不是写代码 |
| **R-d 契约静默破坏** | B4/B5 改动两个 MCP server 之一 | 必须先有 B9 的对照测试；改动前记录 `search_disease` 的输入/输出样例作为 golden |
| **R-e 收口后反弹** | A 档做完但无门禁，3 个月内重新堆积 | Q5 必须包含"是否上 CI + coverage 门槛"；B8 的新规范必须写入"禁止根目录临时文件" |
| **R-f 误信旧数字** | 报告/文档继续引用 HEAD 版 README | A6 提交后统一以工作树=HEAD 为准；A8 完成后只保留单一数字 |

---

## 6. 本轮交付自检

- [x] **A 档顺序依赖正确**：A1（存档）→ A2（worktree remove）→ A3（整仓副本）→ A4（探针/散落脚本）严格串行；`A16` 明确标注须在 `A2` 之后（检出中的分支不可删除）；`A7` 建议在 `A6` 之后；`A8` 依赖 `A7`
- [x] **每项都有回滚方式**：A/B/C 三档共 39 项全部填写"回滚方式"列，并区分"可 git 恢复"与"不可 git 恢复（需备份）"
- [x] **B/C 未混入 A**：A 档 18 项全部满足"机械、可逆、无架构判断"；凡涉及契约/布局/文档权威的（B1–B10）与依赖外部条件的（C1–C11，含人类已定暂缓的 `.git` 重写）均未进入 A
- [x] **未新增阶段 1–2 未发现的问题**：39 项全部映射到 H-01～H-38（覆盖度对照见 [CONSOLIDATION_PLAN.md §4](CONSOLIDATION_PLAN.md)），无新编号
- [x] **未执行任何动作**：本轮仅写入 2 份报告；`git status` 应仅显示新增 `reports/CONSOLIDATION_PLAN.md`、`reports/NEXT_ACTIONS.md`
- [x] **人类决策问题 ≤5 且按阻塞排序**：Q1（4–6 人日的共同阻塞点）> Q2（最高风险）> Q3（数字治理）> Q4（最低成本、建议先答）> Q5（决定"基线"是否真实）

---

## 7. 批准的三种粒度（供选择）

| 粒度 | 范围 | 预计耗时 | 产出 |
|---|---|---|---|
| **最小** | 仅批次 0（A1–A4、A6–A8） | **约 2–3 小时** | 仓库可判断：worktree 干净、数字唯一、工作树=HEAD |
| **推荐** | 批次 0 + 批次 1（A1–A18 全部） | **约 2–3 人日**（含验证与三次三入口冒烟） | 仓库可判断 + 可复现：测试能跑、构建上下文瘦身、分支收敛、回收 ≥190 MB |
| **完整** | 全部 A + 回答 Q1–Q5 后启动批次 2 | **8–12 人日** | 从"原型"走到"工程基线"第一步：有包管理、有事实源、有规范 |

---

*三份报告的阅读顺序：[PROJECT_INVENTORY.md](PROJECT_INVENTORY.md)（现状）→ [PROJECT_HEALTH.md](PROJECT_HEALTH.md)（判断）→ [CONSOLIDATION_PLAN.md](CONSOLIDATION_PLAN.md)（清单）→ 本文件（路线与勾选）。*
