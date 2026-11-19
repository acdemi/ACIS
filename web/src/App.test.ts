import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.vue";

const demoQueries = [
  "玉米下部叶片出现长梭形灰绿色至灰褐色病斑，湿度高时病斑快速扩大，请诊断。",
  "小麦叶片出现黄色粉状小疱，沿叶脉排列成条带；请与叶锈病鉴别。",
  "玉米长势不好，叶片有点发黄，具体原因不清楚。",
];
const apiKey = "test-api-key-0123456789abcdef0123456789";
const diagnosisPayload = {
  decision: "玉米大斑病",
  confidence: 0.84,
  risk_level: "medium",
  judge_mode: "rules",
  need_human_review: false,
  action_plan: ["记录病斑变化并咨询当地植保人员。"],
  traces: [{ agent: "RAG", claim: "检索到相关知识", execution: { status: "success", mode: "memory", duration_ms: 12 } }],
  report: {
    crop: { code: "maize", label: "玉米" },
    confidence: { score: 0.84, band: "high", meaning: "依据本次证据聚合" },
    evidence: ["下部叶片长梭形病斑"],
    knowledge_sources: { rag_status: "success", rag: [{ title: "玉米大斑病识别", backend: "memory", score: 0.92, text: "长梭形灰褐色病斑。" }], kg: { backend: "memory" } },
    risk: "medium",
    request_id: "trace-demo-001",
    duration_ms: 123.4,
  },
  trace_id: "trace-demo-001",
  trace: {
    trace_id: "trace-demo-001",
    events: [
      { stage: "request", timestamp: "2026-01-01T00:00:00Z", payload: { status: "success" } },
      { stage: "memory", timestamp: "2026-01-01T00:00:01Z", payload: { status: "success" } },
      { stage: "experts", timestamp: "2026-01-01T00:00:02Z", payload: { status: "success" } },
      { stage: "judge", timestamp: "2026-01-01T00:00:03Z", payload: { status: "success" } },
    ],
  },
};

function response(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

describe("ACIS Vue workbench", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/health") {
          return response({ status: "ok", judge_configured: false });
        }
        if (url === "/images") return response({ image_path: "/tmp/acis-upload/leaf.png" });
        if (url === "/decisions?limit=50") return response([]);
        if (url === "/diagnose") return response(diagnosisPayload);
        return response({ detail: "not found" }, 404);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a clear welcome and does not claim unmeasured metrics", async () => {
    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.text()).toContain("农业智能诊断工作台");
    expect(wrapper.text()).toContain("配置 API Key");
    expect(wrapper.text()).not.toMatch(/准确率\s*\d|诊断成功率/);
  });

  it.each(demoQueries)("loads fixed demo input %s", async (query) => {
    const wrapper = mount(App);
    await flushPromises();
    const target = wrapper.findAll("button").find((button) =>
      button.element.getAttribute("data-query") === query,
    );

    expect(target, `demo case input missing: ${query}`).toBeTruthy();
    await target!.trigger("click");
    await flushPromises();

    expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe(query);
    expect(wrapper.text()).toContain("DEMO / FIXTURE MODE");
  });

  it("sends a selected case to the protected API and renders its returned report and trace", async () => {
    const wrapper = mount(App);
    await flushPromises();
    await wrapper.get("#api-key").setValue(apiKey);
    await wrapper.get(".credential-card form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("连接成功");
    await wrapper.findAll("button").find((button) => button.element.getAttribute("data-query") === demoQueries[0])!.trigger("click");
    await flushPromises();
    await wrapper.get(".diagnosis-form").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("玉米大斑病");
    expect(wrapper.text()).toContain("玉米大斑病识别");
    expect(wrapper.text()).toContain("DEMO / FIXTURE MODE");
    expect(wrapper.text()).toContain("trace-demo-001");
    expect(wrapper.text()).toContain("已记录 · 1");

    const diagnoseCall = vi.mocked(fetch).mock.calls.find(([input]) => String(input) === "/diagnose");
    expect(diagnoseCall).toBeTruthy();
    expect(JSON.parse(String(diagnoseCall?.[1]?.body)).query).toBe(demoQueries[0]);
    expect(new Headers(diagnoseCall?.[1]?.headers).get("X-API-Key")).toBe(apiKey);
  });

  it("uploads an image with API authentication and sends its staged path to diagnosis", async () => {
    const wrapper = mount(App);
    await flushPromises();
    await wrapper.get("#api-key").setValue(apiKey);
    await wrapper.get(".credential-card form").trigger("submit");
    await flushPromises();

    const image = new File(["image bytes"], "leaf.png", { type: "image/png" });
    const imageInput = wrapper.get("#diagnosis-image").element as HTMLInputElement;
    Object.defineProperty(imageInput, "files", { configurable: true, value: [image] });
    await wrapper.get("#diagnosis-image").trigger("change");
    await flushPromises();

    expect(wrapper.text()).toContain("leaf.png");
    const uploadCall = vi.mocked(fetch).mock.calls.find(([input]) => String(input) === "/images");
    expect(uploadCall).toBeTruthy();
    expect(uploadCall?.[1]?.body).toBe(image);
    expect(new Headers(uploadCall?.[1]?.headers).get("X-API-Key")).toBe(apiKey);
    expect(new Headers(uploadCall?.[1]?.headers).get("Content-Type")).toBe("image/png");

    await wrapper.findAll("button").find((button) => button.element.getAttribute("data-query") === demoQueries[0])!.trigger("click");
    await flushPromises();
    await wrapper.get(".diagnosis-form").trigger("submit");
    await flushPromises();

    const diagnoseCall = vi.mocked(fetch).mock.calls.find(([input]) => String(input) === "/diagnose");
    expect(JSON.parse(String(diagnoseCall?.[1]?.body)).image_path).toBe("/tmp/acis-upload/leaf.png");
  });
});
