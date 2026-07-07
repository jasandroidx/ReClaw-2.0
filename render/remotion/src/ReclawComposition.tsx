import React from "react";
import {
  AbsoluteFill,
  interpolate,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { DynamicChart } from "./DynamicChart";
import { SceneOverlay } from "./SceneOverlay";
import type { HHVCTAScene, ReclawCompositionProps } from "./types";

/** Minimal props — matches video_manifest_generator.py / classic 16s layout */
export type ReclawManifestProps = Pick<
  ReclawCompositionProps,
  "city" | "hookText" | "valueText" | "sourceText" | "chartData"
>;

const CLASSIC_DURATION_S = 16;

const GridBackground: React.FC = () => (
  <div
    style={{
      position: "absolute",
      width: "100%",
      height: "100%",
      backgroundImage:
        "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
      backgroundSize: "40px 40px",
      zIndex: 0,
    }}
  />
);

const BrandHeader: React.FC<{ city: string }> = ({ city }) => {
  const frame = useCurrentFrame();
  const pulse = interpolate(frame % 60, [0, 30, 60], [1, 1.35, 1]);

  return (
    <>
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 60,
          zIndex: 10,
          display: "flex",
          alignItems: "center",
          gap: 15,
        }}
      >
        <div
          style={{
            width: 20,
            height: 20,
            backgroundColor: "#ef4444",
            borderRadius: "50%",
            transform: `scale(${pulse})`,
            boxShadow: "0 0 20px rgba(239, 68, 68, 0.5)",
          }}
        />
        <span
          style={{
            fontSize: 32,
            fontWeight: 800,
            letterSpacing: 2,
            color: "#f8fafc",
          }}
        >
          RECLAW <span style={{ color: "#ef4444" }}>AUDIT</span>
        </span>
      </div>
      <div
        style={{
          position: "absolute",
          top: 60,
          right: 60,
          zIndex: 10,
          padding: "10px 20px",
          backgroundColor: "rgba(51, 65, 85, 0.5)",
          border: "1px solid #475569",
          borderRadius: 12,
        }}
      >
        <span style={{ fontSize: 24, color: "#94a3b8", fontFamily: "monospace" }}>
          TARGET: {city.toUpperCase()}
        </span>
      </div>
    </>
  );
};

/** Classic 3-scene layout from Project ReClaw spec (Hook 0–4s, Value 4–12s, CTA 12–16s). */
const ClassicComposition: React.FC<ReclawManifestProps & { disclaimer?: string }> = ({
  city,
  hookText,
  valueText,
  sourceText,
  chartData,
  disclaimer,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, 15], [50, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#020617",
        color: "white",
        fontFamily: "Inter, sans-serif",
      }}
    >
      <GridBackground />
      <BrandHeader city={city} />

      <Sequence from={0} durationInFrames={fps * 4}>
        <AbsoluteFill
          style={{ justifyContent: "center", alignItems: "center", padding: 80 }}
        >
          <h1
            style={{
              fontSize: 72,
              fontWeight: 900,
              textAlign: "center",
              lineHeight: 1.2,
              opacity: titleOpacity,
              transform: `translateY(${titleY}px)`,
              textShadow: "0 10px 30px rgba(0,0,0,0.8)",
              margin: 0,
            }}
          >
            {hookText}
          </h1>
        </AbsoluteFill>
      </Sequence>

      <Sequence from={fps * 4} durationInFrames={fps * 8}>
        <AbsoluteFill style={{ justifyContent: "center", padding: 60 }}>
          <div style={{ transform: "translateY(-100px)" }}>
            <DynamicChart data={chartData} />
          </div>
          <div
            style={{
              position: "absolute",
              bottom: 150,
              left: 60,
              right: 60,
              backgroundColor: "rgba(15, 23, 42, 0.8)",
              backdropFilter: "blur(10px)",
              padding: 40,
              borderRadius: 24,
              borderLeft: "8px solid #ef4444",
              boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
            }}
          >
            <p
              style={{
                fontSize: 42,
                fontWeight: 600,
                lineHeight: 1.4,
                color: "#f1f5f9",
                margin: 0,
              }}
            >
              {valueText}
            </p>
          </div>
        </AbsoluteFill>
      </Sequence>

      <Sequence from={fps * 12}>
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
            padding: 80,
            backgroundColor: "#ef4444",
          }}
        >
          <h2
            style={{
              fontSize: 64,
              fontWeight: 900,
              color: "white",
              textAlign: "center",
              marginBottom: 20,
            }}
          >
            THE MATH IS PUBLIC.
          </h2>
          <p style={{ fontSize: 36, color: "#fca5a5", fontFamily: "monospace" }}>
            Source: {sourceText}
          </p>
          <div
            style={{
              marginTop: 60,
              padding: "20px 40px",
              backgroundColor: "white",
              color: "#ef4444",
              fontSize: 48,
              fontWeight: 900,
              borderRadius: 20,
            }}
          >
            TAG YOUR CITY COUNCIL
          </div>
        </AbsoluteFill>
      </Sequence>

      {disclaimer && (
        <div
          style={{
            position: "absolute",
            bottom: 20,
            left: 48,
            right: 48,
            fontSize: 13,
            color: "#fca5a5",
            textAlign: "center",
            zIndex: 20,
          }}
        >
          {disclaimer}
        </div>
      )}
    </AbsoluteFill>
  );
};

