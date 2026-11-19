# 盘点 B：源码 / 测试 / 技术债 / 重复实现

> 盘点员：inv-code（只读）。范围：`*.py` 与根配置；跳过 `.venv node_modules __pycache__ .mypy_cache .pytest_cache .ruff_cache .git dist build vendor logs data results pytest-of-lkl torchinductor_lkl`。
> 方法：`rg` 静态统计 + 文件行数实测（`ReadAllLines`）+ `pytest --collect-only -q -p no:cacheprovider`（不落缓存）+ `git -c safe.directory=… log/status` 只读。**未运行任何测试用例**（仅收集）。
> 行号格式 `路径:行号`；`[待确认]`=证据不足，`[推测]`=启发式推断。

## B1 代码规模

- 纳入统计 **119 个 .py**，合计 **23,179 行**（总行）/ **19,229 行**（去空行与整行注释）。
- 统计口径排除目录（`logs/` 里有 114 个文件，含历史快照，不计入源码量）。

| # | 文件 | 总行 | 代码行 | >500 风险 |
|---|---|---|---|---|
| 1 | benchmarks/capability_matrix.py | 987 | 863 | ⚠ 超长 |
| 2 | tests/test_challenge_evaluation.py | 726 | 619 | ⚠ 超长 |
| 3 | scripts/generate_stability_report.py | 662 | 595 | ⚠ 超长 |
| 4 | agents/judge_agent.py | 661 | 615 | ⚠ 超长 |
| 5 | src/openmetaphysics/evaluation/challenge_report.py | 600 | 530 | ⚠ 超长 |
| 6 | ui/tui.py | 560 | 487 | 接近 |
| 7 | experiments/analysis.py | 556 | 452 | 接近 |
| 8 | rag/knowledge_base.py | 548 | 474 | 接近 |
| 9 | evals/report.py | 535 | 447 | 接近 |
| 10 | kg_adapter.py | 532 | 419 | 接近 |
| 11 | experiments/manager.py | 520 | 435 | 接近 |
| 12 | src/openmetaphysics/evaluation/challenge_scorer.py | 518 | 430 | 接近 |
| 13 | tests/test_metrics.py | 465 | 399 | — |
| 14 | rule_engine/sensor_anomaly.py | 450 | 391 | — |
| 15 | kg/mcp_server.py | 446 | 372 | — |
| 16 | tests/test_capabilities.py | 440 | 341 | — |
| 17 | debate/critic.py | 413 | 367 | — |
| 18 | tests/test_experiments.py | 392 | 328 | — |
| 19 | evals/runner.py | 387 | 316 | — |
| 20 | scripts/run_challenge_evaluation.py | 380 | 327 | — |
| 21 | benchmarks/metadata.py | 358 | 300 | — |
| 22 | orchestrator.py | 347 | 291 | — |
| 23 | tests/test_capability_metrics.py | 332 | 269 | — |
| 24 | tests/test_challenge_scorer.py | 326 | 235 | — |
| 25 | rag/retriever.py | 323 | 266 | — |

**>500 行超长文件共 12 个**：`benchmarks/capability_matrix.py`、`tests/test_challenge_evaluation.py`、`scripts/generate_stability_report.py`、`agents/judge_agent.py`、`src/openmetaphysics/evaluation/challenge_report.py`、`ui/tui.py`、`experiments/analysis.py`、`rag/knowledge_base.py`、`evals/report.py`、`kg_adapter.py`、`experiments/manager.py`、`src/openmetaphysics/evaluation/challenge_scorer.py`。其中 `agents/judge_agent.py` 单个类就占 575 行（`agents/judge_agent.py:86` 起），`benchmarks/capability_matrix.py` 单文件承担 30 个函数（`:89`–`:952`）。

**各顶层单元规模**（文件数 / 总行 / 代码行，按总行降序）：

