# ACIS 交付审计 — 核心流程可运行 / 演示可执行（实测取证）

- 仓库：`E:\knowledge_database\ACIS`　分支：`work/20261024-delivery-audit`（未切换、未 commit、未改任何被跟踪文件）
- 日期：2026-10-24　执行者：teammate `flow-runner`（任务 task-1）
- 解释器：`.\.venv\Scripts\python.exe`（Python 3.13.3）
- 统一环境变量：`PYTHONIOENCODING=utf-8`、`PYTHONPATH=.`
- 证据目录：`logs/delivery_audit_20261024/flow/`（gitignored）
- 本文件所有命令均在仓库根执行；pwsh 中外部程序输出一律落文件（`Start-Process -RedirectStandardOutput`），不经 cmdlet 管道。

## 0. 关键环境事实（影响所有结论的解释前提）

| # | 事实 | 证据 |
|---|---|---|
| E1 | 本机 Neo4j **在线可用**：`kg_adapter.py --status` → `neo4j_connected: true`，`bolt://localhost:7687` | `kg_status.out.txt` |
| E2 | 本机 Qdrant **在线可用**（1.18.2）；但**系统代理（Clash 类）劫持 localhost HTTP**，未设 `NO_PROXY` 时所有 localhost 请求返回 **502**，RAG 静默降级为 `fallback` | `network_probe.out.txt` vs `network_probe_noproxy.out.txt`；`start.ps1:22-24` 注释已说明该现象 |
| E3 | 设 `NO_PROXY=localhost,127.0.0.1` 后本地服务正常（Qdrant 200），RAG 后端变为 `qdrant` | `cli_rules_only_noproxy.out.txt`（rag=qdrant） |
| E4 | 沙箱 ACL：`os.mkdir(path, 0o700)` 创建的目录**不可列举**（`PermissionError [WinError 5]`），其他 mode 正常；pytest 的 tmp 目录全部用 0o700 | `probe_acl3.py` 输出：`p_700` 稳定 LIST-FAIL，`p_600/755/777/default` LIST-OK |
| E5 | 沙箱禁止 `subprocess` 创建管道（`_winapi.CreatePipe` → `PermissionError [WinError 5]`），故任何 `capture_output=True` 的子进程调用在测试中失败 | `pytest_full.out.txt` FAILURES 段 |
| E6 | 注入的 Judge 端点走系统代理时会被 502 掩盖为 `server_error`；设 `NO_PROXY` 后才是真实连接错误/超时 | §4 四种变体对照 |

> 结论前提：本机**不是**“离线/无服务”环境（Neo4j、Qdrant 都在跑），代理是唯一的网络噪声源。

---

## 1. pytest 全量（退出码 / passed / failed / errors / 归因）

### 1.1 规范命令（任务书指定形式）
```
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
  （TEMP=TMP=logs\delivery_audit_20261024\tmp，目录已预建）
```
- 结果：`1 failed, 286 passed, 44 errors in 16.41s`，进程退出码 **1**，总墙钟 18.7s
- 原始输出：`pytest_full.out.txt`（5515 行），stderr 空 `pytest_full.err.txt`
- 收集阶段先撞到仓库根遗留目录：`ERROR collecting pytest-of-lkl → PermissionError: E:\knowledge_database\ACIS\pytest-of-lkl`（首次运行）；加 `--ignore=pytest-of-lkl` 后才进入用例执行。

### 1.2 失败/错误归因（全部为沙箱环境，非代码缺陷）
- **44 errors** ＝ `tmp_path` fixture setup 阶段炸掉：
  `_pytest/pathlib.py:175 find_prefixed → os.scandir(E:\...\tmp\pytest-of-lkl) → PermissionError [WinError 5]`
  根因是 E4（0o700 目录不可列举），pytest 在 `make_numbered_dir`/`mktemp` 中固定 `mode=0o700`。
- **1 failed** ＝ `tests/test_experiments.py::test_build_manifest_has_reproducibility_fields`：
  `experiments/archive.py:58 subprocess.run(["git","rev-parse",...], capture_output=True)` →
  `subprocess.py:1388 _winapi.CreatePipe → PermissionError [WinError 5]`（E5）。
  注：`experiments/archive.py:66` 只 `except (FileNotFoundError, TimeoutExpired)`，**未兜 OSError/PermissionError**，与其 docstring “empty strings if unavailable” 不符 —— 属轻微健壮性缺口（沙箱触发，非主线功能）。

