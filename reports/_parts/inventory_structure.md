# 盘点 A：结构 / 入口点 / 依赖 / 配置

> 范围：`E:\knowledge_database\ACIS`（Windows / pwsh）。只读盘点；本次唯一写操作=本文件。
> 折叠目录：`.venv` `.git` `node_modules(不存在)` `__pycache__` `*_cache` `dist` `build` `vendor` `logs` `data` `results` `pytest-of-lkl` `torchinductor_lkl`（仅统计规模）。
> 统计口径：**源码** = 排除上述目录后的 `*.py`，共 **119 个**（含 `tests/` 27 个、根目录 5 个）。所有计数为静态扫描（`Select-String`），未运行任何程序。

## A1 目录结构与职责

规模（`Get-ChildItem -Recurse | Measure-Object Length`）：

| 目录 | 文件数 | 体积 | 性质 |
|---|---|---|---|
| `.venv` | 44533 | 1272.3 MB | 本地虚拟环境（uv，`pyvenv.cfg` 记录 Python 3.13.3） |
| `.git` | 758 | 255.2 MB | 版本库；本沙箱 `git.exe` 被拒（见 A7-1） |
| `data` | 191 | 266.0 MB | 运行时数据：`agri.db`(1.7MB)、`eval.db`(6.7MB)、`Agriculture_KnowledgeGraph-master/`、`evaluation/`、`.fuse_hidden*` |
| `results` | 1239 | 56.8 MB | 评测/实验原始结果 |
| `logs` | 4177 | 90.5 MB | 运行日志 + **3 份整仓源码副本**（`logs/delivery_audit_20261024/env/clean` py=125、`logs/p6-exp` py=122、`logs/p6-wt` py=120），会污染全仓 grep |
| 源码树 | — | — | 119 个 py（下述） |

两层结构（排除折叠项；`[n py]` 为该目录 py 文件数）：

```text
ACIS/
├─ orchestrator.py(14.8KB) workflow.py(7.9KB) _env.py(1.0KB) kg_adapter.py(20.5KB) decision_semantics.py(3.8KB)  ← 平铺在仓库根
├─ agents/ [16py]   感知(视觉/传感器/天气)+记忆(RAG/KG/案例/结果)+专家(病理/气象/栽培/经济/生态)+Judge；另含 vision.py/weather.py 底层实现
├─ debate/ [3py]    engine.py(DebateEngine) + critic.py(CriticEngine)
├─ gateway/ [2py]   __init__.py, app.py（FastAPI 应用）
├─ ui/ [3py]        __init__.py, tui.py(rich 终端), web_app.py(streamlit，未验证)
├─ planner/ [4py]   planner/types/prompts/__init__（ACIS_ENABLE_PLANNER 门控）
├─ tool_router/ [3py] router/types/__init__（只生成 ToolRequest，不执行）
├─ trace/ [4py]     types/collector/exporter/__init__（10 阶段统一 Trace）
├─ rag/ [3py]       retriever/knowledge_base/__init__（Qdrant→内存回退）
├─ kg/ [2py]        __init__.py, mcp_server.py（AgriKG MCP Server 独立进程）
├─ rule_engine/ [2py] sensor_anomaly.py（IsolationForest/Chronos 三层异常检测，缺失降级）
├─ storage/ [3py]   db.py(SQLite schema)+repository.py+__init__
├─ utils/ [7py]     judge_runtime.py(端点/重试/脱敏)、confidence_calibration.py、omission.py、generate_calibration.py、2 份 json
├─ evals/ [11py]    固定夹具评测：runner/ablation/fixture_eval/smoke_eval/metrics/report/README
├─ experiments/ [10py] 实验管理：schema/manager/runner_adapter/analysis/archive/catalog/figures/definitions/
├─ benchmarks/ [7py] 基准数据集框架：datasets/、capability_matrix.py、taxonomy.py、schema.py
├─ scripts/ [6py]   __init__.py + 5 个 CLI（delivery eval / challenge eval / stability report / calibration fit / AgriKG import）+ AGRiKG_SETUP.md
├─ src/ [4py]       src/openmetaphysics/{__init__,evaluation/{__init__,challenge_report,challenge_scorer}}（Phase 4 评测工具包）
├─ tests/ [27py]    conftest.py + 26 个 test_*.py + fixtures/ 6 个 json
├─ docs/ [29]       ARCHITECTURE_DECISIONS.md、DEMO_RUNBOOK.md、rfc/RFC001-System Architecture.md、archive/(26)
├─ context/ [2]     EVIDENCE_LEDGER.md、KNOWN_DEBT.md（证据台账/技术债登记）
├─ reports/ [36]    acceptance/experiment_audit/phase4-6 报告、delivery_eval/、archive/(16)
├─ neo4j/           import/(空) plugins/apoc.jar logs/*.log —— docker 挂载用，全部 gitignore
└─ .claude/ .vscode/  工具状态（.claude/pytest_tmp_base ACL 拒绝访问）
```

