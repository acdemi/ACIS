# 20261019 | AG-DISTILL-T2F | 剩余 Top5 四主题启动评估

## 主题与目标
评估 TOM-NWM-02 / MAI-01 / TOM-DMG-02 / TOM-NWM-01 的启动可否与顺位（8 项评估 + 四桶分类），不做提取、不建候选包、不动工程代码。

## 变更文件（新增）
- `reports/ag-distill-t2f-topic-readiness/topic_readiness_assessment.md` — 四主题评估报告

## 变更摘要
- 四桶结论：TOM-NWM-02=①可立即启动（仅受全局前置约束）；MAI-01=③需先工程修复（CROP_MAP 无玉米 + 定量承载契约）；TOM-DMG-02=②需先补资料（农药登记标签门禁体量，WHE-02 同型；可用"识别面 only"折衷）；TOM-NWM-01=④暂不启动（与 MAI-01 框架高度重叠、取证最薄）。
- 推荐顺次 TOM-NWM-02 → MAI-01 → TOM-DMG-02 → TOM-NWM-01，与 T1 Top5 #2-#5 完全一致。
- 全局前置四项：契约批准、审计独立性、P1 证据认领机制、教师模型降级影响确认——先于任何新主题。

## 验证结果
- 本报告为纯评估文档：全部结论以 T1 地图行号（L213-221/269-278/279-287/389-397/472-482）、T2D 调查（CROP_MAP/硬约束实证）、WHE-02 六轮 T2A-T2E 实践为证据锚点，无新执行性验证需求。
- 引用数据均可回溯已提交产物（T2B audit、T2D schema_ingestion_survey.md）。

## 分支与提交
- 分支：`work/20261019-t2e-t2f-release-readiness`
- 提交：`2bd7bbd`（T2F 产品）
- 环境：与 T2E 同一批 worktree 隔离执行（主树被并发会话占用，见 T2E 归档"过程异常"）。
