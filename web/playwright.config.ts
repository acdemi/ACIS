import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import path from "node:path";

const repositoryRoot = path.resolve(import.meta.dirname, "..");
const evidenceDirectory = process.env.ACIS_E2E_ARTIFACT_DIR;
const ownershipToken = process.env.ACIS_E2E_OWNERSHIP_TOKEN;
if (!evidenceDirectory || !ownershipToken) throw new Error("Run E2E via npm run test:e2e to initialize isolated artifacts");
const runtimeDirectory = path.join(evidenceDirectory, "runtime-data");

const apiPortValue = process.env.ACIS_E2E_PORT || "18765";
if (!/^\d{1,5}$/.test(apiPortValue)) throw new Error("ACIS_E2E_PORT must be an integer between 1 and 65535");
const apiPort = Number(apiPortValue);
if (!Number.isInteger(apiPort) || apiPort < 1 || apiPort > 65535) {
  throw new Error("ACIS_E2E_PORT must be an integer between 1 and 65535");
}
const apiKey = "acis-e2e-local-test-key-0123456789abcdef";
const python = path.resolve(process.env.ACIS_E2E_PYTHON || path.join(
  repositoryRoot,
  process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python",
));
if (!existsSync(python)) throw new Error(`E2E Python executable does not exist: ${python}`);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  outputDir: path.join(evidenceDirectory, "test-output"),
  reporter: [
    ["list"],
    ["json", { outputFile: path.join(evidenceDirectory, "results.json") }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${apiPort}`,
    browserName: "chromium",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    viewport: { width: 1440, height: 1000 },
  },
  webServer: {
    command: `"${process.execPath}" "${path.join(import.meta.dirname, "e2e", "start-server.mjs")}"`,
    cwd: repositoryRoot,
    url: `http://127.0.0.1:${apiPort}/health`,
    timeout: 120_000,
    reuseExistingServer: false,
    env: {
      PATH: process.env.PATH || "",
      SystemRoot: process.env.SystemRoot || "",
      WINDIR: process.env.WINDIR || "",
      TEMP: process.env.TEMP || "",
      TMP: process.env.TMP || "",
      USERPROFILE: process.env.USERPROFILE || "",
      LOCALAPPDATA: process.env.LOCALAPPDATA || "",
      APPDATA: process.env.APPDATA || "",
      PYTHON_DOTENV_DISABLED: "true",
      ACIS_E2E_PYTHON: python,
      ACIS_E2E_PORT: String(apiPort),
      ACIS_API_KEY: apiKey,
      AGRI_AI_DB_PATH: path.join(runtimeDirectory, "e2e.sqlite3"),
      ACIS_IMAGE_UPLOAD_DIR: path.join(runtimeDirectory, "uploads"),
      AGRI_AI_KG_BACKEND: "memory",
      AGRI_AI_RAG_BACKEND: "memory",
      AGRI_AI_JUDGE_PROVIDER: "rules",
      AGRI_AI_JUDGE_API_KEY: "",
      AGRI_AI_PERSIST: "1",
      ACIS_E2E_ARTIFACT_DIR: evidenceDirectory,
      ACIS_E2E_RUNTIME_DIR: runtimeDirectory,
      ACIS_E2E_OWNERSHIP_TOKEN: ownershipToken,
    },
  },
  globalTeardown: "./e2e/global-teardown.mjs",
});
