# ACIS 项目盘点报告（阶段 1：Inventory）

> **盘点对象**：`E:\knowledge_database\ACIS`（ACIS — 农业病害诊断与决策支持原型）
> **执行日期**：2026-11-01 ｜ **基线提交**：`main @ d2fa727`（2026-10-24 21:19 +0800）
> **方法**：3 路并行只读扫描（结构/依赖/配置、源码/测试/债务、文档/Git/冗余）+ Lead 主干深读与交叉验证。
> **只读声明**：本轮未修改/删除/移动任何项目文件，未执行任何 git 写命令、未改 git 配置、未安装依赖、未构建、未部署。
> **唯一写入**：本报告 + `reports/PROJECT_HEALTH.md` + 证据附录 `reports/_parts/*.md`。
> **证据约定**：所有结论标注 `路径:行号` 或命令输出摘要；`[待确认]` = 证据不足，`[推测]` = 启发式推断。
> **详细证据附录**：[inventory_structure.md](_parts/inventory_structure.md)（结构/入口/依赖/配置）、[inventory_code.md](_parts/inventory_code.md)（源码/测试/债务）、[inventory_docs_git.md](_parts/inventory_docs_git.md)（文档/Git/冗余）。

---

## 0. 一页速览

| 维度 | 实测值 | 证据 |
|---|---|---|
| 项目性质 | 单机离线可运行的**多阶段 AI 流水线工程原型**（非生产系统，自述无田间验证） | `README.md:1-10` |
| 源码规模 | **119 个 .py / 23,179 行**（代码行 19,229） | 附录 B1 |
| 测试 | 26 个测试文件 + `conftest.py`；静态 `def test_` = **316**；`pytest --collect-only` = **342 collected** | 附录 B7 |
| 版本库 | 96 提交（2 个根提交）；近 30 天 **50**、近 90 天 **80**；已静默 8 天 | `git rev-list --count` |
| 跟踪文件 | **235 个**；磁盘（排除缓存/.venv/.git）**5,681 个** → **95.9% 未跟踪且全部被 .gitignore 覆盖** | `.git/index` 解析 + `git ls-files` |
| 工作区 | **3 个已修改未提交**（`README.md`、`docs/DEMO_RUNBOOK.md`、`tests/test_planner.py`）；无 stash / 无 tag | `git status --porcelain` |
| 分支 | 本地 24 个：22 个已并入 main、1 个未合并（`codex/acis-implementation-plan` 领先 1 提交）、1 个仍被额外 worktree 检出 | `git branch -a -vv`、`git worktree list` |
| 磁盘占用 | `.venv` 1272 MB、`data` 266 MB、`.git` 255 MB、`.mypy_cache` 153 MB、`logs` 90.5 MB、`results` 56.8 MB | 目录实测 |
| 依赖 | `requirements.txt` 16 项 / `requirements.docker.txt` 10 项 / `requirements-lock.txt` 134 项锁定 | `requirements*.txt` |
| 打包 | **无 `pyproject.toml` / `setup.py` / `setup.cfg`**；靠 **19 处 `sys.path.insert`** 解析模块 | 附录 A6-2、B6-8 |
| 债务可视化 | `context/KNOWN_DEBT.md`（12 项）+ `context/EVIDENCE_LEDGER.md`（E007–E020）质量高于同类原型 | `context/*.md` |

**一句话盘点结论**：这是一个**"演示链路完整、研究证据留痕、但工程基线与仓库卫生未收口"**的原型仓——核心决策链路（CLI/TUI/API 三入口共用同一编排器）真实可用且实现度高；主要问题不在业务代码质量，而在**打包缺失、依赖/配置声明漂移、Git 与磁盘卫生、文档多重事实源**四类系统性债务。

---

## 1. 结构与模块划分

### 1.1 规模总表（排除生成物与依赖目录）

| 目录/单元 | 文件数 | 体积 | Python 文件 | 性质 |
|---|---:|---:|---:|---|
| `.venv/` | 44,533 | 1,272.3 MB | — | 本地虚拟环境（uv，Python 3.13.3） |
| `.git/` | 758 | 255.2 MB | — | 版本库（5 个 pack，`size-pack` 253.34 MiB） |
| `data/` | 191 | 266.0 MB | 8 | 本地数据：`agri.db`(1.79 MB)、`eval.db`(6.7 MB)、`Agriculture_KnowledgeGraph-master/`(245.4 MB, **vendored 第三方仓库**) |
| `results/` | 1,239 | 56.8 MB | 0 | 历史实验运行输出 |
| `logs/` | 4,177 | 90.5 MB | **483** | 运行产物 + **3 份整仓源码副本** + **1 个已登记 git worktree** |
| `.mypy_cache/` | 155 | 153.1 MB | — | mypy 缓存（体量异常） |
| `neo4j/` | 6 | 3.67 MB | — | docker 挂载用（`apoc.jar` 3.3 MB + 日志） |
| `tests/` | 27 | 1.75 MB | 27 | `conftest.py` + 26 个 `test_*.py` |
| `reports/` | 36 | 0.81 MB | 0 | 实验证据与验收报告 |
| `agents/` | 16 | 0.36 MB | 16 | 15 个 Agent + `types.py` |
| `benchmarks/` | 24 | 0.34 MB | 7 | 基准框架 + **5 份散落的能力报告 md** |
| `experiments/` | 18 | 0.33 MB | 10 | 实验管理（experiment-as-code） |
| `scripts/` | 7 | 0.25 MB | 6 | 5 个 CLI + `AGRiKG_SETUP.md` |
| `docs/` | 29 | 0.23 MB | 0 | 架构决策、演示手册、RFC001、`archive/`(26) |
| `evals/` | 11 | 0.23 MB | 10 | 固定夹具评测 |
| `src/` | 4 | 0.16 MB | 4 | `openmetaphysics/evaluation/`（Phase 4 评测工具包） |
| `rag/` | 3 | 0.13 MB | 3 | `knowledge_base.py`(548 行) + `retriever.py` |
| `utils/` | 7 | 0.12 MB | 5 | 校准/判定运行时 + 2 份校准 JSON |
| `debate/` | 3 | 0.11 MB | 3 | `engine.py` + `critic.py` |
| `rule_engine/` | 2 | 0.11 MB | 2 | 传感器异常检测（三层，可降级） |
| `ui/` | 3 | 0.11 MB | 3 | `tui.py`(560 行) + `web_app.py`(streamlit，未验证) |
| `trace/` | 4 | 0.08 MB | 4 | 10 阶段统一 Trace |
| `planner/` · `tool_router/` · `storage/` · `kg/` · `gateway/` · `context/` | 4/3/3/2/2/2 | 合计 ≈0.13 MB | 14 | 计划 / 路由 / 持久化 / KG MCP / API / 台账 |
| 根目录 | 21 文件 + 30 目录 | ≈0.1 MB | **5** | `orchestrator.py`、`workflow.py`、`kg_adapter.py`、`decision_semantics.py`、`_env.py` |

