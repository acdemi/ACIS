# 归档：AG-DISTILL-T1 农业知识域探测（2026-10-19）

## 对话主题与目标

- 主题：AG-DISTILL-T1 农业知识域探测 — 建立知识提取地图（只建图，不做深入提取）
- 目标主题：番茄病害与调控；番茄水肥与营养；甜菜、小麦、玉米等主要粮食作物与大田作物
- 用户填充：目标区域 / 生产体系留空；existing_knowledge 以 `rag/knowledge_base.py` 为准
- 目标：产出 10 项内容（核心概念/过程机制/生产规则/关键因素/交互/定量指标/易混淆/相反结论/
  待验证/重复主题）+ 候选主题目录（9 字段）+ Top5 优先子主题

## 变更文件清单

| 文件 | 操作 |
|---|---|
| `docs/knowledge/20261019-ag-distill-t1-domain-map.md` | 新增（489 行） |
| `context/archive/20261019-ag-distill-t1-domain-scan.md` | 新增（本归档） |

- 前置分支操作：由 `main`（a928061 上层）创建 `work/20261019-ag-distill-domain-scan`。
- 未纳入提交的无关文件：`reports/phase4_judge_recovery_20261019/`（未跟踪，属其他轮次，保持原状）。

## 变更摘要

- 建立 26 个候选主题的提取地图，覆盖番茄病害 7 项（TOM-DMG-01~07）、番茄水肥营养 4 项
  （TOM-NWM-01~04）、甜菜 4 项（SWT-01~04）、小麦 5 项（WHE-01~05）、玉米 5 项（MAI-01~05）、
  跨作物通用机制 4 项（XCR-01~04）。
- 每主题含 topic_id / title / knowledge_type / scope / key_questions /
  expected_knowledge_value / evidence_requirements / extraction_priority / uncertainty 九字段。
- 核心结论：
  - 用户点名的甜菜/小麦/玉米在现库零覆盖（小麦、玉米完全空白；甜菜仅 2 病害+1 指南）；
  - 现库 27 个条件/数值字段全部无出处标注（rag-kb 无源），统一登记为"已有、待复核"；
  - `severity_indicators` 分级未经田间校准，直接作为行动阈值属"伪量化"风险条目；
  - 登记了 7 组"研究条件依赖可能相反"的分歧（亏缺灌溉、控氮、密植、CO2×通风等），本轮不裁决；
  - 与已有知识重复主题以表登记（10 对），按公约不判定其内容完全等价。
- Top5 优先深取：WHE-02 赤霉病与毒素 > TOM-NWM-02 番茄营养与脐腐 > MAI-01 玉米需水临界
  > TOM-DMG-02 晚疫病 > TOM-NWM-01 番茄水分精细化（理由见地图 §12）。

## 验证结果

- 本轮无 Python 代码改动，未运行 pytest / ruff / mypy（文档轮次不适用）。
- 文档质量检查：以 rg 扫描全文拉丁残留词与乱码模式，共清理 40+ 处生成伪影/r区乱码，
  二次扫描确认拉丁 token 均为合法术语（SSR 名单核对）；分段复读首尾与抽查正文，无残留。
- 事实纪律核对：全部数值仅三类——[rag-kb]（无出处）、[待查证]、数学换算（15-20 m³/亩≈22-30mm）；
  未登记任何记忆中的文献/试验结论为事实。

## 分支名与提交号

- 分支：`work/20261019-ag-distill-domain-scan`
- 提交 1：`d9b37d6` docs: add AG-DISTILL-T1 agri knowledge domain map
- 提交 2：（本归档提交，见 `git log` 第二条）

## 状态

- 已完成（本轮目标即"只建地图"；未做提取轮任务，无未完成事项）。
- 后续：等待用户决定是否启动 Top5 提取轮 / 是否调整主题清单。
