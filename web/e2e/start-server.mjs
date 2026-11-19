import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(scriptDirectory, "../..");
const python = process.env.ACIS_E2E_PYTHON;
const portValue = process.env.ACIS_E2E_PORT;

if (!python || !existsSync(python)) {
  console.error("ACIS E2E Python executable is missing or unavailable.");
  process.exit(1);
}
if (!/^\d{1,5}$/.test(portValue || "")) {
  console.error("ACIS_E2E_PORT must be an integer between 1 and 65535.");
  process.exit(1);
}
const port = Number(portValue);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error("ACIS_E2E_PORT must be an integer between 1 and 65535.");
  process.exit(1);
}

const server = spawn(
  python,
  ["-m", "uvicorn", "acis.api.app:app", "--host", "127.0.0.1", "--port", String(port), "--app-dir", repositoryRoot],
  { cwd: repositoryRoot, env: process.env, stdio: "inherit", windowsHide: true },
);

let stopping = false;
const stopServer = () => {
  if (stopping) return;
  stopping = true;
  if (server.exitCode === null && server.signalCode === null) server.kill();
};

process.on("SIGINT", stopServer);
process.on("SIGTERM", stopServer);
server.once("error", (error) => {
  console.error(`Could not start the ACIS E2E API process: ${error.message}`);
  process.exitCode = 1;
});
server.once("exit", (code, signal) => {
  process.exitCode = code ?? (signal ? 1 : 0);
});
