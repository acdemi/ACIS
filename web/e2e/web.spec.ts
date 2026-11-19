import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";

const apiKey = "acis-e2e-local-test-key-0123456789abcdef";
const evidenceDirectory = process.env.ACIS_E2E_ARTIFACT_DIR;
type BrowserDiagnostics = { consoleErrors: string[]; pageErrors: string[]; requestFailures: string[]; httpErrors: string[] };
const diagnostics = new WeakMap<Page, BrowserDiagnostics>();
const expectedRequestFailurePages = new WeakSet<Page>();
const expectedHttpStatuses = new WeakMap<Page, Set<number>>();
const tinyPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAAE0lEQVR4nGO0a3FngAEmOAsvBwA0vQERaGUntgAAAABJRU5ErkJggg==",
  "base64",
);

if (!evidenceDirectory) throw new Error("ACIS_E2E_ARTIFACT_DIR was not configured");
mkdirSync(evidenceDirectory, { recursive: true });

test.beforeEach(async ({ page }) => {
  const events: BrowserDiagnostics = { consoleErrors: [], pageErrors: [], requestFailures: [], httpErrors: [] };
  diagnostics.set(page, events);
  expectedHttpStatuses.set(page, new Set());
  page.on("console", (message) => {
    if (message.type() === "error") events.consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => events.pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    events.requestFailures.push(`${request.method()} ${request.url()} :: ${request.failure()?.errorText ?? "failed"}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) events.httpErrors.push(`${response.status()} ${response.url()}`);
  });
});

test.afterEach(async ({ page }, testInfo) => {
  const events = diagnostics.get(page);
  if (events) {
    expect(events.pageErrors, "uncaught browser errors").toEqual([]);
    const allowedStatuses = expectedHttpStatuses.get(page)!;
    for (const status of allowedStatuses) {
      expect(events.httpErrors.some((entry) => entry.startsWith(`${status} `)), `expected HTTP ${status}`).toBe(true);
    }
    const unexpectedConsoleErrors = events.consoleErrors.filter(
      (message) => {
        if (/^Failed to load resource: net::ERR_(FAILED|CONNECTION_REFUSED|CONNECTION_RESET)$/.test(message)) return false;
        const httpStatus = message.match(/server responded with a status of (\d{3})/);
        return !httpStatus || !allowedStatuses.has(Number(httpStatus[1]));
      },
    );
    expect(unexpectedConsoleErrors, "unexpected browser console errors").toEqual([]);
    if (!expectedRequestFailurePages.has(page)) {
      expect(events.requestFailures, "unexpected failed browser requests").toEqual([]);
    }
    await testInfo.attach("browser-network-and-console.json", {
      body: Buffer.from(JSON.stringify(events, null, 2)),
      contentType: "application/json",
    });
  }
});

async function capture(page: Page, testInfo: TestInfo, filename: string): Promise<void> {
  const screenshotPath = path.join(evidenceDirectory!, filename);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await testInfo.attach(filename, { path: screenshotPath, contentType: "image/png" });
}

async function connect(page: Page, key = apiKey): Promise<void> {
  await page.locator("#api-key").fill(key);
  await page.getByRole("button", { name: /连接服务|重新连接/ }).click();
}

async function runDemo(page: Page, index: number): Promise<void> {
  await page.locator(".demo-case").nth(index).click();
  await page.getByRole("button", { name: "运行诊断" }).click();
  await expect(page.locator("#result-title")).toBeVisible({ timeout: 110_000 });
}

test("loads production shell and assets, then survives refresh", async ({ page }, testInfo) => {
  const assetResponses: number[] = [];
  page.on("response", (response) => {
    if (new URL(response.url()).pathname.startsWith("/assets/")) assetResponses.push(response.status());
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "农业智能诊断工作台" })).toBeVisible();
  await expect(page.getByText("API 已连接", { exact: true })).toBeVisible();
  await expect.poll(() => assetResponses.length).toBeGreaterThan(0);
  expect(assetResponses.every((status) => status === 200)).toBe(true);

  await page.reload();
  await expect(page.getByRole("heading", { name: "农业智能诊断工作台" })).toBeVisible();
  await expect(page.getByText("API 已连接", { exact: true })).toBeVisible();
  const events = diagnostics.get(page)!;
  expect(events.pageErrors).toEqual([]);
  expect(events.requestFailures).toEqual([]);
  await capture(page, testInfo, "01-home-and-refresh.png");
});

test("auto-connects with a launcher key and restores the current tab after refresh", async ({ page }) => {
  await page.goto("/#acis_key=" + apiKey);
  await expect(page.getByText("连接成功", { exact: false })).toBeVisible();
  expect(new URL(page.url()).hash).toBe("");

  await page.reload();
  await expect(page.getByText("连接成功", { exact: false })).toBeVisible();
  await expect(page.locator("#api-key")).toHaveValue("");
});

test("recovers from a controlled API outage injected by browser routing", async ({ page }, testInfo) => {
  expectedRequestFailurePages.add(page);
  await page.route("**/health", (route) => route.abort("failed"));
  await page.goto("/");
  await expect(page.getByText("API 暂不可用", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("无法连接 ACIS API，请检查服务是否启动。")).toBeVisible();
  await capture(page, testInfo, "02-api-unavailable.png");

  await page.unroute("**/health");
  await page.getByRole("button", { name: "刷新系统状态" }).click();
  await expect(page.getByText("API 已连接", { exact: true })).toBeVisible();
});

test("rejects a wrong API key and reconnects with the correct key", async ({ page }, testInfo) => {
  expectedHttpStatuses.get(page)!.add(401);
  await page.goto("/");
  await connect(page, "wrong-e2e-api-key-0123456789abcdef0123456789");
  await expect(page.getByRole("alert")).toContainText("API Key 无效");
  await capture(page, testInfo, "03-invalid-api-key.png");

  await connect(page);
  await expect(page.getByRole("status").filter({ hasText: "连接成功" })).toBeVisible();
});

test("shows an empty history state from a browser-intercepted API response", async ({ page }, testInfo) => {
  await page.route("**/decisions**", async (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.pathname === "/decisions" && requestUrl.searchParams.get("limit") === "50") {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
      return;
    }
    await route.continue();
  });
  await page.goto("/");
  await connect(page);
  await expect(page.getByRole("status").filter({ hasText: "连接成功" })).toBeVisible();
  await page.getByRole("button", { name: /历史记录/ }).click();
  await expect(page.getByText("暂无历史诊断")).toBeVisible();
  await capture(page, testInfo, "04-empty-history.png");
});

test("shows upload progress while a browser-intercepted response is pending", async ({ page }, testInfo) => {
  await page.goto("/");
  await connect(page);
  await expect(page.getByRole("status").filter({ hasText: "连接成功" })).toBeVisible();
  await page.route("**/images", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 700));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ image_path: "/e2e/staged.png", size_bytes: tinyPng.length, content_type: "image/png" }),
    });
  });
  await page.locator("#diagnosis-image").setInputFiles({
    name: "e2e-leaf.png",
    mimeType: "image/png",
    buffer: tinyPng,
  });
  await expect(page.getByRole("status").filter({ hasText: "正在上传：e2e-leaf.png" })).toBeVisible();
  await capture(page, testInfo, "05-upload-in-progress.png");
  await expect(page.getByRole("status").filter({ hasText: "已上传：e2e-leaf.png" })).toBeVisible();
});

test("uploads an image and runs fixture-mode maize diagnosis through the real API", async ({ page }, testInfo) => {
  await page.goto("/");
  await connect(page);
  await expect(page.getByRole("status").filter({ hasText: "连接成功" })).toBeVisible();
  await page.locator(".demo-case").nth(0).click();

  const uploadResponsePromise = page.waitForResponse((response) => response.url().endsWith("/images"));
  await page.locator("#diagnosis-image").setInputFiles({
    name: "e2e-leaf.png",
    mimeType: "image/png",
    buffer: tinyPng,
  });
  const uploadResponse = await uploadResponsePromise;
  expect(uploadResponse.status()).toBe(200);
  const uploaded = await uploadResponse.json() as { image_path: string; size_bytes: number; content_type: string };
  expect(uploaded.image_path).toMatch(/\.png$/i);
  expect(uploaded.size_bytes).toBeGreaterThan(0);
  await expect(page.getByRole("status").filter({ hasText: "已上传：e2e-leaf.png" })).toBeVisible();
  await expect(page.locator(".support-note")).toContainText("Mock");

  const diagnosisRequestPromise = page.waitForRequest((request) => request.url().endsWith("/diagnose"));
  await page.getByRole("button", { name: "运行诊断" }).click();
  const diagnosisRequest = await diagnosisRequestPromise;
  expect(diagnosisRequest.postDataJSON().image_path).toBe(uploaded.image_path);
  await expect(page.locator("#result-title")).toBeVisible({ timeout: 110_000 });
  await expect(page.locator(".fixture-badge")).toHaveText("DEMO / FIXTURE MODE");
  await expect(page.locator(".trace-card")).toContainText("执行 Trace");
  await expect(page.locator(".report-card").filter({ hasText: "知识来源" })).toBeVisible();
  await capture(page, testInfo, "05-maize-diagnosis-with-upload.png");

  await page.getByRole("button", { name: /查看历史记录/ }).last().click();
  await expect(page.locator(".history-item").first()).toBeVisible();
  await page.locator(".history-item").first().click();
  await expect(page.locator(".history-detail-panel")).toContainText("执行 Trace");
  await page.getByText("展开 Trace 事件").click();
  await expect(page.locator(".history-detail-panel pre").last()).toBeVisible();
  await capture(page, testInfo, "06-history-detail-and-trace.png");
});

test("runs the wheat differential fixture through the real API path", async ({ page }, testInfo) => {
  await page.goto("/");
  await connect(page);
  await expect(page.getByRole("status").filter({ hasText: "连接成功" })).toBeVisible();
  await runDemo(page, 1);
  await expect(page.locator(".fixture-badge")).toHaveText("DEMO / FIXTURE MODE");
  await expect(page.locator(".result-section")).toContainText("鉴别");
  await expect(page.locator(".trace-card")).toContainText("Judge 评估");
  await capture(page, testInfo, "07-wheat-differential.png");
});

test("renders the information-insufficient abstention through the real API path", async ({ page }, testInfo) => {
  await page.goto("/");
  await connect(page);
  await expect(page.getByRole("status").filter({ hasText: "连接成功" })).toBeVisible();
  await runDemo(page, 2);
  await expect(page.locator(".verdict-content")).toContainText("证据不足");
  await expect(page.locator(".review-warning")).toBeVisible();
  await expect(page.locator(".follow-up-box")).toBeVisible();
  await capture(page, testInfo, "08-information-insufficient-abstention.png");
});

test("shows a simulated HTTP 500 diagnosis error without a false result", async ({ page }, testInfo) => {
  expectedHttpStatuses.get(page)!.add(500);
  await page.goto("/");
  await connect(page);
  await expect(page.getByRole("status").filter({ hasText: "连接成功" })).toBeVisible();
  await page.route("**/diagnose", (route) => route.fulfill({
    status: 500,
    contentType: "application/json",
    body: JSON.stringify({ detail: "E2E simulated server failure" }),
  }));
  await page.locator(".demo-case").first().click();
  await page.getByRole("button", { name: "运行诊断" }).click();
  await expect(page.getByRole("alert")).toContainText("E2E simulated server failure");
  await expect(page.locator("#result-title")).toHaveCount(0);
  await capture(page, testInfo, "09-http-500-recovery-state.png");
});

test("shows an upload failure and does not submit diagnosis", async ({ page }, testInfo) => {
  let diagnosisRequests = 0;
  expectedHttpStatuses.get(page)!.add(500);
  await page.goto("/");
  await connect(page);
  await expect(page.getByRole("status").filter({ hasText: "连接成功" })).toBeVisible();
  await page.route("**/diagnose", async (route) => {
    diagnosisRequests += 1;
    await route.continue();
  });
  await page.route("**/images", (route) => route.fulfill({
    status: 500,
    contentType: "application/json",
    body: JSON.stringify({ detail: "E2E simulated upload failure" }),
  }));
  await page.locator("#diagnosis-image").setInputFiles({
    name: "e2e-leaf.png",
    mimeType: "image/png",
    buffer: tinyPng,
  });
  await expect(page.getByRole("alert")).toContainText("E2E simulated upload failure");
  expect(diagnosisRequests).toBe(0);
  expect(diagnostics.get(page)!.httpErrors.some((entry) => entry.startsWith("500 "))).toBe(true);
  await capture(page, testInfo, "10-upload-failure.png");
});

test("returns a real 404 for an invalid decision ID", async ({ page }, testInfo) => {
  expectedHttpStatuses.get(page)!.add(404);
  await page.goto("/");
  const result = await page.evaluate(async (key) => {
    const response = await fetch("/decisions/2147483647", { headers: { "X-API-Key": key } });
    return { status: response.status, payload: await response.json() };
  }, apiKey);
  expect(result.status).toBe(404);
  expect(result.payload.detail).toBe("decision not found");
  await capture(page, testInfo, "11-invalid-decision-id.png");
});