### 1.3 用 harness shim 剥离环境噪声后的“真实代码状态”
为把 44 个 ACL error 与代码质量分离，写了一个**仅作用于 gitignored 证据目录**的 pytest 插件（不改仓库、不改被测代码）：`tmpshim.py` 把目录创建 mode `0o700 → 0o777`。

```
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -p tmpshim --ignore=logs --ignore=pytest-of-lkl
  （PYTHONPATH=.;logs\delivery_audit_20261024\flow，TEMP 指向新目录）
```
- 结果：**`3 failed, 328 passed, 22 warnings in 42.14s`**（总墙钟 44.8s）→ 331 用例，与 1.1 的 286+44+1 完全对齐
- 3 个 failed 全部是同一个 E5 子进程管道问题：
  `test_experiments.py::test_build_manifest_has_reproducibility_fields`、
  `test_experiments.py::test_manager_run_archives_full_bundle`、
  `test_experiments.py::test_manager_run_ablation_arm`
- **代码级失败 = 0**；44 个 ACL error 全部转为 pass。
- 原始输出：`pytest_shim.out.txt` / `pytest_shim.err.txt`
- 结论（第 1 项核心流程测试面）：**PASS（条件是环境）**，但“规范命令”本身脆弱（见 §8-d）。

---

## 2. 回归脚本 `evals/smoke_eval.py`、`evals/fixture_eval.py`

| 项 | 命令 | 退出码 | 耗时 | 结果 |
|---|---|---|---|---|
| smoke | `.\.venv\Scripts\python.exe evals/smoke_eval.py` | 0 | **30.98s** | `smoke eval passed`；3 套 × 3 场景：`[rules]`、`[langgraph]`、`[langgraph+llm-judge]` 各 3 行均为 `medium | rules | ...` |
| fixture | `.\.venv\Scripts\python.exe evals/fixture_eval.py` | 0 | **28.56s** | `fixture eval passed (12 scenarios)`，12 条全 `[ok]`；`tomato_irrigate_with_disease`、`tomato_mold_low_humidity` 为 `risk=high` ＋ `critic=on`（反驳轮次确实触发） |

- 证据：`smoke_eval.out.txt`、`fixture_eval.out.txt`（stderr 均为 Qdrant 502 + UserWarning，与 E2 一致）
- **不写 `results/`**：运行前后 `results/` 条目数均为 6，mtime 仍为 2026-09-01 → 回归脚本不污染结果目录。
- 仅写 `data/eval.db`（`AGRI_AI_DB_PATH` 默认 `data/eval.db`，gitignored）；主流程另写 `data/agri.db`（持久化开关默认开）。
- 观察：`smoke_eval.py:76-81` 第三套只是 `pop DEEPSEEK_API_KEY`，在本轮注入假 key（`AGRI_AI_JUDGE_API_KEY`）时仍会**发起真实请求**并回退；它不断言 `judge_mode=="deepseek"`，所以“LLM Judge 套件”在无网络时也会显示通过 —— 该套件对 LLM 路径的失败是**不可见**的（`smoke_eval.py:37` 仅允许 `{rules, deepseek}`，回退后仍是 rules）。
- 判定：**PASS**（脚本自身可用、确定性 12 场景全绿）。

---

## 3. 真实输入端到端（规则 / LangGraph 两条路径，同一句输入）

输入（真实病害咨询原句）：
```
温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？
```

| 运行 | 命令 | 退出码 | 墙钟 | judge_mode | confidence | risk_level | agents | action_plan | decision_id |
|---|---|---|---|---|---|---|---|---|---|
| 规则 | `orchestrator.py --rules-only "<q>"` | 0 | 8.55s | rules | 0.72 | medium | 12 | 6 | 36（--json 那次） |
| LangGraph | `orchestrator.py "<q>"`（默认） | 0 | 9.06s | rules | 0.74 | medium | 15 | 6 | 37（--json 那次） |