> 口径说明：`logs/` 下的 483 个 `.py` 与 `data/` 下的 8 个 `.py` **不计入源码量**（前者为整仓副本，后者为 vendored 第三方项目）。源码口径 = 119 个 `.py`，与附录 A/B 一致。

### 1.2 两层结构（实测，非设计文档转述）

```text
ACIS/
├─ orchestrator.py(347行)  workflow.py(186行)  _env.py(32行)  kg_adapter.py(532行)  decision_semantics.py(110行)   ← 平铺在仓库根
├─ agents/      感知(视觉/传感器/天气) + 记忆(RAG/KG/案例/经验) + 专家(病理/气象/栽培/经济/生态) + Judge
│               另含 MCP 形态底层实现：vision.py(294行, FastMCP+transformers)、weather.py
├─ debate/      DebateEngine + CriticEngine
├─ gateway/     FastAPI `app`（/health /diagnose /decisions /feedback /outcome）
├─ ui/          tui.py（rich，6 个演示场景）；web_app.py（streamlit，占位入口）
├─ planner/     ExecutionPlan（默认关闭，AGRI_AI_ENABLE_PLANNER=0）
├─ tool_router/ 只生成 ToolRequest，不执行施药/灌溉
├─ trace/       固定 10 阶段 Trace + JSON 导出
├─ rag/         Qdrant 优先 / 内存回退；**knowledge_base.py 同时是 MCP Server 且承载 DISEASE_DB**
├─ kg/          mcp_server.py（独立进程，9 个 @mcp.tool()）
├─ rule_engine/ 传感器异常检测（IsolationForest / Chronos / LSTM-AE 三层，缺库降级）
├─ storage/     SQLite `decisions` 审计表 + repository
├─ utils/       judge_runtime（端点/重试/脱敏）+ confidence_calibration（Platt/Isotonic）+ 2 份校准 JSON
├─ evals/       固定夹具评测（runner/ablation/metrics/report/fixtures）
├─ experiments/ 实验定义/管理/分析/归档/绘图（消费 evals + benchmarks）
├─ benchmarks/  数据集 schema/loader/taxonomy/capability_matrix（876+ 行巨文件）+ 5 份 md 报告
├─ scripts/     delivery_eval · challenge_evaluation · stability_report · fit_decision_calibration · import_agrikg
├─ src/         openmetaphysics/evaluation/（challenge_scorer 518 行、challenge_report 600 行，仅测试/脚本注入路径后可用）
├─ tests/       conftest.py + 26 个 test_*.py
├─ docs/        ARCHITECTURE_DECISIONS(ADR-001~005) · DEMO_RUNBOOK · rfc/RFC001 · archive/(26)
├─ context/     EVIDENCE_LEDGER.md · KNOWN_DEBT.md
├─ reports/     acceptance / experiment_audit / phase4-6 证据 / delivery_eval / archive/(16)
└─ neo4j/       import/(空) plugins/apoc.jar logs/*.log（全部 gitignore）
```

### 1.3 包级职责与证据（抽样核对）

| 单元 | 证据 |
|---|---|
| `agents/` | `orchestrator.py:12-13` 注释"Agent 类定义已拆分到 `agents/` 和 `debate/`"；`:56-68` 逐类 import |
| `debate/` | `orchestrator.py:69` `from debate.engine import DebateEngine`；`:128` `from debate.critic import CriticEngine` |
| `gateway/` | `gateway/app.py:1,25` FastAPI 应用；`:35,41,62,68,81,96` 六个路由 |
| `ui/` | `ui/tui.py:518,559` 可执行入口；`ui/web_app.py:275` 仅 `if __name__=="__main__": pass` |
| `planner/` `tool_router/` `trace/` | `orchestrator.py:27-29,131-134` 组装；各自 `__init__.py:1-5` 声明职责 |
| `rag/` `kg/` `rule_engine/` | `rag/retriever.py:33-48` 可用性探测→回退；`kg/__init__.py:1-7`；`rule_engine/sensor_anomaly.py:1-6` |
| `storage/` | `storage/db.py:16` `CREATE TABLE IF NOT EXISTS decisions` |
| `src/` | `src/openmetaphysics/__init__.py:1` "OpenMetaphysics package root (Phase 4 evaluation tooling)"；**无任何 orchestrator 实现** |

**结构判定要点**：项目采用**扁平根布局**——5 个核心模块直接平铺在仓库根，与 `agents/`、`gateway/` 等包同级。这是历史重构 `6a74817 "refactor: agri-ai 铺平至仓库根目录"` 的结果，不是污染；真正的结构问题在 §3 的打包缺失与 `src/` 的半迁移状态。

---

## 2. 入口点与运行方式

| 入口 | 启动命令 | 入口证据 | 复用同一编排器 | 状态 |
|---|---|---|---|---|
| **CLI** | `python orchestrator.py [--rules-only] [--seed N] [--json] [--trace-out P] [--image P] [--llm-judge] [--llm-critic] "问题"` | `orchestrator.py:308` `main()`、`:346` `__main__`、`:309-318` argparse | ✅ `orchestrator.py:112` | **真实可用**（`tests/test_cli_smoke.py:40-48` 以 subprocess 实跑） |
| **TUI** | `python -m ui.tui` | `ui/tui.py:518` `main()`、`:559` `__main__` | ✅ `ui/tui.py:46` | **真实可用**（恰好 6 个 `DEMO_SCENARIOS`，`:73-122`） |
| **API** | `uvicorn gateway.app:app --port 8000` | `gateway/app.py:25` 模块级 `app`；**无** `if __name__`/`uvicorn.run` | ✅ `gateway/app.py:20` | **真实可用**（`tests/test_delivery_contract.py:238` TestClient） |
| Web UI | 需 `streamlit run ui/web_app.py` | `ui/web_app.py:275` 仅 `pass`；**全仓 `streamlit run` 命中 0** | ✅ `ui/web_app.py:67` | **名存实亡**（README.md:79,197 自认未验证） |
| 评测脚本 | `python scripts/run_delivery_eval.py` 等 5 个 | 各自 `main()`/`__main__`（见附录 A2） | — | 4 个有文档/测试引用，`fit_decision_calibration.py` 无引用者 [推测：一次性工具] |
| 容器 | `docker compose up -d --build`（`start.ps1`/`start.sh` 封装） | `Dockerfile:18` CMD、`docker-compose.yml:1-72` | — | **未实测**（本环境无 Docker；`context/KNOWN_DEBT.md:13-14` 亦自述未验证） |

另有 **12 个带 `__main__` 的次级 CLI**（`evals/{runner,ablation,fixture_eval,smoke_eval}.py`、`experiments/manager.py:519`、`benchmarks/{capability_matrix,taxonomy}.py`、`kg/mcp_server.py:445`、`rag/{retriever,knowledge_base}.py`、`utils/generate_calibration.py:85`、`agents/vision.py:293`、`kg_adapter.py:531`、`src/.../challenge_report.py:599`），入口密度偏高（对使用者不友好，但均属工具性 CLI）。

