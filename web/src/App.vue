<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import DiagnosisForm from "./components/DiagnosisForm.vue";
import HistoryPanel from "./components/HistoryPanel.vue";
import ResultPanel from "./components/ResultPanel.vue";
import {
  ApiError,
  getDecision,
  getDecisions,
  getHealth,
  runDiagnosis as requestDiagnosis,
  sendFeedback,
  uploadImage,
  type ApiHealth,
  type DecisionDetail,
  type DecisionSummary,
  type DiagnosisResult,
} from "./api";
import { demoCases, type DemoCase } from "./demoCases";

type ViewName = "diagnose" | "history";

const currentView = ref<ViewName>("diagnose");
const apiKeyDraft = ref("");
const apiKey = ref("");
const apiHealth = ref<ApiHealth | null>(null);
const healthState = ref<"checking" | "ready" | "error">("checking");
const healthMessage = ref("正在检查 API 状态");
const healthError = ref("");
const connectionError = ref("");
const connectionMessage = ref("");
const diagnosisError = ref("");
const imageUploadError = ref("");
const historyError = ref("");
const isConnecting = ref(false);
const isRunning = ref(false);
const isUploadingImage = ref(false);
const isLoadingHistory = ref(false);
const isCopying = ref(false);
const copyMessage = ref("");
const feedbackMessage = ref("");
const history = ref<DecisionSummary[]>([]);
const detail = ref<DecisionDetail | null>(null);
const diagnosis = ref<DiagnosisResult | null>(null);
const uploadedImage = ref<{ name: string; path: string } | null>(null);
const activeDemoId = ref("");

const selectedDemo = computed<DemoCase | null>(
  () => demoCases.find((item) => item.id === activeDemoId.value) ?? null,
);

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "发生意外错误，请稍后重试或检查服务日志。";
}

async function refreshHealth(): Promise<void> {
  healthState.value = "checking";
  healthMessage.value = "正在检查 API 状态";
  try {
    apiHealth.value = await getHealth();
    healthState.value = "ready";
    healthMessage.value = "API 已连接";
    healthError.value = "";
  } catch (error) {
    apiHealth.value = null;
    healthState.value = "error";
    healthMessage.value = "API 暂不可用";
    healthError.value = errorMessage(error);
  }
}

async function loadHistory(): Promise<void> {
  if (!apiKey.value) return;
  isLoadingHistory.value = true;
  historyError.value = "";
  try {
    history.value = await getDecisions(apiKey.value);
  } catch (error) {
    historyError.value = errorMessage(error);
    if (error instanceof ApiError && error.status === 401) apiKey.value = "";
  } finally {
    isLoadingHistory.value = false;
  }
}

async function connectApi(): Promise<void> {
  const candidate = apiKeyDraft.value.trim();
  connectionMessage.value = "";
  connectionError.value = candidate.length < 32
    ? "API Key 至少需要 32 个字符。"
    : !/^[\x00-\x7F]+$/.test(candidate)
      ? "API Key 只能包含 ASCII 字符。"
      : "";
  if (connectionError.value) return;

  isConnecting.value = true;
  try {
    history.value = await getDecisions(candidate);
    apiKey.value = candidate;
    apiKeyDraft.value = "";
    connectionMessage.value = "连接成功。密钥仅保存在当前页面内存中，刷新后需重新输入。";
  } catch (error) {
    apiKey.value = "";
    connectionError.value = errorMessage(error);
  } finally {
    isConnecting.value = false;
  }
}

async function submitDiagnosis(payload: {
  query: string;
  demoId: string;
  useLlmJudge: boolean;
  useLlmCritic: boolean;
}): Promise<void> {
  diagnosisError.value = "";
  copyMessage.value = "";
  if (!apiKey.value) {
    diagnosisError.value = "请先在左侧输入有效的本地 API Key，再运行诊断。";
    return;
  }
  if (!payload.query.trim()) {
    diagnosisError.value = "请描述作物、症状或现场问题后再提交。";
    return;
  }
  if (payload.query.length > 4000) {
    diagnosisError.value = "输入内容超过 API 的 4000 字符限制，请精简后重试。";
    return;
  }

  activeDemoId.value = payload.demoId;
  isRunning.value = true;
  diagnosis.value = null;
  detail.value = null;
  try {
    diagnosis.value = await requestDiagnosis(apiKey.value, payload.query, {
      useLlmJudge: payload.useLlmJudge,
      useLlmCritic: payload.useLlmCritic,
      imagePath: uploadedImage.value?.path,
    });
    await loadHistory();
  } catch (error) {
    diagnosisError.value = errorMessage(error);
  } finally {
    isRunning.value = false;
  }
}

