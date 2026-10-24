# 2026-10-24 交付验收与简历材料整理

## 对话主题与目标

对已实现的 ACIS MVP 做最终端到端验收，审计已有 C0/C1/C2 实验，更新 README，形成技术展示材料与中文简历项目描述，并给出最终交付判定。不启动新 Phase、不 push、不 merge。

## 执行与验收结果

### 端到端
- 环境：Windows / `.venv` Python 3.13.3；未新增依赖；核心文本链无 key 可跑。
- CLI 规则链路：exit 0；`病理判断首选：番茄叶霉病`；置信度 0.72；10 阶段 Trace；19 事件；`--trace-out` 产出可校验 JSON。
- CLI LangGraph：exit 0；置信度 0.74；第二轮辩论；22 事件。
- API：`/health` 200（含 `judge_configured`）；`/diagnose` 200（decision/judge_mode/confidence/trace_id/10 stages/decision_id）。
- 异常：假 key + 假端点 → `judge_mode=rules`、`fallback_reason_code=connection_error`、`retry_exhausted=true`、系统不中断；单测覆盖 LangGraph 回退/持久化失败/无效输出。
- 测试：新契约测试 12 passed；全量 ACL shim 下 3 failed/340 passed（3 个为沙箱禁止子进程管道）；沙箱原样 1 failed/286 passed/56 errors（`tmp_path` ACL）。
- 回归：smoke exit 0；fixture 12/12；delivery eval 12/12 且两次哈希一致。
- 真实模型：opencode / `deepseek-v4.1-flash` 单次受控调用 **success**，34.56s，10,354 tokens；标注为连通性验证，非质量评测。
- TUI 本轮因沙箱 `Start-Process` 重定向不可用未回放；上轮同环境已实测。

### 实验审计
新增 `reports/experiment_audit_20261024.md`：
- Phase6 baseline seed42：72/72 真实 Judge 成功、0 回退；C0 20/24、C1 19/24、C2 24/24；单 seed 不能证明架构收益；C1 ECE 报告 0.339 vs committed scorer 0.3758（分箱边界 bug）；报告"84/84"实为 72 calls。
- SC：seed42 13/24 可评（11 connection_error）、seed43 24/24；ECE/corr 依赖 trace 中 agreement，committed raw 不能复算。
- Phase 4.2-R/R3 报告中的 "accuracy" 是 factor coverage（`generate_stability_report.py:66-75`），不是诊断准确率；191/216 为规则回退。
- 给出"能证明/不能证明"与最小补充验证方案（同条件多 seed + 配对检验 + 字段落库）。

## 变更文件清单

新增：
- `reports/acceptance_20261024.md`（端到端验收记录）
- `reports/experiment_audit_20261024.md`（C0/C1/C2 实验与口径审计）
- `reports/delivery_verdict_20261024.md`（最终交付判定）
- `docs/PORTFOLIO.md`（架构图/业务流程图/请求输出/结果表/故障记录/演示流程）
- `docs/RESUME_ACIS.md`（中文简历项目描述与面试口径）
- `context/archive/20261024-acceptance-portfolio.md`（本归档）

修改：
- `README.md`：新增"项目解决的问题/系统能力与适用范围/架构与关键数据流/技术栈/演示案例/验收与材料"；移除空的历史状态标题；标注历史实验口径；补 opencode 映射说明。
- `.env.example`：补 opencode → `AGRI_AI_JUDGE_*` 映射注释。

未触碰：`decision_semantics.py`、`evals/metrics.py`、`challenge_report.py`、`tests/test_challenge_evaluation.py`、`tests/test_metrics.py`、`tests/fixtures/`、`reports/phase6_ablation_20261024/`（用户未提交修改，保持原状）。

## 验证结果

- `git diff --cached --check` 通过（提交前）。
- 所有数字来自本轮实测或已提交原始结果；未调用付费模型以外的外部服务；未把模拟输出当真实服务。
- 沙箱限制与未验证项在验收报告/判定文档中逐条标注。

## 分支与提交

- Branch：`work/20261024-acceptance-portfolio`（基于 `work/20261024-mvp-delivery` @ `3b5cc99`）
- 材料提交：见该分支提交 `docs(portfolio): acceptance, experiment audit and resume materials`
- 本归档提交：该分支后续提交

## 遗留 / 待用户决定

- 用户 5 个未提交修改 + `tests/fixtures/` 仍未冻结；fresh clone 一致性需授权后处理。
- 普通 Windows 环境未跑全量测试；Docker/TUI 现场彩排未做。
- 最终判定：MVP 达到简历展示门槛（有条件），建议冻结功能、进入作品集阶段；不启动新 Phase。