顶层目录职责证据：

| 目录 | 职责（引用证据） |
|---|---|
| `agents/` | `orchestrator.py:12-13` 注释“Agent 类定义已拆分到 `agents/` 和 `debate/`”；`orchestrator.py:56-68` 逐类 import |
| `debate/` | `orchestrator.py:69` `from debate.engine import DebateEngine`；`:128` `from debate.critic import CriticEngine` |
| `gateway/` | `gateway/app.py:1` “FastAPI gateway for the agriculture Agent orchestrator”；`:25` `app = FastAPI(...)` |
| `ui/` | `ui/tui.py:1-8`（rich 演示界面，`python -m ui.tui`）；`ui/web_app.py:1-2`（Streamlit v2）；README.md:77,79 |
| `planner/` `tool_router/` `trace/` | 各自 `__init__.py:1-5` 明示职责；`orchestrator.py:27-29,131-134` 组装 |
| `rag/` `kg/` `rule_engine/` | `rag/retriever.py:33-48`（Qdrant 可用性→回退）、`kg/__init__.py:1-7`、`rule_engine/sensor_anomaly.py:1-6` |
| `storage/` | `storage/db.py:1-5`（SQLite 审计库，`AGRI_AI_DB_PATH`）；`gateway/app.py:62-105` 读写接口 |
| `evals/` `experiments/` `benchmarks/` | `evals/__init__.py:1`、`experiments/__init__.py:1-11`（experiment-as-code）、`benchmarks/__init__.py:1`、`benchmarks/README.md:1-12` |
| `scripts/` | `scripts/__init__.py:1`（Phase 4 评测工具）；`scripts/AGRiKG_SETUP.md:126` |
| `src/` | `src/openmetaphysics/__init__.py:1` “OpenMetaphysics package root (Phase 4 evaluation tooling)”；仅测试与 `scripts/generate_stability_report.py:41` 使用 |
| `docs/` `context/` `reports/` | README.md:202-213 文档导航；`context/EVIDENCE_LEDGER.md:1-5` |
| `data/` `results/` `logs/` | `.gitignore:38-42` 明确为 local data & run output |

## A2 入口点

| 文件 | 启动命令 | main/入口 | 被谁引用（证据） |
|---|---|---|---|
| `orchestrator.py` | `python orchestrator.py [--rules-only] [--seed N] [--json] [--trace-out P] [--image P] [--llm-judge] [--llm-critic] "问题"`；无参数时 `run_demo()` | 有：`main()` `orchestrator.py:308`，`if __name__=="__main__"` `:346`，argparse `:309-318` | README.md:104；`tests/test_cli_smoke.py:40-48`（subprocess 实跑 `python orchestrator.py --rules-only --seed 7`）；`gateway/app.py:20`、`ui/tui.py:46`、`ui/web_app.py:67`、`evals/runner.py:57`、`scripts/run_delivery_eval.py:42`、`utils/generate_calibration.py:24`、`tests/test_delivery_contract.py:19`、`tests/test_cli_output.py:7` |
| `workflow.py` | 不可独立启动（无 `main`/`__main__`，全仓 grep 确认） | 无；导出 `compile_workflow()` `workflow.py:185`，LangGraph `StateGraph` `:37,39-59` | 被 `orchestrator.py:235` 懒加载（`try: from workflow import compile_workflow`）；`workflow.py:62` 反向 `from orchestrator import build_context` |
| `gateway/app.py` | `uvicorn gateway.app:app --port 8000`（README.md:110）；Docker `CMD ["uvicorn","gateway.app:app","--host","0.0.0.0","--port","8000"]` `Dockerfile:18` | **无** `if __name__`、**无** `uvicorn.run`；模块级 `app` `gateway/app.py:25`；路由 `/health`:35 `/diagnose`:41 `/decisions`:62,68 `/decisions/{id}/feedback`:81 `/decisions/{id}/outcome`:96 | `Dockerfile:18`；README.md:110；`tests/test_delivery_contract.py:238`（TestClient） |
| `ui/tui.py` | `python -m ui.tui` | 有：`main()` `ui/tui.py:518`，`__main__` `:559`；菜单含 6 个 `DEMO_SCENARIOS` `:73-122` | README.md:109；`docs/DEMO_RUNBOOK.md:34`；`ui/__init__.py`(0B) 保证 `-m` 可用；`ui/tui.py:7` 自带用法 |
| `ui/web_app.py` | 只有 `streamlit run ui/web_app.py` 才能执行；**全仓无任何文档给出该命令**（grep `streamlit run` = 0 命中） | 无真实入口：`if __name__=="__main__": pass` `ui/web_app.py:275`；`import streamlit as st` `:20` | README.md:79 归入“已声明但未纳入验证”；`requirements.txt:18` 声明 streamlit，`requirements.docker.txt` 未声明 |
| `scripts/run_delivery_eval.py` | `python scripts/run_delivery_eval.py` | `main()` `:184`，`__main__` `:205` | README.md:90,174；`reports/README.md:31`；`reports/acceptance_20261024.md:65` |
| `scripts/run_challenge_evaluation.py` | `python scripts/run_challenge_evaluation.py …` | `main()` `:328`，`__main__` `:379` | `reports/phase4_evaluation_metric_contract_audit.md:236` |
| `scripts/generate_stability_report.py` | `python scripts/generate_stability_report.py --pilot-reference …` | `main()` `:642`，`__main__` `:661` | README.md:189；`tests/test_stability_metric_contract.py:5`；`context/KNOWN_DEBT.md:19` |
| `scripts/fit_decision_calibration.py` | `python scripts/fit_decision_calibration.py …` | `main(argv)` `:77`，`__main__` `:104` | `docs/archive/changelog.md:8`；`reports/phase6_redesign_20261023/implementation_status.md:22` |
| `scripts/import_agrikg.py` | `python scripts/import_agrikg.py --repo-dir … --yes` | `main()` `:257`，`__main__` `:307` | `start.ps1:78`、`start.sh:69`、`scripts/AGRiKG_SETUP.md:70` |
| `start.ps1` / `start.sh` | `.\start.ps1 [start|import|status|logs|stop]` / `./start.sh …` | 脚本非 Python 入口；`switch` `start.ps1:63`、`case` `start.sh:55` | 无其他文件引用；docker 一键启动（见 A5） |

