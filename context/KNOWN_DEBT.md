# Known Technical Debt

> 仅登记当前项目仍存在、且会影响复现/结论可信度的问题；历史 Sprint 细节已移出公开树。
> 更新：2026-10-24。

## 测试与环境

- **全量测试未在普通环境验证**：当前只在受限沙箱执行；ACL shim 下为 340 passed / 3 failed，
  3 个失败均为沙箱禁止子进程管道（`tests/test_experiments.py` 调 git），不是业务断言失败。
  普通 Windows/Linux 环境需复跑后才能声明“全绿”。
- **依赖锁的平台局限**：`requirements-lock.txt` 由 Windows + Python 3.13.3 的 `pip freeze` 生成，
  含平台相关包；其他平台应使用 `requirements.txt` 重新解析。
- **Docker 未验证**：`Dockerfile` / `docker-compose.yml` 存在，但本环境没有 Docker，未构建验证；
  镜像的依赖裁剪、启动参数、Neo4j 导入行为均未实测。

## 评测与指标

- **历史 accuracy 口径混用**：Phase 4.1/4.2-R/R3 部分报告中的 `accuracy` 是 factor coverage；
  `scripts/generate_stability_report.py` 仍用历史字段名，易被误读为诊断准确率。对应报告已归档/加注，
  但脚本字段名尚未重命名。
- **C1 ECE 分箱边界**：`src/openmetaphysics/evaluation/challenge_scorer.py` 的
  `int(conf/bin_size)` 会把 conf=0.3 放进 [0.2,0.3)；报告值 0.339 与 committed scorer 0.3758
  的差异由此产生。修复会影响历史数字，需单独评估。
- **自一致性指标依赖 trace**：SC 的 ECE/corr 使用 trace 中的 `agreement`，该字段不在 raw 结果中；
  仅本地 trace 可复算，公开仓库无法只凭 raw 复现。
- **Phase 6 覆盖不足**：C1 只有两个 seed，seed42 仅 13/24 可评；agreement=0.0 分层 n=3；
  C0/C2 对照未在同等条件下完成，不能据此得出架构结论。
- **架构收益未证明**：C1 未优于 C0；R3 排名跨 seed 翻转；任何“完整架构更好”的表述都缺证据。

## 可靠性 / 诊断

- **LLM Judge 端点与重试策略**：历史 Phase 4.2-R 出现 191/216 次连接失败回退；端点/模型/重试
  配置需要统一并重新验证，否则真实 Judge 结果不可用。
- **Harness vs 真实 Agent 一致性**：历史预检出现过标签/置信度偏移（C2 ABSTAIN vs 叶霉病等）；
  评测器与真实链路口径尚未完全对齐。
- **静默失败路径**：持久化失败、LangGraph 回退、自一致性采样失败已加日志，但仍可能有未覆盖异常；
  故障注入只验证了部分路径。
- **视觉/传感器为模拟或 mock**：真实视觉模型效果未验证；传感器与天气不是真实数据，
  不能用于生产或田间结论。

## 代码风格 / 类型

- `judge_agent.py` 既有 ruff 告警（I001、BLE001、S110）与部分模块的 mypy 历史错误；
  属既有问题，未在 MVP 中扩大修复范围。
- `planner.py` mypy overload 警告、`orchestrator.py` E402（dotenv 加载顺序）仍为已知低优先级问题。
- 能力标注（52/64）与 capability scoring 的严格性仍是研究口径问题；若继续做评测需先冻结定义。
