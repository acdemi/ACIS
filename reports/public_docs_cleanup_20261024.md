# ACIS 公开仓库文档清理报告（2026-10-24）

> 执行依据：`context/archive/20261024-public-docs-audit-plan.md` 与
> `reports/document_cleanup_manifest.csv`（二者已复制到仓库外本地归档）。
> 本轮不提交、不 push、不 merge；不处理用户 WIP。所有改动留在工作区，等待人工检查 diff。

## 1. 结果摘要

| 指标 | 清理前 | 清理后（计划公开树） |
|---|---:|---:|
| Git 索引文件数 | 373 | 373（未提交，索引未变） |
| 工作区实际存在的跟踪文件 | 373 | **180** |
| 新增公开归档/索引文件 | 0 | **44**（41 个移动归档 + 2 个 README + 本报告） |
| 计划公开文件数 | 373 | **224** |
| 公开文件体积 | **4.44 MB** | **约 1.80 MB**（1,803,339 B，含本报告） |
| 删除（无独立价值） | 0 | **28** |
| 移出公开仓库（本地归档） | 0 | **124** |
| 仓库内公开归档（移动） | 0 | **41** |

- `reports/` 从 113 个文件降到约 32 个（不含归档子目录的重复）；根目录从 34 个降到 19 个；
  `context/` 从 34 个降到 2 个（仅保留证据台账与技术债）。
- 公开入口 `README.md` 重写为约 150–200 行；TUI、RFC-001、演示脚本、证据台账、技术债与两份报告同步修正。
- 非技术个人展示材料、内部交付审计、AI 会话归档、AG-DISTILL 支线与原始模型输出均移出公开仓库，
  在仓库外保留了带 SHA-256 的副本。

## 2. 修改文件（13 个，另 5 个用户 WIP 未动）

| 文件 | 变更摘要 |
|---|---|
| `README.md` | 重写为公开入口：问题、真实/模拟/mock/可选/未实现边界、架构、快速开始、测试与证据、限制、文档导航；移除个人展示链接 |
| `ui/tui.py` | 仅改显示文案（去掉非中性演示措辞）；无逻辑变更 |
| `docs/rfc/RFC001-System Architecture.md` | 增加 Implementation Status：说明当前是文本 MVP 子集；修正 ROADMAP/审计引用 |
| `docs/DEMO_RUNBOOK.md` | 去掉“答辩/交付清单”措辞；修正置信度区间、路径与依赖说明 |
| `context/EVIDENCE_LEDGER.md` | 保留 E007–E020；标注历史 accuracy=factor coverage、Phase 6 单 seed 边界；更新数据来源 |
| `context/KNOWN_DEBT.md` | 重写为当前仍有效的测试/指标/可靠性/风格债务；移除旧计数与提交号 |
| `reports/acceptance_20261024.md` | 去个人展示措辞；修正测试环境表述；“预期通过”改为“未复跑” |
| `reports/experiment_audit_20261024.md` | 去掉个人展示措辞；不引用未提交 WIP 数据；更新归档报告路径 |
| `reports/phase4_judge_recovery_20261019/judge_recovery_report.md` | 更新 blocked precheck 的归档路径 |
| `reports/phase4_judge_recovery_20261019/provenance_addendum.md` | 同上 |
| `MODEL_AGENT_ORCHESTRATION.md` | 增加状态说明；视觉行改为“默认 mock/可选模型（未验证）” |
| `requirements-lock.txt` | 明确 Windows 11 x64 / Python 3.13.3 / `.venv` 生成，不是跨平台锁 |
| `.gitignore` | 增加 `pytest-of-lkl/`、`torchinductor_lkl/`、本地归档目录、根级 `trace_*.json` |

没有修改业务逻辑、模型逻辑、评测算法或测试实现。

## 3. 仓库外备份

| 项 | 内容 |
|---|---|
| 位置 | `%REPO_PARENT%\acis-local-archive\20261024`（仓库外；绝对路径仅记录在本地元数据） |
| 条目 | **126** 个文件（124 个 ARCHIVE_LOCAL + 审计计划 + 原 manifest） |
| 字节 | **2,962,066 B**（约 2.83 MB） |
| 校验 | 逐文件复制后比较源/目标 SHA-256 与字节数；**失败 0** |
| 元数据 | `_archive_metadata.json`（每个条目的源路径、目标路径、字节、SHA-256、ok） |
| 关键哈希 | 126 个条目的 SHA-256 全部记录在本地 `_archive_metadata.json`；本报告不复制个人材料名称或绝对路径 |

归档顺序：先复制 → 比较数量/字节/SHA-256 → 确认可读 → 才删除工作树源文件。
无文件因“无法复制”而被删除；所有 124 个 ARCHIVE_LOCAL 均已确认离开公开跟踪树。

