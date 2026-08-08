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
- **venv dev tools**: pytest（9.1.1）/ ruff（0.16.2）/ mypy（2.3.0）均已装入 `.venv`（2026-08-08）
- **src/ 空目录**: 已移除（2026-08-08，清理 commit 89fa630）
