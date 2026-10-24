# 2026-10-24 工作模式切换：只读盘点与简历交付路径

## 对话主题与目标

用户要求 ACIS 从"架构研发"切换为"简历交付"：在最大化复用现有资产的前提下，形成一个可运行、可演示、可复现、可写进简历的农业 AI 工程项目。本轮只做**只读盘点 + 最小交付路径**，不重构、不启动新 Phase、不执行不可逆 Git 操作。

## 盘点方法

- 继承上一轮交付审计（`reports/delivery_audit_20261024/`，2 PASS / 4 PARTIAL）的实测证据；
- 本轮复查：git 状态/分支、目录与代码量、入口与模块引用、知识库覆盖、测试与数据资产、本地数据体积、历史分支；
- 未修改任何产品代码；未安装依赖；未 push/merge/删除。

## 关键盘点结论

- 系统已有可交付闭环：自然语言 → 诊断/置信度/风险/行动建议 → 证据链 → SQLite 落库；CLI/TUI/FastAPI 三入口实测可用；无需重写。
- 建议 MVP 场景：**温室番茄病害诊断与处置建议**（辅以"灌溉 vs 病害冲突"演示 Critic）；4 作物/7 病害知识库中番茄覆盖最好。
- 真阻塞在"可复现工程外壳"：README 过期、依赖未锁定、无 `.env.example`、`pytest -q` 脆弱、Trace 无出口、5 处静默失败、工作树有未提交 WIP、关键证据（agreement/traces/分析脚本）未入库。
- 组件五级分类完成：保留（核心链/TUI/API/evals/知识库/可靠性工具）、暂缓（LLM 真实路径/Web UI/MCP Server/Qdrant/Docker）、部分实现（opencode 配置/AgriKG/视觉/校准）、仅设计（World Model/RFC-011~014/Phase 5/6）、应清理（codex/根目录旧 phase4 快照/phase0_check/本地缓存/历史分支，需授权）。
- 建议停止扩张：Phase 5/6、新 Agent/记忆/校准、RFC/ADR 治理、AG-DISTILL 支线、真实 AgriKG/Qdrant/视觉升级、Web 前端扩展。

## 变更文件清单

新增：
- `docs/RESUME_DELIVERY_PLAN.md`（本轮主交付物：盘点、组件五级分类、保留/必修/暂缓/停止清单、M0–M4 最小交付路径、MVP 验收条件、简历口径、决策点、下一步）
- `context/archive/20261024-resume-delivery-plan.md`（本归档）

修改/删除：无。

## 变更摘要

- 给出 2.5–3.5 个工作日的最小交付路径：M0 冻结基线（0.5d）→ M1 核心缺陷修复（1d）→ M2 一键可复现评测（0.5d）→ M3 演示与简历材料（0.5–1d）→ M4 可选环境加固（0.5d）。
- 列出 7 个 P0（冻结 WIP、README 快速开始、依赖锁、pytest.ini、Trace 出口、静默失败、可复现评测）与 5 个 P1。
- 定义 11 条可执行 MVP 验收条件（命令 + 通过标准）与简历"可写/不可写"口径。
- 列出 7 个需用户确认的决策点（WIP 处理、AG-DISTILL 范围、MVP 场景、清理授权、Docker、真实 LLM 演示、分支合并）。

## 验证结果

- 本轮为文档/方案轮，无产品代码改动；`git diff --cached --check` 通过（提交 `166da76` 前）。
- 方案中的事实数字均来自上一轮实测证据或本轮只读复查（代码量 125 py / 25,486 行；23 测试文件；data 264MB/logs 76MB/results 57MB；17 条历史 work/* 分支等）。
- 未执行：代码修改、测试重跑、安装、push、merge、删除。

## 分支与提交

- Branch：`work/20261024-resume-delivery-plan`（基于上一轮审计分支 `d4197f3`；因审计分支尚未合并，为保证审计报告与证据在树内，未直接基于 `main` `6420e34`）
- 方案提交：`166da76`（docs(plan): read-only inventory and minimal resume-delivery path）
- 本归档提交：该分支后续提交（docs(archive): 20261024 resume delivery plan round）

## 未完成 / 等待用户决定

- 4 类 PARTIAL 交付项的 P0 整改均未实施（本轮只出方案）。
- 工作树中并行会话未提交改动（5 个被跟踪文件 + `tests/fixtures/` + `reports/phase6_ablation_20261024/`）仍在；本方案建议纳入冻结基线，待用户确认。
- 清理类操作（codex/旧快照/缓存/历史分支）与合并/推送均未执行，等待授权。
