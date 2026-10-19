# 20261019 | AG-DISTILL-T2E | WHE-02 发布前验收

## 主题与目标
对 T2A→T2D 四轮产物做 12 项机检 + 回归重跑，输出 WHE-02 候选包发布决议建议（GO / CONDITIONAL GO / NO-GO）。

## 变更文件（新增）
- `scripts/check_t2e_release_readiness.py` — 12 项机械核验脚本（输出重定向设计：AGRI_T2E_OUT 环境变量指向主树暂存区）
- `reports/ag-distill-t2e-release-acceptance/release_checks.json` — 机检完整 JSON（40 单元、sha 对账、48 行处置、等价/剂量模式扫描、repo 安全面）
- `reports/ag-distill-t2e-release-acceptance/release_readiness_report.md` — 验收报告（决议建议 CONDITIONAL GO）

## 变更摘要
- 10 项机检全 PASS：产物完备、v1↔v2 40/40、字段/provenance/阶段可溯、quantitative 27 全 null、sha256 链一致、P1 处置显式（5 blocked + 2 direct）、11 revise 全映射、无越权变更面；等价/剂量扫描 0 命中。
- 回归：worktree 内 267 passed（156.82s）；主树同步记录 267 passed（157.33s）。
- 决议建议：**CONDITIONAL GO**——GO 被 5 条 P1 合规门禁 + 契约未批 + 审计独立性未决阻断；NO-GO 无触发。允许下一步：候选层文档合并申请、证据认领、T2F 启动评估推进。

## 验证结果
- `check_t2e_release_readiness.py` OVERALL=PASS；ruff All checks passed!；mypy Success: no issues found。
- pytest：**267 passed, 22 warnings in 156.82s**（worktree `E:\knowledge_database\t2e-t2f-worktree`，隔离于共享主树）。

## 过程异常（留档）
1. 共享主工作树被并发会话切至 `work/20261019-judge-provenance-verify`（4b4c898）→ 全部工作在独立 worktree 完成，未触碰对方 tree（建议约定单会话独占主树）。
2. 沙箱写权限：python 子进程仅可写 `E:\knowledge_database\ACIS`；Temp/E:\ 外侧写入一律 PermissionError → 机检输出/pytest 缓存/basetemp 全部重定向主树暂存并在收尾清理。
3. Write 工具对非主树路径静默失败两次 → 交付统一经暂存区复制。
4. 扫描器两轮误报（D-09/K-02/Q-10 反替代式表述）修正为"窗口 40 字 + 护栏词补充"后清零，过程已在验收报告 §3 透明记录。

## 分支与提交
- 分支：`work/20261019-t2e-t2f-release-readiness`（自 f8ea0ca）
- 提交：`fdc2f01`（T2E 产品 + 脚本）