补充：另有 12 个带 `__main__` 的次级 CLI（不属于“三入口”，供评测/工具使用）：`evals/{runner,ablation,fixture_eval,smoke_eval}.py`、`experiments/manager.py:519`、`benchmarks/{capability_matrix,taxonomy}.py`、`kg/mcp_server.py:445`、`rag/{retriever,knowledge_base}.py`、`utils/generate_calibration.py:85`、`agents/vision.py:293`、`kg_adapter.py:531`、`src/openmetaphysics/evaluation/challenge_report.py:599`。

**README 声称核验（第 6/8 节）**

| 声称 | 结论 | 证据 |
|---|---|---|
| §6 CLI 入口 `python orchestrator.py` | ✅ 真实存在 | `orchestrator.py:308,346`；`tests/test_cli_smoke.py:40-48` |
| §6 TUI 入口 `python -m ui.tui` | ✅ 真实存在，且恰为 6 个演示场景 | `ui/tui.py:518,559`；`DEMO_SCENARIOS` `ui/tui.py:73-122` 共 6 项 |
| §6 FastAPI 入口 `uvicorn gateway.app:app --port 8000` | ✅ 真实存在（`app` 对象在 `gateway/app.py:25`） | `Dockerfile:18` 同一命令 |
| §6 “三入口同链路复用 AgentOrchestrator” | ✅ 成立 | 三者均 `AgentOrchestrator`：`gateway/app.py:20,43`、`ui/tui.py:46,129`、`orchestrator.py:112` |
| §8 “26 个测试文件” | ✅ 成立 | `tests/` 下 `test_*.py` = 26（+`conftest.py`=27 py） |
| §8 “344 个用例 / 342 passed” | ⚠ 无法静态确认 | 静态计数 `def test_` = 316、`@pytest.mark.parametrize` = 9 处；实跑需写临时文件，本轮禁跑 → 见 A7-2 |
| §6 环境 “Python 3.13” | ⚠ 与容器不一致 | README.md:71,95 vs `Dockerfile:2` `FROM python:3.11-slim` |

## A3 依赖

### A3.1 三份清单差异（逐包）

`requirements.txt` = 16 个直接依赖（L5-36）；`requirements.docker.txt` = 10 个（L11-20）；`requirements-lock.txt` = 134 个 `==` 锁定条目（L7-140，Windows/py3.13.3 的 `pip freeze` 快照，文件头 L1-6 自述非跨平台）。

| 包 | requirements.txt | docker | lock 版本 |
|---|---|---|---|
| mcp | L5 `>=1.0.0,<2.0.0` | L11 有 | 1.28.1 |
| httpx | L6 `>=0.27.0` | L12 有 | 0.28.1 |
| pydantic | L7 `>=2.0.0` | L13 有 | 2.13.4 |
| openai | L10 `>=1.0.0` | L14 有 | 2.45.0 |
| langgraph | L13 `>=0.2.0` | L15 有 | **1.2.9** |
| fastapi | L16 `>=0.111.0` | L16 有 | 0.139.0 |
| uvicorn[standard] | L17 `>=0.30.0` | L17 有 | uvicorn 0.51.0（extras 不入 freeze） |
| streamlit | L18 `>=1.36.0` | **无** | 1.59.2 |
| transformers | L21 `>=4.40.0` | **无** | **5.13.1** |
| torch | L22 `>=2.2.0` | **无** | 2.13.0 |
| pillow | L23 `>=10.0.0` | **无** | 12.3.0 |
| numpy | L24 `>=1.26.0` | **无** | 2.5.1 |
| scikit-learn | L27 `>=1.4.0` | **无** | 1.9.0 |
| qdrant-client | L30 `>=1.9.0` | L18 有 | 1.18.0 |
| neo4j | L33 `>=5.0.0` | L19 有 | 6.2.0 |
| rich | L36 `>=13.0.0` | L20 有 | 15.0.0 |