---

## 3. 依赖

### 3.1 三份清单的关系：**范围差异，不是矛盾**

- `requirements.txt`：16 个直接依赖（`L5-36`），含 streamlit/transformers/torch/pillow/numpy/scikit-learn。
- `requirements.docker.txt`：10 个（`L11-20`），是 `requirements.txt` 的**真子集**，注释 `L1-8` 明示"torch/transformers/scikit-learn 有意不打包"。
- `requirements-lock.txt`：134 个 `==` 锁定（`L7-140`），文件头 `L1-6` 自述"Windows + Python 3.13.3 + 当前 `.venv` 的 pip freeze"，**非跨平台锁**。

裁剪安全性**已被代码验证**：视觉/异常检测/校准三条重依赖路径均为 `try/except` 懒加载降级——`agents/vision.py:114-120`、`rule_engine/sensor_anomaly.py:89-101,110-120`、`utils/confidence_calibration.py:73-80`。这是本项目一个**正面工程决策**。

### 3.2 声明缺失（代码在用、清单没写）

| 包 | 使用点 | 影响 |
|---|---|---|
| **pytest** | 18 处，全部 `tests/` | 按 `README.md:99-101` 装完依赖**不能跑测试** |
| matplotlib | `experiments/figures.py:22,25` | 仅锁文件经 streamlit 传递可得 |
| PyYAML | `experiments/schema.py:21` | 同上 |
| chronos | `rule_engine/sensor_anomaly.py:114,147` | `.venv` 亦无此包 → 该预测层**必然降级**为线性回归（`:104-134` 有捕获） |
| huggingface_hub | `rule_engine/sensor_anomaly.py:113`（直接 `import huggingface_hub.constants`） | 隐式依赖（transformers 传递） |

### 3.3 声明了但未使用 / 版本风险

| 项 | 证据 | 判定 |
|---|---|---|
| `pillow` | `requirements.txt:23`；全仓 `import PIL` 命中 0 | 疑似未使用 `[推测]` |
| `httpx` | `requirements.txt:6`；仅 `tests/test_judge_runtime.py:243` 引用 | 生产代码零引用 `[推测：冗余]` |
| `uvicorn` | 零 Python import | 非缺陷——以 CLI 形式由 `Dockerfile:18` 启动 |
| `langgraph>=0.2.0` vs 锁 `1.2.9` | `requirements.txt:13` / `requirements-lock.txt:57` | 跨大版本，API 兼容性未实测 `[待确认]` |
| `transformers>=4.40.0` vs 锁 `5.13.1` | `requirements.txt:21` / `requirements-lock.txt:128` | 同上 |
| `numpy 2.5.1` + `scikit-learn 1.9.0` | `requirements-lock.txt:74,111` | 组合兼容性未验证 `[推测]` |

---

## 4. 配置

### 4.1 配置清单与职责

| 文件 | 行数/体积 | 职责 | 关键事实 |
|---|---:|---|---|
| `.env.example` | 3,209 B / 29 键 | 配置模板 | `L11-67` 覆盖 LLM Judge/Critic、`AGRI_AI_*` 开关、SQLite、RAG/KG、离线开关 |
| `.env` | 631 B / 9 键 | 本地真实配置（值未读取、未输出） | 含 `DEEPSEEK_*`、`NEO4J_*`、`HF_HUB_OFFLINE`、`OPENCODE_*`；被 `.gitignore:11-13` 忽略 |
| `pytest.ini` | 7 行 | **唯一**测试配置源 | `testpaths=tests`(`:5`)；`norecursedirs` 显式排除 `logs results data neo4j pytest-of-lkl torchinductor_lkl`(`:6`)，注释 `:2-4` 直言仓库根有 "stray pytest-of-lkl/" |
| `docker-compose.yml` | 72 行 | api + qdrant + neo4j 三服务 | `8000:8000`(`:13`)、neo4j `17474:7474`/`7687`(`:49-51`)、qdrant `6333`(`:41`)、`.:/app` 绑定挂载(`:10`) |
| `Dockerfile` | 18 行 | API 镜像 | `FROM python:3.11-slim`(`:2`)；装 `requirements.docker.txt`；`CMD uvicorn gateway.app:app`(`:18`) |
| `.gitignore` | 86 行 | 忽略密钥/本地/可再生 | `L4-8` 声明"与 pytest.ini / .dockerignore 保持同步" |
| `.dockerignore` | 20 行 | 构建上下文裁剪 | 含 `data results tests .venv .git` 等，**缺 `logs`** |
| `_env.py` | 32 行 | 自研 `.env` 加载器 | `L16-28` `os.environ.setdefault` 不覆盖已有值；模块导入即执行(`:32`) |
| `.vscode/settings.json` | 1 行 | 编辑器 | `"python.terminal.useEnvFile": true` → 与 `_env.py` 属**两条并存的 .env 注入路径** |
| `.claude/settings.local.json` | 243 B | 工具权限（与本项目无关） | 仅存在于 `.claude/worktrees/amazing-bardeen-551868/` |

### 4.2 配置冲突与缺口

| # | 问题 | 证据 | 严重度 |
|---|---|---|---|
| C-1 | `.env.example` **缺 10 个代码实际读取的键**：`AGRI_AI_ABSTAIN_MIN_SUFFICIENCY`、`AGRI_AI_CALIB_ALPHA`、`AGRI_AI_CALIBRATION`、`AGRI_AI_COHERENCE_MODEL`、`AGRI_AI_JUDGE_SESSION_ID`、`AGRI_AI_KG_DRAFTS_LOAD/PATH/PROPOSE`、`AGRI_AI_PLANNER_MODEL`、`PYTHONIOENCODING` | `agents/judge_agent.py:270,593`、`utils/confidence_calibration.py:28,112`、`utils/judge_runtime.py:166,187`、`kg_adapter.py:449,458`、`planner/planner.py:130`、`ui/web_app.py:22` | 中 |
| C-2 | `.env` 含 2 个源码不读的键（`OPENCODE_BASE_URL`/`OPENCODE_API_KEY`），`utils/judge_runtime.py:147-156` 只用 host 字符串推断 provider | `.env` 键名对照 | 低 |
| C-3 | compose 硬编码 `NEO4J_PASSWORD: agriai2026`（`:23,58`），与 `.env.example:58` 默认值 `neo4j` 不一致 | `docker-compose.yml:23,58` vs `.env.example:58` | 低 |
| C-4 | `.dockerignore` 缺 `logs` → **构建上下文实测 4,209 文件 / 90.3 MB**，其中 `logs/` 占 4,177 文件 / 90.5 MB（含 3 份整仓源码副本） | `.dockerignore:1-20`；实测统计 | 中 |
| C-5 | compose 的 `.:/app` bind mount 让宿主树（含 `.env`）进入容器并**整体遮蔽镜像内容**，使 `.dockerignore` 对运行期失效 | `docker-compose.yml:10`；`_env.py:17` 会读 `/app/.env` | 中 |
| C-6 | `README.md:71,95` 声称 Python 3.13，`Dockerfile:2` 固定 3.11-slim；两套运行时 | `.venv/pyvenv.cfg` `version_info = 3.13.3` | 中 |
| C-7 | 无 lint/type 配置（`pyproject.toml`/`setup.cfg`/`tox.ini` 均不存在）→ `ruff`/`mypy` 只能跑默认规则 | 文件存在性命令验证 | 中 |

