# ACIS 3–5 分钟演示脚本（交付/答辩用）

> 配套交付清单：`reports/delivery_audit_20261024/DELIVERY_CHECKLIST.md`
> 目标：用 4 分钟左右演示 **正常任务 → 证据追溯 → 异常处理** 三件事，全部离线可跑、不依赖外网与付费 API。
> 本脚本基于 2026-10-24 实测（`.venv` Python 3.13、TUI 12.2s 启动、每场景 1.4–1.7s）。

---

## 0. 演示前 5 分钟准备（不上台）

```powershell
cd E:\knowledge_database\ACIS
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='.'
$env:NO_PROXY='localhost,127.0.0.1'     # 必设：否则本机代理会把 localhost 打成 502，RAG 静默降级
$env:HF_HUB_OFFLINE='1'                # 避免视觉/时序模型联网下载
$py = 'E:\knowledge_database\ACIS\.venv\Scripts\python.exe'
```

检查三件事：

1. `.\.venv\Scripts\python.exe -V` → `Python 3.13.3`（仓库自带 venv，不要用系统 python）。
2. `& $py orchestrator.py --rules-only "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"` → 能出 `病理判断首选：番茄叶霉病`（冷启动约 8–9s）。
3. 开第二个终端预跑一遍演示命令，避免首次 import/模型预热占用演示时间。

**可选（有 Key 才用）**：`$env:DEEPSEEK_API_KEY='sk-...'`，并在 TUI 中按 `[j]` 开 LLM Judge；**无 Key 时不要承诺 LLM 演示**，直接讲规则版（本脚本默认）。

---

## 1. 演示时间轴（离线规则版，约 4 分 10 秒）

### 0:00–0:30 · 开场 + 启动
```powershell
& $py -m ui.tui
```
讲：
> "这是 ACIS 的 TUI 演示入口。主链是 感知 → 记忆 → 专家 → 辩论 → Critic → Judge，默认走离线规则裁决；右侧状态条显示 Neo4j / RAG / Judge 开关，没有外部服务时会自动降级。"

指给观众看：菜单 6 个场景、状态条 `Judge:关 Critic:关`、`KG后端`、`RAG`。

### 0:30–1:40 · 正常任务（场景 1）
输入 `1` 回车。

讲（跟着画面走）：
> "输入是真实中文咨询：番茄叶片黄斑、叶背灰色霉层。可以看到 12 条 Agent 轨迹逐条刷出：感知层三个 Agent → 记忆层 RAG/知识图谱/案例库 → 专家层病理/气象/栽培。"
> "最终裁决是番茄叶霉病，置信度 75–85%，风险 medium；下面是 6 条行动建议，右侧是辩论共识与缺失证据（缺少图像证据）。"

关注点：Agent 轨迹、置信度条、`★ 最终裁决`、行动建议。

### 1:40–2:30 · 冲突与反驳（场景 2）
返回菜单后输入 `2` 回车（高湿 + 灌溉 vs 病害冲突）。

讲：
> "第二个场景加入冲突：环境高湿、需要灌溉，但高湿又是病害风险。Debate 发现冲突，Critic 进入反驳轮次并对可疑专家降权——这展示了多 Agent 不是各说各话，而是有可审计的冲突处理。"

关注点：`Debate & Critic` 面板、`Critic 反驳`、降权记录（若触发）。

### 2:30–3:20 · 证据追溯（本演示的核心差异化）
**方式 A（推荐，继续用 TUI）**：停在场景 1 的 `KG 锚定裁决分析` 面板，讲：
> "每个结论都能回溯到证据：知识图谱后端、参照疾病、硬约束是否触发、传感器读数、裁决推理；这些字段同时写入 SQLite 的决策记录。"

**方式 B（更有说服力，开第二个终端）**：
```powershell
& $py -c "import json; from orchestrator import AgentOrchestrator; o=AgentOrchestrator(use_llm_judge=False); d=o.run('温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？'); t=o.last_trace; print('trace_id=',t.trace_id); print('stages=',t.stages_present); print('judge_runtime=',json.dumps(t.judge[0].payload['judge_analysis']['judge_runtime'],ensure_ascii=False))"
```
讲：
> "一条命令给出统一 Trace 的 trace_id、10 个阶段（request…metrics）和 Judge 运行元数据；同一条决策在 SQLite 里有 decision_id。这就是'可追溯'的落点。"

### 3:20–4:10 · 异常处理（故障注入，证明"故障可解释"）
在第二个终端执行（复制即可）：
```powershell
$env:AGRI_AI_JUDGE_API_KEY='sk-test'
$env:AGRI_AI_JUDGE_BASE_URL='http://127.0.0.1:9'
$env:AGRI_AI_JUDGE_TIMEOUT_SECONDS='10'
$env:AGRI_AI_JUDGE_MAX_RETRIES='0'
& $py orchestrator.py --rules-only --llm-judge --json "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"
```
讲，并指给观众看四样东西：
1. **进程正常退出、仍有裁决** → `judge_mode=rules`（自动回退，服务不中断）；
2. `judge_runtime.outcome=fallback`、`fallback_reason_code=connection_error`、`retry_exhausted=true`；
3. `debate.missing_evidence` 里有一句"LLM Judge 不可用，已回退规则裁决 [connection_error] …"；
4. stderr 三行日志：`Judge request:` → `Judge exception:` → `Judge fallback:`，且 **API key 已脱敏**（看不到 sk-）。
> "从 401/402/429/超时/连接失败/非 JSON 输出，到 5xx，都有稳定的 reason_code、trace 字段和日志；这是评测和排障能对上的原因。"

