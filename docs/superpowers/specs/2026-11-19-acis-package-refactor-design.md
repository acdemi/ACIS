# ACIS 包化重构设计（2026-11-19）

## 状态

- 状态：已批准（2026-11-19）
- 范围：目录精简、单一 `acis/` 包、入口统一、有限鲁棒性加固
- 原则：**行为不变**。诊断逻辑、Agent 行为、LLM 策略、输出契约、Web 前端均不改动。

## 1. 背景与问题

当前仓库的运行时 Python 代码只有约 40 个文件、约 1.6 万行，却被平铺在 20 多个顶层目录中，并依赖：

- 仓库根目录在 `sys.path` 中，使用 `from orchestrator import ...` 这类扁平导入；
- 多个模块在 import 时执行 `load_env()`，产生隐式副作用；
- `storage/db.py` 在 import 时读取相对路径 `data/agri.db`，路径依赖当前工作目录；
- 没有 `pyproject.toml`，包元数据、lint、pytest 配置分散；
- 工作区存在大量未跟踪垃圾：`logs/` 内嵌 3 份完整项目副本（共 1,097 个文件）、pytest 临时根、torch inductor 缓存、smoke 目录、根目录 `xx`（git diff 转储）。

这些因素降低了集成度、可读性和可移植性，也使测试与部署对启动目录敏感。

## 2. 目标结构

```
ACIS/
├── acis/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── types.py
│   │   ├── orchestrator.py
│   │   ├── workflow.py
│   │   └── decision.py
│   ├── agents/
│   ├── knowledge/
│   │   ├── rag/
│   │   ├── kg/
│   │   └── storage/
│   ├── reasoning/
│   │   ├── debate/
│   │   ├── planner/
│   │   ├── rule_engine/
│   │   └── tool_router/
│   ├── observability/
│   │   └── trace/
│   ├── evaluation/
│   │   ├── evals/
│   │   ├── benchmarks/
│   │   ├── experiments/
│   │   └── openmetaphysics/
│   ├── api/
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── demo_cases.py
│   │   └── tui/
│   └── utils/
├── scripts/
├── tests/
├── web/
├── docs/
├── reports/
├── data/
├── orchestrator.py          # 公开 CLI 兼容 shim
├── ui/                      # 薄弃用 shim（python -m ui.tui）
├── pyproject.toml
└── README.md 等
```

顶层工程目录从 20+ 个减少到约 8 个。

## 3. 模块映射

| 现路径 | 目标路径 |
|---|---|
| `agents/` | `acis/agents/` |
| `agents/types.py` | `acis/core/types.py` |
| `orchestrator.py` | `acis/core/orchestrator.py`；根目录保留 launcher |
| `workflow.py` | `acis/core/workflow.py` |
| `decision_semantics.py` | `acis/core/decision.py` |
| `_env.py` | `acis/config.py` |
| `rag/` | `acis/knowledge/rag/` |
| `kg/` | `acis/knowledge/kg/` |
| `kg_adapter.py` | `acis/knowledge/kg/adapter.py` |
| `storage/` | `acis/knowledge/storage/` |
| `debate/` | `acis/reasoning/debate/` |
| `planner/` | `acis/reasoning/planner/` |
| `rule_engine/` | `acis/reasoning/rule_engine/` |
| `tool_router/` | `acis/reasoning/tool_router/` |
| `trace/` | `acis/observability/trace/` |
| `evals/` | `acis/evaluation/evals/` |
| `benchmarks/` | `acis/evaluation/benchmarks/` |
| `experiments/` | `acis/evaluation/experiments/` |
| `src/openmetaphysics/` | `acis/evaluation/openmetaphysics/` |
| `gateway/` | `acis/api/` |
| `ui/` | `acis/ui/` |
| `utils/` | `acis/utils/` |
| `context/` | `docs/context/` |

`scripts/`、`tests/`、`web/`、`docs/`、`reports/`、`data/` 保持顶层。

## 4. 导入与入口

### 导入

- 所有运行时导入改为绝对包导入：`from acis.core.orchestrator import AgentOrchestrator`。
- 循环依赖处理：共享契约 `AgentOutput` / `RequestContext` / `DebateResult` / `DecisionOutput` 位于 `acis.core.types`，不反向依赖 Agent 或编排器。
- 不再依赖 `PYTHONPATH=.`；`pip install -e .` 或从仓库根运行均可。

### 入口

| 入口 | 形式 |
|---|---|
| CLI | `python -m acis`、`acis` console script |
| 兼容 CLI | `python orchestrator.py ...`（薄 shim） |
| API | `uvicorn acis.api.app:app` |
| TUI | `python -m acis tui`；`python -m ui.tui` 保留弃用提示 shim |
| 评测 | `python -m acis eval ...` 与 `scripts/run_delivery_eval.py` 双入口 |
| 自检 | `python -m acis doctor` 检查 Python、依赖、数据目录、API Key 配置 |