async function stageDiagnosisImage(file: File): Promise<void> {
  uploadedImage.value = null;
  imageUploadError.value = "";
  if (!apiKey.value) {
    imageUploadError.value = "请先连接 ACIS API，再上传图片。";
    return;
  }

  isUploadingImage.value = true;
  try {
    const stagedImage = await uploadImage(apiKey.value, file);
    uploadedImage.value = { name: file.name, path: stagedImage.image_path };
  } catch (error) {
    imageUploadError.value = errorMessage(error);
    if (error instanceof ApiError && error.status === 401) apiKey.value = "";
  } finally {
    isUploadingImage.value = false;
  }
}

function clearDiagnosisImage(): void {
  uploadedImage.value = null;
  imageUploadError.value = "";
}

function reportMarkdown(result: DiagnosisResult): string {
  const confidence = result.report.confidence?.score ?? result.confidence;
  const sources = result.report.knowledge_sources?.rag ?? [];
  return [
    `# ${result.report.crop?.label ?? "农业问题"}诊断报告`,
    "",
    `- 诊断结论：${result.decision}`,
    `- 置信度：${Math.round(confidence * 100)}%`,
    `- 风险等级：${result.report.risk ?? result.risk_level}`,
    `- Judge 模式：${result.judge_mode}`,
    `- Trace ID：${result.trace_id ?? result.report.request_id ?? "未提供"}`,
    "",
    "## 建议措施",
    ...(result.action_plan ?? []).map((item) => `- ${item}`),
    "",
    "## 知识来源",
    ...(sources.length
      ? sources.map((item) => `- ${item.title ?? item.source ?? item.id ?? "未命名来源"}`)
      : ["- 本次报告未提供 RAG 来源"]),
    "",
    ...(result.report.follow_up_questions?.length
      ? ["## 建议补充", ...result.report.follow_up_questions.map((item) => `- ${item}`)]
      : []),
  ].join("\n");
}

async function copyDiagnosis(): Promise<void> {
  if (!diagnosis.value) return;
  isCopying.value = true;
  copyMessage.value = "";
  try {
    await navigator.clipboard.writeText(reportMarkdown(diagnosis.value));
    copyMessage.value = "报告已复制到剪贴板。";
  } catch {
    copyMessage.value = "浏览器未授权剪贴板，请展开报告并手动复制。";
  } finally {
    isCopying.value = false;
  }
}

async function openDecision(item: DecisionSummary): Promise<void> {
  if (!apiKey.value) return;
  historyError.value = "";
  try {
    detail.value = await getDecision(apiKey.value, item.id);
    diagnosis.value = null;
  } catch (error) {
    historyError.value = errorMessage(error);
  }
}

async function markFeedback(feedback: "correct" | "incorrect" | "partial"): Promise<void> {
  if (!apiKey.value || !detail.value) return;
  feedbackMessage.value = "";
  try {
    detail.value = await sendFeedback(apiKey.value, detail.value.id, feedback);
    await loadHistory();
    feedbackMessage.value = "人工复核已保存。";
  } catch (error) {
    historyError.value = errorMessage(error);
  }
}

function startNewDiagnosis(): void {
  currentView.value = "diagnose";
  activeDemoId.value = "";
  diagnosis.value = null;
  detail.value = null;
  diagnosisError.value = "";
}

function showHistory(): void {
  currentView.value = "history";
  if (apiKey.value && !history.value.length) void loadHistory();
}

function changeDemo(id: string): void {
  activeDemoId.value = id;
  diagnosis.value = null;
  diagnosisError.value = "";
}

