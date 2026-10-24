# ACIS MVP 端到端验收记录（2026-10-24）

> 验收对象：MVP 实现提交 `work/20261024-mvp-delivery` @ `3b5cc99`；验收材料提交在本轮分支 `work/20261024-acceptance-portfolio`（代码与验收对象一致）。
> 验收环境：Windows / `.venv` Python 3.13.3；本机 Neo4j/Qdrant 在线；未新增依赖。
> 判定口径：**实际运行**，不以静态检查代替；外部模型调用单独标注；沙箱限制逐条记录。

---

## 1. 环境与启动

| 项 | 结果 |
|---|---|
| Python | `.venv` 3.13.3；`pip check` 无破损（依赖锁定见 `requirements-lock.txt`） |
| 依赖 | 未新增；锁文件为本机 `pip freeze` 生成（Windows 平台） |
| 配置 | `.env.example` 提供完整模板；核心文本链无 key 可跑 |
| 启动（CLI） | `python orchestrator.py --rules-only "..."` exit 0；冷启动约 8–9s，预热后约 1.4–2.7s |
| 启动（API） | `TestClient` `/health` 200；真实 `uvicorn` 未起服务（避免占用端口），接口层已实测 |
| 启动（TUI） | 本轮沙箱禁止 `Start-Process` 重定向，无法非交互回放；同环境上一轮实测 `python -m ui.tui` 12.2s 跑通场景 1；本轮未改 TUI 代码 |

---

## 2. 正常业务案例（端到端）

**输入**：`温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？`

**输出（规则链路，实测）**
- 裁决：`病理判断首选：番茄叶霉病`
- 置信度：0.72；风险：medium；人工复核：否
- 6 条行动建议；12 条 Agent 轨迹（感知 3 / 记忆 4 / 专家 5）
- `decision_id` 落库；Trace 10/10 阶段；19 事件
- 命令：`python orchestrator.py --rules-only --seed 7 --trace-out logs/trace_acceptance.json "..."`
- Trace 校验：`trace_id=4c0e91f7...`；阶段齐全；`judge_runtime.outcome=rules`；19 events

**LangGraph 路径**：`python orchestrator.py --seed 7 "..."`
- 同诊断；置信度 0.74；第二轮辩论生效（15 条轨迹）；22 事件；10/10 阶段。

**API**：
- `GET /health` → 200 `{"status":"ok","judge_configured":true}`
- `POST /diagnose` → 200，`decision=病理判断首选：番茄叶霉病`、`judge_mode=rules`、`confidence=0.74`、`trace_id` 有值、`trace_stages=10`、`decision_id=79`

---

## 3. 异常处理与恢复

| 故障场景 | 方法 | 实测结果 |
|---|---|---|
| 外部模型连接失败 | 假 key + `AGRI_AI_JUDGE_BASE_URL=http://127.0.0.1:9` + `--llm-judge` | 进程 exit 0；`judge_mode=rules`；`outcome=fallback`；`fallback_reason_code=connection_error`；`retry_exhausted=true`；`missing_evidence` 含原因；假 key 未泄漏 |
| LangGraph 执行失败 | 单测注入 `_compiled_graph.invoke` 抛 `RuntimeError` | 自动回退规则编排；`missing_evidence` 含"回退规则编排"；决策仍输出（`test_delivery_contract.py`） |
| SQLite 持久化失败 | 单测替换 `save_decision` 抛 `RuntimeError` | 决策仍返回（`decision_id=None`），WARNING 日志可见（`test_delivery_contract.py`） |
| LLM 输出无效/格式错误 | 单测注入 `JudgeResponseFormatError` | 回退规则；`fallback_reason_code=response_format_error`（`test_delivery_contract.py`） |
| 视觉模型不可用 | `HF_HUB_OFFLINE=1` + 临时图 | <2s 返回 mock 结果（修复后为"番茄叶霉病/0.87"），不再挂起 HF 下载 |
| 规则冲突 | fixture 场景 `tomato_irrigate_with_disease` / `tomato_mold_low_humidity` | 风险 high + Critic triggered（12/12 fixture 中 2 例） |

---

## 4. 自动化测试