| 单元 | 文件 | 总行 | 代码行 | 备注 |
|---|---|---|---|---|
| tests | 27 | 6100 | 4837 | conftest + 26 测试文件 |
| experiments | 10 | 2447 | 2036 | 实验管理/分析/报告 |
| benchmarks | 7 | 2038 | 1729 | 数据集+能力矩阵（含 987 行巨文件） |
| evals | 10 | 1977 | 1600 | 评测 runner/metrics/report |
| scripts | 6 | 1664 | 1447 | 入口脚本 |
| agents | 16 | 1547 | 1354 | 15 个 Agent + types |
| src | 4 | 1124 | 964 | 仅 openmetaphysics/evaluation（Phase 4） |
| rag | 3 | 871 | 740 | knowledge_base 内含 DISEASE_DB（`rag/knowledge_base.py:34`） |
| ui | 3 | 836 | 712 | tui 560 行；web_app 为 streamlit 未验证 |
| utils | 5 | 749 | 615 | 校准/判定运行时 |
| kg_adapter.py（根） | 1 | 532 | 419 | Judge 的 KG 混合检索门面 |
| trace | 4 | 506 | 404 | 10 阶段 Trace |
| debate | 3 | 483 | 430 | engine + critic |
| kg | 2 | 454 | 378 | mcp_server 446 行 |
| rule_engine | 2 | 450 | 391 | 传感器异常检测 |
| orchestrator.py（根） | 1 | 347 | 291 | CLI 入口 |
| planner | 4 | 257 | 216 | 默认关闭 |
| storage | 3 | 194 | 170 | SQLite |
| workflow.py（根） | 1 | 186 | 161 | LangGraph 图 |
| tool_router | 3 | 170 | 142 | 只生成请求 |
| decision_semantics.py（根） | 1 | 110 | 90 | 语义唯一源 |
| gateway | 2 | 105 | 80 | FastAPI |
| _env.py（根） | 1 | 32 | 23 | .env 注入 |

## B2 债务标记

`rg -n "TODO|FIXME|HACK|XXX|deprecated|DEPRECATED|待实现|临时"` 在 **源码范围内仅 3 处命中（2 个文件）**，无 FIXME/HACK/XXX/deprecated：

| 路径:行号 | 内容摘要 |
|---|---|
| utils/confidence_calibration.py:5 | 模块 docstring：手写 Platt Scaling，"TODO: 迁移到 sklearn LogisticRegression" |
| utils/confidence_calibration.py:79 | 同类 TODO（代码内重复声明一次） |
| agents/vision.py:235 | 注释"清理临时文件"（"临时"为语义词，非债务标记） |

结论：**代码内联债务标记极少**（历史上有一轮 lint 债务清理：`git log` 0111465 "chore: fix lint debt (F401/F841/F541/E722/E741/E401)"）。真正的债务集中在仓库级文档登记：

| # | 债务项（context/KNOWN_DEBT.md 行号） | 涉及代码证据 |
|---|---|---|
| 1 | 全量测试未在普通环境验证，沙箱下 340 passed / 3 failed（`:8-10`） | 与 README.md:171 的 "342 passed / 2 skipped" 口径冲突 |
| 2 | requirements-lock.txt 平台绑定（`:11-12`） | requirements-lock.txt:1（Windows+3.13.3 pip freeze） |
| 3 | Docker 未构建验证（`:13-14`） | Dockerfile:1 / docker-compose.yml:1 |
| 4 | 历史 accuracy = factor coverage，字段名未重命名（`:18-20`） | scripts/generate_stability_report.py:66-75 |
| 5 | ECE 分箱边界 `int(conf/bin_size)` 浮点误差（`:21-23`） | src/openmetaphysics/evaluation/challenge_scorer.py:154 |
| 6 | 自一致性指标依赖 trace.agreement，不可由 raw 复现（`:24-25`） | — |
| 7 | Phase 6 覆盖不足/架构收益未证明（`:26-29`） | 见 README.md:177-190 |
| 8 | LLM Judge 端点与重试策略未统一（`:32-33`） | utils/judge_runtime.py:21 |
| 9 | 静默失败路径仍有未覆盖异常（`:36-37`） | 见 B6 吞异常 2 处 |
| 10 | 视觉/传感器模拟，真实效果未验证（`:38-39`） | agents/vision.py:1-20 注释、rule_engine/sensor_anomaly.py |
| 11 | ruff/mypy 既有告警（I001/BLE001/S110、planner overload、orchestrator E402）（`:42-45`） | orchestrator.py:53 后置 import（E402），kg/mcp_server.py:29 `# noqa: E402` |
| 12 | 能力标注 52/64 与 scoring 严格性未冻结（`:46-47`） | benchmarks/capability_matrix.py:415-441 |

## B3 注释掉的大段代码

启发式扫描（连续 ≥5 行以 `#` 开头，且块内 ≥3 行含代码特征：`def/class/return/=/self./调用括号`；另检 `if False:` / `if 0:`）：

