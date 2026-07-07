import React from "react";
import { Composition, getInputProps } from "remotion";
import sampleManifest from "../../../data/manifests/gibson/manifest_gibson.json";
import { loadManifest } from "./loadManifest";
import { ReclawComposition } from "./ReclawComposition";
import type { RawManifest } from "./types";

function resolveManifest(): RawManifest {
  const input = getInputProps() as RawManifest;
  if (input?.schema || input?.beats || input?.metadata || input?.scenes) {
    return input;
  }
  return sampleManifest as RawManifest;
}

const props = loadManifest(resolveManifest());

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ReclawAudit"
      component={ReclawComposition}
      durationInFrames={props.durationInFrames}
      fps={props.fps}
      width={1080}
      height={1920}
      defaultProps={props}
    />
  );
};