---

## 5. 测试

| 项 | 实测 | 证据 |
|---|---|---|
| 测试文件 | 26 个 `test_*.py` + `conftest.py`（共 27 py） | `tests/` 实测；与 `README.md:78` 一致 |
| 静态用例数 | `def test_` = **316**；`@pytest.mark.parametrize` = 9 处 | `rg -c` 统计 |
| 收集结果 | **342 collected**（含 2 个模块级 skip） | `pytest --collect-only -q -p no:cacheprovider`（未执行用例） |
| README 声称 | **344 个用例** / **342 passed + 2 skipped** | `README.md:78,169,171` |
| skip | 2 处，均为模块级 `pytest.importorskip`，指向**已被删除**的脚本 | `tests/test_phase4_harness_runtime.py:9-13`（`scripts.run_phase4_2`）、`tests/test_phase4_reliability.py:11-16`（`scripts.run_phase4_2_real_agent`，"removed in f1c7e98"） |
| xfail | 0 处 | `rg` |
| 框架配置 | `pytest.ini` 为唯一配置；无重复配置源 | 见 §4.1 |

**覆盖缺口（按 import 粗判）**：`rag/`、`kg/`、`rule_engine/`、`ui/` **零测试覆盖**——即 Qdrant 检索、Neo4j 图谱、传感器异常检测三层、TUI/Web 均无自动化保护。`kg_adapter.py` 的 Neo4j 路径、`kg/mcp_server.py`、`rag/knowledge_base.py` 的 MCP 工具面全部无测试。

**口径冲突（需一次实跑定案）**：`README.md:171` 的"342 passed / 2 skipped"与 `context/KNOWN_DEBT.md:8-10` 的"受限沙箱 340 passed / 3 failed、普通环境未复跑"直接冲突；而"344 用例"与实测 `342 collected` 差 2，差额恰好等于 2 个模块级 skip（`[推测]` 是把 skip 记为用例）。

---

## 6. Git 状态与活跃度

| 项 | 实测值 | 证据 |
|---|---|---|
| 当前分支 / HEAD | `main` @ `d2fa727`（与 `origin/main` 同点） | `git rev-parse --abbrev-ref HEAD` |
| 提交总数 | HEAD 可达 **96**；`--all` 97；**2 个根提交**（`3542e6c`、`74f92b4`，均 2026-07-02） | `git rev-list --count`、`git log --max-parents=0 --all` |
| 时间跨度 | 2026-07-02 → 2026-10-24 21:19（约 115 天） | `git log -1 --date=iso` |
| 近 30 / 90 天 | **50 / 80** 次提交（7 月 11、8 月 29、9 月 6、**10 月 50**） | `git rev-list --count --since=…` |
| 最近活动 | 2026-10-25 ~ 11-01 **0 提交**（静默 8 天） | `git rev-list --count --since/--until` |
| 未提交改动 | **3 个已修改、0 个未忽略未跟踪**：`README.md`（+87/−?）、`docs/DEMO_RUNBOOK.md`（+30）、`tests/test_planner.py`（−17/+14） | `git status --porcelain`、`git diff --stat` |
| stash / tag | **0 / 0** | `git stash list`、`git tag` |
| worktree | **2 个**：主树 `E:/…/ACIS`[main]；`E:/…/ACIS/logs/p6-wt`[`work/20261023-phase6-arch-redesign` @ `18abe26`] | `git worktree list` |
| 本地分支 | 24（main + 23）：**22 已并入 main**；**1 未合并** `codex/acis-implementation-plan`（领先 1 提交 `6de83b2 Save changes to tui.py`）；1 个仍被 worktree 检出 | `git branch -a -vv` |
| 远程 | 仅 `origin/main`、`origin/codex/acis-implementation-plan`、`origin/HEAD`；`sprint-04.5B-capability-contract` 上游 `gone` | `git branch -vv` |
| 跟踪 vs 磁盘 | tracked **235** vs 磁盘（排除缓存/.venv/.git）**5,681** → **95.9% 未跟踪**，且全部被 `.gitignore` 覆盖（logs 4,006 / results 1,239 / data 191 / 其它缓存） | `.git/index` 头解析 + `git ls-files` |
| 仓库体积 | `.git` **255.2 MB**，`size-pack` **253.34 MiB**（最大 pack 133.6 MB + 130.8 MB） | `git count-objects -vH` |
| 最大跟踪文件 | `reports/phase6_baseline_20261023/raw_results.json` **228,607 B**（其余 ≤133 KB） | `git ls-tree -r -l HEAD` |

**关键异常**：`.git` 的 253 MB pack 与"当前树 235 个文件、最大单文件 0.22 MB"**严重不匹配** → 大对象存在于**历史**而非当前树（`git log -- data/ results/ *.db .venv logs/` 无大目录入库记录）`[推测]`。

---

## 7. 文档

### 7.1 现行文档（17 组）

| 文档 | 规模 | 定位 |
|---|---|---|
| `README.md` | 216 行 | **现行事实源**（`docs/rfc/RFC001…:39` 明示）；工作树版比 HEAD 版大 4,449 B（有未提交修改） |
| `docs/rfc/RFC001-System Architecture.md` | 22,284 B | 架构规格权威（status Accepted v2.1.1，自带实现边界表） |
| `docs/ARCHITECTURE_DECISIONS.md` | 14,505 B | ADR-001~005；**front matter 仍写 `last_updated: 2026-07-10`**（`:11`） |
| `docs/DEMO_RUNBOOK.md` | 11,586 B | 3–5 分钟演示 + 故障注入 |
| `MODEL_AGENT_ORCHESTRATION.md` | 10,669 B | 小模型/Agent 编排设计说明；**README 文档导航未列它**，定位不明 `[待确认]` |
| `context/KNOWN_DEBT.md` | 46 行 | 12 项现行债务登记（质量高） |
| `context/EVIDENCE_LEDGER.md` | 41 行 | 证据台账 E007–E020（含 Untested/Superseded 状态，口径诚实） |
| `reports/README.md` | 37 行 | 报告索引 + accuracy 口径提醒 |
| `docs/archive/**` | 26 文件 | 9 份历史 RFC、10 份 Sprint 报告、vision/roadmap/changelog/current-sprint/architecture-state/architecture-principles |
| `benchmarks/` 内 5 份 md | 5 文件 | `CAPABILITY_*`/`COVERAGE.md` 报告与代码混放 |
| `scripts/AGRiKG_SETUP.md` | 6,103 B | AgriKG 导入说明 |