- **注释掉的可执行代码块：0 个**（0 个块满足"连续 ≥5 行且像代码"）；`if False:` / `if 0:` 亦为 0 处。
- 全仓 `#` 连续块 ≥5 行的仅 **2 处**，且均为说明性注释，不是被注释的代码：

| 路径:起止行 | 行数 | 内容 |
|---|---|---|
| agents/types.py:25-29 | 5 | "ACIS cognitive upgrade: hypothetical observations that would change…" 字段语义说明 |
| src/openmetaphysics/evaluation/challenge_scorer.py:62-66 | 5 | `#:` Sphinx 属性注释，说明 FACTOR_ALIASES 词表来源 |

- 注释密度最高文件（整行 `#` 占比）：agents/types.py 13%（67 行/9 行注释）、ui/web_app.py 9%、tests/test_agent_output.py 9%、utils/confidence_calibration.py 7%。无异常高比例。
- 结论：**不存在"大段注释掉旧实现"的堆积**（与 6a74817/0111465/xx 记录的清理历史一致，见 B4）。遗留的正是"无用历史代码"以文件级形式存在：`logs/p6-*/` 快照（被 .gitignore:41 忽略）与根目录 `xx`（见 B8）。

## B4 重复实现（含结论：真实现 vs 废弃副本）

### B4.1 结论（先给答案）

**根目录 4 个文件全部是"被使用的真实现"，不是被复制/废弃的旧版；仓库内不存在同职责的第二份实现。** 证据：

| 根文件 | 被谁 import（路径:行号） | 定义 | 结论 |
|---|---|---|---|
| orchestrator.py | gateway/app.py:20、ui/tui.py:46、ui/web_app.py:67、evals/runner.py:57、evals/fixture_eval.py:20、evals/smoke_eval.py:20、scripts/run_delivery_eval.py:42、utils/generate_calibration.py:24、tests/test_delivery_contract.py:19、tests/test_cli_output.py:7 | 唯一 `class AgentOrchestrator`（orchestrator.py:112） | 真实现（CLI/API/TUI 共用，README.md:42,89 成立） |
| workflow.py | orchestrator.py:235（方法内延迟 import） | 唯一 `class AgricultureWorkflow`（workflow.py:32） | 真实现（LangGraph 主图） |
| kg_adapter.py | agents/judge_agent.py:20、kg/mcp_server.py:29、ui/web_app.py:94 | 唯一 KG 混合检索门面（kg_adapter.py:396 `query_kg`） | 真实现 |
| decision_semantics.py | agents/judge_agent.py:17-19、evals/metrics.py:17、src/…/challenge_report.py:52-53、src/…/challenge_scorer.py:34-45、scripts/generate_stability_report.py:40、tests/test_decision_confidence.py:10 | 唯一语义定义（decision_semantics.py:26-101） | 真实现（语义唯一源） |

补充证据：全仓 `class *Orchestrator*` 仅 1 处（orchestrator.py:112），`AgentOutput/RequestContext/DebateResult/DecisionOutput` 仅在 agents/types.py:13,34,43,52 定义一次；`git -c … log -1` 显示 6a74817 "refactor: agri-ai 铺平至仓库根目录" 把实现从子包**上移到根**，因此根文件是**最新**实现而非副本（最后一次提交：orchestrator.py d2fa727 2026-10-24、decision_semantics.py f1c7e98 2026-10-24、kg_adapter.py 6a74817 2026-07-15、workflow.py 0111465 2026-08-09）。

### B4.2 README 第 3 节 vs `src/` 是什么

- README.md:42 声称 `CLI["CLI: orchestrator.py"] --> ORCH["AgentOrchestrator.run"]`；实测成立（orchestrator.py:112,308-346，且 gateway/ui/evals 均复用同一类，README.md:89 "不存在两套业务实现" 与证据一致）。
- `src/` **不是** orchestrator 的替代实现，而是 **Phase 4 评测工具包**：`src/openmetaphysics/__init__.py:1` "OpenMetaphysics package root (Phase 4 evaluation tooling)"；仅 4 个文件（challenge_scorer 518 行、challenge_report 600 行 + 2 个 `__init__`），无 `AgentOrchestrator`（`rg 'AgentOrchestrator|orchestrat' src` 无命中），无 CLI 入口（`scripts/run_delivery_eval.py` 走根 orchestrator）。
- 它能被 `from openmetaphysics.evaluation import …` 使用，靠测试引导把 `src/` 塞进 sys.path：tests/conftest.py:10-11（`SRC = ROOT / "src"`），消费方为 tests/test_challenge_evaluation.py:27、tests/test_challenge_scorer.py:25、tests/test_challenge_set_valid.py:19、scripts/generate_stability_report.py:41。**这是隐式路径约定，不是包安装**（无 pyproject.toml/setup.py，见 B6）。

