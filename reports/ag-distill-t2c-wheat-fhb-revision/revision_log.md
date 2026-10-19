# AG-DISTILL-T2C 修订日志 — WHE-02 候选单元（v1 → v2）

- 轮次：AG-DISTILL-T2C；日期：2026-10-19；分支：`work/20261019-t2c-t2d-wheat-fhb`
- 输入：`reports/ag-distill-t2a-wheat-fhb-20261019/candidate_knowledge.json`（v1，AG-DISTILL-T2A-WHE02-CANDIDATES-v1，未修改）+ T2B 审计记录 48 条（`claim_audit.csv` / `audit_findings.json`）
- 输出：`candidate_knowledge_v2.json`（AG-DISTILL-T2C-WHE02-CANDIDATES-v2）、`diff_report.json`（19 条变更的机读 diff）、`revision_status.csv`（48 行逐问题处置）
- 执行器：`scripts/apply_t2c_revisions.py`（旧值断言 → 变更 → 全文档 walk-diff 验证仅预期路径变化；新增自由文本强制无数字；证据等级签名比对）

## 修订政策

- 仅处理 P0/P1/P2（P0=0）；P3 原则上留待后续维护（8 项 deferred），仅当自然被 P1/P2 修正吸收时一并处置（D-03 原子性、关系补链条目）。
- **未提高任何证据等级**：所有单元 provenance/knowledge_layer/quantitative 签名 v1=v2；全部 value 仍 null + needs-verification。
- 未解决项保持 open（5 项合规门禁 + 1 项方法层人工决策），未伪造闭环。

## 逐项变更记录（19 项 / 12 单元）

### WHE02-D-03（AUD-T2B-003 P1、AUD-T2B-004 P3）
- statement（replace）：
  - 旧：`镰刀菌侵染还可引起茎基腐和秆腐，表现为茎基部或茎秆褐变、输导组织坏死，与穗腐属同一病原复合体的不同侵染类型。`
  - 新：`镰刀菌侵染还可引起茎基腐和秆腐，表现为茎基部或茎秆褐变、输导组织坏死；其与穗腐是否属同一病原复合体不作为本单元断言。`
- uncertainties（append）：`与穗腐是否属同一病原复合体的不同侵染类型：待区域病原分离数据核验；核验完成前不得主张三者复合体同一。`
- 复核：walk-diff 单路径；同一性主张收敛为待核验问题，未升级证据；原子性双主张消除。

### WHE02-D-09（AUD-T2B-010 P1）
- statement（replace）：
  - 旧：`赤霉病流行取决于菌源基数、花期降雨或高湿、以及感病品种三者叠加，任一条件缺失时流行程度显著降低。`
  - 新：`赤霉病流行取决于菌源基数、花期降雨或高湿、以及感病品种三者叠加；关键条件缺失或弱化时流行程度通常明显降低，但不排除例外年份与替代路径，该边界待区域流行学数据核验。`
- uncertainties（append）：`本单元不再使用逐项必然式表述；条件间替代关系与例外年份数据未核验。`
- 复核：绝对化断言软化；倾向性表述 + 边界声明，证据等级不变。

### WHE02-R-01（AUD-T2B-012 P2）
- conditions（append）：`适用前提：区域具备可用的流行预警或菌源监测信息；品种抽穗扬花不同步时统一时窗覆盖不全，须分批次判断。`
- 复核：内容源自本单元既有 failure_modes/uncertainties 文案，无新事实。

### WHE02-R-03（AUD-T2B-014 P2、AUD-T2B-015 P2）
- uncertainties（append）：`防治次数与补治间隔核验指向：现行登记标签与本地试验结果；核验前不得以模型常识填充数值。`
- related_units（append）：`WHE02-R-08`（R-08 侧已含 R-03，本次补齐对称；对应 AUD-T2B-015 与 R-03/R-08 窗口张力的关联合并处置）
- 数值字段（防治次数/补治间隔 value=null, needs-verification）未动。

### WHE02-R-04（AUD-T2B-016 P2）
- uncertainties（append）：`本单元不指定具体削减方式与操作参数，方式集合须按区域耕作制度条件化后另行核证。`
- 复核：不引入无证据操作参数；(existing) `不同还田方式的效果差异需分区验证` 保留。

### WHE02-R-06（AUD-T2B-018 P2）
- uncertainties（append）：`区域绑定字段保持留空：本规则区域性强，适用范围须待区域降雨规律与品种生育期数据核验。`
- applicability.region 保持 null。

### WHE02-R-08（AUD-T2B-020 P2）
- uncertainties（append）：`补治决策以扬花完成为定性衰减参照点，与补治口径规则互为边界约束；确切定量拐点未确定。`
- 复核：定性边界落位（既有 statement 已含"随灌浆推进递减"），定量拐点保持待验证。

### WHE02-K-05（AUD-T2B-026 P2，映射 026/032/038）
- related_units（append ×3）：`WHE02-D-10`、`WHE02-F-05`、`WHE02-Q-10`

### WHE02-F-05（AUD-T2B-032 P2）
- related_units（append ×2）：`WHE02-K-05`、`WHE02-D-10`

### WHE02-D-10（AUD-T2B-011 no-issue 行指定的统一补链）
- related_units（append ×2）：`WHE02-K-05`、`WHE02-F-05`

### WHE02-F-02（AUD-T2B-028 P2；AUD-T2B-029 仅注记不改）
- uncertainties（append）：`信息前提：花期天气预报与菌源监测不可得或不可靠时，本单元仅作定性参考，不得单独驱动放弃或维持防治的决策。`
- 前缀 F / layer=rule 不一致：按任务要求不改分类（closed-annotation，manifest 注记保持）。

### WHE02-Q-10（AUD-T2B-038 P2 → closed-direct 部分 + 注记）
- related_units（append ×1）：`WHE02-K-05`
- provenance=model-inference 与 layer=quantitative 的混合层记法：维持注记，不改。

## 未做数据变更的问题（如实保留 open）

- **AUD-T2B-019（R-07）、022（K-02）、035（Q-04）、036（Q-05）、037（Q-06）**：五条合规/标准发布门禁——数据层门禁已由 value=null + needs-verification 承载，本轮**不做任何数据变更**，等待证据责任人提供现行登记标签/限量文本/收购条款核验。未核验前不得进入决策链路（拒收判定、合规测算、处置建议）。
- **AUD-T2B-048**：教师 API 统一路由 deepseek-flash → 异构模型审计不可用，方法层问题，待人工决策。

## P3 留待后续维护（8 项，不闭不弃）

001（D-01 非镰刀菌病原谱补充）、005（D-04 种子源层级）、007（D-06"花器闭合"措辞）、013（R-02 预警核验文案显式化）、017（R-05"不得替代药剂"显式化）、021/023/024（K-01/K-02/K-03 的 quantitative unit 空字符串）。

## 记录级勘误（不改 T2B 已归档文件）

- T2B `audit_findings.json` 中 AUD-T2B-011（D-10 no-issue 行）文案所引"AUD-T2B-036 统一项"系笔误，所指应为关系补链条目 AUD-T2B-026/032/038；本轮按该正确映射执行（D-10 补链），T2B 产物文件未作改动，在此登记勘误。

## 处置汇总（48 项）

| 处置 | 数量 |
|---|---|
| closed-direct（直接修订） | 13 |
| closed-no-action（复核通过/维持候选） | 20 |
| closed-annotation（仅注记） | 1 |
| open-blocked（待外部证据） | 5 |
| open-human（人工决策） | 1 |
| deferred-p3（P3 留待维护） | 8 |
| **合计** | **48** |