- **只在 `requirements.txt` 出现**：streamlit、transformers、torch、pillow、numpy、scikit-learn（6 个）。
- **只在 `requirements.docker.txt` 出现**：无（docker 是 requirements.txt 的真子集，语义为“精简核心”，见 `requirements.docker.txt:1-8` 注释）。
- **lock 独有 119 条**（传递依赖 + 开发工具），关键：pytest 9.1.1、mypy 2.3.0、ruff 0.16.2、PyYAML 6.0.3、matplotlib 3.11.1、pandas 3.0.3、GitPython、boto3、pywin32(312，L99 自述 Windows 专用)。
- 三份不是互相矛盾，而是**范围不同**：声明文件只写 `>=` 下限，lock 写实测版本；锁里的 langgraph 1.2.9 / transformers 5.13.1 均为下限允许范围内的大版本跃迁 [推测：跨大版本 API 兼容性未验证]。

### A3.2 源码 import 实测计数（`^\s*(import|from) <pkg>`）

| 包（import 名） | 生产代码 | tests | evals/experiments/benchmarks/scripts/src | 判定 |
|---|---|---|---|---|
| openai | 3（agents/judge_agent.py、debate/critic.py、planner/planner.py） | 6 | 1 | 使用中（多为函数内懒加载） |
| rich | 8（ui/tui.py:37-44） | 0 | 0 | 使用中（仅 TUI） |
| torch | 7（rule_engine/sensor_anomaly.py:112,148,168,190-191,304,354） | 0 | 0 | 使用中（try 内懒加载） |
| mcp | 3（agents/vision.py:15、kg/mcp_server.py:23、rag/knowledge_base.py） | 0 | 0 | 使用中（`agents/vision.py:15` 为顶层 import，属硬依赖） |
| numpy | 4（rule_engine/sensor_anomaly.py:90,189,303,353） | 0 | 1 | 使用中（懒加载） |
| qdrant_client | 5（rag/retriever.py:35 等） | 0 | 0 | 使用中（可用性探测） |
| sklearn | 3（rule_engine/sensor_anomaly.py:91,139、utils/confidence_calibration.py:74） | 0 | 0 | 使用中（懒加载） |
| langgraph | 2（workflow.py:37,170，均在函数内） | 0 | 0 | 使用中（可选，缺失即回退规则） |
| neo4j | 1（kg_adapter.py:229） | 0 | 1 | 使用中（懒加载） |
| fastapi | 1（gateway/app.py:17） | 1 | 0 | 使用中（仅 gateway） |
| pydantic | 1（gateway/app.py:18） | 0 | 0 | 使用中 |
| transformers | 1（agents/vision.py:115，try 内） | 0 | 0 | 使用中（可选） |
| streamlit | 1（ui/web_app.py:20） | 0 | 0 | 仅未验证的 web_app 使用 |
| httpx | **0** | 1（tests/test_judge_runtime.py:243） | 0 | ⚠ 仅测试引用 |
| uvicorn | **0** | 0 | 0 | ⚠ 零代码引用，仅 `Dockerfile:18`/README.md:110 以命令形式使用 |
| pillow(PIL) | **0** | 0 | 0 | ⚠ 疑似未使用：全仓无 `import PIL`/`Image.open` |
| pytest | 0 | 18 | 0 | ⚠ 测试必需但三份声明文件都没有 |

### A3.3 代码使用但**未声明**的第三方包

| 包 | 次数/位置 | 说明 |
|---|---|---|
| pytest | 18 处，全部在 `tests/` | 开发/测试依赖，未进任何 requirements → 按 README.md:99-101 装完依赖仍不能跑 §8 测试 |
| matplotlib | `experiments/figures.py:22,25` | 仅 `experiments` 使用，未声明（lock 中有 3.11.1，属 streamlit 传递链） |
| PyYAML | `experiments/schema.py:21` | 同上，未声明（lock 中有 6.0.3） |
| chronos | `rule_engine/sensor_anomaly.py:114,147` | 可选预测后端，未声明，且 `.venv` 亦无 `chronos`→ 该层必然降级（`:104-125` try/except） |
| huggingface_hub | `rule_engine/sensor_anomaly.py:113`（`import huggingface_hub.constants`） | 未声明（transformers 传递依赖），直接 import 属隐式依赖 |

### A3.4 疑似未使用 / 过时 / 冲突 [推测]