### B4.3 真实存在的"同名/同职责"重复（按风险排序）

| # | 重复对象 | 性质 | 证据 | 风险 |
|---|---|---|---|---|
| 1 | **两套 MCP Server**：`kg/mcp_server.py`（446 行，9 个 `@mcp.tool()`，服务名见 `:428`）与 `rag/knowledge_base.py`（548 行，5 个 `@mcp.tool()`，`:5-7` 自建 `FastMCP("agri-knowledge")`）都定义了 **同名工具 `search_disease`** 与 **同名资源 `knowledge://diseases`** | 职责重叠的真重复 | kg/mcp_server.py:144-145 vs rag/knowledge_base.py:371-372；资源 kg/mcp_server.py:428-429 vs rag/knowledge_base.py:535-536；kg/mcp_server.py:41 注释还引用已被删除的 `knowledge_mcp_server.py`（`Test-Path` = False，仓库无此文件） | 高：两个 server 各自暴露同名工具，语义/返回结构可能漂移；且注释指向不存在文件 |
| 2 | **两套能力矩阵文档生成器**：`benchmarks/taxonomy.py` 与 `benchmarks/capability_matrix.py` 都生成 `CAPABILITY_MATRIX.md` + `COVERAGE.md` | 同产物双写 | taxonomy.py:258-262、:271-275、:300-301 vs capability_matrix.py:277-284、:447、:563-567；capability_matrix.py:54 从 taxonomy 复用常量，属"扩展但覆盖同一输出" | 中高：谁最后写谁生效，`python -m benchmarks.taxonomy`（taxonomy.py:11）与 `python -m benchmarks.capability_matrix`（capability_matrix.py:26）会互相覆盖 |
| 3 | 同名双文件"实现 + 薄包装"：`agents/vision.py`(294 行) / `agents/vision_agent.py`(30 行)、`agents/weather.py`(46 行) / `agents/weather_agent.py`(14 行) | 包装模式，非逻辑重复 | vision_agent.py:14 函数内 `from agents.vision import diagnose_image`；weather_agent.py:4 `from agents.weather import …` | 低（但相同命名前缀易误判为重复；两处都是延迟 import） |
| 4 | `challenge_scorer.py` 内的同名函数 `is_abstention`(170) / `normalize_decision_label`(175) / `_decision_text`(369) / `_is_abstention`(420) | **委托转发，不是复制** | challenge_scorer.py:34-45 import 自 decision_semantics，函数体仅 `return _shared_*()`：:172、:181、:370、:421 | 低：语义唯一源正确；但同名转发层易被误读为重复实现 |
| 5 | 根目录同名模块的"旧版快照" | 未入库的本地副本 | logs/p6-exp/orchestrator.py（12,145B，2026-10-24 02:42）vs 当前 14,759B；logs/delivery_audit_20261024/env/clean/ 同类 5 文件；`git check-ignore` 确认 logs/ 被 .gitignore:41 忽略 | 低：不在版本库内，不入统计 |
| 6 | 已删除实现的"墓碑" | 已删除，但测试留着 importorskip | xx（tracked 的 diff dump）尾部显示 `scripts/run_phase4_2.py | 587 --`、`scripts/run_phase4_2_real_agent.py | 675 --` 被删；tests/test_phase4_harness_runtime.py:9-13、test_phase4_reliability.py:11-16 仍以 `pytest.importorskip` 指向它们 | 低：不报错，但形成 2 个永久 skip（见 B7） |

### B4.4 其他非重复判定（排除误报）

- `evals/report.py`（指标/消融报告）与 `experiments/report.py`（LaTeX/Markdown 实验报告）职责不同：前者 `write_metrics_csv`/`write_ablation_report`（evals/report.py:55,326），后者 `generate_report`（experiments/report.py:132）。
- `benchmarks/capabilities.py`（能力枚举/解析）与 `evals/capability_metrics.py`（7 项能力打分）职责不同。
- `benchmarks/metadata.py` 与 `benchmarks/schema.py` 分工为"元数据校验/结构校验"。`_mean` 等 3 行小工具在 evals/report.py:483、benchmarks/capability_matrix.py:943、challenge_report.py:272 各写一份——琐碎重复，不构成架构债 [推测：可接受]。

