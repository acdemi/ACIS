# ACIS 最终交付判定（2026-10-24）

> 依据：`reports/acceptance_20261024.md`、`reports/experiment_audit_20261024.md`、
> `reports/delivery_eval/`、`docs/PORTFOLIO.md`、`docs/DEMO_RUNBOOK.md`。
> 判定对象：MVP 文本链路（温室番茄病害诊断与处置建议），非全部历史 Phase。

---

## 1. 是否达到简历展示门槛

**达到（有条件）。**

- 有明确业务问题、真实可运行的端到端链路、可复现的离线评测、可演示的 TUI/CLI/API；
- 有测试、故障回退、Trace 与审计记录；
- 对实验结论做了口径审计，能够如实说明"能证明什么、不能证明什么"。

**条件**：
- 只能作为**个人项目/原型**展示，不能写成生产系统、真实田间验证或"架构优于基线"；
- 面试前需自己按 `docs/DEMO_RUNBOOK.md` 彩排一遍；
- 需要先冻结未提交的 WIP + `tests/fixtures/`，否则"他人按说明复现"会与当前验证树不一致。

---

## 2. 是否可以现场演示

**可以（离线规则版，推荐）；LLM 版可选。**

- TUI 6 场景、CLI 一条命令出完整裁决、API `/diagnose` 均可演示；
- 故障注入可现场展示"Judge 不可用 → 规则回退 + 原因 + 日志"；
- 有 key 时可加演真实 LLM Judge（本轮单次调用成功，34.56s / 10,354 tokens），但要接受网络/额度风险；
- 演示前必须设 `NO_PROXY`、`HF_HUB_OFFLINE=1`；无 key 不要承诺 LLM 效果。

---

## 3. 是否可以由他人按说明复现

**核心路径：可以。完整测试：有条件。**

可以：
- README 提供 venv 创建、`requirements-lock.txt`、`.env.example`、启动/评测命令；
- 无 Neo4j/Qdrant/API key 也能跑通 CLI/API/固定评测；`scripts/run_delivery_eval.py` 两次输出哈希一致。

有条件/阻碍：
- 当前工作树有 **5 个未提交修改 + `tests/fixtures/` 未跟踪**（并行会话产物）；fresh clone 与验证树不完全一致，
  且 `tests/test_challenge_evaluation.py` 依赖这些 fixture。**需用户授权后冻结（提交或回退）**。
- 普通 Windows 环境未实测；当前仅在受限沙箱验证（340 passed / 3 沙箱管道失败）。
- Docker 未构建；Web UI/MCP/Phase 4–6 未验证，不在 MVP 范围。

---

## 4. 哪些结果可以公开写入简历

**可以写（有原始数据/命令支撑）**
- 端到端文本诊断链路：CLI/TUI/FastAPI；规则 + LangGraph；Trace 10 阶段；SQLite 审计；
- 12/12 fixture 回归、12/12 离线交付评测（两次哈希一致）；
- 12 项交付契约测试；全量 343 用例中受限环境 340 通过（3 个为沙箱限制）；
- Phase 6 baseline seed42：72/72 真实 Judge 调用成功、0 回退；C0 20/24、C1 19/24、C2 24/24（单 seed）；
- Phase 4.2-R：191/216 次规则回退（说明降级真实发生且服务可用）；
- 真实 LLM 单次受控调用成功（34.56s / 10,354 tokens）；
- 故障分类/脱敏/自动回退、`--trace-out`、`--seed`、固定评测等可靠性工作。

**不可以写**
- "完整架构优于裸基线 / 准确率提升"（C1 未优于 C0；单 seed、n=24）；
- "准确率 1.00"（C2 24/24 仅 seed42，未复现；且是特定挑战集）；
- "R3/Phase 4.2 accuracy 0.36/0.19"（那是 factor coverage，不是诊断准确率）；
- "生产级 / 真实田间验证 / 用户规模 / 高并发"；
- "置信度校准已解决"（仅 C1、2 seed、13–24 有效样本）；
- "视觉识别已验证"（默认 mock，真实模型未验证）。

---

## 5. 哪些技术债可以合理保留

可以保留（不阻碍 MVP 展示）：
- Docker/部署、Web UI、MCP Server、实验管理器、Phase 4–6 评测链；
- 传感器/天气模拟、视觉 mock、真实 AgriKG/Qdrant 接入；
- 依赖锁为 Windows 平台生成（跨平台需调整）；
- 历史文档/Sprint 报告中的旧数字（已在 README 标注历史口径）。

应尽快处理（影响"可复现"承诺）：
- 冻结用户 WIP + `tests/fixtures/`；
- 在普通 Windows 环境复跑一次全量测试；
- 演示前重置/说明 SQLite 案例状态（`data/agri.db`）。

---

## 6. 仍阻碍交付的问题

| 问题 | 是否阻断简历展示 | 是否阻断"他人复现" | 处理 |
|---|---|---|---|
| 5 个未提交修改 + fixtures 未跟踪 | 否 | **是（部分测试/一致性）** | 需用户授权后冻结 |
| 普通环境未跑全量测试 | 否 | 部分（测试数字只能引用受限环境） | 找普通环境复跑 |
| Docker 未验证 | 否 | 否（不承诺部署） | 保持"未验证"标注 |
| 真实 LLM 仅单次调用 | 否 | 否（LLM 为可选） | 面试前可选复跑 |
| TUI 本轮未彩排 | 否 | 否 | 面试前按 runbook 彩排 |

---

## 7. 结论与建议

- **建议判定：MVP 达到交付标准，冻结功能，进入求职作品集阶段。**
- 不再启动 Phase 5/6 或架构扩展；不新增 Agent/记忆/校准/治理。
- 后续只做三类工作：
  1. 冻结 WIP/fixtures，普通环境复跑测试；
  2. 演示彩排与截图/GIF（可选）；
  3. 按岗位微调 `docs/RESUME_ACIS.md` 的措辞。
