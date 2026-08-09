# 20260810 — 建立 Agent 工作约定（AGENTS.md）

## 对话主题与目标
- 主题：为 ACIS 仓库建立 agent 强制工作约定
- 目标：每次对话的输出都在独立分支上进行；每轮结束进行输出文件归档；
  合并与下一步由用户把控

## 变更文件清单
- 新增：`AGENTS.md`（仓库根，opencode 自动加载的约定文件）

## 变更摘要
- 约定 1：每轮对话从 `main` 创建 `work/<日期>-<主题>` 分支，所有输出只在该分支
- 约定 2：每轮结束在 `context/archive/<YYYYMMDD>-<主题>.md` 写归档记录
  （主题 / 变更清单 / 摘要 / 验证结果 / 分支名与提交号），并随分支提交；
  中途打断也提交进度并注明"未完成"
- 约定 3：合并、删除分支、进入下一步一律由用户决定

## 验证结果
- 无代码变更，无需 pytest / ruff / mypy

## 分支名与提交号
- 分支：`work/20260810-agent-conventions`
- 提交：`3cd33ca`（AGENTS.md）
- 归档：`context/archive/20260810-agent-conventions.md`

## 备注
- 工作区另有与本轮无关的未跟踪文件（challenge set 评估相关：
  `benchmarks/challenge_set_v1.json`、`reports/`、`scripts/run_challenge_evaluation.py`
  等及 `tests/conftest.py` 的修改），未纳入本轮提交，等待用户处理