## B5 import 拓扑与循环依赖

**跨单元 import 边（按 import 语句计；`(root)` = 根目录 6 个模块）**：

| 源 → 目标 | 次数 | 源 → 目标 | 次数 |
|---|---|---|---|
| (root) → agents | 14 | tests → benchmarks | 23 |
| agents → (root) | 4 | tests → evals | 16 |
| (root) → debate/planner/rag/storage/tool_router/trace | 各 2/1/1/1/1/1 | tests → agents | 16 |
| agents → rag | 4 | tests → experiments | 7 |
| agents → utils | 4 | tests → trace | 4 |
| agents → storage / rule_engine | 2 / 1 | tests → (root)/planner/storage/utils | 各 3 |
| debate → agents | 1 | tests → scripts/tool_router | 各 2 |
| evals → (root)/agents/benchmarks/rule_engine/trace | 4/1/4/2/3 | tests → debate/gateway | 各 1 |
| experiments → evals / benchmarks | 7 / 1 | ui → (root) | 5 |
| gateway → (root) / storage / utils | 2 / 4 / 1 | ui → rule_engine / storage | 1 / 1 |
| kg → (root) | 1 | scripts → (root)/evals/utils/rule_engine | 2/3/2/1 |
| planner → agents | 1 | src → (root) | 6 |
| storage → agents | 1 | trace → agents/planner/tool_router | 1/1/1 |
| utils → (root)/evals/rule_engine | 1/1/1 | tool_router → planner | 1 |

**双向依赖 / 循环判定**：

- 单元级双向：**`(root)` ↔ `agents`**（orchestrator.py:55-69 模块级 import agents；agents/judge_agent.py:17-20 模块级 import 根模块 decision_semantics/kg_adapter）。经逐模块核对，**不构成模块级真循环**：judge_agent 依赖的是 decision_semantics/kg_adapter，这两者不 import orchestrator/agents（decision_semantics.py:13-18 仅标准库；kg_adapter.py:34 只 import `rag.knowledge_base`）。
- **真循环但均为延迟 import**：`orchestrator.py` ↔ `workflow.py` —— orchestrator.py:235 在 `_build_langgraph` 内 `from workflow import compile_workflow`；workflow.py:62 在 `context_node` 内 `from orchestrator import build_context`。两者都在调用期才解析，**import 期不成环**（安全，但耦合方向双向）。
- 显式"为避免循环"的局部 import：benchmarks/loader.py:79 `from benchmarks.taxonomy import validate_suite_cases  # local: avoid cycle`。
- 包内自引用：planner/planner.py:20 `from planner import prompts`（依赖 planner/__init__.py 的再导出，能工作但脆弱）。
- 其他延迟 import：agents/vision_agent.py:14、agents/judge_agent.py 内多处（见 B6）、kg/mcp_server.py:29 为模块级（前置 sys.path 注入，`# noqa: E402`）。
- 未发现 `import` 期即触发 RecursionError 的环 [推测：静态判定，未做运行时 import 图验证]。

## B6 坏味道清单

