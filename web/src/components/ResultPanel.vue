<script setup lang="ts">
import { computed } from "vue";
import type { DiagnosisResult, DiagnosisReport } from "../api";
import type { DemoCase } from "../demoCases";

const props = defineProps<{
  result: DiagnosisResult;
  demo: DemoCase | null;
  isCopying: boolean;
  copyMessage: string;
}>();
const emit = defineEmits<{ copy: []; history: [] }>();

const confidence = computed(() => {
  const score = Number(props.result.report.confidence?.score ?? props.result.confidence);
  return Number.isFinite(score) ? Math.max(0, Math.min(1, score)) : 0;
});

const stages = computed(() => {
  const events = props.result.trace?.events ?? [];
  const definitions = [
    { key: "request", title: "输入校验" },
    { key: "memory", title: "知识检索" },
    { key: "experts", title: "Agent 分析" },
    { key: "judge", title: "Judge 评估" },
  ];
  const entries = definitions.map((stage) => {
    const matched = events.filter((event) => event.stage === stage.key);
    const failed = matched.some((event) => {
      const payload = event.payload ?? {};
      return payload.status === "failed" || payload.error !== undefined;
    });
    return { ...stage, count: matched.length, failed };
  });
  entries.push({ key: "report", title: "报告生成", count: props.result.report ? 1 : 0, failed: false });
  return entries;
});