onMounted(() => {
  void refreshHealth();
});
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-lockup"><span class="brand-mark">⌁</span><div><strong>ACIS</strong><small>AGRICULTURAL INTELLIGENCE</small></div></div>
      <p class="sidebar-label">工作空间</p>
      <nav class="primary-nav" aria-label="主导航">
        <button type="button" :class="{ active: currentView === 'diagnose' }" @click="startNewDiagnosis"><span>⌖</span>诊断工作台</button>
        <button type="button" :class="{ active: currentView === 'history' }" @click="showHistory"><span>▤</span>历史记录<small>{{ apiKey ? history.length : '—' }}</small></button>
      </nav>

      <section class="sidebar-card system-card">
        <div class="sidebar-card-heading"><i :class="`state-${healthState}`"></i><strong>系统连接</strong><button type="button" aria-label="刷新系统状态" @click="refreshHealth">↻</button></div>
        <div class="system-row"><span>ACIS API</span><b :class="`text-${healthState}`">{{ healthMessage }}</b></div>
        <div class="system-row"><span>LLM Judge</span><b>{{ apiHealth ? (apiHealth.judge_configured ? '已配置' : '未配置') : '待检查' }}</b></div>
        <p>知识库状态将在每次诊断报告中按真实检索结果展示。</p>
      </section>

      <section class="sidebar-card credential-card">
        <div class="credential-heading"><span>⌑</span><div><strong>配置 API Key</strong><small>密钥仅保留在当前页面内存</small></div></div>
        <form @submit.prevent="connectApi">
          <label class="sr-only" for="api-key">本地 ACIS API Key</label>
          <input id="api-key" v-model="apiKeyDraft" type="password" autocomplete="off" placeholder="输入本地 API Key" :disabled="isConnecting" />
          <button type="submit" :disabled="isConnecting">{{ isConnecting ? '连接中…' : apiKey ? '重新连接' : '连接服务' }}</button>
        </form>
        <p v-if="connectionError" class="credential-error" role="alert">{{ connectionError }}</p>
        <p v-else-if="connectionMessage" class="credential-success" role="status">{{ connectionMessage }}</p>
        <p v-else class="credential-hint">至少 32 个 ASCII 字符；刷新页面后需重新输入。</p>
      </section>

      <div class="sidebar-footer"><span>FIELD NOTES · TRACEABLE DECISIONS</span><b>ACIS v1.0</b></div>
    </aside>

    <main class="main-panel">
      <header class="topbar"><div><span>ACIS</span><i>/</i>{{ currentView === 'diagnose' ? '工作台' : '历史记录' }}</div><span class="local-status"><i></i>本地数据 · 私有连接</span></header>
      <div v-if="healthError" class="service-warning" role="status"><strong>服务暂不可用</strong><span>{{ healthError }}</span><button type="button" @click="refreshHealth">重新检查</button></div>

      <template v-if="currentView === 'diagnose'">
        <section class="hero-card">
          <div class="hero-copy"><p class="eyebrow">AGRICULTURAL DECISION SUPPORT</p><h1>让田间症状，<br /><em>有据可循。</em></h1><p>汇集农业知识检索与多智能体分析，输出可核对的诊断依据和执行记录。</p><div class="hero-tags"><span>知识证据</span><span>鉴别分析</span><span>全过程 Trace</span></div></div>
          <div class="hero-illustration" aria-hidden="true"><span class="hero-orbit"></span><svg viewBox="0 0 180 210" fill="none"><path d="M90 184V75" stroke="#D8E7A3" stroke-width="2"/><path d="M90 129C40 128 25 98 30 43c49 0 75 27 60 84Z" fill="#C5D980"/><path d="M91 153c2-50 29-78 79-76-1 51-30 79-79 76Z" fill="#8FAF68"/><path d="M45 62c16 14 28 28 42 45m67-17c-17 14-35 29-58 48" stroke="#527550" stroke-width="2" stroke-linecap="round"/></svg><small>01 — 05<br/>Evidence to decision</small></div>
          <span class="hero-year">ACIS · 2026</span>
        </section>

        <section class="workbench-heading"><div><p class="section-kicker">DIAGNOSTIC WORKSPACE</p><h2>农业智能诊断工作台</h2></div><span>● 输入 → 检索 → 分析 → 报告</span></section>
        <div v-if="diagnosisError" class="error-banner" role="alert">{{ diagnosisError }}</div>
        <DiagnosisForm :judge-configured="Boolean(apiHealth?.judge_configured)" :is-running="isRunning" :api-key-ready="Boolean(apiKey)" :is-uploading-image="isUploadingImage" :uploaded-image-name="uploadedImage?.name ?? ''" :image-upload-error="imageUploadError" @run="submitDiagnosis" @demo-change="changeDemo" @image-select="stageDiagnosisImage" @image-remove="clearDiagnosisImage" />
        <div v-if="isRunning" class="run-progress" role="status"><i></i><div><strong>任务已接收，诊断流程运行中</strong><p>后端当前只返回完成后的 Trace；不会伪造实时阶段进度。</p></div></div>
        <ResultPanel v-if="diagnosis" :result="diagnosis" :demo="selectedDemo" :is-copying="isCopying" :copy-message="copyMessage" @copy="copyDiagnosis" @history="showHistory" />
        <div v-else-if="!isRunning" class="welcome-strip"><span>↗</span><div><strong>从一条症状描述开始</strong><p>输入作物和观察到的症状，或选择固定案例体验真实诊断流程。</p></div><small>READY WHEN YOU ARE</small></div>
      </template>

      <template v-else>
        <HistoryPanel :api-key-ready="Boolean(apiKey)" :items="history" :detail="detail" :loading="isLoadingHistory" :error="historyError" :feedback-message="feedbackMessage" @select="openDecision" @feedback="markFeedback" @new-diagnosis="startNewDiagnosis" />
      </template>

      <footer class="main-footer"><span>ACIS · 农业认知智能系统</span><span>AI 决策辅助 · 证据可追溯 · 结果需人工审慎复核</span></footer>
    </main>
  </div>
</template>