| # | 类别 | 计数/位置 | 说明 |
|---|---|---|---|
| 1 | **bare `except:`** | **0 处**（`rg 'except\s*:'` 无命中） | 历史 E722 已清理（commit 0111465） |
| 2 | `except Exception` | **45 处**，Top：rule_engine/sensor_anomaly.py 7、kg_adapter.py 6、agents/judge_agent.py 5、ui/web_app.py 4、ui/tui.py 3、rag/retriever.py 3、agents/vision.py 3 | 多数为有意的"降级边界"并附 `# noqa: BLE001`（如 agents/judge_agent.py:96、:127，gateway/app.py:48 "boundary: never leak a bare 500"） |
| 3 | **静默吞异常** | 2 处：ui/web_app.py:148 `except Exception: pass`（删除临时上传图失败）；debate/engine.py:16 `except Exception: return None`（取湿度读数失败） | web_app.py:148 是唯一 `pass`，且位于未纳入测试的 streamlit 路径 |
| 4 | **硬编码绝对路径** | 代码 **0 处**（`rg '[A-Za-z]:\\'` 仅命中文档示例 scripts/AGRiKG_SETUP.md:60 `E:\download\…` 与一段 YAML 字符串 tests/test_experiments.py:79） | 本地服务地址是带环境变量默认值的相对配置：kg_adapter.py:196 `bolt://localhost:7687`、rag/retriever.py:21 `http://localhost:6333`、planner/planner.py:128 `https://api.deepseek.com` |
| 5 | 超长函数 | 1 个 >100 行：agents/judge_agent.py:340 `_run_llm_judge`（121 行）；>60 行 8 个（scripts/run_delivery_eval.py:56 `run` 85 行、ui/web_app.py:153 `_show_decision` 70 行、ui/tui.py:393 67 行、agents/judge_agent.py:275 65 行、:469 61 行、experiments/analysis.py:480 65 行、tests/test_metrics.py:61 69 行） | 度量按 dedent 边界 [推测]，跨多行字符串可能略偏 |
| 6 | 魔法数 | workflow.py:178 `0.6 <= decision.confidence <= 0.85`；agents/judge_agent.py:264 `min(0.9, 0.45 + score*0.08)`、:295 `min(confidence,0.6)`、:542/544 `0.45`、:593/595 `0.55`；debate/critic.py:151-152 `0.72`/`*0.6`/`0.15`、:189 `*0.55`；planner/planner.py:94 `< 0.6` | 部分可通过环境变量覆盖（`AGRI_AI_MEMORY_GATE_MIN_CONF`、`AGRI_AI_ABSTAIN_MIN_SUFFICIENCY`），其余写死 |
| 7 | 同步阻塞 sleep | 1 处：ui/tui.py:282 `time.sleep(0.07)`（演示逐字打印） | 不在核心链路 [推测] |
| 8 | **sys.path 手工注入** | 19 处：tests/conftest.py:8,11；gateway/app.py:9；ui/tui.py:17；ui/web_app.py:15；kg/mcp_server.py:27；evals/{ablation,fixture_eval,runner,smoke_eval}.py；scripts/{run_delivery_eval,run_challenge_evaluation,generate_stability_report,fit_decision_calibration}.py；utils/generate_calibration.py:19；src/…/challenge_report.py:50 | 仓库无 pyproject/setup.py（实测均不存在），因此每个入口都必须"垫路径"，这是结构性债务；亦导致 E402 告警（KNOWN_DEBT:42-45） |
| 9 | 关键词硬编码上下文解析 | orchestrator.py:72-99（温室/作物/意图全部 if-else 关键词表） | 与 README 的"上下文解析"表述相比，规则极简；属 [推测] 可接受的原型实现 |
| 10 | 超长单文件/巨类 | agents/judge_agent.py:86 类 575 行；benchmarks/capability_matrix.py 30 函数 863 代码行 | 见 B1 |

## B7 测试现状（含 README 声称 vs 实际）

**清单**：`tests/` 共 27 个 `.py`（conftest.py + 26 个 `test_*.py`，`Get-ChildItem` 实测）→ 与 README.md:78 的"26 个测试文件"一致。

**用例数核对**：

| 口径 | 数值 | 证据 |
|---|---|---|
| 静态 `def test_` 计数 | **316**（26 文件相加） | `rg -c '^\s*(async )?def test_' tests` |
| `pytest --collect-only -q -p no:cacheprovider` 实测 | **342 collected** | 输出 "342 tests collected in 3.26s"；其中含 26 个 parametrize 展开 |
| README 声称 | **344 个用例** | README.md:78（"26 个测试文件、344 个用例"）、README.md:169 |
| 差值 | **-2**（README 多算 2） | 且 README.md:171 又写 "342 passed / 2 skipped"，与 344 自相矛盾；实测 342 是 **含 2 个 skip 的总量**，实际可执行仅 340 |

**skip / xfail**：
- skip 仅 2 处，均为模块级 `pytest.importorskip`：tests/test_phase4_harness_runtime.py:9-13（`scripts.run_phase4_2` 已删）、tests/test_phase4_reliability.py:11-16（`scripts.run_phase4_2_real_agent` 已删；注释写明 "removed in f1c7e98"）。collect-only 输出 `SKIPPED [1] …: Phase 4.2 direct harness absent…` / `Phase 4 evaluation harness absent…`。
- **xfail：0 处**；parametrize 出现在 9 个文件（test_benchmarks.py:42,48、test_metrics.py:426、test_delivery_contract.py:105、test_enriched.py:119、test_judge_runtime.py:216、test_taxonomy.py:60,69、test_challenge_scorer.py:311）。

