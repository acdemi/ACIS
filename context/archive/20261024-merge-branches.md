# 2026-10-24 合并待合并分支（用户明确指示）

## 对话主题与目标

用户指示「按规则合并分支」。按 `AGENTS.md` 约定 3（合并由用户决定），本次用户已明确授权执行合并：

- 把已完成并各自归档的工作分支并入 `main`；
- 不推送、不删除分支（约定 3 仍由用户决定，等待指示）；
- 不触碰工作树中并行会话的未提交改动。

## 合并对象与结果

| 分支 | 分支 tip | 提交数 | 内容 | main 上的合并提交 |
|---|---|---|---:|---|
| `work/20261019-t2e-t2f-release-readiness` | `2a75d26` | 12 | AG-DISTILL T1–T2F；其 tip 已包含其余 AG-DISTILL 中间分支（domain-scan / t2a / t2b / t2c-t2d） | `b9c6ae2` |
| `work/20261019-judge-provenance-verify` | `e09244f` | 1 | 六份预检报告迁回 + provenance addendum + closeout 归档 | `26b2133` |
| `work/20261023-phase6-arch-redesign` | `18abe26` | 7 | Phase 6 决策置信度链路（ADR-005，自一致性采样） | `81d63ed` |

- 合并前 `main`：`292152e`；合并后 `main`：`81d63ed`（ahead origin/main 23 commits）。
- 按轮次时间顺序合并，三个合并提交均保留双父（等价 `--no-ff`），各轮分支 tip 完整保留。
- 合并完成后，`work/*` 全部 7 个待合并分支尖均已成为 `main` 祖先（`git branch --merged main` 可查）。

## 变更文件清单

`git diff --shortstat 292152e 81d63ed`：**89 files changed, 24394 insertions(+), 9 deletions(-)**，无整文件删除。

- 新增（按目录）：
  - `context/archive/`：AG-DISTILL T1/T2A/T2B/T2C/T2D/T2E/T2F 七份轮次归档 + `20261019-phase4-judge-provenance-closeout.md`；
  - `docs/knowledge/20261019-ag-distill-t1-domain-map.md`；
  - `reports/ag-distill-t2a-wheat-fhb-20261019/`（含 S1–S7 stage_logs）、`reports/ag-distill-t2b-wheat-fhb-audit/`、`reports/ag-distill-t2c-wheat-fhb-revision/`、`reports/ag-distill-t2d-schema-survey-20261019/`、`reports/ag-distill-t2e-release-acceptance`、`reports/ag-distill-t2f-topic-readiness`；
  - `reports/phase4_judge_recovery_20261019/`：六份 `precheck_*.md` + `provenance_addendum.md`；
  - `reports/phase6_baseline_20261023/`、`reports/phase6_redesign_20261023/`、`reports/phase6_sc_20261023/`、`reports/phase6_sc43_20261024/`；
  - `scripts/apply_t2c_revisions.py`、`scripts/assemble_ag_distill_t2a_wheat_fhb.py`、`scripts/check_t2e_release_readiness.py`、`scripts/emit_t2b_audit.py`、`scripts/extract_ag_distill_t2a_wheat_fhb.py`、`scripts/fit_decision_calibration.py`；
  - `utils/decision_calibration_data.json`、`tests/test_decision_confidence.py`。
- 修改：`context/CHANGELOG.md`、`context/CURRENT_SPRINT.md`、`context/KNOWN_DEBT.md`、`docs/ARCHITECTURE_DECISIONS.md`、`agents/judge_agent.py`、`utils/confidence_calibration.py`、`utils/judge_runtime.py`、`tests/test_judge_runtime.py`、`scripts/run_challenge_evaluation.py`、`scripts/run_phase4_2.py`、`scripts/run_phase4_2_real_agent.py`、`scripts/generate_stability_report.py`。

## 合并方式（环境限制与替代做法）

本会话沙箱禁止子进程管道，`git merge` 会固定触发内部 stash 子进程并失败（`fatal: could not run stash`，在空白探针仓库同样复现，与工作树是否干净无关）。因此改用 plumbing 等价实现，语义与 `git merge --no-ff` 相同：

1. `git merge-tree --write-tree <parent> <branch>`：三方合并生成树（三次均零冲突）；
2. `git commit-tree <tree> -p <parent> -p <branch> -m ...`：生成双父合并提交；
3. `git reset --merge <commit>`：把 `main` 推进到合并提交，并保留工作树未提交改动。

## 验证结果

在隔离 worktree（`.claude/merge_wt`，干净检出）中对照运行全量测试：

