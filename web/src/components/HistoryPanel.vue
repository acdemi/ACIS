<script setup lang="ts">
import { computed, ref } from "vue";
import type { DecisionDetail, DecisionSummary } from "../api";

const props = defineProps<{
  apiKeyReady: boolean;
  items: DecisionSummary[];
  detail: DecisionDetail | null;
  loading: boolean;
  error: string;
  feedbackMessage: string;
}>();

const emit = defineEmits<{
  select: [item: DecisionSummary];
  feedback: [value: "correct" | "incorrect" | "partial"];
  newDiagnosis: [];
}>();

const query = ref("");
const crop = ref("all");
const cropOptions = computed(() => [...new Set(props.items.map((item) => item.crop).filter(Boolean))]);
const filtered = computed(() => props.items.filter((item) => {
  const search = query.value.trim().toLocaleLowerCase();
  const queryMatch = !search || `${item.query} ${item.decision}`.toLocaleLowerCase().includes(search);
  return queryMatch && (crop.value === "all" || item.crop === crop.value);
}));

function confidence(value: number): string {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

function risk(value: string): string {
  return ({ low: "低", medium: "中", high: "高" } as Record<string, string>)[value] ?? value ?? "未评估";
}

function cropMark(value: string): string {
  return value?.slice(0, 1) || "田";
}
</script>

<template>
  <section class="history-page">
    <header class="page-heading"><div><p class="section-kicker">DECISION ARCHIVE</p><h1>历史记录</h1><p>来自 ACIS SQLite 决策存储；不展示未加载的统计信息。</p></div><button class="submit-button compact-submit" type="button" @click="emit('newDiagnosis')"><span>新建诊断</span><span class="submit-arrow">＋</span></button></header>

    <div v-if="!apiKeyReady" class="empty-state panel"><span class="empty-state-icon">▤</span><h2>连接 API 后查看诊断记录</h2><p>请在左侧输入本地 ACIS API Key。系统只会读取真实存储记录。</p></div>
    <div v-else class="history-layout">
      <section class="panel history-list-panel" aria-label="诊断记录列表">
        <div class="history-toolbar"><label class="search-field"><span aria-hidden="true">⌕</span><input v-model="query" type="search" placeholder="搜索问题或结论" aria-label="搜索问题或结论" /></label><label class="crop-filter"><span class="sr-only">按作物筛选</span><select v-model="crop"><option value="all">全部作物</option><option v-for="item in cropOptions" :key="item" :value="item">{{ item }}</option></select></label></div>
        <div v-if="props.loading" class="history-empty">正在读取 SQLite 决策记录…</div>
        <div v-else-if="props.error" class="history-empty error-text" role="alert">{{ props.error }}</div>
        <div v-else-if="!filtered.length" class="history-empty"><strong>{{ props.items.length ? '没有匹配的诊断记录' : '暂无历史诊断' }}</strong><span>{{ props.items.length ? '调整搜索词或作物筛选条件。' : '完成一次诊断后，真实记录会显示在这里。' }}</span></div>
        <button v-for="item in filtered" :key="item.id" class="history-item" :class="{ selected: props.detail?.id === item.id }" type="button" @click="emit('select', item)">
          <span class="history-crop-mark">{{ cropMark(item.crop) }}</span>
          <span class="history-item-content"><span class="history-item-top"><strong>{{ item.crop || '未识别作物' }}</strong><time>{{ item.created_at }}</time></span><span class="history-query">{{ item.query }}</span><span class="history-decision">{{ item.decision }}</span></span>
          <span class="history-item-confidence">{{ confidence(item.confidence) }}</span>
        </button>
        <p v-if="props.items.length" class="history-footnote">显示最近 {{ props.items.length }} 条记录（API 返回上限 50 条）</p>
      </section>

      <section v-if="props.detail" class="panel history-detail-panel" aria-label="诊断记录详情">
        <div class="detail-overline">DECISION #{{ props.detail.id }}<span>{{ props.detail.created_at }}</span></div>
        <h2>{{ props.detail.decision }}</h2><p class="detail-query">{{ props.detail.query }}</p>
        <div class="detail-metrics"><span><small>置信度</small><strong>{{ confidence(props.detail.confidence) }}</strong></span><span><small>风险</small><strong>{{ risk(props.detail.risk_level) }}</strong></span><span><small>Judge</small><strong>{{ props.detail.judge_mode }}</strong></span></div>
        <div v-if="props.detail.action_plan?.length" class="detail-section"><h3>建议措施</h3><ol><li v-for="action in props.detail.action_plan" :key="action">{{ action }}</li></ol></div>
        <div v-if="props.detail.report_json" class="detail-section"><h3>诊断报告</h3><details><summary>展开完整报告</summary><pre>{{ JSON.stringify(props.detail.report_json, null, 2) }}</pre></details></div>
        <div v-if="props.detail.trace_json" class="detail-section"><h3>执行 Trace · {{ props.detail.trace_id || props.detail.trace_json.trace_id || '未提供 ID' }}</h3><details><summary>展开 Trace 事件</summary><pre>{{ JSON.stringify(props.detail.trace_json, null, 2) }}</pre></details></div>
        <div class="feedback-area"><h3>人工复核</h3><p>保存复核标签以完善后续案例分析。</p><div class="feedback-buttons"><button type="button" @click="emit('feedback', 'correct')">正确</button><button type="button" @click="emit('feedback', 'partial')">部分符合</button><button type="button" @click="emit('feedback', 'incorrect')">不正确</button></div><span v-if="props.feedbackMessage" class="inline-success" role="status">{{ props.feedbackMessage }}</span></div>
      </section>
      <section v-else class="panel history-detail-empty"><span>←</span><strong>选择一条记录查看报告与 Trace</strong><p>详细内容来自决策存储接口。</p></section>
    </div>
  </section>
</template>