| 项 | 证据 | 标注 |
|---|---|---|
| pillow 声明但零 import | `requirements.txt:23`；全仓无 PIL 引用 | [推测] 历史遗留（可能为早期视觉路径或 streamlit 间接需要） |
| httpx 直接声明但仅测试使用 | `requirements.txt:6`；`tests/test_judge_runtime.py:243` | [推测] 冗余（openai SDK 自带 httpx 传递依赖） |
| uvicorn 零 import | `requirements.txt:17` | 非缺陷：以 CLI 形式由 `Dockerfile:18` 启动 |
| langgraph 声明 `>=0.2.0`、锁 1.2.9 | `requirements.txt:13` vs `requirements-lock.txt:57` | [推测] 跨大版本，`StateGraph` 用法未在 1.x 实测 |
| transformers 声明 `>=4.40.0`、锁 5.13.1 | `requirements.txt:21` vs `requirements-lock.txt:128` | [推测] `pipeline` API 跨 5.x 兼容性未验证 |
| numpy 锁 2.5.1 + scikit-learn 1.9.0 | `requirements-lock.txt:74,111` | [推测] 组合兼容性未验证（代码路径有 try/except 降级） |
| docker 精简 6 包是否安全 | `reason`: 视觉/异常/校准三处均 try/except 降级：`agents/vision.py:114-120`、`rule_engine/sensor_anomaly.py:89-101,110-120`、`utils/confidence_calibration.py:73-80`；但 `agents/vision.py:15` 顶层 import mcp，故 mcp 不可裁 | ✅ 结论：docker 裁剪与代码降级设计一致（正面） |

## A4 配置