| 状态 | 结果 |
|---|---|
| 合并前 `292152e` | **262 passed, 1 failed, 44 errors**（10.6s） |
| 合并后 `81d63ed` | **272 passed, 1 failed, 44 errors**（13.1s） |

- 通过数 +10，恰好等于 `tests/test_decision_confidence.py` 新增的 10 项测试；failed / errors 集合完全一致。
- 1 failed + 44 errors 均为沙箱环境问题，合并前即存在，非本次合并引入：
  - pytest 临时目录 ACL（`PermissionError: [WinError 5]`，`%TEMP%\dsh-*\pytest-of-lkl` 不可读），44 个 `tmp_path` 类用例报错；
  - 沙箱禁止子进程管道，`test_build_manifest_has_reproducibility_fields` 内 `subprocess.run(git ...)` 报 `WinError 5`。
- 内容一致性核验：
  - Phase 6 分支触及的全部路径，`git diff 81d63ed 18abe26` 为空；
  - 另两支自 merge-base 起新增/修改的文件，合并后 `main` 的 blob 与分支完全一致；
  - `git merge-tree` 三次均为零冲突，未产生冲突标记。
- `ruff 0.16.2`（对 Phase 6 触及文件）：8 项，均属该轮既有代码，非合并引入。其中 `utils/confidence_calibration.py:80` 在 `@staticmethod` 内使用 `self._platt_fit`（F821），仅当 isotonic 初始化失败时才触发，是真实潜在缺陷，建议后续单独修复；其余为 import 排序、未用 import、盲捕获等既有问题。
- 未执行真实 LLM 调用；未 push。

## 未完成 / 遗留（等待用户决定）

- **push `origin/main`**：本会话未执行（约定 1/3：推送由用户把控）。但 2026-10-24 13:07:42，`origin/main` 被本会话之外的并发进程以 `update by push` 推进到 `81d63ed`（详见文末「事后补记」）；此后新增的本归档提交仍仅在本地（`main` 领先 `origin/main` 1 个提交）。
- **删除已合并分支**：未执行；7 个 `work/*` 分支尖均已并入 `main`，可按需删除。
- **Phase 6 轮次归档缺口**：`work/20261023-phase6-arch-redesign` 未按约定 2 写入 `context/archive/20261023-*.md`（仅有 CHANGELOG / ADR / KNOWN_DEBT 记录），本轮未替其补写，建议后续补记。
- **并行会话未提交改动**：工作树保留 `decision_semantics.py`、`evals/metrics.py`、`src/openmetaphysics/evaluation/challenge_report.py`、`tests/test_challenge_evaluation.py`、`tests/test_metrics.py`、`tests/fixtures/`。合并前后已用 sha256 逐一比对，内容完全一致，本轮未纳入、未改写、未回退。
- **`codex/acis-implementation-plan`**：2026-07 旧分支（含 `tui.py` 等无关提交），不在本次合并范围。

## 回滚方式

- 合并前 `main` = `292152e`；需要回退时：`git reset --hard 292152e`（会丢弃工作树未提交改动，先备份）。
- 中间态亦可按合并提交逐层回退：`81d63ed` → `26b2133` → `b9c6ae2` → `292152e`。

## 分支与提交

- Branch: `work/20261024-merge-branches`（仅承载本归档提交，基于 `81d63ed`）
- `main` 合并提交：`b9c6ae2`（AG-DISTILL T1–T2F）、`26b2133`（judge provenance）、`81d63ed`（Phase 6）
- 本归档提交：即该分支 tip

## 事后补记（2026-10-24 13:07 外部推送）

本会话全程未执行 `git push` / `git fetch`（沙箱禁止子进程管道，`ls-remote` 亦失败），但收尾核查发现
`origin/main` 已被推进：

- `refs/remotes/origin/main` 的 reflog：`81d63ed ... update by push` @ `2026-10-24 13:07:42 +0800`
  （上一条为 `292152e ... update by push` @ `12:52:12`）；
- `.git/FETCH_HEAD` 修改时间 `13:07:18`，说明同期有一次 fetch；
- 本地 `main` 当时已是 `81d63ed`（本会话 13:03:57 合并落地），因此该推送把本会话的三个合并提交
  （无归档提交）发布到了 `origin/main`。

即：**合并已随外部推送到达 origin（`origin/main` = `81d63ed`）**，而本归档提交（`main` 当前 tip）
仍只在本地、领先 1 个提交。该推送来自本工作区共享 `.git` 的其他进程/会话（其具备网络与管道权限），
不是本会话所为，也未获用户对「推送」的明确指示——如需还原远端，只能由用户在远端执行回退
（例如把 `origin/main` 强制指回 `292152e`），本会话未对远端做任何写操作。
