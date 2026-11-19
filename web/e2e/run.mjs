import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import { existsSync, lstatSync, mkdirSync, readFileSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const webDirectory = path.resolve(scriptDirectory, "..");
const repositoryRoot = path.resolve(webDirectory, "..");
const runId = `${new Date().toISOString().replace(/\D/g, "").slice(0, 14)}-${randomUUID()}`;
const requestedArtifactDirectory = process.env.ACIS_E2E_ARTIFACT_DIR;
const artifactBaseDirectory = path.resolve(requestedArtifactDirectory || path.join(repositoryRoot, "reports"));
const evidenceDirectory = path.join(
  artifactBaseDirectory,
  requestedArtifactDirectory ? `run-${runId}` : `web-e2e-${runId}`,
);
const runtimeDirectory = path.join(evidenceDirectory, "runtime-data");
const ownershipToken = randomUUID();
const apiKey = "acis-e2e-local-test-key-0123456789abcdef";
const portValue = process.env.ACIS_E2E_PORT || "18765";
if (!/^\d{1,5}$/.test(portValue)) throw new Error("ACIS_E2E_PORT must be an integer between 1 and 65535");
const port = Number(portValue);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error("ACIS_E2E_PORT must be an integer between 1 and 65535");
}

const python = path.resolve(process.env.ACIS_PYTHON || path.join(
  repositoryRoot,
  process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python",
));
if (!existsSync(python)) throw new Error(`E2E Python executable does not exist: ${python}`);
const playwrightCli = path.join(webDirectory, "node_modules", "@playwright", "test", "cli.js");
if (!existsSync(playwrightCli)) throw new Error("Playwright is not installed. Run npm ci in the web directory first.");

mkdirSync(artifactBaseDirectory, { recursive: true });
mkdirSync(evidenceDirectory);
mkdirSync(runtimeDirectory);
writeFileSync(path.join(runtimeDirectory, ".acis-e2e-owned"), ownershipToken, { flag: "wx" });

const childEnvironment = {
  ...process.env,
  ACIS_E2E_ARTIFACT_DIR: evidenceDirectory,
  ACIS_E2E_RUNTIME_DIR: runtimeDirectory,
  ACIS_E2E_OWNERSHIP_TOKEN: ownershipToken,
  ACIS_E2E_PYTHON: python,
  ACIS_E2E_PORT: String(port),
  ACIS_API_KEY: apiKey,
  AGRI_AI_DB_PATH: path.join(runtimeDirectory, "e2e.sqlite3"),
  ACIS_IMAGE_UPLOAD_DIR: path.join(runtimeDirectory, "uploads"),
  AGRI_AI_KG_BACKEND: "memory",
  AGRI_AI_RAG_BACKEND: "memory",
  AGRI_AI_JUDGE_PROVIDER: "rules",
  AGRI_AI_JUDGE_API_KEY: "",
  AGRI_AI_PERSIST: "1",
  PYTHON_DOTENV_DISABLED: "true",
};

let exitCode = 1;
try {
  console.log(`[ACIS E2E] Artifacts: ${evidenceDirectory}`);
  const child = spawn(process.execPath, [playwrightCli, "test", ...process.argv.slice(2)], {
    cwd: webDirectory,
    env: childEnvironment,
    stdio: "inherit",
    windowsHide: true,
  });
  const forwardSignal = (signal) => {
    if (child.exitCode === null && child.signalCode === null) child.kill(signal);
  };
  process.on("SIGINT", () => forwardSignal("SIGINT"));
  process.on("SIGTERM", () => forwardSignal("SIGTERM"));
  exitCode = await new Promise((resolve) => {
    child.once("error", (error) => {
      console.error(`[ACIS E2E] Failed to start Playwright: ${error.message}`);
      resolve(1);
    });
    child.once("exit", (code, signal) => resolve(code ?? (signal ? 1 : 0)));
  });
} catch (error) {
  console.error(`[ACIS E2E] ${error.message}`);
  exitCode = 1;
} finally {
  if (existsSync(runtimeDirectory)) {
    try {
      const resolvedEvidence = realpathSync(evidenceDirectory);
      const resolvedRuntime = realpathSync(runtimeDirectory);
      const marker = path.join(resolvedRuntime, ".acis-e2e-owned");
      if (
        path.dirname(resolvedRuntime) !== resolvedEvidence ||
        path.basename(resolvedRuntime) !== "runtime-data" ||
        resolvedRuntime !== path.resolve(runtimeDirectory) ||
        !lstatSync(marker).isFile() ||
        readFileSync(marker, "utf8") !== ownershipToken
      ) {
        throw new Error("Runtime data ownership check failed; directory was preserved.");
      }
      rmSync(resolvedRuntime, { recursive: true, force: false });
    } catch (error) {
      console.error(`[ACIS E2E] Cleanup refused: ${error.message}`);
      if (exitCode === 0) exitCode = 1;
    }
  }
}

process.exitCode = exitCode;