| 文件 | 职责 | 关键内容 | 冲突/缺口 |
|---|---|---|---|
| `.env.example`（29 键，L11-67） | 配置模板（不含真实密钥） | LLM Judge/Critic、AGRI_AI_* 开关、SQLite、RAG/KG、离线开关 | 缺 10 个代码实际读取的键（见下）；文件头注释与 `.env` 实际键不同步 |
| `.env`（9 键） | 本地真实配置（**值全部省略不输出**） | 键名：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`、`HF_HUB_OFFLINE`、`TRANSFORMERS_OFFLINE`、`OPENCODE_BASE_URL`、`OPENCODE_API_KEY`（均为非空） | `OPENCODE_*` 两键**源码不读取**（见下）；`AGRI_AI_*` 全部缺省（走默认值）；`.gitignore:11` 已忽略，但是否曾入库无法验证（A7-1） |
| `pytest.ini`（7 行） | 唯一的 pytest 配置 | `testpaths=tests` L5；`norecursedirs=.git .venv __pycache__ .mypy_cache .ruff_cache .pytest_cache logs results data neo4j pytest-of-lkl torchinductor_lkl` L6；`addopts=-ra` L7 | 不存在 `pyproject.toml`/`setup.cfg`/`tox.ini`（命令验证均为 False）→ 无重复配置；但 `pytest` 本身未在 requirements.txt |
| `docker-compose.yml`（72 行） | 3 服务编排 api/qdrant/neo4j | api `8000:8000` L12-13；环境 `PYTHONIOENCODING/PYTHONPATH/DEEPSEEK_*/NEO4J_*/AGRI_AI_*/QDRANT_URL` L14-26；`depends_on: neo4j(healthy)` L27-29；healthcheck 打 `/health` L30-35；qdrant `6333` L37-43；neo4j `17474:7474`,`7687` L45-68；卷 `qdrant_storage`,`neo4j_data` L70-72 | `NEO4J_PASSWORD: agriai2026` 硬编码 L23、`NEO4J_AUTH=neo4j/agriai2026` L58 与 `.env.example:58` 的 `neo4j` 默认值不同；api 不依赖 qdrant；`.:/app` bind mount L10 覆盖镜像 |
| `Dockerfile`（18 行） | API 镜像 | `FROM python:3.11-slim` L2；`COPY requirements.docker.txt` + pip L11-12；`COPY . .` L14；`EXPOSE 8000` L16；`CMD uvicorn gateway.app:app` L18 | Python 3.11 ≠ README 的 3.13；无 `HEALTHCHECK`（依赖 compose 的） |
| `.gitignore`（86 行） | 忽略密钥/本地/可再生 | `.env` L11-13；`.venv` L19；`data/logs/results` L40-42；`pytest-of-*` `torchinductor_lkl` L45-46；`.claude/` `.vscode/` L69,74 | L7 自称“与 pytest.ini / .dockerignore 保持同步”，但 `.dockerignore` 缺 `logs` 等（见 A6） |
| `.dockerignore`（20 行） | 构建上下文裁剪 | `.git/.claude/.context/.env/.venv/__pycache__`、`data/results/neo4j`、`tests`、`REVIEW_REPORT.md` | **缺 `logs`**（`.gitignore:41` 有）→ 构建上下文实测≈90.3MB/4209 文件，几乎全是 `logs/`(90.5MB/4177) |
| `.vscode/settings.json`（1 行） | 编辑器配置 | `"python.terminal.useEnvFile": true` | 与 `_env.py` 并存 → 存在两条 `.env` 注入路径（VS Code 终端 vs 运行时 `load_env()`） |
| `.claude/settings.local.json` | 工具权限（非项目配置） | 仅存在于 `.claude/worktrees/amazing-bardeen-551868/.claude/settings.local.json`（243B，一条 Bash grep 白名单）；`.claude/pytest_tmp_base/` ACL 拒绝访问 | `.claude/` 已被 `.gitignore:69` 忽略；内容与 ACIS 配置无关 |
| `_env.py`（32 行） | 自研 .env 加载器（无第三方依赖） | `load_env()` L16-28；`os.environ.setdefault` 不覆盖已有值 L28；模块导入时自动执行 L32 | 被 `orchestrator.py:26`、`gateway/app.py:11`、`ui/tui.py:23`、`ui/web_app.py:17` 调用；`orchestrator.py:53` 与 `gateway/app.py:12` 各调一次（幂等） |

`.env.example` 与代码读取键的差集（读取点来自 `os.environ.get/getenv/[]`、`_first()`、`env.get()` 全量扫描，共 35 键）：

- **代码读取、模板缺失（10 键）**：`AGRI_AI_ABSTAIN_MIN_SUFFICIENCY`(`agents/judge_agent.py:593`)、`AGRI_AI_CALIB_ALPHA`(`utils/confidence_calibration.py:112`)、`AGRI_AI_CALIBRATION`(`:28`)、`AGRI_AI_COHERENCE_MODEL`(`src/.../challenge_report.py:398`, `challenge_scorer.py:456`)、`AGRI_AI_JUDGE_SESSION_ID`(`utils/judge_runtime.py:166,187`)、`AGRI_AI_KG_DRAFTS_LOAD`(`agents/judge_agent.py:270`)、`AGRI_AI_KG_DRAFTS_PATH`(`kg_adapter.py:449`)、`AGRI_AI_KG_DRAFTS_PROPOSE`(`kg_adapter.py:458`)、`AGRI_AI_PLANNER_MODEL`(`planner/planner.py:130`)、`PYTHONIOENCODING`(`ui/web_app.py:22`)。
- **模板中但代码不读**：无（`AGRI_AI_JUDGE_BASE_URL/MODEL/PROVIDER/TIMEOUT_SECONDS/MAX_RETRIES` 均在 `utils/judge_runtime.py:72-93` 经 `_first(env, ...)` 读取，静态正则会漏计，已人工核对）。
- **`.env` 中但代码不读（2 键）**：`OPENCODE_BASE_URL`、`OPENCODE_API_KEY` —— `utils/judge_runtime.py:150,159` 只用 host 字符串推断 provider，README.md:24-25 亦明示“代码不直接读 OPENCODE_*”。

## A5 构建与运行脚本

| 脚本 | 步骤摘要 | 证据 |
|---|---|---|
| `start.ps1` | 设 `NO_PROXY` → 校验 docker → `docker compose up -d --build` → 轮询 `http://localhost:8000/health` 30×2s（≤60s）→ 打印入口提示；子命令 `import/status/logs/stop`（stop=`docker compose down`，保留卷） | `start.ps1:19-20,22-28,30-46,63-87` |
| `start.sh` | 与 ps1 逐项对应（`set -euo pipefail`、`NO_PROXY`、同样的健康轮询与 5 个子命令），差异仅在 curl/PowerShell 实现 | `start.sh:11-16,20-38,55-82` |
| `Dockerfile` | 3.11-slim → ENV(PYTHONUNBUFFERED/PYTHONIOENCODING/PYTHONPATH=/app) → 装 `requirements.docker.txt` → `COPY . .` → EXPOSE 8000 → uvicorn 启动 | `Dockerfile:2-18` |
| `docker-compose.yml` | api 构建本地镜像 + 绑定端口 8000 + 绑定挂载宿主目录 + 依赖 neo4j 健康 + 健康检查；另起 qdrant、neo4j 容器与具名卷 | `docker-compose.yml:1-72` |

一致性核对：