### 4:10–4:40 · 收尾（二选一）
- 规则/API：`& $py -c "from fastapi.testclient import TestClient; from gateway.app import app; c=TestClient(app); print(c.get('/health').status_code, c.post('/diagnose', json={'query':'番茄叶片黄斑，叶背灰色霉层'}).status_code)"` → `200 200`。
- 或指 SQLite：`decision_id` 已落库，说明有审计记录。

收尾话术：
> "总结：离线规则主链保证随时可跑；检索与 KG 提供可核对证据；多 Agent/Critic 让冲突可见；LLM Judge 是可选增强，故障时自动回退并留下可追踪记录。我们的评测也如实记录了架构增益尚未被证明的负向结果（ADR-005）。"

---

## 2. 3–5 分钟版/2 分钟版裁剪

| 时长 | 内容 |
|---|---|
| 5 分钟（推荐） | 上面完整流程 0:00–4:40 |
| 3 分钟 | 启动 30s + 场景 1（60s）+ 证据追溯命令（40s）+ 故障注入（50s）+ 收尾 |
| 2 分钟（电梯版） | 场景 1 的最终裁决 + 一句话证据追溯（trace_id/10 stages）+ 一句话回退设计，不敲故障注入 |

---

## 3. 兜底预案（现场出问题怎么办）

| 故障 | 处理 |
|---|---|
| TUI 起不来/终端不支持 | 改跑 `& $py orchestrator.py "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"`（9s 出完整裁决，含 12 条 Agent Trace） |
| 没有 Neo4j | 正常演示；讲"KG 后端自动回退内置 DISEASE_DB，状态条会显示 backend" |
| Qdrant 502 / RAG 降级 | 正常演示；讲"检索后端不可用时内存回退，不影响决策"。**先设 `NO_PROXY` 可避免** |
| 没有 API Key | 全程规则版；不要按 `[j]/[c]`，直接讲离线降级设计 |
| 有 Key 但网络失败 | TUI 会显示 `规则裁决` + 缺失证据回退文案；顺势讲异常处理，不掩饰 |
| 时间被压缩 | 只保留：场景 1 + trace 一行命令 + 一句回退设计 |

---

## 4. 讲解口径（对应交付清单，避免被问倒）

| 可能的问题 | 建议回答 |
|---|---|
| 为什么要规则 + Agent 混合？ | 规则保证确定性/离线/低延迟（预热后 1.4s），是故障回退底座；Agent 负责证据聚合与冲突暴露；LLM Judge 只在需要结构化融合时启用（单例 43–55s、9–11k tokens）。 |
| 检索带来了什么？ | 病害知识召回 + KG 硬约束锚定，让结论可核对；消融可看到 memory_hits 31→0。代价是低置信检索会注入噪声，Challenge Set 上曾出现 C1 19/24 vs C2 24/24，因此加了记忆门控。 |
| 多 Agent 真的更强吗？ | **不声称更强**：Challenge Set 上 C1 未优于 C0，排名跨 seed 翻转；我们把它定位为"可解释的证据聚合"，而不是"已证明的性能提升"。 |
| 效果怎么验证？ | 固定 Challenge Set 24 例（4 组）+ 64 例 benchmark，标签/原始结果/评分脚本可对应；baseline 指标可复算；负向结果也如实保留。 |
| 故障怎么办？ | Judge 8 类故障都有 reason_code + trace + 日志 + 脱敏；网络失败自动回退规则，进程不崩；已知缺口（持久化/图回退/采样失败静默）在审计报告里。 |
| 环境怎么复现？ | 仓库自带 venv 可直接跑；配置 `.env` 后启用真实 Judge。已知限制：依赖未锁定、README 部分数字过期（审计报告 §2.2）。 |

**不要说的话**：❌"准确率 1.00"（依赖服务与配置）❌"完整架构优于基线"（证据不支持）❌"所有故障都有记录"（仍有静默路径）❌"每次决策 <1s"（实测 1.4–2.7s，冷启动 8–9s）。

---

## 5. 现场检查清单（提前 10 分钟）

- [ ] `.venv\Scripts\python.exe -V` = 3.13.3
- [ ] `NO_PROXY`、`HF_HUB_OFFLINE` 已设
- [ ] 终端字号调大（TUI 表格较宽，建议 ≥120 列 × 30 行）
- [ ] 第二个终端已打开并 cd 到仓库根
- [ ] 故障注入命令已复制到剪贴板
- [ ] 不连生产/付费 API（演示默认离线；有 Key 才开 `[j]`）
