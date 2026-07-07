import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

export const SceneOverlay: React.FC<{
  bursts: string[];
  accent?: string;
}> = ({ bursts, accent = "#ef4444" }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div
      style={{
        position: "absolute",
        top: 140,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        gap: 12,
        flexWrap: "wrap",
        padding: "0 40px",
        opacity,
      }}
    >
      {bursts.map((text, i) => (
        <span
          key={`${text}-${i}`}
          style={{
            padding: "10px 18px",
            backgroundColor: i === 0 ? accent : "rgba(51, 65, 85, 0.8)",
            border: `1px solid ${i === 0 ? "#f87171" : "#475569"}`,
            borderRadius: 10,
            fontSize: 28,
            fontWeight: 900,
            letterSpacing: 1,
            fontFamily: "monospace",
          }}
        >
          {text}
        </span>
      ))}
    </div>
  );
};