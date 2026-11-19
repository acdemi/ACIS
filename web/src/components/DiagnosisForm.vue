<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { demoCases } from "../demoCases";

const props = defineProps<{
  judgeConfigured: boolean;
  isRunning: boolean;
  apiKeyReady: boolean;
  isUploadingImage: boolean;
  uploadedImageName: string;
  imageUploadError: string;
}>();
const emit = defineEmits<{
  run: [payload: { query: string; demoId: string; useLlmJudge: boolean; useLlmCritic: boolean }];
  demoChange: [id: string];
  imageSelect: [file: File];
  imageRemove: [];
}>();

const selectedDemoId = ref("");
const formError = ref("");
const selectedImageName = ref("");
const localImageError = ref("");
const useLlmJudge = ref(false);
const useLlmCritic = ref(false);
const form = reactive({
  crop: "",
  growthStage: "",
  variety: "",
  environment: "",
  symptoms: "",
});

const composedQuery = computed(() => {
  const symptoms = form.symptoms.trim();
  if (!symptoms) return "";
  const details = [
    form.crop && `作物：${form.crop}`,
    form.growthStage.trim() && `生育期：${form.growthStage.trim()}`,
    form.variety.trim() && `品种：${form.variety.trim()}`,
    form.environment.trim() && `环境信息：${form.environment.trim()}`,
  ].filter(Boolean);
  return details.length ? `${symptoms}\n\n补充信息：\n${details.join("\n")}` : symptoms;
});

function chooseDemo(id: string): void {
  const item = demoCases.find((candidate) => candidate.id === id);
  if (!item) return;
  selectedDemoId.value = item.id;
  Object.assign(form, { crop: "", growthStage: "", variety: "", environment: "", symptoms: item.query });
  formError.value = "";
  emit("demoChange", item.id);
}

function markCustom(): void {
  selectedDemoId.value = "";
  emit("demoChange", "");
}

function selectImage(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;

  selectedImageName.value = file.name;
  localImageError.value = "";
  formError.value = "";
  const extension = file.name.split(".").pop()?.toLowerCase();
  const supportedType = ["image/jpeg", "image/png", "image/bmp"].includes(file.type.toLowerCase());
  const supportedExtension = ["jpg", "jpeg", "png", "bmp"].includes(extension ?? "");
  if (!supportedType && !supportedExtension) {
    selectedImageName.value = "";
    localImageError.value = "图片格式仅支持 JPEG、PNG 或 BMP。";
    emit("imageRemove");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    selectedImageName.value = "";
    localImageError.value = "图片不能超过 10 MiB。";
    emit("imageRemove");
    return;
  }
  emit("imageSelect", file);
}

function removeImage(): void {
  selectedImageName.value = "";
  localImageError.value = "";
  emit("imageRemove");
}

function submit(): void {
  if (selectedImageName.value && !props.uploadedImageName) {
    formError.value = props.imageUploadError
      ? "图片上传失败，请重新选择或移除图片后再运行诊断。"
      : "图片尚未上传完成，请稍候。";
    return;
  }
  const query = composedQuery.value;
  formError.value = !query
    ? "请描述作物、症状或现场问题后再提交。"
    : query.length > 4000
      ? "输入内容超过 API 的 4000 字符限制，请精简后重试。"
      : "";
  if (formError.value) return;
  emit("run", {
    query,
    demoId: selectedDemoId.value,
    useLlmJudge: useLlmJudge.value,
    useLlmCritic: useLlmCritic.value,
  });
}
</script>