### 7.2 文档冗余：同一主题平均 **3.2 份**承载

| 主题 | 承载文档数 | 主要承载者 |
|---|---:|---|
| 测试与评测数字 | **8** | README §8、DEMO_RUNBOOK、KNOWN_DEBT、EVIDENCE_LEDGER、reports/README、changelog、current-sprint、RFC001 |
| 能力边界（真实/模拟/未实现） | **5** | README §2、MODEL_AGENT_ORCH、RFC001、KNOWN_DEBT、vision |
| accuracy = factor coverage 口径 | **4** | README §8、EVIDENCE_LEDGER、KNOWN_DEBT、reports/README |
| 系统分层/组件职责 | 4 | README、MODEL_AGENT_ORCH、RFC001、vision |
| 架构决策为何如此 | 4 | ADR、README、MODEL_AGENT_ORCH、RFC001 |

### 7.3 文档间硬冲突（9 处，全部可机械核对）

| ID | 冲突 | 证据 |
|---|---|---|
| D1 | 测试状态：README「本机复跑 342 passed / 2 skipped」vs KNOWN_DEBT「沙箱 340 passed / 3 failed，普通环境未复跑」 | `README.md:171,198` vs `context/KNOWN_DEBT.md:8-10` |
| D2 | 作物数量：README=4 作物/7 病害；MODEL_AGENT_ORCH=「番茄/甜菜/棉花三种」；代码=4 作物 | `README.md:25-26` vs `MODEL_AGENT_ORCHESTRATION.md:181`；`rag/knowledge_base.py:12-19` |
| D3 | ADR-005 标 Accepted（`:162`），文末却称「ADR-002~005 均为 Proposed」（`:240`） | `docs/ARCHITECTURE_DECISIONS.md:162` vs `:240` |
| D4 | 谁是事实源：RFC001 说 README；vision §5.2 把 README 排 Priority 5；archive/README 说归档非事实源；roadmap 以 `context/CURRENT_SPRINT.md` 为唯一源（该文件已删） | `RFC001:39`、`vision.md:362-366`、`archive/README.md:3-5`、`roadmap.md:15` |
| D5 | ADR-001 规定 `docs/architecture.md` 降级为指针，该文件已被 `f1c7e98` 删除 | `ARCHITECTURE_DECISIONS.md:43,239` |
| D6 | `reports/README.md:36` 称「原始 raw JSON 已移出公开仓库」，实际仍有 **5 份**（≈596 KB）被跟踪 | `git ls-files`；最大 228,607 B |
| D7 | `archive/architecture-state.md` 自称「模块稳定性唯一事实源」「Judge Frozen」，与 ADR-005 的 Judge 重构冲突 | `architecture-state.md:4,11` vs `ARCHITECTURE_DECISIONS.md:160-235` |
| D8 | `archive/current-sprint.md` 引用的 3 个脚本 / 4 个报告路径全部不存在 | `current-sprint.md:46,53-54` |
| D9 | 根 `AGENTS.md` 已被删除（`f1c7e98`），其规定的归档目录 `context/archive/` 同批删除 | `xx:4`、`xx:21-40`；3 份副本仅存于 `logs/`（同一 blob `962ae16`） |

### 7.4 文档 vs 实现核对（22 项机械验证）

**18 项一致**（26 个测试文件、4 作物/7 病害、Python 3.13.3、`workflow.py:37` StateGraph、`orchestrator.py:172-178` 回退、`gateway/app.py:25`、`judge_agent.py:73` fallback code、`trace/types.py:36-47` 10 阶段、`storage/db.py:16` decisions 表、TUI 6 场景、12/12 离线评测与 0.6583 平均置信度、Phase 6 的 72/72 与 C0/C1/C2 数字、191/216 回退、accuracy 口径、文档导航 6 链接、LICENSE 等）。
**2 项脱节**：D2（三种作物）、`MODEL_AGENT_ORCHESTRATION.md:146` 的 `agri-agent-mvp/scripts/...` 路径已失效。
**2 项待确认**：用例数 344 vs 342；`README.md:130` 示例置信度 72% vs `reports/delivery_eval` 同案 74%（运行配置不同，非同一条件）。

> 结论：README 的**可机械核对项准确率 18/22**，属于诚实度较高的项目自述；但多文档并存的复述层（D1/D4/D6/D7）会持续产生"引用即失真"风险。

---

## 8. 未完成工作与遗留物

### 8.1 代码内的债务标记（极少）

全仓源码 `TODO|FIXME|HACK|XXX|deprecated` **仅 3 处命中**：

| 路径:行号 | 内容 |
|---|---|
| `utils/confidence_calibration.py:5` | 模块 docstring："TODO: 迁移到 sklearn LogisticRegression" |
| `utils/confidence_calibration.py:79` | 同类 TODO（代码内重复声明） |
| `agents/vision.py:235` | 注释"清理临时文件"（"临时"为语义用词，非债务标记） |

`FIXME`/`HACK`/`XXX`/`deprecated` **0 处**；`bare except:` **0 处**（历史 `0111465` 的 lint 清偿有效）。**注释掉的大段可执行代码块 0 个**——不存在"旧实现以注释形式堆积"。

### 8.2 真实的未完成工作（集中在登记文档，而非代码标记）

`context/KNOWN_DEBT.md` 12 项，与代码交叉核对后可确证的核心 6 项：

| 债务 | 代码/证据 | 与盘点一致性 |
|---|---|---|
| 全量测试未在普通环境验证 | `README.md:171` 与 `KNOWN_DEBT.md:8-10` 冲突 | ✅ 一致（§5） |
| 依赖锁平台绑定 | `requirements-lock.txt:1-6` | ✅ 一致 |
| Docker 未构建验证 | `Dockerfile`/`docker-compose.yml` 存在但未实测 | ✅ 一致（§2） |
| accuracy 字段名未重命名 | `scripts/generate_stability_report.py:66-75` 仍用历史字段 | ✅ 一致 |
| ECE 分箱浮点误差 | `src/openmetaphysics/evaluation/challenge_scorer.py:154` `int(conf/bin_size)` | ✅ 一致（未改动） |
| 架构收益未证明（C1 未优于 C0） | `README.md:177-190`、`EVIDENCE_LEDGER.md:16-17`（E012 Untested） | ✅ 一致（学术口径诚实） |

### 8.3 功能层面的"已声明未实现"

| 项 | 证据 | 说明 |
|---|---|---|
| 工具执行 | `tool_router/router.py` 只生成 `ToolRequest` | README.md:36 已自认"只生成请求，不执行施药/灌溉" |
| Web UI | `ui/web_app.py:275` 占位 `pass` | 无文档化启动命令 |
| Planner | 默认关闭（`AGRI_AI_ENABLE_PLANNER=0`） | 开启只生成计划，不自动执行 |
| 图片识别 | 默认 mock；真实 Swin 模型路径存在但**效果未验证** | `agents/vision.py:1-20`、`README.md:34` |
| MCP 服务 | `kg/mcp_server.py`、`rag/knowledge_base.py`、`agents/vision.py` 各建 `FastMCP` | 三者均未纳入测试；是否同时部署 `[待确认]` |

