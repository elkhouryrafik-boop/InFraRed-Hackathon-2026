import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { colors, fonts } from "../theme";

export type Cue = { text: string; fromF: number; toF: number };

// Styled, VO-synced captions burned into the lower third.
export const Captions: React.FC<{ cues: Cue[] }> = ({ cues }) => {
  const frame = useCurrentFrame();
  const active = cues.find((c) => frame >= c.fromF && frame < c.toF);
  if (!active) return null;
  const local = frame - active.fromF;
  const dur = active.toF - active.fromF;
  const opacity = interpolate(
    local,
    [0, 4, dur - 4, dur],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  return (
    <div
      style={{
        position: "absolute",
        bottom: 70,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity,
          maxWidth: 1240,
          textAlign: "center",
          fontFamily: fonts.display,
          fontWeight: 600,
          fontSize: 34,
          lineHeight: 1.25,
          color: colors.text,
          padding: "10px 26px",
          borderRadius: 12,
          background: "rgba(8,11,16,0.62)",
          backdropFilter: "blur(6px)",
          border: `1px solid ${colors.hairline}`,
          textShadow: "0 2px 18px rgba(0,0,0,0.85)",
          letterSpacing: 0.2,
        }}
      >
        {active.text}
      </div>
    </div>
  );
};

// Build cues from a VTT file's parsed segments (start/end in seconds) and a list
// of caption phrases; we distribute phrases across the VTT word timeline.
export function cuesFromTimings(
  phrases: string[],
  segments: { start: number; end: number }[],
  fps: number,
): Cue[] {
  if (segments.length === 0 || phrases.length === 0) return [];
  // map phrases evenly onto the covered time span
  const t0 = segments[0].start;
  const t1 = segments[segments.length - 1].end;
  const span = Math.max(0.001, t1 - t0);
  const per = span / phrases.length;
  return phrases.map((text, i) => ({
    text,
    fromF: Math.round((t0 + i * per) * fps),
    toF: Math.round((t0 + (i + 1) * per) * fps),
  }));
}