| 项目 | start.ps1 | start.sh | Dockerfile | compose | 结论 |
|---|---|---|---|---|---|
| API 端口 | 8000(`:31,35,52`) | 8000(`:28,31,44`) | EXPOSE 8000(`:16`) + CMD `--port 8000`(`:18`) | `"8000:8000"`(`:13`) | ✅ 一致 |
| 启动命令 | `docker compose up -d --build`(`:66`) | 同(`:58`) | `uvicorn gateway.app:app --host 0.0.0.0 --port 8000`(`:18`) | 未覆盖 command → 用镜像 CMD | ✅ 一致 |
| 健康检查 | 轮询 `/health` 60s(`:30-46`) | 同(`:27-38`) | 无 | 容器内 urllib 打 `/health`，interval 10s/start 15s(`:30-35`) | ✅ 兼容（应用侧剧本比编排侧更宽松） |
| Neo4j 端口 | 提示 `localhost:17474`(`:53`) | 同(`:45`) | — | `17474:7474`、`7687:7687`(`:49-51`) | ✅ 一致 |
| Qdrant 端口 | 提示 6333(`:54`) | 同(`:46`) | — | `6333:6333`(`:41`) | ✅ 一致 |
| 环境变量 | 仅 `NO_PROXY`(`:19`)；不显式传 key | 同上(`:15`) | 只设 3 个基础 ENV | 显式传 `PYTHONIOENCODING/PYTHONPATH/DEEPSEEK_*/NEO4J_*/AGRI_AI_*/QDRANT_URL`(`:14-26`) | ⚠ `.env` 只在宿主侧（compose 变量替换）与容器 bind mount 内生效，容器内不复制 `.env`（`.dockerignore:5`） |
| 卷 | 无 | 无 | — | `.:/app` + `./data:/app/data`(`:10-11`)、`neo4j/logs|import|plugins`(`:54-56`)、具名卷(`:70-72`) | ⚠ `.:/app` 使镜像内 `/app` 被宿主树覆盖；镜像 `COPY . .` 仅对无挂载场景有意义 |

## A6 结构与合规性问题清单

| # | 现象 | 证据 | 严重度 |
|---|---|---|---|
| 1 | `agents/` 是唯一被 import 却缺 `__init__.py` 的 Python 包（隐式命名空间包）；`site-packages` 中若有同名 `agents` 包存在遮蔽风险 | `agents/` 无 `__init__.py`（`Test-Path`=False）；`orchestrator.py:55-68` 直接 `from agents.xxx import`；其余 15 个包均有 `__init__.py` | 中 |
| 2 | 无 `pyproject.toml`/`setup.py`，项目不可安装；模块解析依赖 CWD 或 `sys.path` 硬改（15 个文件） | 命令验证上述文件均不存在；`sys.path.insert` 见 `gateway/app.py:8-9`、`ui/tui.py:16-17`、`ui/web_app.py:14-15`、`evals/{ablation,fixture_eval,runner,smoke_eval}.py`、`kg/mcp_server.py:26-27`、`scripts/*.py` 4 处、`src/.../challenge_report.py:49-50`、`tests/conftest.py:7-11`、`utils/generate_calibration.py:18-19` | 中 |
| 3 | 5 个核心模块平铺在仓库根，且 `src/` 不在默认 `sys.path`，只能靠测试/脚本注入才能 `import openmetaphysics` | 根：`orchestrator.py`/`workflow.py`/`_env.py`/`kg_adapter.py`/`decision_semantics.py`；`openmetaphysics` 仅在 `tests/conftest.py:10-11` 与 `scripts/generate_stability_report.py:41`（依赖注入路径）可用 | 中 |
| 4 | 三份 requirements 均无 `pytest`，而 README §8 要求跑测试；`matplotlib`/`PyYAML`/`chronos`/`huggingface_hub` 亦未声明 | `requirements.txt:1-36`、`requirements.docker.txt:1-20`；import 点见 A3.3 | 中 |
| 5 | `pillow` 声明但 0 处 import（疑似未使用依赖） | `requirements.txt:23`；全仓 `^\s*(import\|from)\s+PIL` = 0 | 低 |
| 6 | `README` 声称 Python 3.13，容器固定 3.11-slim；两套运行时不一致 | README.md:71,95 vs `Dockerfile:2`；`.venv/pyvenv.cfg` version_info=3.13.3 | 中 |
| 7 | `.dockerignore` 缺 `logs`，与 `.gitignore:41`、自身注释“保持同步”矛盾；构建上下文≈90MB 且含 3 份源码副本 | `.dockerignore:1-20` 无 `logs`；实测 docker 上下文 4209 文件/90.3MB，`logs/`=4177 文件/90.5MB | 中 |
| 8 | compose 的 `.:/app` bind mount 让宿主树（含 `.env`）在容器内可见，使 `.dockerignore` 对运行期配置失效；同时把镜像内容整体遮蔽 | `docker-compose.yml:10`；`.dockerignore:5` 只影响 build；`_env.py:17` 会读 `/app/.env` | 中 |
| 9 | compose 硬编码 `NEO4J_PASSWORD=agriai2026`，与 `.env.example:58` 的 `neo4j` 默认值不一致；api 仅 `depends_on: neo4j`，Qdrant 无启动依赖 | `docker-compose.yml:23,58`、`:27-29`、`:26` | 低 |
| 10 | `.env` 含 2 个源码不读的键（`OPENCODE_*`），属无效配置；同时 `.env.example` 缺 10 个代码读取的键 | `.env` 键名清单 vs `requirements` 无关；读取扫描见 A4；`utils/judge_runtime.py:147-156` 仅做 host 推断 | 低 |
| 11 | 同名模块：`types.py`×4、`report.py`×2、`schema.py`×2；当前 import 路径唯一、无实际冲突，但增加阅读/误导入成本（无 `orchestration` 同名包） | `agents/types.py`、`planner/types.py`、`tool_router/types.py`、`trace/types.py`；`evals/report.py`、`experiments/report.py`；`benchmarks/schema.py`、`experiments/schema.py` | 低 |
| 12 | `src/openmetaphysics/evaluation/` 存在 `stability_report.cpython-313.pyc` 但无对应 `.py` 源码（残缺缓存） | 目录列表：`__pycache__/stability_report.cpython-313.pyc`(19136B)；源码仅 `challenge_report.py`/`challenge_scorer.py` | 低 |
| 13 | 仓库根遗留文件 `xx`（15082B），内容是 `git` 告警 + 彩色 diff 的输出重定向残留 | `xx` 首行 `warning: in the working copy of '.gitignore', LF will be replaced by CRLF…`；含 `ui/tui.py | 4 +-` diff 片段 | 低 |
| 14 | `logs/` 内嵌 3 份完整源码副本，使全仓静态统计（grep/import 计数）在默认口径下失真 | `logs/delivery_audit_20261024/env/clean`=125py、`logs/p6-exp`=122py、`logs/p6-wt`=120py；mcp 词匹配 185 次 vs 源码真实 import 3 次 | 中 |
| 15 | 根目录 `pytest-of-lkl/`、`torchinductor_lkl/` 与 `logs/**/pytest-of-lkl` 存在 ACL 拒绝访问目录（读取时反复报 Access denied） | `Get-ChildItem` 报 `Access to the path '…\pytest-of-lkl' is denied`；`.gitignore:45-46`、`pytest.ini:6` 均声明忽略 | 低 |
| 16 | `TUI` 是 rich 全功能入口、`web_app.py` 却无任何文档化启动命令；web 入口名存实亡（README 亦承认未验证） | `ui/web_app.py:275` 只有 `pass`；全仓 `streamlit run` 命中 0；README.md:79,197 | 低 |

