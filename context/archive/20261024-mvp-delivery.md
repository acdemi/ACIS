# 2026-10-24 最小交付实施（MVP Delivery）

## 对话主题与目标

按已确认的 MVP 范围与优先级，对 ACIS 做最小必要工程实现：建立可运行基线、打通文本核心流程、修复工程阻塞、补最小测试，并产出可复现的离线评测与演示入口。不扩张架构、不启动新 Phase、不 push/merge。

## 执行前提与分支

- 基线分支：`work/20261024-resume-delivery-plan` @ `39df292`
- 本轮分支：`work/20261024-mvp-delivery`（基于上述分支）
- **未覆盖用户未提交修改**：`decision_semantics.py`、`evals/metrics.py`、`src/openmetaphysics/evaluation/challenge_report.py`、`tests/test_challenge_evaluation.py`、`tests/test_metrics.py`、`tests/fixtures/`、`reports/phase6_ablation_20261024/` 保持原状，未纳入本轮提交。
- 未执行 push / merge；未删除实验数据；未改核心接口（仅增量字段）。

## 变更文件清单

新增：
- `pytest.ini`：收集范围限定 `tests/`，避免根目录本地产物污染 `pytest -q`
- `.env.example`：完整环境变量模板（Judge/记忆门控/存储/后端/离线）
- `requirements-lock.txt`：当前验证环境的 `pip freeze` 锁定
- `scripts/run_delivery_eval.py`：离线 12 例固定评测，输出 `reports/delivery_eval/summary.{json,md}`
- `reports/delivery_eval/summary.json`、`summary.md`：已提交的评测结果
- `tests/test_delivery_contract.py`：12 个核心路径/失败路径/数据契约测试

修改：
- `orchestrator.py`：`--trace-out` Trace 导出、`--seed` 随机种子、`--json` 增量输出 `trace_id/trace_stages`、LangGraph 回退与持久化失败 WARNING 日志
- `gateway/app.py`：`/diagnose` 异常边界（JSON 500）、响应增量 `trace_id/trace_stages`、`/health` 增加 `judge_configured`
- `agents/vision_agent.py`：修复视觉结果字段（`diagnosis` vs `top_prediction`）
- `agents/vision.py`：离线/mock 模式下跳过 HF 模型加载，避免演示阻塞
- `agents/judge_agent.py`：自一致性采样失败分类 + WARNING 日志 + `failure_codes`
- `README.md`：新增"最小可交付版本"、干净环境准备、Trace/seed 用法、环境变量、测试/评测命令与数字校正
- `docs/DEMO_RUNBOOK.md`：演示命令改用 `--trace-out logs/...` 与 `--seed 7`

## 实现内容与验收结果

| 验收项 | 命令 | 真实结果 |
|---|---|---|
| 新测试 | `pytest -q tests/test_delivery_contract.py`（沙箱 ACL shim） | **12 passed** |
| 全量测试（普通环境近似） | `pytest -q -p tmpshim`（ACL shim，仅证据目录） | **3 failed, 340 passed**；3 个失败均为沙箱禁止子进程管道（`experiments/archive.py` git 调用），非业务代码失败 |
| 全量测试（沙箱原样） | `pytest -q` | **1 failed, 286 passed, 56 errors**；56 errors 为沙箱 `tmp_path` 0o700 ACL，1 failed 为子进程管道；**收集阶段已修复**（不再有 31 collection errors） |
| smoke | `python evals/smoke_eval.py` | exit 0，3 套×3 场景（第三套无 key 回退 rules） |
| fixture | `python evals/fixture_eval.py` | exit 0，12/12 通过（2 例 critic=on） |
| 离线评测 | `python scripts/run_delivery_eval.py` ×2 | 12/12 期望命中、Critic 2 例、平均置信度 0.6583；两次输出 **SHA256 完全一致** |
| CLI 规则 + Trace | `orchestrator.py --rules-only --seed 7 --trace-out logs/trace_demo.json "<query>"` | exit 0；输出 trace_id + 10 stages；trace JSON 含 judge_runtime |
| CLI LangGraph + Trace | `orchestrator.py --seed 7 --trace-out ... "<query>"` | exit 0；22 事件、10/10 阶段；第二轮辩论生效 |
| CLI JSON 契约 | `orchestrator.py --json "<query>"` | 原有 decision 字段 + `trace_id/trace_stages` 增量字段 |
| API | TestClient `GET /health`、`POST /diagnose` | 200；health 含 `judge_configured`；diagnose 返回 decision/confidence/`trace_id`/`trace_stages` |
| 故障回退 | 假 key + `127.0.0.1:9` + `--llm-judge` | exit 0；`judge_mode=rules`、`fallback_reason_code=connection_error`、`retry_exhausted=true`、缺失证据含回退说明、假 key 不泄漏 |
| 视觉修复 | 离线 mock 图 + `HF_HUB_OFFLINE=1` | `claim=图像最可能识别为：番茄叶霉病`，`confidence=0.87`（修复前"未知类别/0"） |

## 未完成 / 未验证

- **P0-1 冻结用户 WIP 未执行**：按 Git 边界保留 5 个未提交修改 + `tests/fixtures/` 未跟踪；fresh clone 的一致性需用户授权后再提交/回退。
- LLM Judge/Critic 真实服务路径未在本轮调用（成本/可用性）；故障路径用测试替身与本地连接拒绝验证，未做真实模型质量验证。
- TUI 非交互回放在本轮沙箱被禁止（`Start-Process` 重定向不可用）；同环境上一轮已实测通过，本轮未改 TUI 代码。
- Docker 构建未执行；Web UI / MCP Server / Phase 4-6 评测链未验证，属于本轮范围外。
- 演示输出仍依赖本地 SQLite 案例状态（`data/agri.db`）；空 DB 时案例库文案会退回硬编码模式（决策/置信度不变），需在演示前重置或说明。
- `evals/smoke_eval.py` 第三套 LLM Judge 在无 key 时仍回退 rules（盲区未改）。

## 运行环境与外部依赖

- Windows，`.venv` Python 3.13.3；本轮未装新依赖。
- 本机 Neo4j/Qdrant 在线；设 `NO_PROXY=localhost,127.0.0.1` 后 RAG 走 Qdrant，否则回退内存。
- 沙箱限制：`tmp_path` 0o700 目录不可列举、禁止子进程管道；普通 Windows 环境无此问题。
- 未调用真实 LLM/外网。

## 分支与提交

- Branch：`work/20261024-mvp-delivery`
- 实现提交：`059fc0b`（14 files changed, +1239/−59）
- 本归档提交：该分支后续提交（docs(archive): 20261024 mvp delivery）

## 下一项最值得投入的工作

1. 经用户确认后冻结 WIP + `tests/fixtures/`，使 fresh clone 与当前验证树一致（P0-1）。
2. 按 `docs/DEMO_RUNBOOK.md` 做一次 TUI 现场彩排（含 trace 导出与故障注入），确认真终端动画/交互。
3. 若允许外部模型：用 `.env` 配置一次真实 LLM Judge 冒烟，记录 `judge_mode=deepseek` 与延迟；否则保持"可选、未验证"标注。