function confidenceLabel(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function riskLabel(value?: string): string {
  return ({ low: "低", medium: "中", high: "高" } as Record<string, string>)[value ?? ""] ?? value ?? "未评估";
}

function formatSource(source: { title?: string; source?: string; id?: string }): string {
  return source.title || source.source || source.id || "未命名来源";
}

function reportValue(report: DiagnosisReport): string {
  return JSON.stringify(report, null, 2);
}
</script>

<template>
  <section class="result-section" aria-labelledby="result-title">
    <div class="result-topline"><div><p class="section-kicker">DIAGNOSTIC OUTPUT</p><h2 id="result-title">诊断结果</h2></div><span v-if="demo" class="fixture-badge">DEMO / FIXTURE MODE</span><span v-else class="result-live-badge"><i></i>本次 API 响应</span></div>
    <div v-if="demo" class="fixture-explanation">当前使用“{{ demo.title }}”固定输入；以下内容来自本次服务执行，而非预存诊断结果。</div>

    <div class="result-summary">
      <div class="verdict-content"><div class="verdict-label"><span class="verdict-icon">✓</span>首选诊断</div><h3>{{ result.decision || result.report.diagnosis || '未能形成明确诊断' }}</h3><p v-if="result.need_human_review" class="review-warning">需要人工复核：当前结论存在不确定性或证据限制。</p><p v-if="result.report.differential_analysis?.alternative" class="differential-note">鉴别对象：{{ result.report.differential_analysis.alternative }}<span v-if="result.report.differential_analysis.rejection_reason"> · {{ result.report.differential_analysis.rejection_reason }}</span></p></div>
      <div class="verdict-metrics"><div class="confidence-gauge" :style="{ '--confidence': `${confidence * 100}%` }"><div><strong>{{ confidenceLabel(confidence) }}</strong><span>置信度</span></div></div><div class="risk-block"><span>风险等级</span><strong :class="`risk-${result.report.risk ?? result.risk_level}`">{{ riskLabel(result.report.risk ?? result.risk_level) }}</strong></div></div>
    </div>

    <div class="report-grid">
      <article class="panel report-card">
        <div class="card-heading"><span class="card-index">A</span><div><h3>诊断依据</h3><p>来自本次分析的证据摘要</p></div></div>
        <ul v-if="result.report.evidence?.length" class="evidence-list"><li v-for="(item, index) in result.report.evidence" :key="`${index}-${item}`"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ item }}</li></ul><p v-else class="empty-inline">报告未单独提供依据摘要，可查看 Agent 执行记录。</p>
        <div v-if="result.traces?.length" class="agent-summary"><div class="subsection-title">Agent 执行</div><div v-for="(agent, index) in result.traces" :key="`${agent.agent}-${index}`" class="agent-row"><span class="agent-index">{{ String(index + 1).padStart(2, '0') }}</span><span class="agent-name">{{ agent.agent || 'Agent' }}</span><span class="agent-claim">{{ agent.claim || '已执行' }}</span><span class="agent-status" :class="{ failed: agent.execution?.status === 'failed' || agent.execution?.fallback }">{{ agent.execution?.status || '状态未提供' }}<template v-if="agent.execution?.mode"> · {{ agent.execution.mode }}</template></span></div></div>
      </article>

      <article class="panel report-card">
        <div class="card-heading"><span class="card-index">B</span><div><h3>知识来源</h3><p>只显示本次实际返回的检索信息</p></div></div>
        <div class="source-status-row"><span>RAG</span><strong>{{ result.report.knowledge_sources?.rag_status || '报告未提供状态' }}</strong><span class="source-backend">KG · {{ result.report.knowledge_sources?.kg?.backend || '未提供' }}</span></div>
        <div v-if="result.report.knowledge_sources?.rag?.length" class="source-list"><article v-for="(source, index) in result.report.knowledge_sources.rag" :key="source.id || `${source.title}-${index}`" class="source-item"><span class="source-number">{{ String(index + 1).padStart(2, '0') }}</span><div><strong>{{ formatSource(source) }}</strong><p>{{ source.text || source.content || '本次检索未提供片段正文。' }}</p><small>{{ source.backend || 'backend 未提供' }}<span v-if="typeof source.score === 'number'"> · score {{ source.score.toFixed(3) }}</span></small></div></article></div><p v-else class="empty-inline">本次报告没有返回 RAG 来源；不以静态知识样例代替检索结果。</p>
      </article>

      <article class="panel report-card">
        <div class="card-heading"><span class="card-index">C</span><div><h3>建议与风险</h3><p>结合证据审慎使用</p></div></div>
        <ol v-if="result.action_plan?.length" class="action-list"><li v-for="(item, index) in result.action_plan" :key="`${index}-${item}`"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ item }}</li></ol><p v-else class="empty-inline">当前结果未提供建议措施。</p>
        <div v-if="result.report.follow_up_questions?.length" class="follow-up-box"><strong>建议补充信息</strong><ul><li v-for="question in result.report.follow_up_questions" :key="question">{{ question }}</li></ul></div>
        <div v-if="result.report.environment" class="environment-row"><strong>环境记录</strong><details><summary>查看本次提交内容</summary><pre>{{ JSON.stringify(result.report.environment, null, 2) }}</pre></details></div>
        <div class="risk-disclaimer">农业诊断辅助信息，不替代当地植保专业人员现场判断。</div>
      </article>

      <article class="panel report-card trace-card">
        <div class="card-heading trace-heading"><span class="card-index">D</span><div><h3>执行 Trace</h3><p>阶段状态来源于本次响应记录</p></div><span class="trace-id">{{ result.trace_id || result.report.request_id || 'Trace ID 未提供' }}</span></div>
        <div class="trace-timeline"><div v-for="(stage, index) in stages" :key="stage.key" class="trace-step" :class="{ missing: !stage.count, failed: stage.failed }"><span class="trace-step-index">{{ String(index + 1).padStart(2, '0') }}</span><span class="trace-step-name">{{ stage.title }}</span><span class="trace-step-status">{{ stage.failed ? '检测到异常' : stage.count ? `已记录 · ${stage.count}` : '未提供记录' }}</span></div></div>
        <details v-if="result.trace" class="raw-trace"><summary>展开完整 Trace JSON</summary><pre>{{ JSON.stringify(result.trace, null, 2) }}</pre></details><p v-else class="empty-inline">API 响应未包含 Trace；页面不会补造执行阶段。</p>
      </article>
    </div>

    <div class="result-actions"><div><span class="result-meta">Judge：{{ result.judge_mode }} · 耗时：{{ result.report.duration_ms != null ? `${result.report.duration_ms.toFixed(1)} ms` : '未提供' }}</span><span v-if="copyMessage" class="copy-feedback" role="status">{{ copyMessage }}</span></div><div class="action-buttons"><button class="secondary-button" type="button" :disabled="isCopying" @click="emit('copy')">{{ isCopying ? '复制中…' : '复制诊断报告' }}</button><button class="secondary-button" type="button" @click="emit('history')">查看历史记录 ↗</button></div></div>
  </section>
</template>
