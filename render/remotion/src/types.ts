export interface AnomalyData {
  label: string;
  value: number;
  isAnomaly: boolean;
}

export interface HHVCTAScene {
  scene: string;
  hhvcta: string;
  start_s: number;
  end_s: number;
  duration_s: number;
  spoken_script: string;
  on_screen_text: string[];
  visual_directives?: string[];
}

export type RenderMode = "classic" | "hhvcta";

export interface ReclawCompositionProps {
  city: string;
  hookText: string;
  valueText: string;
  sourceText: string;
  chartData: AnomalyData[];
  /** classic = 16s 3-scene (Hook / Value+Chart / CTA). hhvcta = full 60s script_body. */
  renderMode: RenderMode;
  hintText?: string;
  credibilityText?: string;
  takeawayText?: string;
  actionText?: string;
  disclaimer?: string;
  scenes: HHVCTAScene[];
  fps: number;
  durationInFrames: number;
}

export interface RawManifest {
  schema?: string;
  county?: string;
  hook_text?: string;
  script_body?: HHVCTAScene[];
  scribe?: { hook_text?: string; script_body?: HHVCTAScene[]; copy?: Record<string, string> };
  metadata?: {
    target?: string;
    fps?: number;
    duration_s?: number;
    render_mode?: "classic" | "hhvcta";
    render_resolution?: [number, number];
  };
  atomic_finding?: {
    category?: string;
    data_point?: string;
    description?: string;
    provenance?: string;
  };
  beats?: Record<string, { start_s?: number; end_s?: number; text?: string; on_screen?: string }>;
  scenes?: Array<{
    hhvcta?: string;
    duration_seconds?: number;
    spoken_script?: string;
    text_overlay?: string;
    on_screen_text?: string[];
  }>;
  disclaimer?: string;
}