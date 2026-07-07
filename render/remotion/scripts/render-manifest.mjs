#!/usr/bin/env node
/**
 * Render ReclawAudit MP4 from reclaw.video_manifest JSON.
 * Usage: node scripts/render-manifest.mjs <manifest.json> [output.mp4]
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const manifestPath = resolve(process.argv[2] || resolve(root, "../../data/manifests/gibson/manifest_gibson.json"));
const outPath = resolve(process.argv[3] || resolve(root, "out/reclaw-audit.mp4"));
const manifestJson = readFileSync(manifestPath, "utf8");

mkdirSync(dirname(outPath), { recursive: true });

execFileSync(
  "npx",
  ["remotion", "render", "src/index.ts", "ReclawAudit", outPath, `--props=${manifestJson}`],
  { stdio: "inherit", cwd: root }
);

console.log(`[+] Rendered ${outPath}`);