## 4. 本地归档（124 个，仓库外）

| 类别 | 数量 | 说明 |
|---|---:|---|
| `reports/ag-distill-*` | 51 | 小麦知识蒸馏支线；候选知识/原始 prompt/response，未纳入主项目 |
| `reports/delivery_audit_20261024/` | 19 | 内部交付审计证据；含本机路径与测试假 key |
| `context/archive/*` | 21 | AI 编码会话轮次记录；含个人展示材料引用 |
| `reports/phase4_real_agent_consistency_20261017/` | 7 | 内部预检/单条 trace |
| Phase 4.2 原始 JSON | 4 | `phase4_2*raw_results.json`（约 1.5 MB） |
| `docs/rfc/archive/RFC-011..014` | 4 | 未实施的前瞻 RFC |
| `docs/audit/` + `docs/knowledge/` | 2 | AI 审计与 AG-DISTILL 领域图 |
| 个人展示材料 | 3 | 非技术用途，路径见本地归档 metadata；不在公开树中 |
| 其他 | 13 | `AGENTS.md`、历史审计、交付判定、AG-DISTILL/旧实验脚本 |

完整 124 条路径在 `_archive_metadata.json` 中；其中个人展示材料不在此报告中重复列出，避免公开文档再次出现非技术导向。

## 5. 公开归档（41 个，仓库内）

| 目标 | 数量 | 来源 |
|---|---:|---|
| `docs/archive/sprints/` | 10 | Trace/Eval/Benchmark/Ablation/Capability/Experiment Manager/Research Eval 报告 |
| `docs/archive/rfc/` | 9 | RFC-002 ~ RFC-010 |
| `docs/archive/`（单篇） | 6 | `vision.md`（原 ACIS.md）、`architecture-principles.md`、`roadmap.md`、`architecture-state.md`、`changelog.md`、`current-sprint.md` |
| `reports/archive/phase4/` | 7 | Phase 4.1 pilot、4.2 validation、R2/R3 稳定性、R3 压测、R4 预检、blocked precheck |
| `reports/archive/phase4_2/` | 3 | 真实 Agent 环境差异/预检/稳定性 |
| `reports/archive/phase4_judge_recovery/` | 6 | 六次 Judge 恢复预检 |
| 合计 | **41** | 公开历史，不是当前事实源 |

新增 `docs/archive/README.md` 与 `reports/README.md`，分别说明历史文档和当前证据/历史实验/复现方式。
`reports/archive` 中历史报告的 `accuracy` 继续标注为 factor coverage（见 `reports/README.md`）。

## 6. 删除（28 个）

```text
codex/IMPLEMENT.md  codex/PATCH.md  codex/REPORT.md  codex/REVIEW.md  codex/SYSTEM_PROMPT.md
context/README.md  context/ROADMAP.md
context/template/ACCEPTANCE.md  CONSTRAINTS.md  CURRENT_STATE.md  FILES.md  GOAL.md  NEXT.md
docs/architecture.md  docs/rfc/RFC-000-template.md
phase4_1_pilot_results.json
phase4_2_baseline_commit.txt  phase4_2_post_diff.txt  phase4_2_post_status.txt
phase4_2_pre_diff.txt  phase4_2_pre_status.txt
phase4_2_r2_full_status.txt  phase4_2_r2_status.txt
phase4_2_r3_full_status.txt  phase4_2_r3_status.txt
phase4_2_real_agent_post_status.txt  phase4_2_real_agent_status.txt
scripts/phase0_check.py
```

删除原则：空文件/空模板、已 Superseded 的重复架构入口、一次性运行状态快照、无引用旧检查脚本；
均有 git 历史或本地归档可追溯。

## 7. 公开入口与技术事实更新

- `README.md` 不再包含个人展示材料链接；公开入口按“农业智能决策支持与多阶段 AI 系统工程原型”表述。
- TUI 不再出现非中性演示措辞，改为“ACIS 演示”。
- 明确区分：真实实现（规则/LangGraph/记忆/专家/Judge/审计）、模拟数据（传感器/天气）、
  mock（视觉）、可选（LLM Judge/Critic、Planner）、未实现/未验证（Tool 执行、World Model、
  生产部署、真实田间、真实视觉质量）。
- 明确“343 个用例”是总数，不是通过数；列出 12 契约测试通过、受限沙箱 340/343、沙箱原样
  286/1/56 errors、普通环境未复跑。
- 历史 `accuracy` 口径统一：Phase 4.1/4.2-R/R3 报告中的 accuracy 是 factor coverage；
  README、`reports/README.md`、实验审计、RFC-001 状态说明均给出提示。