- 两者 `decision` 一致：`病理判断首选：番茄叶霉病`；LangGraph 多出**第二轮辩论**（`debate.consensus[0]="【多轮辩论·第2轮】…"`，专家层 12→15 条 trace，confidence 0.72→0.74）。
- 全链路无任何人工修改中间数据：单条命令 → 感知(3)→记忆(4)→专家(5)→Debate→Critic→Judge→`action_plan`→SQLite 落库(`decision_id`)；`kg_backend=neo4j`。
- `--json` 输出 32KB/43KB，顶层键：`action_plan, confidence, debate, decision, decision_id, judge_analysis, judge_mode, need_human_review, reasoning_trace, risk_level, summary, token_usage, traces` —— **不含统一 Trace**（见 §8-f）。
- 证据：`cli_rules_only.out.txt`、`cli_langgraph.out.txt`、`cli_rules_only_json.out.txt`、`cli_langgraph_json.out.txt`、`cli_json_summary.json`。

### 3.1 统一 Trace 覆盖（进程内读取 `orchestrator.last_trace`）
`probe_orchestrator.py`（输出 `orchestrator_probe.json`）：

| 模式 | trace_id | events | stages_present | required_stages_missing |
|---|---|---|---|---|
| 规则 | `600affdb0a584af2bb06d10c744bfac8` | 19 | 10/10：request, perception, memory, experts, debate, critic, judge, planner, tool_router, metrics | `[]` |
| LangGraph | `260dda31b7504f82a6bf4a59cdb9beca` | 22 | 10/10（同上） | `[]` |

- 阶段计数（规则）：request 1 / perception 3 / memory 4 / experts 5 / debate 1 / critic 1 / judge 1 / planner 1 / tool_router 1 / metrics 1。
- **Planner/Tool Router 默认关闭**：`build_planner()` 仅在 `ACIS_ENABLE_PLANNER=1` 时返回实例（`planner/planner.py:187-195`），默认 trace 里 planner/tool_router 记为 `{"enabled": false}`。
- 补测开启 Planner（离线、规则版）：`probe_timing.py` planner_probe → `planner_enabled=true`，`required_tools=["image_capture","spray_workorder","irrigation_control"]`，`tool_router` 3 条请求、0 未解析，单次 1.45s，`judge_mode=rules` → **Planner→感知→…→Judge 全链路离线可跑**。
- 判定：**PASS**（核心流程 1）；缺陷仅是可观测性问题（trace 未出口，§8-f）。

---

## 4. 故障注入：LLM Judge 不可用 → 规则回退是否可解释

基础命令（任务书指定）：
```
set AGRI_AI_JUDGE_API_KEY=sk-test
set AGRI_AI_JUDGE_BASE_URL=http://127.0.0.1:9
set AGRI_AI_JUDGE_TIMEOUT_SECONDS=2
set AGRI_AI_JUDGE_MAX_RETRIES=0
.\.venv\Scripts\python.exe orchestrator.py --rules-only --llm-judge --json "<同一句>"
```

四种网络条件下的实测（全部**进程正常退出 0**、全部 `judge_mode=rules`、全部 `judge_runtime.outcome=fallback`）：

| 变体 | 环境 | 分类 code | fallback_detail（已脱敏） | retry_exhausted | 耗时 |
|---|---|---|---|---|---|
| A 指定注入 | 系统代理在（未设 NO_PROXY） | **server_error** | `InternalServerError: Error code: 502` | True | 13.37s |
| B 黑洞地址 | `http://10.255.255.1:81`，timeout=2 | **timeout** | `APITimeoutError: Request timed out.` | True | 13.11s |
| C NO_PROXY + 短超时 | `NO_PROXY=localhost,127.0.0.1`，timeout=2 | **timeout** | `APITimeoutError: Request timed out.` | True | 11.17s |
| D **NO_PROXY + timeout=10** | 同上，timeout=10 | **connection_error** ✅ | `APIConnectionError: Connection error.` | True | 12.19s |

- **A 与 D 的差异是环境（系统代理）而非代码**：E2 显示 `127.0.0.1:9` 在代理下被返回 502（被归类 server_error），设 `NO_PROXY` 后是真实连接拒绝（归类 connection_error，与任务书预期一致）。
- `debate.missing_evidence` 每次都追加可读回退说明，例如 D：
  `LLM Judge 不可用，已回退规则裁决 [connection_error] APIConnectionError: Connection error.`
  另一条常驻缺失证据：`缺少有效图像证据，视觉 Agent 未参与确认`。