正面结论（避免误报）：① README 三入口真实存在且共享同一 `AgentOrchestrator`；② `requirements.docker.txt` 的裁剪与代码中“缺库即降级”的 try/except 设计一致（`agents/vision.py:114-120` 等）；③ `pytest.ini` 是唯一测试配置源，无重复/冲突；④ `.gitignore`/`pytest.ini` 的忽略项基本互洽（除 `logs` 在 `.dockerignore` 缺位）。

## A7 本线程未能确认的事项 [待确认]

1. **git 不可用**：所有 `git -c safe.directory=… <只读子命令>` 均被沙箱拒绝（`ResourceUnavailable: 程序'git.exe'运行失败：拒绝访问`）→ 无法确认工作区是否干净、`.env`/`data/`/`logs/` 是否曾入库、当前分支/commit。
2. **测试用例数与通过状态**：README §8 的 344/342 passed/2 skipped 无法静态复现（实跑会写 `.pytest_cache`，本轮禁写）；静态仅得 26 个 test 文件、316 个 `def test_`、9 处 `parametrize`。
3. **Docker 链路未实测**：本环境无 Docker，`Dockerfile`/`compose` 仅做静态一致性核对；`context/KNOWN_DEBT.md:13-14` 亦自述未构建验证。
4. **版本组合的实际兼容性**：langgraph 1.2.9、transformers 5.13.1、numpy 2.5.1+sklearn 1.9.0 均未运行验证（无法 `pip install`/`import` 实测）。
5. **`.env` 中 `NEO4J_PASSWORD` 是否等于 compose 的 `agriai2026`**：为避免输出密钥值未比对，故本机直连 Neo4j 的可用性未知。
6. **`.claude/pytest_tmp_base/` 用途**：ACL 拒绝读取（可能为测试临时根），无法确认是否含残留数据。
7. **`xx` 文件的生成来源**：内容确为 git 告警+diff，但生成命令与时间不可考（[推测] 某次 `git diff > xx` 或 `2> xx` 残留）。
8. **`src/.../stability_report.pyc` 无源码**：是源码移动/删除还是分支残留未知（[推测] Phase 4 重构后删除，pyc 未清）。
9. **`requirements-lock.txt` 与当前 `.venv` 是否一致**：无法运行 `pip freeze`/`pip check` 比对（禁执行会写盘的程序）。
10. **`.env.example` 是否被 CI/测试断言**：无 CI 配置（`.github` 不存在），无法判断模板漂移是否被自动检查。

---
*本文件为“盘点 A”唯一产出；除本文件外未改动、未删除、未创建任何文件，未运行 pytest/docker/构建/pip，未修改 git 配置。*
