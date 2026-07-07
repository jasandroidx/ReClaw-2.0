import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { AnomalyData } from "./types";

/** Matches video_manifest_generator.py chart spec — spring bars, red anomaly glow. */
export const DynamicChart: React.FC<{ data: AnomalyData[] }> = ({ data }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const maxValue = Math.max(...data.map((d) => d.value), 1);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
        height: "600px",
        gap: "20px",
        padding: "40px",
      }}
    >
      {data.map((item, index) => {
        const delay = index * 5;
        const animationProgress = spring({
          frame: frame - delay,
          fps,
          config: { damping: 12, mass: 0.5, stiffness: 100 },
        });
        const targetHeight = (item.value / maxValue) * 500;
        const currentHeight = interpolate(animationProgress, [0, 1], [0, targetHeight]);
        const isRedFlag = item.isAnomaly;
        const bgColor = isRedFlag ? "#ef4444" : "#334155";
        const glow = isRedFlag ? "0 0 40px rgba(239, 68, 68, 0.6)" : "none";

        return (
          <div
            key={`${item.label}-${index}`}
            style={{ display: "flex", flexDirection: "column", alignItems: "center" }}
          >
            <div
              style={{
                width: "60px",
                height: `${currentHeight}px`,
                backgroundColor: bgColor,
                borderRadius: "12px 12px 0 0",
                boxShadow: glow,
                border: isRedFlag ? "2px solid #f87171" : "1px solid #475569",
              }}
            />
            <span
              style={{
                marginTop: "16px",
                color: "#94a3b8",
                fontSize: "24px",
                fontFamily: "monospace",
                fontWeight: "bold",
              }}
            >
              {item.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};