- 脱敏：`judge_runtime` 只含 `provider/endpoint_id/model/timeout_seconds/sdk_max_retries/config_sources`，**无 api_key、无 Authorization**；`secret_scan.py` 对 64+ 证据文件扫描 `.env` 全部密钥（DEEPSEEK/OPENCODE/NEO4J）+ `sk-` 模式 → 判定文件除 TUI 硬编码密码外 **0 泄漏**；`fallback_detail` 不含 `sk-`。
- stderr 日志行（A，原始三行，`judge_agent.py`）：
  - `INFO  Judge request: provider=openai-compatible endpoint=http://127.0.0.1:9 model=deepseek-chat timeout=2.0s sdk_max_retries=0 temperature=0.1`（:354）
  - `ERROR Judge exception: type=InternalServerError code=server_error provider=… endpoint=…`（:370）
  - `WARNING Judge fallback: code=server_error provider=… endpoint=… sdk_max_retries=0 detail=Error code: 502`（:145）
- 证据：`fault_cli_judge.{out,err}.txt`、`fault_cli_judge_timeout.*`、`fault_cli_noproxy.*`、`fault_cli_conn.*`、`fault_injection.json`、`fault_summary.json`、`secret_scan.json`。
- 判定：**PASS**（故障可解释）；**但**“指定命令 + 默认无 NO_PROXY”在本机会被代理掩盖成 `server_error`，需在演示脚本里显式 `NO_PROXY`（§8-e）。

---

## 5. FastAPI 进程内（TestClient，不联网）

请求体格式（`gateway/app.py:24-28`）：`{"query": str, "image_path": str|None, "use_llm_judge": bool=False, "use_llm_critic": bool=False}`。

| 调用 | 状态码 | 响应要点 | 耗时 |
|---|---|---|---|
| `GET /health` | **200** | `{"status":"ok"}` | 0.097s |
| `POST /diagnose` `{"query":"温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"}` | **200** | `decision=病理判断首选：番茄叶霉病`、`judge_mode=rules`、`confidence=0.74`、`risk_level=medium`、`traces=15`、`action_plan=6`、`decision_id` 有值、`judge_analysis.judge_runtime.outcome=rules` | 7.55s（含首次进程内预热；整脚本 10.75s） |

- 响应 = `dataclasses.asdict(decision)`，顶层键与 CLI `--json` 完全一致（**无统一 Trace**）。
- 无 `/trace`、无 `/traces` 端点（`gateway/app.py` 仅有 `/decisions`、`/decisions/{id}`、`/feedback`、`/outcome`）。
- 证据：`fastapi_probe.json`、`fastapi_stdout.txt`、`fastapi_stderr.txt`。
- 判定：**PASS**。

---

## 6. TUI 演示（`ui/tui.py`，560 行）

### 6.1 静态确认
- **6 个演示场景**：`DEMO_SCENARIOS`（`ui/tui.py:73-122`）——番茄叶霉病诊断 / 灌溉与病害冲突(Critic) / 甜菜褐斑病 / 棉花枯萎病 / 番茄环境预警 / 高湿病害 vs 低湿（诊断存疑）。**README 第 159 行写“5 个”，与代码不符**。
- **Agent Trace 动画**：`_animate_trace()`（:268-292）用 `rich.live.Live`，每行 `time.sleep(0.07)` 逐条刷出感知/记忆/专家三层 12–15 条 trace，含置信度条形图与 ⚠ 警告。
- **Judge 分析展示**：`_render_judge_analysis()`（:393-457）——`judge_mode=deepseek` 时展示 agent 诊断/KG 一致性表、证据权重、KG 贡献度；`rules` 时展示硬约束违反、传感器读数、裁决推理。
- **无 key / 网络失败回退**：`_run_scenario()` try/except → 红色错误 Panel（:503-509）；Judge 失败时 `judge_agent` 回退 → 面板标题角标显示 `规则裁决`（:473）、缺失证据区显示回退原因（:374-378）。**注意**：TUI 只展示 `missing_evidence` 文案，不展示 `judge_runtime.outcome/fallback_reason_code` 字段。
- 其它：`[j]/[c]` 无 key 时明确拒绝（:534-545）；`sensor_override` 场景后恢复（:510）；`random.seed(7)` 保证演示可复现（:495）。

