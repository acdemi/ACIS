# ACIS 3–5 分钟演示脚本

> 配套验收记录：`reports/acceptance_20261024.md`
> 目标：用 4 分钟左右演示 **正常任务 → 证据追溯 → 异常处理** 三件事，全部离线可跑、不依赖外网与付费 API。
> 本脚本基于 2026-10-24 实测（`.venv` Python 3.13、TUI 12.2s 启动、每场景 1.4–1.7s）。

---

## 0. 演示前 5 分钟准备（不上台）

```powershell
cd <ACIS 仓库根目录>
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH='.'
$env:NO_PROXY='localhost,127.0.0.1'     # 必设：否则本机代理会把 localhost 打成 502，RAG 静默降级
$env:HF_HUB_OFFLINE='1'                # 避免视觉/时序模型联网下载
$py = '.\.venv\Scripts\python.exe'
```

检查三件事：

1. `.\.venv\Scripts\python.exe -V` → `Python 3.13.3`（使用仓库自己的 `.venv`，不要用系统 python）。
2. `& $py -m acis --rules-only --seed 7 --trace-out logs/trace_demo.json "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"` → 能出 `病理判断首选：番茄叶霉病`，并生成 `logs/trace_demo.json`（冷启动约 8–9s）。
3. 开第二个终端预跑一遍演示命令，避免首次 import/模型预热占用演示时间。

**可选（有 Key 才用）**：`$env:DEEPSEEK_API_KEY='sk-...'`，并在 TUI 中按 `[j]` 开 LLM Judge；**无 Key 时不要承诺 LLM 演示**，直接讲规则版（本脚本默认）。

---

## 1. 演示时间轴（离线规则版，约 4 分 10 秒）

### 0:00–0:30 · 开场 + 启动
```powershell
& $py -m acis tui
```
讲：
> "这是 ACIS 的 TUI 演示入口。主链是 感知 → 记忆 → 专家 → 辩论 → Critic → Judge，默认走离线规则裁决；右侧状态条显示 Neo4j / RAG / Judge 开关，没有外部服务时会自动降级。"

指给观众看：菜单 9 个场景（7–9 为固定案例并标明 `DEMO / FIXTURE MODE`）、状态行 `Judge:关 Critic:关`、最近 `KG` 后端与 RAG 状态。

### 0:30–1:40 · 正常任务（场景 1）
输入 `1` 回车。