- `requirements-lock.txt` 明确平台限制；不再暗示跨平台锁定。
- RFC-001 增加 Implementation Status，说明规范与当前实现的差距；不删除负结果与限制。
- `MODEL_AGENT_ORCHESTRATION.md` 增加“设计说明/当前子集”状态，避免把设计表当成已实现能力。

## 8. 验收检查

| 检查 | 结果 | 说明 |
|---|---|---|
| `git diff --check` | **通过**（exit 0） | 工作区有 193 个删除、13 个文档修改、WIP 不变 |
| Markdown 相对链接 | **0 broken**（当前树） | 已处理移动后的路径 |
| 公开入口/技术文档个人展示措辞 | **0**（README/docs/reports/context 当前技术文档；清理报告本身为处置记录） | 历史归档原文不要求为零 |
| 真实密钥扫描 | **未发现真实密钥** | 测试假 key 已随内部审计移出公开树 |
| 本机绝对路径 | **0**（当前公开树） | 两处历史报告头已改为仓库相对路径 |
| `pytest -q tests/test_delivery_contract.py` | **12 passed**（10.45s） | 使用既有 ACL shim 与临时目录；仅此文件，不代表全量 |
| 清理前后数量/体积 | 见第 1 节 | 373 → 计划 224；4.44 MB → 约 1.80 MB |
| WIP 保护 | **5 个修改 + 7 个未跟踪文件全部保留** | SHA-256 与清理前一致 |

**WIP 哈希（清理后复核）**

```text
F480776C...C3A3  decision_semantics.py
E2D82B19...495   evals/metrics.py
E4D2A214...708   src/openmetaphysics/evaluation/challenge_report.py
87E0D750...1EA1F tests/test_challenge_evaluation.py
66D64A34...5B7   tests/test_metrics.py
```

未跟踪保护：`tests/fixtures/phase4_judge_recovery_20261019/*.json`（6 个）、
`reports/phase6_ablation_20261024/raw_results_c0c2_seed43.json`（1 个）。

## 9. 测试与环境限制

- 仅运行 `tests/test_delivery_contract.py`：**12 passed**；未运行全量测试。
- 受限沙箱中全量历史结果为 340 passed / 3 failed（3 个为禁止子进程管道），当时另有 56 个
  `tmp_path` ACL error；这些是环境限制，不是本次文档清理的结果，也没有在普通环境复跑。
- TUI 视觉/交互、Docker、真实 LLM 多次调用未在本次清理中验证。
- Markdown 链接检查覆盖当前所有 Markdown；历史归档中的纯文本路径引用不当作链接检查对象。

## 10. 未完成与待人工检查

1. **未提交**：按要求不 commit/push/merge；`git` 索引仍是旧树（373 条），工作区显示
   193 个删除 + 13 个文档修改 + 44 个新增；请用 `git status` / `git diff` 检查后再决定提交方式。
2. **manifest 的源文件仍被其他进程占用**：副本已在仓库外归档；工作树中的
   `reports/document_cleanup_manifest.csv` 无法删除（共享冲突）。已将它加入 `.gitignore`，
   防止误提交；本报告统计基于该清单。进程释放后可手动删除。
3. **全量测试未复跑**；仅交付契约测试通过。普通 Windows 环境仍需复跑全量。
4. **历史报告仍有旧数字/旧路径**（`docs/archive/`、`reports/archive/`）；已在新索引中标注
   历史口径，但未逐篇重写历史报告正文。
5. **个人展示材料**仅存在于仓库外本地归档，未删除；是否彻底删除由你决定。
6. **外部归档目录**不在 Git 中，也不会被 push；请自行确认磁盘备份策略。

## 11. 清理后目录概览

```text
docs/
  ARCHITECTURE_DECISIONS.md
  DEMO_RUNBOOK.md
  rfc/RFC001-System Architecture.md
  archive/{README.md, vision.md, roadmap.md, architecture-*.md, changelog.md,
           current-sprint.md, rfc/, sprints/}
reports/
  README.md
  acceptance_20261024.md
  experiment_audit_20261024.md
  delivery_eval/
  phase6_baseline_20261023/ phase6_sc_20261023/ phase6_sc43_20261024/
  phase6_redesign_20261023/ phase4_evaluation_*.md phase4_2_real_agent/diagnosis_judge_fallback.md
  phase4_judge_recovery_20261019/
  archive/{phase4/, phase4_2/, phase4_judge_recovery/}
context/
  EVIDENCE_LEDGER.md
  KNOWN_DEBT.md
```

代码目录、测试、benchmarks/evals/experiments 未重排；只清理了文档/报告与一次性工作材料。
