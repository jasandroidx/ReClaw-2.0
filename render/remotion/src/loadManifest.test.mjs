/**
 * Quick smoke test for loadManifest (run: node src/loadManifest.test.mjs)
 * Uses ts-node alternative: inline duplicate of key logic for CI without tsc
 */
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const manifest = JSON.parse(
  readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), "../../../data/manifests/gibson/manifest_gibson.json"),
    "utf8"
  )
);

const city = manifest.metadata?.target ?? manifest.county;
const hasHook = manifest.beats?.hook?.text || manifest.scenes?.[0]?.spoken_script;

if (!city || !hasHook) {
  console.error("FAIL: manifest missing city or hook");
  process.exit(1);
}

const mode = manifest.script_body?.length >= 4 ? "hhvcta" : "classic";
console.log("OK: Gibson manifest —", city, "— mode:", mode, "—", String(hasHook).slice(0, 50));