const sceneFrames = (scene: HHVCTAScene, fps: number) => ({
  from: Math.round(scene.start_s * fps),
  durationInFrames: Math.max(1, Math.round(scene.duration_s * fps)),
});

const HhvctaScene: React.FC<{ scene: HHVCTAScene; props: ReclawCompositionProps }> = ({
  scene,
  props,
}) => {
  const { hhvcta, spoken_script, on_screen_text } = scene;

  if (hhvcta === "value") {
    return (
      <AbsoluteFill style={{ justifyContent: "center", padding: 60 }}>
        <SceneOverlay bursts={on_screen_text} accent="#6366f1" />
        <div style={{ transform: "translateY(-100px)" }}>
          <DynamicChart data={props.chartData} />
        </div>
        <div
          style={{
            position: "absolute",
            bottom: 150,
            left: 60,
            right: 60,
            backgroundColor: "rgba(15, 23, 42, 0.8)",
            backdropFilter: "blur(10px)",
            padding: 40,
            borderRadius: 24,
            borderLeft: "8px solid #ef4444",
          }}
        >
          <p style={{ fontSize: 42, fontWeight: 600, lineHeight: 1.4, margin: 0 }}>
            {spoken_script || props.valueText}
          </p>
        </div>
      </AbsoluteFill>
    );
  }

  if (hhvcta === "credibility" || hhvcta === "action") {
    return (
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: 80,
          backgroundColor: "#ef4444",
        }}
      >
        <SceneOverlay bursts={on_screen_text} accent="#ffffff" />
        <h2 style={{ fontSize: 64, fontWeight: 900, color: "white", textAlign: "center" }}>
          {hhvcta === "action" ? "TAG YOUR OFFICIALS" : "THE MATH IS PUBLIC."}
        </h2>
        <p style={{ fontSize: 36, color: "#fca5a5", fontFamily: "monospace", marginTop: 20 }}>
          {hhvcta === "credibility"
            ? `Source: ${props.sourceText}`
            : spoken_script || props.actionText}
        </p>
      </AbsoluteFill>
    );
  }

  const frame = useCurrentFrame();
  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, 15], [50, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 80 }}>
      <SceneOverlay bursts={on_screen_text} />
      <h1
        style={{
          fontSize: 72,
          fontWeight: 900,
          textAlign: "center",
          lineHeight: 1.2,
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          textShadow: "0 10px 30px rgba(0,0,0,0.8)",
          margin: 0,
        }}
      >
        {spoken_script || props.hookText}
      </h1>
    </AbsoluteFill>
  );
};

export const ReclawComposition: React.FC<ReclawCompositionProps> = (props) => {
  const { fps } = useVideoConfig();

  if (props.renderMode !== "hhvcta") {
    return (
      <ClassicComposition
        city={props.city}
        hookText={props.hookText}
        valueText={props.valueText}
        sourceText={props.sourceText}
        chartData={props.chartData}
        disclaimer={props.disclaimer}
      />
    );
  }

  const scenes = props.scenes;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#020617",
        color: "white",
        fontFamily: "Inter, sans-serif",
      }}
    >
      <GridBackground />
      <BrandHeader city={props.city} />
      {scenes.map((scene) => {
        const { from, durationInFrames } = sceneFrames(scene, fps);
        return (
          <Sequence
            key={`${scene.hhvcta}-${scene.start_s}`}
            from={from}
            durationInFrames={durationInFrames}
          >
            <HhvctaScene scene={scene} props={props} />
          </Sequence>
        );
      })}
      <div
        style={{
          position: "absolute",
          bottom: 20,
          left: 48,
          right: 48,
          fontSize: 13,
          color: "#64748b",
          textAlign: "center",
          zIndex: 20,
        }}
      >
        {props.disclaimer}
      </div>
    </AbsoluteFill>
  );
};