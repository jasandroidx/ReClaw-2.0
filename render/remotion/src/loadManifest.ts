import type {
  AnomalyData,
  HHVCTAScene,
  RawManifest,
  ReclawCompositionProps,
  RenderMode,
} from "./types";

const DEFAULT_FPS = 30;
const CLASSIC_DURATION_S = 16;
const HHVCTA_DURATION_S = 60;

function parseDollarAmount(text: string | undefined): number {
  if (!text) return 0;
  const m = text.match(/\$?([\d,]+(?:\.\d+)?)/);
  if (!m) return 0;
  return parseFloat(m[1].replace(/,/g, "")) || 0;
}

function buildChartData(manifest: RawManifest): AnomalyData[] {
  const finding = manifest.atomic_finding;
  const amount = parseDollarAmount(finding?.data_point);
  const category = finding?.category ?? "flag";
  const baseline = Math.max(amount * 0.35, 25_000);

  if (category.includes("benford")) {
    return [
      { label: "1", value: 28, isAnomaly: false },
      { label: "2", value: 18, isAnomaly: false },
      { label: "3", value: 14, isAnomaly: false },
      { label: "4", value: 11, isAnomaly: false },
      { label: "5", value: 22, isAnomaly: true },
      { label: "6", value: 4, isAnomaly: false },
      { label: "7", value: 2, isAnomaly: false },
      { label: "8", value: 1, isAnomaly: false },
    ];
  }

  return [
    { label: "Median", value: baseline, isAnomaly: false },
    { label: "Peer", value: baseline * 1.4, isAnomaly: false },
    { label: "Flagged", value: amount || baseline * 2.2, isAnomaly: true },
    { label: "Budget", value: baseline * 3.5, isAnomaly: false },
  ];
}

function sceneFromBeat(
  hhvcta: string,
  beat: { start_s?: number; end_s?: number; text?: string; on_screen?: string },
  onScreenFallback: string[]
): HHVCTAScene {
  const start = beat.start_s ?? 0;
  const end = beat.end_s ?? start + 3;
  const bursts = beat.on_screen
    ? beat.on_screen.split(/[·|]/).map((s) => s.trim()).filter(Boolean).slice(0, 3)
    : onScreenFallback;
  return {
    scene: hhvcta.toUpperCase(),
    hhvcta,
    start_s: start,
    end_s: end,
    duration_s: end - start,
    spoken_script: beat.text ?? "",
    on_screen_text: bursts.length ? bursts : onScreenFallback,
  };
}

function scenesFromManifest(manifest: RawManifest): HHVCTAScene[] {
  const scriptBody =
    manifest.script_body ??
    manifest.scribe?.script_body ??
    null;

  if (scriptBody?.length) {
    return scriptBody;
  }

  if (manifest.beats) {
    const order = ["hook", "hint", "value", "credibility", "takeaway", "action"] as const;
    const defaults: Record<string, string[]> = {
      hook: ["PUBLIC RECORD"],
      hint: ["PATTERN FOUND"],
      value: ["THE DATA"],
      credibility: ["SOURCE"],
      takeaway: ["YOUR MONEY"],
      action: ["TAG THEM"],
    };
    return order
      .filter((k) => manifest.beats?.[k])
      .map((k) => sceneFromBeat(k, manifest.beats![k]!, defaults[k] ?? ["RECLAW"]));
  }

  if (manifest.scenes?.length) {
    let cursor = 0;
    return manifest.scenes.map((s) => {
      const dur = s.duration_seconds ?? 3;
      const scene: HHVCTAScene = {
        scene: (s.hhvcta ?? "scene").toUpperCase(),
        hhvcta: s.hhvcta ?? "scene",
        start_s: cursor,
        end_s: cursor + dur,
        duration_s: dur,
        spoken_script: s.spoken_script ?? "",
        on_screen_text: s.on_screen_text ?? (s.text_overlay ? [s.text_overlay] : ["RECLAW"]),
      };
      cursor += dur;
      return scene;
    });
  }

  return [];
}

function copyField(
  manifest: RawManifest,
  key: string,
  scenes: HHVCTAScene[],
  fallback = ""
): string {
  const scribeCopy = manifest.scribe?.copy?.[key];
  if (scribeCopy) return scribeCopy;
  const scene = scenes.find((s) => s.hhvcta === key);
  if (scene?.spoken_script) return scene.spoken_script;
  const beat = manifest.beats?.[key];
  if (beat?.text) return beat.text;
  return fallback;
}

function resolveRenderMode(manifest: RawManifest, scenes: HHVCTAScene[]): RenderMode {
  if (manifest.metadata?.render_mode === "hhvcta") return "hhvcta";
  if (manifest.metadata?.render_mode === "classic") return "classic";
  const scriptBody = manifest.script_body ?? manifest.scribe?.script_body;
  if (scriptBody && scriptBody.length >= 4) return "hhvcta";
  if (scenes.length >= 4 && scenes.some((s) => s.end_s >= 45)) return "hhvcta";
  return "classic";
}

export function loadManifest(manifest: RawManifest): ReclawCompositionProps {
  const scenes = scenesFromManifest(manifest);
  const city = manifest.metadata?.target ?? manifest.county ?? "County";
  const fps = manifest.metadata?.fps ?? DEFAULT_FPS;
  const renderMode = resolveRenderMode(manifest, scenes);

  const hookText =
    manifest.hook_text ??
    manifest.scribe?.hook_text ??
    copyField(manifest, "hook", scenes, "Public records show a pattern worth questioning.");

  const valueText = copyField(
    manifest,
    "value",
    scenes,
    manifest.atomic_finding?.description ?? "The flagged line is in the public checkbook."
  );

  const durationS =
    renderMode === "hhvcta"
      ? manifest.metadata?.duration_s ??
        (scenes.length ? Math.max(...scenes.map((s) => s.end_s)) : HHVCTA_DURATION_S)
      : CLASSIC_DURATION_S;

  return {
    city,
    hookText,
    valueText,
    sourceText: manifest.atomic_finding?.provenance ?? "Indiana Gateway",
    chartData: buildChartData(manifest),
    renderMode,
    hintText: copyField(manifest, "hint", scenes, "I ran the math on the official records."),
    credibilityText: copyField(
      manifest,
      "credibility",
      scenes,
      `Source: ${manifest.atomic_finding?.provenance ?? "Indiana Gateway public records"}`
    ),
    takeawayText: copyField(
      manifest,
      "takeaway",
      scenes,
      "It's your tax money. Fair questions deserve answers on the record."
    ),
    actionText: copyField(
      manifest,
      "action",
      scenes,
      "Tag your local officials and ask them to explain this on the record."
    ),
    disclaimer:
      manifest.disclaimer ??
      "Patterns in public financial records only. Not an allegation of crime or wrongdoing.",
    scenes,
    fps,
    durationInFrames: Math.round(durationS * fps),
  };
}