### 6.2 非交互实测（`Start-Process -RedirectStandardInput`，未用管道）
```
python -m ui.tui  <  tui_input.txt   （内容 "1\n\nq\n"）
```
- 退出码 **0**，墙钟 **12.2s**，stdout **24,444 字节**，stderr 仅 Qdrant 502 + UserWarning。
- 输出关键标记（`tui_run.out.txt`）：第 34 行“演示场景”面板 → 第 52 行“Agent 执行轨迹”（逐行 trace，含 `记忆层 RAG …85%`、`专家层 病理Agent …85%`）→ 第 75 行“★ 最终裁决”（`病理判断首选：番茄叶霉病`，`medium`）→ 第 88 行“辩论与反驳”→ 第 100 行“KG 锚定裁决分析”（`知识图谱后端：neo4j`，参照疾病列表，裁决推理）→ 第 112 行“行动建议”→ 第 139 行 `请选择 (1): 再见！🌱`。
- **6 场景中至少场景 1 在非 TTY 下完整跑通**（其余场景同一渲染路径、同一 orchestrator 调用）。
- 局限（如实记录）：非 TTY 下 `rich.Live` 动画不“动”（rich 自动降级为静态打印），动画本身只能在真终端演示；`[j]` LLM 裁判路径**未实测**（本轮禁止真实 LLM/外网）。
- 判定：**PASS（离线规则演示链路）** / **PARTIAL（LLM Judge 演示、动画效果未验证）**。

---

## 7. 计时（同一句输入，`probe_timing.py` → `timing_probe.json`）

| 场景 | 样本 | 中位 | 备注 |
|---|---|---|---|
| 规则模式，进程内预热后单次 | 1.408 / 1.553 / 1.434 s | **1.434s** | 含 2 次 Qdrant HTTP |
| LangGraph 模式，预热后单次 | 1.439 / 2.691 / 1.675 s | **1.675s** | 多一轮辩论 |
| 规则模式，冷启动整进程 | — | **7.30–8.55s** | 含 import torch/sklearn + Qdrant 客户端 + 传感器模型 |
| LangGraph 冷启动整进程 | — | **9.06s** | |
| `python orchestrator.py`（内置 2 场景 demo） | — | **9.02s** | 无需参数即可演示 |
| TUI 启动+1 场景+退出 | — | **12.2s** | 含 ~10s 传感器模型预热 |
| FastAPI 首次 `/diagnose` | — | **7.55s** | 进程内首调 |

- 重复性：同一 query 连续 4 个独立进程（`repeat_rules_1..3` + `cli_rules_only_json`）结果完全一致：`confidence=0.72, risk=medium, agents=12`；仅 1 次进程内首跑出现 `risk=low`（天气 Agent 使用未固定种子的 `random`，`agents/weather.py:14-20`）→ **decision 文本稳定，risk/confidence 有轻微抖动**。
- 与 README 第 161 行“之后每次决策 <1s”**不符**（实测 1.4–2.7s）。

---

## 8. 与 README / 文档声称不一致之处

| # | README/文档 | 实测 | 严重度 |
|---|---|---|---|
| a | `README.md:194` “单元测试（267 个，18 个测试文件 + conftest.py）” | **331 用例 / 23 个测试文件**（328 pass + 3 沙箱失败） | 中（数字过期，影响可验证性） |
| b | `README.md:159` “内置 5 个演示场景” | **6 个**（`ui/tui.py:73-122`） | 低 |
| c | `README.md:161` “之后每次决策 <1s” | 预热后 **1.43s（规则）/1.68s（LangGraph）**，最慢 2.69s | 中（演示节奏预期） |
| d | `README.md:4,53` 架构写明 Planner / Tool Router 为核心组成 | 二者**默认关闭**，需 `ACIS_ENABLE_PLANNER=1`（`planner/planner.py:187-195`），且该变量未列入 README 第 180-189 行环境变量清单 | 中（架构宣称 vs 默认行为） |
| e | 本地 HTTP 依赖 `NO_PROXY` | README:242 与 `start.ps1:22-24` 只在 start.ps1 路径设置；直接 `python orchestrator.py` 时系统代理把 localhost 打成 502，RAG **静默降级 fallback**（stderr 有 502 INFO 行），且 localhost Judge 端点会被误判 `server_error` | 中（环境可复现 + 故障分类） |
| f | 交付强调“统一 Trace” | Trace 仅存在于 `orchestrator.last_trace` 进程内；CLI `--json`、HTTP 响应、TUI 均**不输出** trace_id / 10 阶段。仅 `evals/runner.py:217-240` 用 `export_trace_json` 落盘。**无任何演示界面可视化统一 Trace** | 中（可观测性/演示卖点） |
| g | 凭证展示 | `ui/tui.py:221` **明文打印 Neo4j 密码**（`agriai2026`，与 README:143、`.env` 一致）——文档已公开，故为低危；但 UI 硬编码密码而非读 env | 低 |
| h | README:195 推荐 `python -m pytest -q` | 仓库**无 pytest.ini/pyproject.toml**：根目录任何遗留/不可列举目录（如 `pytest-of-lkl`）会让该命令**收集中断**；`logs/`、`data/` 也会被收集 | 中（一键复现脆弱） |
| i | `smoke_eval.py` 第三套标称 `langgraph+llm-judge` | 无网络时静默回退 rules 仍判 pass（未断言 `judge_mode=="deepseek"`） | 低（测试盲区） |