| 命令 | 结果 | 说明 |
|---|---|---|
| `pytest -q tests/test_delivery_contract.py`（沙箱 ACL shim） | **12 passed** | 正常流程/回退/契约 |
| `pytest -q -p tmpshim`（全量，ACL shim） | **3 failed, 340 passed** | 3 个失败均为沙箱禁止子进程管道（`tests/test_experiments.py` 调 git），非业务代码失败 |
| `pytest -q`（全量，沙箱原样） | **1 failed, 286 passed, 56 errors** | 56 errors 为沙箱 `tmp_path` 0o700 ACL；收集阶段已修复（此前 31 collection errors） |
| `python evals/smoke_eval.py` | exit 0 | 3 套×3 场景；第三套无 key 回退 rules |
| `python evals/fixture_eval.py` | exit 0 | 12/12 通过 |
| `python scripts/run_delivery_eval.py` ×2 | 12/12 命中、2 例 Critic、平均置信度 0.6583；两次 `summary.json` **SHA256 一致** | 离线、零 API |

---

## 5. 模型调用与评测

### 5.1 真实模型调用（受控单次）

- 通道：opencode zen gateway（`https://opencode.ai/zen/go/v1`），模型 `deepseek-v4.1-flash`；
- 配置：`AGRI_AI_JUDGE_TIMEOUT_SECONDS=30`、`MAX_RETRIES=0`、`SELF_CONSISTENCY_K=1`；
- 结果：**成功**；`judge_mode=deepseek`、`outcome=success`、耗时 **34.56s**；
- Token：prompt 5,743 / completion 4,611 / total **10,354**；
- 输出：`番茄叶霉病（黄枝孢霉 Fulvia fulva）——高疑似，但环境硬约束不满足，需人工/镜检复核后方可定论`；confidence 0.3815；risk medium；
- **边界**：这是"接口与真实服务连通"的单次验证，不是质量评测；k=1，未做多 seed。

### 5.2 已有 C0/C1/C2 实验审计

详见 `reports/experiment_audit_20261024.md`。关键结论：
- Phase 6 baseline seed42：72/72 次真实 Judge 调用成功、0 回退；C0 20/24、C1 19/24、C2 24/24（单 seed，不能证明架构收益）。
- SC：seed42 仅 13/24 可评（11 次 connection_error），seed43 24/24；ECE/corr 依赖 trace 中 agreement，committed raw 不能复算。
- Phase 4.2-R 报告中的 "accuracy" 是 factor coverage，不是诊断准确率；191/216 为规则回退，不可作为模型效果。
- 简历只能引用"链路可运行/回退可统计/固定评测可复现"，不能引用"架构优于基线"。

---

## 6. 环境限制与未完成验证

| 项 | 状态 |
|---|---|
| 沙箱 `tmp_path` ACL | 44+12 个用例在沙箱中报错；普通 Windows 环境预期通过，但**本轮无独立普通环境可验证** |
| 沙箱子进程管道 | 3 个 `test_experiments.py` 用例失败；普通环境预期通过，未实测 |
| TUI 非交互回放 | 沙箱 `Start-Process` 重定向不可用；上轮同环境已实测 |
| Docker | 未构建（本机无 Docker）；Dockerfile/compose 存在但未验证 |
| 真实 LLM 多次/质量 | 仅 1 次受控调用；未做多 seed、多 prompt 质量评测 |
| 用户 WIP | 5 个未提交修改 + `tests/fixtures/` 未跟踪，本轮未覆盖、未提交；fresh clone 与该工作树不完全一致 |
| Web UI / MCP / Phase 4-6 | 未验证，交付范围外 |

---

## 7. 验收结论

- 核心文本业务路径：**通过**（CLI/API/规则+LangGraph/落库/Trace/回退）。
- 关键失败路径：**通过**（连接失败/LangGraph 失败/持久化失败/无效输出/视觉不可用；有测试或实测）。
- 自动化测试：**部分通过**（340/343，3 个失败为沙箱限制；普通环境未实测）。
- 可复现评测：**通过**（12 例离线评测两次哈希一致）。
- 真实模型调用：**单次成功**（接口连通验证，非质量评测）。
- 仍阻塞"完全干净复现"的：用户 WIP/fixtures 未冻结；普通环境测试未跑；Docker 未验证。