### 8.4 孤立脚本与死代码

| 项 | 证据 | 判定 |
|---|---|---|
| `scripts/fit_decision_calibration.py` | 无任何代码/测试 import；仅 `docs/archive/changelog.md:8`、`reports/phase6_redesign_20261023/implementation_status.md:22` 提及 | 孤立脚本 `[推测：一次性工具]` |
| 2 个永久 skip 测试 | `tests/test_phase4_*` 指向已删脚本 | 空壳，永久跳过 |
| `evals/{fixture_eval,smoke_eval}.py`、`experiments/manager.py`、`kg/mcp_server.py`、`ui/tui.py`、`ui/web_app.py`、`utils/generate_calibration.py` | 无外部 import，但均有文档/`__main__` 入口 | **非死代码**（手动入口） |
| 根 `xx`（15,082 B，**被 git 跟踪**） | 内容是 `git diff --stat` 终端转储（首行 LF/CRLF 告警，末行 `xx | 214 +` 自引用） | **垃圾且误入库** |
| `logs/gitconfig.local` | 93 B，含 `[safe] directory = E:/knowledge_database/ACIS` + user 信息 | 本地残留 |

---

## 9. 重复与冗余

### 9.1 先回答最关键的疑问：根目录 4 个文件是不是"废弃副本"？

**不是。根目录 `orchestrator.py` / `workflow.py` / `kg_adapter.py` / `decision_semantics.py` 全部是被使用的真实现，仓库内不存在同职责第二份实现。**

| 根文件 | 被谁 import（抽样） | 唯一性 |
|---|---|---|
| `orchestrator.py` | `gateway/app.py:20`、`ui/tui.py:46`、`ui/web_app.py:67`、`evals/runner.py:57`、`evals/fixture_eval.py:20`、`evals/smoke_eval.py:20`、`scripts/run_delivery_eval.py:42`、`utils/generate_calibration.py:24`、`tests/test_delivery_contract.py:19`、`tests/test_cli_output.py:7` | 全仓仅 1 个 `class AgentOrchestrator`（`orchestrator.py:112`） |
| `workflow.py` | `orchestrator.py:235`（方法内延迟 import） | 全仓仅 1 个 `class AgricultureWorkflow`（`:32`） |
| `kg_adapter.py` | `agents/judge_agent.py:20`、`kg/mcp_server.py:29`、`ui/web_app.py:94` | 唯一 KG 混合检索门面（`:396` `query_kg`） |
| `decision_semantics.py` | `agents/judge_agent.py:17-19`、`evals/metrics.py:17`、`src/…/challenge_report.py:52-53`、`src/…/challenge_scorer.py:34-45`、`scripts/generate_stability_report.py:40`、`tests/test_decision_confidence.py:10` | 唯一决策语义定义（`:26-101`） |

补充：`src/` **不是** orchestrator 的替代实现，而是 Phase 4 评测工具包（`src/openmetaphysics/__init__.py:1`；仅 scorer/report 共 4 文件；`rg 'AgentOrchestrator' src` 无命中），靠 `tests/conftest.py:10-11` 把 `src/` 注入 `sys.path` 才能在测试中 import。

### 9.2 真实存在的重复（按风险排序）

| # | 重复对象 | 性质 | 证据 | 风险 |
|---|---|---|---|---|
| R-1 | **两套 MCP Server 暴露同名工具与资源**：`kg/mcp_server.py`（446 行，9 个 `@mcp.tool()`）与 `rag/knowledge_base.py`（548 行，5 个 `@mcp.tool()`）都有 `search_disease` 与 `knowledge://diseases` | 职责重叠的真重复 | `kg/mcp_server.py:144-145,428-429` vs `rag/knowledge_base.py:371-372,535-536`；且 `kg/mcp_server.py:41` 还引用**已不存在**的 `knowledge_mcp_server.py` | **高** |
| R-2 | **两套能力矩阵生成器写同一对产物** `CAPABILITY_MATRIX.md` + `COVERAGE.md` | 同产物双写 | `benchmarks/taxonomy.py:258-262,271-275,300-301` vs `benchmarks/capability_matrix.py:277-284,447,563-567`；各自有 `__main__`（`taxonomy.py:11`、`capability_matrix.py:26`）→ **谁最后跑谁生效** | 中高 |
| R-3 | `agents/vision.py`(294 行)/`agents/vision_agent.py`(30 行)、`agents/weather.py`(46 行)/`agents/weather_agent.py`(14 行) | 实现 + 薄包装（非逻辑重复） | `vision_agent.py:14` 函数内延迟 import；`weather_agent.py:4` | 低（命名前缀易误判） |
| R-4 | `src/openmetaphysics/.../challenge_scorer.py` 内的 `is_abstention`/`normalize_decision_label`/`_decision_text`/`_is_abstention` | **委托转发**，非复制 | `challenge_scorer.py:34-45` import 自 `decision_semantics`，函数体仅 `return _shared_*()`（`:172,181,370,421`） | 低（语义唯一源正确） |
| R-5 | 同名模块：`types.py`×4、`report.py`×2、`schema.py`×2 | 命名撞车 | `agents/ planner/ tool_router/ trace/types.py`；`evals/ experiments/report.py`；`benchmarks/ experiments/schema.py` | 低（当前 import 路径唯一，无实际冲突） |
| R-6 | `evals/report.py` vs `experiments/report.py`；`benchmarks/capabilities.py` vs `evals/capability_metrics.py` | **非重复**（职责不同） | 前者 `write_metrics_csv`/`write_ablation_report`；后者 `generate_report` | — 排除误报 |

### 9.3 其他冗余

- `benchmarks/` 目录内混放 **5 份能力报告 md**（`CAPABILITY_MATRIX.md`、`COVERAGE.md`、`CAPABILITY_CONSISTENCY_REPORT.md`、`CAPABILITY_ANNOTATION_SUGGESTIONS.md`、`CHALLENGE_SET_V1_REPORT.md`）→ 代码目录承担文档职责。
- `docs/archive/` 与现行文档重复覆盖同一主题（见 §7.2），`archive/changelog.md:3-25` 与 `ARCHITECTURE_DECISIONS.md:207-224` 重复记录 ADR-005 结果。
- `logs/` 内 **3 份整仓源码副本**：`logs/delivery_audit_20261024/env/clean`(125 py)、`logs/p6-exp`(122 py)、`logs/p6-wt`(120 py) → 使全仓 grep/import 统计在默认口径下失真（实测 `mcp` 词匹配 185 次 vs 源码真实 import 3 次）。

---

