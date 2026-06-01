// SceneFrame.tsx — the shared shell every scene renders inside (mounted by
// Main/MainShort). Adds the film background, a frame-in/out opacity fade,
// cinematic vignette, film grain, and the VO-synced caption track on top of the
// scene's own content.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { colors } from "./theme";
import { Grain } from "./components/Grain";
import { Captions, Cue } from "./components/Captions";

// Wraps a scene's inner content with the film bg, grain, vignette, fade, and captions.
export const SceneFrame: React.FC<{
  df: number;
  cues: Cue[];
  children: React.ReactNode;
  showCaptions?: boolean;
}> = ({ df, cues, children, showCaptions = true }) => {
  const frame = useCurrentFrame();
  // fade in over the first 14 frames, hold, then fade out over the last 16 —
  // gives every scene a soft cut at both ends. df = this scene's total length.
  const fade = interpolate(
    frame,
    [0, 14, df - 16, df],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  return (
    <AbsoluteFill style={{ background: colors.bg }}>
      <AbsoluteFill style={{ opacity: fade }}>
        {children}
        {/* cinematic vignette */}
        <AbsoluteFill
          style={{
            pointerEvents: "none",
            background:
              "radial-gradient(ellipse at 50% 46%, transparent 52%, rgba(4,6,9,0.55) 100%)",
          }}
        />
        <Grain intensity={0.06} />
        {showCaptions && <Captions cues={cues} />}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
