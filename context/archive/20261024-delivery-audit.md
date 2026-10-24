# 2026-10-24 交付清单审计与检索（ACIS）

## 对话主题与目标

用户要求对 ACIS 仓库做审计与检索，并填写 6 项交付清单：

1. 核心流程可运行；2. 环境可复现；3. 故障可解释；4. 效果可验证；5. 技术取舍可解释；6. 演示可完成。

目标不是"勾满 6 项"，而是逐项给出可复核证据、判定（PASS/PARTIAL/FAIL）与整改项，并补齐演示脚本。

## 审计方法

- 3 条独立证据线并行（Agent Team）：
  - `flow-runner`：核心流程/演示实测（pytest、smoke/fixture、CLI 双路径、Trace 阶段、故障注入、FastAPI TestClient、TUI 非交互回放、计时）；
  - `eval-auditor`：固定测试集/标签清点、报告指标复算、脚本入库性、case↔trace 互查、离线 runner 实测；
  - `env-auditor`：README/Docker/依赖/凭证一致性、`git archive` 干净副本实测、8 类 Judge 故障矩阵、静默失败路径审计。
- Lead：取舍证据汇总、交叉复核（独立复算 baseline/SC/ablation 指标、运行 trace 一行命令）、报告与 runbook 撰写。
- 约束：未调用真实 LLM/外网；Docker 仅静态核验；未触碰工作树中并行会话的未提交改动。

## 判定结果

| 交付项 | 判定 |
|---|---|
| 核心流程可运行 | **PASS** |
| 环境可复现 | **PARTIAL** |
| 故障可解释 | **PARTIAL** |
| 效果可验证 | **PARTIAL** |
| 技术取舍可解释 | **PARTIAL** |
| 演示可完成 | **PASS**（补齐 runbook 后） |

关键证据与缺口见 `reports/delivery_audit_20261024/DELIVERY_CHECKLIST.md` §二/§三/§四。

## 变更文件清单

新增：
- `reports/delivery_audit_20261024/DELIVERY_CHECKLIST.md`（主交付物：清单填写 + 逐项审计 + 整改清单 + 证据索引）
- `reports/delivery_audit_20261024/evidence/`（18 个文件：flow/eval/env 三线证据副本与原始 JSON）
- `docs/DEMO_RUNBOOK.md`（3–5 分钟演示脚本：正常任务/证据追溯/异常处理 + 兜底预案 + 口径）
- `context/archive/20261024-delivery-audit.md`（本归档）

修改/删除：无（并行会话的 5 个未提交修改与未跟踪目录按约定未触碰）。

本机未入库证据（gitignored，复跑生成）：`logs/delivery_audit_20261024/{flow,eval,env}/`。

## 关键发现摘要

- 核心链路径实测：规则 8.55s / LangGraph 9.06s 冷启动，10/10 Trace 阶段，SQLite `decision_id` 落库；预热后 1.4–1.7s。
- pytest：规范命令受沙箱 ACL/子进程管道影响（1 failed / 286 passed / 44 errors）；隔离环境噪声后 3 failed / 328 passed，**代码级失败 0**（331 用例 / 23 文件）。
- 故障链：8 类 Judge 故障均有 reason_code + trace 字段 + 日志 + 脱敏；但 `_persist`、LangGraph 回退、自一致性采样失败等 5 条中危静默路径仍在。
- 效果复算：baseline 23/24 指标可精确复算；SC 两跑的 ECE/corr 依赖 gitignored trace 中的 `agreement`，committed raw 不能复算；`challenge_scorer.py:154` 存在浮点分箱 bug。
- 环境：干净副本可离线跑通（规则/LangGraph），但依赖无锁、无 `.env.example`、Judge/opencode 凭证未文档化、Docker Python 3.11 vs 本地 3.13、README 过期。
- 文档数字错误：pytest 267→331、TUI 5→6 场景、`<1s`→1.4–2.7s、84/84→72 Judge 调用、挑战集难度 9/13、49 GT→64/64。
- 技术取舍：设计动机（`MODEL_AGENT_ORCHESTRATION.md`）、ADR-005 被否证方案、消融/运行/Token 成本均有材料，但架构级收益未被证明（C1 ≤ C0；记忆注入在 Challenge Set 上有害）。

## 验证结果

- `git diff --check`：通过（见提交记录）。
- 交付物自查：`DELIVERY_CHECKLIST.md` 中所有数值均来自本机实测或本目录 `evidence/`；`DEMO_RUNBOOK.md` 的 trace 一行命令已实测通过（输出 10 阶段 + judge_runtime）。
- 证据副本密钥扫描：仅命中已知公开 dev 密码（README 已公开）与明确标注的 fake key（`sk-audit-fake-key-must-not-leak-...`，用于验证脱敏），无真实凭证泄漏。
- 未执行：真实 LLM 复跑、Docker 构建、全量人工语义复核。

## 分支与提交

- Branch：`work/20261024-delivery-audit`（基于 `main` `6420e34`，未 push、未 merge）
- 审计交付提交：`750886c`（20 files changed, 3942 insertions）
- 本归档提交：见该分支后续提交（`docs(archive): 20261024 delivery audit`）

## 遗留 / 待用户决定

- 4 个 PARTIAL 项的 P0 整改（README/依赖锁定/Phase 6 证据闭环/静默失败）未实施——本次任务为审计与检索，不改产品代码。
- 工作树中并行会话的未提交改动仍在（5 个被跟踪文件 + `reports/phase6_ablation_20261024/` + `tests/fixtures/`），未纳入本分支。
- 合并/推送/删除分支由用户决定（AGENTS.md 约定 3）。