<template>
  <div class="workspace-grid">
    <section class="panel form-panel" aria-labelledby="input-title">
      <div class="panel-heading">
        <div class="panel-title-group"><span class="panel-step">01</span><div><h3 id="input-title">描述问题</h3><p>症状为必填，生育期和环境信息可选</p></div></div>
        <span class="required-mark"><i></i> 必填</span>
      </div>
      <form class="diagnosis-form" @submit.prevent="submit">
        <div class="form-grid">
          <label class="field-group"><span>作物 <small>选填</small></span><select v-model="form.crop" @change="markCustom"><option value="">自动识别</option><option value="玉米">玉米</option><option value="小麦">小麦</option><option value="番茄">番茄</option><option value="黄瓜">黄瓜</option><option value="棉花">棉花</option><option value="甜菜">甜菜</option></select></label>
          <label class="field-group"><span>生育期 <small>选填</small></span><input v-model="form.growthStage" type="text" placeholder="如：拔节期、抽穗期" @input="markCustom" /></label>
          <label class="field-group field-span"><span>品种与环境 <small>选填</small></span><input v-model="form.variety" type="text" placeholder="品种、温湿度、近期降雨或栽培条件" @input="markCustom" /><input v-model="form.environment" type="text" placeholder="补充其他现场观察（可选）" @input="markCustom" /></label>
          <label class="field-group field-span"><span>症状描述 <b>*</b></span><textarea v-model="form.symptoms" rows="5" maxlength="4000" aria-label="症状描述" placeholder="请描述作物、受害部位、病斑形态、颜色、分布，以及近期变化。" @input="markCustom"></textarea><span class="field-meta"><span>描述越具体，越有助于鉴别分析</span><span>{{ form.symptoms.length }} / 4000</span></span></label>
          <label class="field-group field-span"><span>病株图片 <small>选填 · JPEG / PNG / BMP，最大 10 MiB</small></span><input id="diagnosis-image" class="image-input" type="file" accept="image/jpeg,image/png,image/bmp,.jpg,.jpeg,.png,.bmp" :disabled="props.isRunning || props.isUploadingImage || !props.apiKeyReady" @change="selectImage" /><span v-if="!props.apiKeyReady" class="field-meta">连接 API 后可上传图片。</span></label>
          <div v-if="selectedImageName" class="image-upload-feedback field-span" role="status"><span v-if="props.isUploadingImage">正在上传：{{ selectedImageName }}</span><span v-else-if="props.uploadedImageName">已上传：{{ props.uploadedImageName }}</span><span v-else>待处理：{{ selectedImageName }}</span><button type="button" :disabled="props.isUploadingImage" @click="removeImage">移除</button></div>
          <p v-if="localImageError || props.imageUploadError" class="form-error field-span" role="alert">{{ localImageError || props.imageUploadError }}</p>
        </div>
        <p v-if="formError" class="form-error" role="alert">{{ formError }}</p>
        <div class="form-options">
          <label class="switch-row" :class="{ disabled: !props.judgeConfigured }"><input v-model="useLlmJudge" type="checkbox" :disabled="!props.judgeConfigured" /><span class="switch-track"></span><span>使用 LLM Judge <small>{{ props.judgeConfigured ? '可选' : '服务端未配置' }}</small></span></label>
          <label class="switch-row" :class="{ disabled: !props.judgeConfigured }"><input v-model="useLlmCritic" type="checkbox" :disabled="!props.judgeConfigured" /><span class="switch-track"></span><span>启用 Critic <small>{{ props.judgeConfigured ? '可选' : '服务端未配置' }}</small></span></label>
        </div>
        <div class="form-actions"><button class="submit-button" type="submit" :disabled="props.isRunning || props.isUploadingImage"><span>{{ props.isRunning ? '诊断运行中…' : props.isUploadingImage ? '图片上传中…' : '运行诊断' }}</span><span class="submit-arrow">↗</span></button><span class="form-footnote">结果由当前 API 实际执行生成</span></div>
      </form>
    </section>

    <aside class="panel demo-panel" aria-labelledby="demo-title">
      <div class="panel-heading"><div class="panel-title-group"><span class="demo-spark">✳</span><div><h3 id="demo-title">快速体验</h3><p>选择固定案例填入诊断表单</p></div></div><span class="demo-chip">DEMO</span></div>
      <div class="demo-list"><button v-for="item in demoCases" :key="item.id" class="demo-case" :class="{ selected: selectedDemoId === item.id }" type="button" :data-query="item.query" @click="chooseDemo(item.id)"><span class="demo-case-icon" :class="`crop-${item.crop_code}`">{{ item.crop_code === 'wheat' ? '麦' : '玉' }}</span><span class="demo-case-copy"><strong>{{ item.title }}</strong><small>{{ item.focus }}</small></span><span class="demo-case-arrow">↗</span></button></div>
      <div class="demo-notice"><span class="notice-mark">!</span><div><strong>DEMO / FIXTURE MODE</strong><p>{{ selectedDemoId ? '固定案例输入；结果由当前 API 实际生成，不是预存答案。' : '选择案例可快速填入示例问题。提交后仍调用当前诊断服务。' }}</p></div></div>
      <div class="support-note"><span>↳</span><p>图片将交由后端 Vision Agent；默认视觉路径为 Mock，实际识别能力需按模型配置单独验证。</p></div>
    </aside>
  </div>
</template>
