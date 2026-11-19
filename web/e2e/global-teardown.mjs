import { existsSync, lstatSync, readFileSync, realpathSync, rmSync } from "node:fs";
import path from "node:path";

export default async function globalTeardown() {
  const runtimeDirectory = process.env.ACIS_E2E_RUNTIME_DIR;
  const evidenceDirectory = process.env.ACIS_E2E_ARTIFACT_DIR;
  const ownershipToken = process.env.ACIS_E2E_OWNERSHIP_TOKEN;
  if (!runtimeDirectory || !existsSync(runtimeDirectory)) return;
  if (!evidenceDirectory || !ownershipToken) throw new Error("E2E cleanup ownership metadata is missing");

  const resolvedEvidenceDirectory = realpathSync(evidenceDirectory);
  const resolvedDirectory = realpathSync(runtimeDirectory);
  const markerPath = path.join(resolvedDirectory, ".acis-e2e-owned");
  if (
    path.basename(resolvedDirectory) !== "runtime-data" ||
    path.dirname(resolvedDirectory) !== resolvedEvidenceDirectory ||
    resolvedDirectory !== path.resolve(runtimeDirectory) ||
    lstatSync(markerPath).isFile() !== true ||
    readFileSync(markerPath, "utf8") !== ownershipToken
  ) {
    throw new Error(`Refusing to remove an E2E runtime directory not created by this run: ${resolvedDirectory}`);
  }
  rmSync(resolvedDirectory, { recursive: true, force: false });
}