**pytest 配置是否失效**：pytest.ini 仅 7 行有效配置——`testpaths = tests`（:5）、`norecursedirs = … logs results data neo4j pytest-of-lkl torchinductor_lkl`（:6）、`addopts = -ra`（:7）。无 `markers` 声明但测试只用内建 mark（parametrize），**不存在未注册 mark 的 warning 风险**；无 `pythonpath`，靠 tests/conftest.py:8,11 注入 ROOT/SRC。残留风险：pytest.ini:2-4 注释自称仓库根有 "stray pytest-of-lkl/"，说明配置是为规避历史 ACL/杂项目录而补的，属环境适配补丁。

**覆盖映射（按测试文件 import 粗判）**：

| 单元 | 覆盖它的测试文件 |
|---|---|
| agents | 8（test_agent_output / test_cli_output / test_collective_omission / test_decision_confidence / test_delivery_contract / test_judge_runtime / test_planner / test_trace） |
| benchmarks | 5（test_benchmarks / test_capabilities / test_challenge_set_valid / test_enriched / test_taxonomy） |
| evals | 7（test_ablation / test_benchmarks / test_capability_metrics / test_challenge_evaluation / test_enriched / test_experiments / test_metrics） |
| experiments | 3（test_analysis / test_experiments / test_fingerprint） |
| trace | 4；planner 3；storage/gateway/debate 各 1（均为 test_delivery_contract）；utils 3；scripts 2（test_challenge_evaluation:29、test_stability_metric_contract:5）；tool_router 2 |
| **src/openmetaphysics** | 有覆盖，但 import 名是 `openmetaphysics.*`（tests/test_challenge_evaluation.py:27、test_challenge_scorer.py:25、test_challenge_set_valid.py:19），不是 `src.*` |
| **未覆盖** | **rag/（0）、kg/（0）、rule_engine/（0）、ui/（0）**；其中 kg_adapter.py 的 Neo4j 路径、rag 检索、mcp_server 完全无测试 |

**能否真的跑**：本轮按约束只做了 collect（不执行用例），collect 通过（exit 0）说明**导入层健康、无 collection error**；`342 passed / 2 skipped` 的通过数 **无法在本轮验证 [待确认]**，且 context/KNOWN_DEBT.md:8-10 记载沙箱下曾为 340 passed / 3 failed（3 个失败为 `tests/test_experiments.py` 调 git 时管道被沙箱禁止）。

## B8 死代码与孤立脚本