## 10. 债务信号（规模 / 耦合 / 坏味道）

### 10.1 超长文件（>500 行共 12 个）

| 文件 | 总行 | 备注 |
|---|---:|---|
| `benchmarks/capability_matrix.py` | 987 | 单文件 30 个函数（`:89-952`） |
| `tests/test_challenge_evaluation.py` | 726 | — |
| `scripts/generate_stability_report.py` | 662 | — |
| `agents/judge_agent.py` | 661 | **单个类占 575 行**（`:86` 起） |
| `src/…/challenge_report.py` | 600 | — |
| `ui/tui.py` | 560 | 接近阈值 |
| `experiments/analysis.py` | 556 | — |
| `rag/knowledge_base.py` | 548 | 同时是 MCP Server + 领域知识库 |
| `evals/report.py` | 535 | — |
| `kg_adapter.py` | 532 | 根目录 |
| `experiments/manager.py` | 520 | — |
| `src/…/challenge_scorer.py` | 518 | — |

### 10.2 耦合与依赖图

- 跨单元 import 边（按语句计）主干：`(根) → agents` 14、`tests → benchmarks` 23、`tests → evals` 16、`evals → (根)` 4、`experiments → evals` 7、`gateway → storage` 4、`src → (根)` 6。
- 分层链条清晰：`benchmarks ← evals ← experiments`、`agents ← (根) ← gateway/ui/tests`。
- **双向依赖 2 处，均为调用期延迟 import，import 期不成环**（安全但耦合方向双向）：
  - `orchestrator.py:235`（方法内 `from workflow import compile_workflow`）↔ `workflow.py:62`（节点内 `from orchestrator import build_context`）；
  - `(根) ↔ agents`：`orchestrator.py:55-69` 模块级 import agents，`agents/judge_agent.py:17-20` 模块级 import 根模块 `decision_semantics`/`kg_adapter`；经核对 `decision_semantics.py`/`kg_adapter.py` 不反向 import，**不构成真循环**。
- 显式"为避免循环"的局部 import：`benchmarks/loader.py:79`（注释 `# local: avoid cycle`）；`planner/planner.py:20` `from planner import prompts`（依赖 `__init__` 再导出，脆弱）。
- **[结构性根因] `sys.path` 手工注入 19 处**：`tests/conftest.py:8,11`、`gateway/app.py:9`、`ui/tui.py:17`、`ui/web_app.py:15`、`kg/mcp_server.py:27`、`evals/{ablation,fixture_eval,runner,smoke_eval}.py`、`scripts/` 4 处、`utils/generate_calibration.py:19`、`src/…/challenge_report.py:50`。因为**仓库无 `pyproject.toml`/`setup.py`**，每个入口都必须自己"垫路径"——这也是 E402 告警的来源（`KNOWN_DEBT.md:42-45` 已登记）。

### 10.3 坏味道统计

| 类别 | 实测 | 说明 |
|---|---|---|
| `bare except:` | **0** | 历史 E722 已清偿 |
| `except Exception` | **45** 处（`rule_engine/sensor_anomaly.py` 7、`kg_adapter.py` 6、`agents/judge_agent.py` 5、`ui/web_app.py` 4…） | 多数是**有意的降级边界**并附 `# noqa: BLE001` 或注释（如 `gateway/app.py:48` "boundary: never leak a bare 500"） |
| 静默吞异常 | **2** 处：`ui/web_app.py:148` `except Exception: pass`（删除临时上传图）、`debate/engine.py:16` `except Exception: return None`（取湿度失败） | 前者位于未测试的 streamlit 路径 |
| 硬编码绝对路径 | 代码 **0** 处 | 本地地址均为"环境变量 + 默认值"（`kg_adapter.py:196`、`rag/retriever.py:21`、`planner/planner.py:128`） |
| 超长函数 | 1 个 >100 行（`agents/judge_agent.py:340` `_run_llm_judge`，121 行）；>60 行 8 个 | 度量为 dedent 启发式 `[推测]` |
| 魔法数 | `workflow.py:178` `0.6 <= confidence <= 0.85`；`judge_agent.py:264,295,542,544,593,595`；`debate/critic.py:151-152,189`；`planner/planner.py:94` | 部分可经环境变量覆盖，其余写死 |
| 阻塞 sleep | 1 处 `ui/tui.py:282` `time.sleep(0.07)`（演示逐字打印） | 不在核心链路 |
| 关键词硬编码上下文解析 | `orchestrator.py:72-99`（温室/作物/意图全 if-else 关键词表） | 原型可接受 `[推测]` |
| 代码风格一致性 | 127 个 `.py` 中 **99 个** 用 `from __future__ import annotations`（缺省的 28 个分散在各包 1–2 个）；**114 个**有模块 docstring；含 Tab 的文件 7 个 | 整体一致，边缘不齐 |

---

## 11. 磁盘占用与历史垃圾

### 11.1 可回收量估算

| 目标 | 体积 | 性质 | 处置前须知 |
|---|---:|---|---|
| `.venv/` | 1,272.3 MB | 可再生 | 重建需网络 |
| `data/` | 266.0 MB | 本地数据，其中 `Agriculture_KnowledgeGraph-master/` 245.4 MB 是 **vendored 第三方 GitHub 仓库**（`hudong_pedia.json` 单文件 110.9 MB、另有 47.0 MB / 44.3 MB zip / 16.0 MB zip / 11.1 MB csv） | 是 AgriKG 导入的源数据；`scripts/import_agrikg.py` 依赖 |
| `.git/` | 255.2 MB | 历史 | 与当前树规模严重不匹配（见 §6） |
| `.mypy_cache/` | 153.1 MB | 可再生 | — |
| `logs/` | 90.5 MB / 4,177 文件 | 历史运行产物 | **内含 1 个已登记 git worktree，直接删会损坏 worktree 注册** |
| `results/` | 56.8 MB / 1,239 文件 | 历史运行输出 | `context/EVIDENCE_LEDGER.md:29` 说明 Phase 2 数据"不公开" |
| `neo4j/logs/` | 0.55 MB | 运行日志 | — |
| 缓存（`__pycache__` 57 处、`.ruff_cache`、`.pytest_cache`） | ≈0.3 MB | 可再生 | — |

粗略合计：**工作区约 570 MB 可回收**（`.venv` 不计入"项目资产"）；`.git` 若做历史重写最多再省约 250 MB `[推测，取决于是否保留历史上游大对象]`。

### 11.2 `logs/` 逐目录性质（4,177 文件 / 90.5 MB）

