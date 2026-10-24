# AG-DISTILL-T2C 未解决问题队列（更新于修订后）

- 基准：T2B 48 项审计问题 → T2C 处置（closed-direct 13 / closed-no-action 20 / closed-annotation 1 / deferred-p3 8 / open-blocked 5 / open-human 1）
- 本队列仅列 open 与 deferred 项；关闭项见 `revision_status.csv`（disposition 列）。
- v2 包内对应单元的门禁字段（value=null、needs-verification、region=null）全部原样保留，任何升级须走明确证据要求。

## open-blocked（5 项——待外部证据，人工驱动）

| 审计ID | 单元 | 阻塞点 | 解除条件 |
|---|---|---|---|
| AUD-T2B-019 | WHE02-R-07 | 安全间隔期合规链路 | 现行农药登记标签（按具体药剂） |
| AUD-T2B-022 | WHE02-K-02 | DON/ZEN 限量框架 | 现行限量标准文本（与 Q-04 绑定核验） |
| AUD-T2B-035 | WHE02-Q-04 | DON/ZEN 限值 | 同上 |
| AUD-T2B-036 | WHE02-Q-05 | 病粒率收购判定 | 现行收购质量标准条款 |
| AUD-T2B-037 | WHE02-Q-06 | 登记杀菌剂防效/抗性谱 | 登记标签与登记试验 |

解除前约束：五项不得作为合规判定、拒收/处置决策依据；不得数值化。

## open-human（1 项——方法层）

| 审计ID | 事项 | 选项 |
|---|---|---|
| AUD-T2B-048 | 教师 API 对请求模型统一路由 deepseek-flash，异构模型审计不可用 | 人工代理审计 / 引入异构模型重审 / 维持 agent 复核（已声明限制） |

## deferred-p3（8 项——留待后续维护，不闭不弃）

| 审计ID | 单元 | 内容 |
|---|---|---|
| AUD-T2B-001 | WHE02-D-01 | 可补非镰刀菌病原谱（如 Microdochium 属）表述，须区域病原谱数据 |
| AUD-T2B-005 | WHE02-D-04 | 带菌种子初侵染贡献层级区分（可拆分单元） |
| AUD-T2B-007 | WHE02-D-06 | "花器闭合"→"花器开放/花药外露阶段结束"词面更正 |
| AUD-T2B-013 | WHE02-R-02 | uncertainties 显式加"按当地预警模型/植保部门指标核验" |
| AUD-T2B-017 | WHE02-R-05 | 显式写入"不得以排水替代药剂"或由人工确认关闭修订项 |
| AUD-T2B-021 | WHE02-K-01 | quantitative unit 空字符串 → 补单位或移除条目 |
| AUD-T2B-023 | WHE02-K-02 | 同上（与限量核验联动） |
| AUD-T2B-024 | WHE02-K-03 | 同上 |

## 记录级勘误（不构成数据问题）

- T2B `audit_findings.json` AUD-T2B-011 行所引"AUD-T2B-036 统一项"系笔误，应为 AUD-T2B-026/032/038（已在 T2C `revision_log.md` 登记勘误，T2B 文件未改动）。