`acis.bat`、`scripts/start_acis.ps1`、`start.sh`、`Dockerfile`、`docker-compose.yml`、`web/e2e/start-server.mjs` 同步更新为 `acis.api.app:app`。

## 5. 鲁棒性改动

1. **路径解析**：`acis/config.py` 通过包位置定位仓库根，提供 `project_root()`、`data_dir()`、`db_path()`、`web_dist_dir()`；相对路径一律基于仓库根或显式环境变量解析。
2. **显式初始化**：`load_env()` 幂等且仅在入口调用；移除 `orchestrator`、`gateway`、`tui` 在 import 时的 `load_env()`。
3. **SQLite**：连接设置 `busy_timeout=5000`，提供上下文管理器，路径由配置函数提供。
4. **API**：
   - 启动时校验 `ACIS_API_KEY`（≥ 32 ASCII 字符），缺失时返回明确错误；
   - 统一异常处理与结构化日志，错误响应不包含密钥或堆栈；
   - 保留现有鉴权、图片大小/像素/格式限制。
5. **CLI**：保留 `_print_safe`；统一退出码与可操作的错误消息。
6. **工具链**：`pyproject.toml` 承载包构建、console scripts、ruff、pytest 配置；删除根 `pytest.ini`。
7. **测试**：
   - 新增 `tests/test_package_imports.py`：导入所有 `acis` 子包，防止遗漏；
   - 新增 `tests/test_config_paths.py`：验证 cwd 无关的路径解析；
   - 更新现有测试的导入路径。

## 6. 清理清单

删除（可再生或重复）：

- `logs/p6-exp/`（384 文件）、`logs/p6-wt/`（277 文件）、`logs/delivery_audit_20261024/env/clean/`（436 文件）
- `pytest-of-lkl/`、`web/pytest-of-lkl/`
- `torchinductor_lkl/`
- `.acis-ui-smoke-local/`
- `.acis_delivery_eval_verify_20261119/`
- 根目录 `xx`
- `acis_delivery_eval.db`
- 根 `__pycache__/`、`.mypy_cache/`、`.ruff_cache/`、`.pytest_cache/`

保留：

- `logs/` 中真实实验产物
- `data/`（AgriKG 数据集）
- `reports/`
- `web/node_modules/`

修正 `.gitignore`：

- 移除对已跟踪目录 `benchmarks/`、`context/`、`docs/`、`reports/` 的忽略；
- 保留 `data/`、`logs/`、`results/`、缓存目录与本地运行产物的忽略；
- 与 `.dockerignore`、`pytest` 配置保持一致。

## 7. 分阶段实施

| 阶段 | 内容 | 验证 |
|---|---|---|
| 0 | 基线测试；分支与 WIP 检查点；清理垃圾；修 `.gitignore` | `pytest -q` 基线记录 |
| 1 | 建 `acis/` 骨架，`git mv` 模块，更新导入 | `python -c "import acis"`、导入 smoke |
| 2 | 入口、shim、`pyproject.toml`、pytest 配置 | `python -m acis --help` |
| 3 | `config.py` 与鲁棒性改动 | 新增 config 测试 |
| 4 | 更新 tests、scripts、docs、Docker/启动脚本 | 全量 pytest |
| 5 | 拆分 `ui/tui.py`（977 行）为 `acis/ui/tui/` | TUI smoke |
| 6 | 全量回归与分逻辑提交 | 见验收标准 |

## 8. 验收标准

- `pytest -q` 结果不低于重构前基线（无新增失败）。
- `python orchestrator.py --rules-only --seed 7 "<样例>"` 正常输出。
- `python -m acis --help`、`python -m acis doctor` 正常。
- `uvicorn acis.api.app:app` 启动后 `/health` 返回 200；未配置 Key 时受保护路由返回明确 503。
- `scripts/run_delivery_eval.py` 12 例结果不变。
- `npm --prefix web run test` 通过（前端未改动）。
- `git grep` 不再出现旧的一级模块导入（`from orchestrator`、`from storage`、`from agents` 等）。
- 顶层目录数量显著减少，根目录无临时/转储文件。

## 9. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 导入改写遗漏或循环依赖 | 自动化替换 + 全量导入 smoke 测试 + 全量 pytest |
| 动态导入/字符串引用遗漏 | 全局 grep `gateway.app`、`ui.tui`、`kg_adapter`、`orchestrator` 等 |
| 未提交 WIP 丢失 | 分支 + checkpoint 提交；untracked 文件保留 |
| 行为意外变化 | 不改业务逻辑，只做移动、导入与配置层加固；逐阶段验证 |
| 路径行为变化 | 新增 cwd 无关测试，覆盖相对/绝对环境变量 |

## 10. 明确不做

- 不修改诊断逻辑、Agent 行为、Debate/Critic/Judge 策略、LLM 调用与回退语义。
- 不合并 Agent 文件，不重写 Web 前端。
- 不删除 `data/`、`reports/` 或真实实验日志。
- 不做与目标无关的格式化或重命名。