| 子目录 | 文件 / 体积 | 性质 |
|---|---|---|
| `phase4_2_real_agent/` · `phase4_2_r2/` · `phase4_2_r3/` | 469·459·459 / 15.4·15.2·14.9 MB | Phase 4.2-R 三轮整跑产物 |
| `delivery_audit_20261024/` | 736 / 13.1 MB | 交付审计；`env/clean` 是**整仓副本**（125 py/115 md，含 AGENTS.md） |
| `p6-exp/` | 384 / 6.0 MB | **整仓副本**（122 py / 92 md） |
| `phase6_baseline_20261023/` | 155 / 5.4 MB | Phase 6 基线 run |
| `p6-wt/` | 277 / 3.6 MB | **已登记 git worktree**（`work/20261023-phase6-arch-redesign @ 18abe26`），含 `.git` 指文件、整仓检出、**3 个未提交修改** |
| `phase6_ablation_20261024/` · `phase6_ab_seed42_20261024/` | 103·103 / 3.4·3.5 MB | 消融 run |
| `phase4_2_r3_stress/` · `phase4_2/` | 120·217 / 2.7·0.6 MB | 压测 / 早期 run |
| `phase6_sc_*` / `phase6_sc43_*` / `phase6_redesign_*` / `phase6_gateoff_*` / `phase4_judge_recovery_*` | 53·52·3·1·24 | 自一致性采样与专项验证 |
| `eng_audit_tmp{,2,3,4,5,6}, _cleanup, _planner` | 1·130·9·0·139·139·9·3 ≈1.1 MB | **沙箱/ACL 探针副本**：内容为 `pytest-of-lkl/pytest-0/...` 与 `torchinductor_lkl` 骨架 |
| `logs/` 根散落 | 114 / ≈0.5 MB | **82 个一次性 `.py` 审计/重算脚本** + 11 `.ps1` + 8 `.txt` + 7 `.json` + 3 `.bin`（`status_z*.bin` 为 `git status` 二进制快照）+ `_wip.diff` + `gitconfig.local` |

### 11.3 特殊：被 gitignore 的目录里藏着一个 git worktree

`git worktree list` → `E:/knowledge_database/ACIS/logs/p6-wt  18abe26 [work/20261023-phase6-arch-redesign]`。
即：`.gitignore:41` 忽略的 `logs/` 内部，存在一个**被版本库登记的活跃工作树**，且该工作树有 3 个未提交修改（`context/CURRENT_SPRINT.md`、`docs/ARCHITECTURE_DECISIONS.md`、`reports/phase6_redesign_20261023/final_evidence.md`）。

**这是本仓最容易踩的清理地雷**：直接 `rmdir logs` 会留下 `.git/worktrees/p6-wt` 悬挂注册并丢失那 3 处未提交状态。该分支已 **0 提交领先 main**（`git rev-list --count main..work/20261023-phase6-arch-redesign` = 0），技术上可安全移除，但顺序必须是 `git worktree remove`（写操作）→ 再清理目录。

---

## 12. 证据索引（结论 → 原始出处）

| 结论 | 主证据 |
|---|---|
| 三入口真实且共用同一编排器 | `orchestrator.py:112,308,346`；`ui/tui.py:46,518,559`；`gateway/app.py:20,25` |
| Web 入口名存实亡 | `ui/web_app.py:275`；全仓 `streamlit run` 命中 0 |
| 根 4 模块是真实现 | 10 处 import（§9.1 表）；全仓唯一 `AgentOrchestrator` |
| `src/` 是 Phase 4 评测包 | `src/openmetaphysics/__init__.py:1`；`tests/conftest.py:10-11` |
| 双 MCP Server 同名工具 | `kg/mcp_server.py:144-145,428-429` vs `rag/knowledge_base.py:371-372,535-536` |
| 双能力矩阵生成器 | `benchmarks/taxonomy.py:300-301` vs `capability_matrix.py:277-284` |
| 打包缺失 + 19 处 sys.path | 无 `pyproject.toml`/`setup.py`；注入点见 §10.2 |
| `agents/` 无 `__init__.py` | 目录实测；`orchestrator.py:55-68` 仍可 import（命名空间包） |
| 依赖声明缺口 | `requirements*.txt` vs `tests/`（pytest 18 处）、`experiments/figures.py:22`、`experiments/schema.py:21`、`rule_engine/sensor_anomaly.py:113-114` |
| Docker 上下文 90.3 MB | `.dockerignore` 无 `logs`；实测 4,209 文件 |
| 3 个未提交改动 | `git status --porcelain` + `git diff --stat` |
| 95.9% 文件未跟踪 | tracked 235（`.git/index`）vs 磁盘 5,681 |
| `.git` 255 MB 与树不匹配 | `git count-objects -vH`；最大跟踪文件 228,607 B |
| `xx` 误入库 | `git ls-files` 含 `xx`；内容为 diff --stat 转储 |
| worktree 藏在 logs/ | `git worktree list` |
| 文档 9 处硬冲突 | §7.3 表（D1–D9） |
| AGENTS.md 被删且副本同一 blob | `xx:4`；3 份 `logs/*/AGENTS.md` hash = `962ae16` |
| 测试口径冲突 | `README.md:171` vs `context/KNOWN_DEBT.md:8-10`；实测 342 collected |

---

## 13. 本轮未确认清单（`[待确认]`）

| # | 事项 | 阻塞原因 |
|---|---|---|
| 1 | 全量测试的真实通过数（342 passed / 2 skipped 还是 340/3） | 只读约束下未执行用例（会写 `.pytest_cache`）；仅确认 `342 collected` |
| 2 | "344 个用例"的确切口径 | 静态 316 + 9 处 parametrize 无法静态展开；与 342 collected 差 2 的成因需实跑确认 |
| 3 | `.git` 253 MB pack 的具体构成 | 需索引化逐项排序；当前只能判定"历史大对象" `[推测]` |
| 4 | `pytest-of-lkl/`、`.claude/pytest_tmp_base/` 的内容与体积 | 目录枚举被 ACL 拒绝（`Access denied`） |
| 5 | `logs/phase4_2_*`、`eng_audit_tmp*` 各目录精确用途 | 仅按命名/内含物/mtime 推断，未逐目录读正文（含巨型 JSON） |
| 6 | 双 MCP Server 是否有意同时部署 | 无运行/部署证据 |
| 7 | `README.md:130` 示例 72% vs `delivery_eval` 74% 是否同条件 | 两处运行配置（RAG/KG/持久化开关）不同 |
| 8 | `MODEL_AGENT_ORCHESTRATION.md` 的定位（设计参考 vs 应归档） | 无现行文档明示；README 文档导航未列 |
| 9 | `scripts/fit_decision_calibration.py` 是否为在用的运维脚本 | 无测试、无 import、仅历史文档提及 |
| 10 | 3 个未提交改动的意图与归属 | 只读盘点不判断工作树改动归属 |
| 11 | Docker/Neo4j/Qdrant 链路是否真能跑通 | 本环境无 Docker；`KNOWN_DEBT.md:13-14` 自述未构建 |
| 12 | 依赖锁与当前 `.venv` 是否一致 | 未运行 `pip freeze`/`pip check`（会写盘） |

---

*本报告为阶段 1（盘点）产物。诊断结论与状态分类见 [PROJECT_HEALTH.md](PROJECT_HEALTH.md)。*