**scripts/*.py 被谁调用（6 个文件）**：

| 脚本 | 调用方（证据） | 状态 |
|---|---|---|
| scripts/run_delivery_eval.py | README.md:174、reports/README.md:31、reports/acceptance_20261024.md:65（`python scripts/run_delivery_eval.py`） | 活（离线回归入口） |
| scripts/run_challenge_evaluation.py | tests/test_challenge_evaluation.py:29 直接 import；自带 `__main__`（:379） | 活（有测试） |
| scripts/generate_stability_report.py | tests/test_stability_metric_contract.py:5 import；README.md:189 | 活（有测试） |
| scripts/import_agrikg.py | start.ps1:78、start.sh:69（`docker compose exec api python scripts/import_agrikg.py`）、scripts/AGRiKG_SETUP.md:70 | 活（仅文档/启动脚本，无测试） |
| scripts/fit_decision_calibration.py | 仅 docs/archive/changelog.md:8、reports/phase6_redesign_20261023/implementation_status.md:22；**无任何代码/测试 import** | **孤立脚本** [推测：一次性工具] |
| scripts/__init__.py | 包标记（`scripts/__init__.py:1`） | — |

**无任何外部 import 的模块**（入度扫描 + 人工复核）：

| 模块 | 判定 | 依据 |
|---|---|---|
| evals/fixture_eval.py | 手动入口，非死代码 | evals/README.md:29-32、reports/acceptance_20261024.md:64；evals/fixture_eval.py:14-15 自垫 sys.path |
| evals/smoke_eval.py | 手动入口 | evals/README.md:8、reports/README.md:33、reports/acceptance_20261024.md:63 |
| experiments/manager.py | 手动 CLI 入口 | experiments/manager.py:519 `__main__`；docs/archive/sprints/EXPERIMENT_MANAGER_SPRINT_05_REPORT.md:61 |
| kg/mcp_server.py | 独立 MCP server 进程 | kg/mcp_server.py:445 `__main__`；kg/__init__.py:3 说明"独立进程" |
| ui/tui.py | 文档入口 | README.md:109 `python -m ui.tui`；docs/DEMO_RUNBOOK.md:34 |
| ui/web_app.py | **未验证的 streamlit 入口**（无测试、README 标注"已声明但未纳入验证" README.md:79） | ui/web_app.py:275 `__main__` |
| utils/generate_calibration.py | 校准样本生成器（仅 `__main__`，:85） | 无 import 者 |
| planner/prompts.py | 被 planner/planner.py:20 包内引用 | 非死 |
| trace/collector.py、trace/exporter.py | 经 trace/__init__.py:12-14 再导出 | 非死 |

**其他遗留物 / 孤儿**：

| 项 | 证据 | 风险 |
|---|---|---|
| **根目录 `xx`（15,082B，被 git 跟踪）** | `git ls-files --error-unmatch xx` 成功；内容为一次大清理的 `git diff --stat` 转储（尾部含 `211 files changed, 606 insertions(+), 68365 deletions(-)`、被删脚本清单） | 中：跟踪了临时转储文件，且泄露历史删除清单；命名无意义 |
| 双 MCP server 的失效交叉引用 | kg/mcp_server.py:41 注释"与 knowledge_mcp_server.py 的 DISEASE_DB 结构一致"，但 `knowledge_mcp_server.py` 已不存在（`Test-Path` False） | 低（注释误导） |
| 主机遗留目录 | pytest-of-lkl/、torchinductor_lkl/、pytest-of-lkl 的 ACL 拒绝访问（`Get-ChildItem` 报 Access denied）；被 .gitignore 与 pytest.ini:6 双重排除 | 低（已隔离） |
| 未提交改动 3 个 | `git status --porcelain` → ` M README.md`、` M docs/DEMO_RUNBOOK.md`、` M tests/test_planner.py`（diffstat: README +87、RUNBOOK +30、test_planner -17/+14） | 中：交付物与工作区不完全一致；`tests/test_planner.py` 未提交的改动会影响 README:171 的可复现性 |
| 已删实现留下的空壳测试 | tests/test_phase4_harness_runtime.py:9-13、test_phase4_reliability.py:11-16 | 低（永久 skip） |
| 文档历史层（不计入代码） | docs/archive/ 与 logs/（114 文件）为本地/历史快照，.gitignore:41 忽略 logs/ | 低 |

## B9 未经确认事项 [待确认]

1. **测试通过数**：README.md:171 声称 `342 passed / 2 skipped`，context/KNOWN_DEBT.md:8-10 声称沙箱 `340 passed / 3 failed`；本轮按只读约束未执行用例，**通过数未验证**；仅确认 `342 collected`（含 2 module-level skip），故"344 用例"（README.md:78,169）与实测差 2。
2. **`xx` 的定位**：被 git 跟踪但内容是 diff 转储，是否有意提交/是否可清理，无法从仓库元数据判定（无 .gitattributes 说明）。
3. **两套 MCP Server 是否为有意设计**：kg/mcp_server.py 与 rag/knowledge_base.py 各自 `FastMCP` + 同名工具，未经运行验证是否同时部署；kg/__init__.py 只描述了 kg 一侧。
4. **能力矩阵双生成器**（benchmarks/taxonomy.py vs benchmarks/capability_matrix.py）是有意分层还是迁移残留：两者写同一对输出文件，但无文档说明谁权威。
5. **scripts/fit_decision_calibration.py** 是否为仍在用的运维脚本：无测试、无 import、仅历史文档提及 [推测为一次性工具]。
6. **循环依赖结论**：基于静态 import 文本 + 延迟 import 位置判定，未做运行时 import 图/`pytest --collect` 之外的动态验证 [推测]。
7. **超长函数与魔法数**：函数边界用 dedent 启发式、魔法数用阈值模式匹配，均为 [推测] 口径，可能与人工判读有 ±若干行的差异。
8. **`openmetaphysics` 的 sys.path 约定**是否会在非 pytest 环境下失效（如 `python -m openmetaphysics.evaluation.challenge_report`，需 PYTHONPATH=src）：challenge_report.py:49-50 自带垫路径，实际可运行性未验证。