讲（跟着画面走）：
> "输入是真实中文咨询：番茄叶片黄斑、叶背灰色霉层。可以看到 12 条 Agent 轨迹逐条刷出：感知层三个 Agent → 记忆层 RAG/知识图谱/案例库 → 专家层病理/气象/栽培。"
> "最终裁决是番茄叶霉病，置信度约 72–74%，风险 medium；下面是 6 条行动建议，右侧是辩论共识与缺失证据（缺少图像证据）。"

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
& $py -m acis --rules-only --seed 7 --trace-out logs/trace_demo.json "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"
& $py -c "import json; d=json.load(open('logs/trace_demo.json',encoding='utf-8')); print('trace_id=',d['trace_id']); print('stages=',[k for k in ('request','perception','memory','experts','debate','critic','judge','planner','tool_router','metrics') if k in d]); print('judge_runtime=',d['judge'][0]['judge_analysis']['judge_runtime'])"
```
讲：
> "`--trace-out` 一条命令把本次运行导出成 JSON：trace_id、10 个阶段（request…metrics）和 Judge 运行元数据都在里面；同一条决策在 SQLite 里有 decision_id。这就是'可追溯'的落点。`--seed 7` 让模拟天气/传感器中的随机部分可复现。"

### 3:20–4:10 · 异常处理（故障注入，证明"故障可解释"）
在第二个终端执行（复制即可）：
```powershell
$env:AGRI_AI_JUDGE_API_KEY='sk-test'
$env:AGRI_AI_JUDGE_BASE_URL='http://127.0.0.1:9'
$env:AGRI_AI_JUDGE_TIMEOUT_SECONDS='10'
$env:AGRI_AI_JUDGE_MAX_RETRIES='0'
& $py -m acis --rules-only --llm-judge --json "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"
```
讲，并指给观众看四样东西：
1. **进程正常退出、仍有裁决** → `judge_mode=rules`（自动回退，服务不中断）；
2. `judge_runtime.outcome=fallback`、`fallback_reason_code=connection_error`、`retry_exhausted=true`；
3. `debate.missing_evidence` 里有一句"LLM Judge 不可用，已回退规则裁决 [connection_error] …"；
4. stderr 三行日志：`Judge request:` → `Judge exception:` → `Judge fallback:`，且 **API key 已脱敏**（看不到 sk-）。
> "从 401/402/429/超时/连接失败/非 JSON 输出，到 5xx，都有稳定的 reason_code、trace 字段和日志；这是评测和排障能对上的原因。"

### 备选 · SQLite 审计记录（可选，约 20 秒，不占主时间轴）

证据追溯还有第三个落点：**同一条决策写进了 SQLite 审计表**（表 `decisions`，默认库 `data/agri.db`）。两种查看方式任选：

```powershell
# 方式一：只读查询，不写库（推荐，无需起服务）
& $py -c "import sqlite3; c=sqlite3.connect('file:data/agri.db?mode=ro',uri=True); [print(r) for r in c.execute('SELECT id,created_at,crop,judge_mode,confidence,need_human_review,substr(decision,1,20) FROM decisions ORDER BY id DESC LIMIT 3')]; c.close()"
```
预期：每行一条 `(id, created_at, crop, judge_mode, confidence, need_human_review, decision 前 20 字)`，最新记录的 `id` 等于刚才 Trace 里的 `decision_id`。

```powershell
# 方式二：走 API 契约，不起服务（与收尾的 /health 检查同一风格）
& $py -c "import os; os.environ['ACIS_API_KEY']='local-test-key-0123456789abcdef0123456789'; from fastapi.testclient import TestClient; from acis.api.app import app; c=TestClient(app); r=c.get('/decisions?limit=3', headers={'X-API-Key':os.environ['ACIS_API_KEY']}); print('status=',r.status_code); [print(x['id'], x['judge_mode'], x['confidence']) for x in r.json()]"
```
预期：`status= 200`，随后每行 `id judge_mode confidence`。该密钥仅用于本地 `TestClient` 示例；`GET /health` 可匿名访问，`GET /decisions`、`GET /decisions/{id}` 等数据接口需要 `X-API-Key`。

讲：
> "裁决不只停留在画面上：每次决策都写一条审计记录，字段包括裁剪/意图/裁决/置信度/风险/human-review 标记/行动建议全量/Trace。`judge_mode` 只有 `rules` 和 `deepseek` 两个取值——**规则回退不会被记成 LLM 结果**，这是可审计的前提。"

> ⚠️ `judge_mode` 口径：`rules` = 离线规则裁决（默认演示路径），`deepseek` = 真实 LLM 裁决。演示时不要把 `rules` 讲成"模型诊断"。

**演示前建议改用隔离库**（可选；不设则写入仓库内 `data/agri.db`）：

```powershell
$env:AGRI_AI_DB_PATH = "$env:TEMP/acis_demo.db"   # 已实测生效：CLI / TUI / API 都遵守
Remove-Item Env:\AGRI_AI_DB_PATH                  # 取消隔离（或直接新开终端）
```

### 4:10–4:40 · 收尾（二选一）
- 规则/API：`& $py -c "import os; os.environ['ACIS_API_KEY']='local-test-key-0123456789abcdef0123456789'; from fastapi.testclient import TestClient; from acis.api.app import app; c=TestClient(app); print(c.get('/health').status_code, c.post('/diagnose', json={'query':'番茄叶片黄斑，叶背灰色霉层'}, headers={'X-API-Key':os.environ['ACIS_API_KEY']}).status_code)"` → `200 200`。
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
| TUI 起不来/终端不支持 | 改跑 `& $py -m acis "温室A番茄叶片出现黄斑，叶背有灰色霉层，如何处理？"`（9s 出完整裁决，含 12 条 Agent Trace） |
| 没有 Neo4j | 正常演示；讲"KG 后端自动回退内置 DISEASE_DB，状态条会显示 backend" |
| Qdrant 502 / RAG 降级 | 正常演示；讲"检索后端不可用时内存回退，不影响决策"。**先设 `NO_PROXY` 可避免** |
| 没有 API Key | 全程规则版；不要按 `[j]/[c]`，直接讲离线降级设计 |
| 有 Key 但网络失败 | TUI 会显示 `规则裁决` + 缺失证据回退文案；顺势讲异常处理，不掩饰 |
| 时间被压缩 | 只保留：场景 1 + trace 一行命令 + 一句回退设计 |

---

## 4. 讲解口径

| 可能的问题 | 建议回答 |
|---|---|
| 为什么要规则 + Agent 混合？ | 规则保证确定性/离线/低延迟（预热后 1.4s），是故障回退底座；Agent 负责证据聚合与冲突暴露；LLM Judge 只在需要结构化融合时启用（单次调用约几十秒、约 1 万 tokens）。 |
| 检索带来了什么？ | 病害知识召回 + KG 硬约束锚定，让结论可核对；消融可看到 memory_hits 31→0。代价是低置信检索会注入噪声，Challenge Set 单 seed 上曾出现 C1 19/24 vs C2 24/24，因此加了记忆门控；该差异不足以证明架构收益。 |
| 多 Agent 真的更强吗？ | **不声称更强**：Challenge Set 上 C1 未优于 C0，排名跨 seed 翻转；我们把它定位为"可解释的证据聚合"，而不是"已证明的性能提升"。 |
| 效果怎么验证？ | 固定 Challenge Set 24 例（4 组）+ 64 例 benchmark，标签/原始结果/评分脚本可对应；baseline 指标可复算；负向结果也如实保留。 |
| 故障怎么办？ | Judge 8 类故障都有 reason_code + trace + 日志 + 脱敏；网络失败自动回退规则，进程不崩；已知缺口（持久化/图回退/采样失败静默）在审计报告里。 |
| 环境怎么复现？ | 按 README 创建 `.venv` 并安装依赖；配置 `.env` 后启用真实 Judge。`requirements-lock.txt` 为 Windows + Python 3.13.3 生成；本次全量 pytest 为 **364 passed / 2 skipped / 1 warning**，运行于 Windows。Docker Compose 另以 Linux Python 3.11.14、Qdrant 1.18.2、Neo4j 2026.05.0 镜像完成隔离构建、三服务健康、API 诊断/Trace/持久化重启验证；测试库无导入语料，故仍走已标明的内存回退。 |

**不要说的话**：❌"准确率 1.00"（依赖服务与配置）❌"完整架构优于基线"（证据不支持）❌"所有故障都有记录"（仍有静默路径）❌"每次决策 <1s"（实测 1.4–2.7s，冷启动 8–9s）。

---

## 5. 现场检查清单（提前 10 分钟）

- [ ] `.venv\Scripts\python.exe -V` = 3.13.3
- [ ] `NO_PROXY`、`HF_HUB_OFFLINE` 已设
- [ ] 终端字号调大（TUI 表格较宽，建议 ≥120 列 × 30 行）
- [ ] 第二个终端已打开并 cd 到仓库根
- [ ] 故障注入命令已复制到剪贴板
- [ ] 不连生产/付费 API（演示默认离线；有 Key 才开 `[j]`）

## 6. ACIS v1.0 诊断闭环案例

以下三个固定输入可在 TUI 菜单 7–9、Web 快捷场景或命令行重复运行。离线复现使用内置 RAG/KG 数据，不调用外部模型；报告会标明 `memory` 后端和命中的知识来源。

```powershell
$env:AGRI_AI_RAG_BACKEND='memory'
$env:AGRI_AI_KG_BACKEND='memory'
& $py -m acis --rules-only --seed 7 --json "玉米下部叶片出现长梭形灰绿色至灰褐色病斑，湿度高时病斑快速扩大，请诊断。"
& $py -m acis --rules-only --seed 7 --json "小麦叶片出现黄色粉状小疱，沿叶脉排列成条带；请与叶锈病鉴别。"
& $py -m acis --rules-only --seed 7 --json "玉米长势不好，叶片有点发黄，具体原因不清楚。"
```

预期核对：玉米病例首选“玉米大斑病”；小麦病例首选“小麦条锈病”并保留替代诊断；信息不足病例必须报告“证据不足”、人工复核和补充问题，不给出针对病害的喷施处置。每次 JSON 输出包含报告、知识来源、Agent 执行状态与完整 Trace；`tests/test_delivery_cases_v1.py` 对实际输出及 SQLite Trace 关联做自动化断言。


## 7. Vue Web 工作台演示

前端开发需 Node.js 22 LTS；不需要启动 Neo4j/Qdrant，默认演示使用本地内存检索后端。若尚未启动本地服务，在两个终端运行：

```powershell
# 终端一
$env:ACIS_API_KEY='replace-with-a-private-key-of-at-least-32-characters'
$env:AGRI_AI_RAG_BACKEND='memory'
$env:AGRI_AI_KG_BACKEND='memory'
uvicorn acis.api.app:app --host 127.0.0.1 --port 8000

# 终端二（首次安装依赖后可省略 npm ci）
npm ci --prefix web
npm --prefix web run dev
```

打开 `http://127.0.0.1:5173`，将同一个本地 Key 输入侧栏并连接 API。依次运行三个快捷案例：玉米大斑病、小麦锈病鉴别、玉米信息不足。案例卡只预填输入，界面会标注 `DEMO / FIXTURE MODE`，诊断、检索来源、Judge 与 Trace 均来自本次 API 响应；第三例应弃权并请求补充信息。可选上传 JPEG、PNG 或 BMP 图片（最大 10 MiB）；上传会由受保护 API 暂存，但视觉识别默认是 Mock，不应承诺真实图像诊断能力。
