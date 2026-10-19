# Known Technical Debt

- **planner.py**: mypy overload warning (accepted, low priority)
- **orchestrator.py**: E402 due to dotenv loading order (accepted)
- **agents/**, **rag/**, **rule_engine/**, **debate/**, **storage/**, **utils/**: pre-existing mypy errors (Sprint 01 legacy, frozen)
- **Capability annotation（Sprint 04.5B）**: 52/64 案例已标注
  （enriched 18 + 能力套件 18 + 难度分层 16）；剩余 12 个难度案例为纯特征匹配，
  按设计不标注（宁可少标，不可乱标）。待 Chief Maintainer 审查后形成冻结元数据。
  Priority: High（Benchmark Scientific Validity）。
- **Capability scoring strictness（Sprint 04.5C）**:
  - `conflict_resolution` 严格依赖 critic `triggered`：3 个环境矛盾案例
    （ce_sugar_beet_root_rot_dry / ce_cotton_wilt_hot / sc_cotton_wilt_anomaly）分数为 0，
    需架构师决定改标注还是改管线
  - `information_gathering` 依赖 planner/judge 文本关键词启发式，提示词变更后需重新校准
  - `sensor_cross_validation` 要求真实传感器异常或 `sensor_verify` 工具请求，
    仅存在传感器数据不得分
- **Judge endpoint / connectivity（Phase 4.2-R2）**: 真实 Agent 运行中 191/216 次 judge 回退 rules
  （`APIConnectionError: Connection error.`）；可重建配置为 `api.deepseek.com` + `deepseek-chat`，
  而审计声明使用 opencode 免费网关 `opencode.ai/zen/go/v1` + `deepseek-v4-flash`。
  2026-08-13 探针：免费网关可用，付费端点返回 402 Insufficient Balance。
  需统一端点配置与重试策略后重跑，否则真实 Agent 结果不可用。Priority: High。
- **Harness vs 真实 Agent 一致性（Phase 4.2-R4）**: 预检 FAIL（C0 置信度偏移 0.320、
  C2 0.750 > 0.3；C2 标签 ABSTAIN vs 叶霉病）。评测器口径与真实链路需对齐后才能出具架构结论。
  Priority: High。
- **核心结论未决（Phase 4.1 ~ 4.2-R3）**: C1（完整 ACIS）在 Challenge Set 上未优于 C0（裸基线），
  ECE 亦未改善；R3 排名跨 seed 翻转、方差大（24 案例 × 3 seed）。
  需架构决策：Phase 5（扩展评测补足证据）或 Phase 6（架构重设计）。Priority: High。
- **Phase 4.2-R 产物（已提交，2026-09-20 核实）**: 仓库根 `phase4_2_*.txt`、`reports/phase4_2_r*.json|md`、
  `scripts/stress_test_judge.py`，以及 `agents/judge_agent.py` 的诊断日志改动均已在 `2851bb9` / `102e623` / `3bc4bd4` 提交，并随 `a928061` 推送。
- **judge_agent.py ruff（既有）**: `ruff check` 报 I001（imports 排序）+ 4×BLE001 + S110（宽泛 `except`），
  与 Phase 4.2-R 诊断改动前版本一致（未引入新问题）；属冻结 Judge 模块既有风格问题，待架构评审后统一处理。
- **venv dev tools**: pytest（9.1.1）/ ruff（0.16.2）/ mypy（2.3.0）均已装入 `.venv`（2026-08-08）；pytest 当前 267 passed（2026-09-20）
- **src/ 空目录**: 已移除（2026-08-08，清理 commit 89fa630）
- **真实 Judge 凭证（2026-10-18）**: `DEEPSEEK_API_KEY` 无效（HTTP 401 `authentication_error`），
  `AGRI_AI_JUDGE_API_KEY` 不存在；真实 Judge 恢复 BLOCKED。最小人工操作：经正常 `.env` 渠道更新密钥
  （勿粘贴至聊天/报告），随后按 `reports/phase4_real_judge_recovery_20261018/blocked_precheck_report.md`
  从 Step 1 重检。Priority: High（Blocker）。
- **factor coverage 契约边界（2026-10-17）**: 现行契约只对最终用户可见决策解释评分，
  不计隐藏专家证据（内部 trace 的 symptom factor 不计入）；全 trace 覆盖率为未来独立指标。
  Priority: Low（设计决定，待架构师确认）。