---

## 9. 演示可行性结论（第 6 项）

- **3–5 分钟演示能否完成：可以（离线/规则版）**。实测：`python -m ui.tui` 启动 10s 预热 + 每场景 1.4–1.7s；一条命令 `python orchestrator.py "<真实咨询>"` 9s 出完整裁决（总结/裁决/置信度/风险/共识/缺失证据/推理/行动建议/12 条 Agent Trace）；`POST /diagnose` 200 可现场演示 API。全流程无人工改中间数据。
- **缺什么（演示短板，按影响排序）**：
  1. **无脚本化 demo**：无 `scripts/demo.*`、无预置输入序列/一键跑全链路的入口（TUI 需人肉选项号，CLI 需手打中文 query）。
  2. **无 Trace 可视化**：统一 10 阶段 Trace 不在任何 UI/CLI/HTTP 出口；TUI 的“Agent 执行轨迹”是 `decision.traces`（12–15 条 Agent 输出），看不到 request→planner→metrics 的阶段级 trace_id/事件流。
  3. **LLM Judge / Critic 演示未验证**：本轮禁止真实 LLM 与外网；若现场网络/Key 异常，只能退化为 `judge_mode=rules`，且 TUI 不展示 `fallback_reason_code`（只有一句 missing_evidence 文案）。
  4. **localhost 代理坑**：演示机若开系统代理而未设 `NO_PROXY`，RAG 会 502 降级（不会崩，但 stderr 噪声 + 少一层能力展示）。
  5. 演示节奏缺口：`README.md:161` 承诺的“每次决策 <1s”达不到（1.4–2.7s），3–5 分钟里更适合演示 2–3 个场景。

---

## 10. 证据文件清单（本目录）

| 文件 | 内容 |
|---|---|
| `pytest_full.out.txt`（5515 行） | 规范 pytest 全量：1 failed / 286 passed / 44 errors |
| `pytest_shim.out.txt` | 加 ACL shim 后：3 failed（子进程管道）/ 328 passed |
| `tmpshim.py` | 仅证据目录内的 pytest 插件（0o700→0o777），不改仓库 |
| `probe_acl*.py` / `probe_acl3.py` 输出 | E4 根因复现（mode=0o700 目录不可列举） |
| `smoke_eval.out.txt` / `fixture_eval.out.txt` | 回归脚本输出与耗时 |
| `cli_rules_only*`, `cli_langgraph*`, `cli_demo_noargs*` | 两条端到端路径 + 内置 demo 的原始输出 |
| `orchestrator_probe.json`, `cli_json_summary.json` | decision/judge_mode/confidence/risk/trace 阶段/agent 清单 |
| `fault_cli_judge*`, `fault_cli_judge_timeout*`, `fault_cli_noproxy*`, `fault_cli_conn*` | 四种故障注入变体的 stdout/stderr |
| `fault_injection.json`, `fault_summary.json` | judge_runtime / reason_code / missing_evidence 汇总 |
| `fastapi_probe.json`, `fastapi_stdout.txt` | /health、/diagnose 状态码与字段 |
| `tui_input.txt`, `tui_run.out.txt`, `tui_run.err.txt` | TUI 非交互跑通场景 1 的完整渲染输出 |
| `timing_probe.json`, `orchestrator_probe.json` | 计时与 Planner-ON 补测 |
| `network_probe*.json/txt`, `kg_status.out.txt` | E1/E2/E3 环境事实 |
| `secret_scan.json` | 64+ 证据文件密钥泄漏扫描（仅 TUI 明文密码命中，已文档化） |
