import React from "react";
import {
  AbsoluteFill,
  staticFile,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";
import { Video } from "@remotion/media";
import { colors, fonts } from "../theme";
import { Reveal } from "../components/Reveal";
import { Kicker } from "../components/kit";

// ── SCENE 01 — "The Hottest Block in Barcelona" ──
// Cold-open over a Higgsfield aerial clip (slow push-in): names the urban heat
// island and poses the film's question — one budget, where do we plant?
// Scene 01 — "The Hottest Block in Barcelona" (higgsfield aerial opener).
export const Scene01: React.FC<{ df: number }> = ({ df }) => {
  const frame = useCurrentFrame();
  const scale = 1 + 0.12 * interpolate(frame, [0, df], [0, 1], { extrapolateRight: "clamp" });
  const drift = interpolate(frame, [0, df], [0, -28], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: "#0b0805" }}>
      <AbsoluteFill style={{ transform: `scale(${scale}) translateY(${drift}px)` }}>
        <Video
          src={staticFile("clips/clip01_heat_aerial.mp4")}
          muted
          loop
          playbackRate={0.5}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>
      {/* heat grade */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(255,120,40,0.10) 0%, transparent 35%, rgba(8,6,5,0.4) 75%, rgba(6,5,4,0.92) 100%)",
        }}
      />
      <AbsoluteFill
        style={{ background: "radial-gradient(ellipse at 50% 40%, transparent 40%, rgba(6,5,4,0.6) 100%)" }}
      />

      {/* Title block, lower-left */}
      <div
        style={{
          position: "absolute",
          left: 120,
          bottom: 220,
          display: "flex",
          flexDirection: "column",
          gap: 22,
          maxWidth: 1300,
        }}
      >
        <Reveal startFrame={14}>
          <Kicker color={colors.heat}>Urban heat island</Kicker>
        </Reveal>
        <Reveal startFrame={26} translateY={34}>
          <div
            style={{
              fontFamily: fonts.display,
              fontWeight: 900,
              fontSize: 104,
              lineHeight: 0.98,
              letterSpacing: -3,
              color: colors.text,
              textShadow: "0 6px 40px rgba(0,0,0,0.7)",
            }}
          >
            The hottest block
            <br />
            in Barcelona
          </div>
        </Reveal>
        <Reveal startFrame={Math.round(df * 0.34)}>
          <div
            style={{
              fontFamily: fonts.mono,
              fontSize: 27,
              letterSpacing: 1,
              color: colors.amber,
            }}
          >
            most sealed · least green · most inhabited
          </div>
        </Reveal>
      </div>

      {/* Closing question punches in late */}
      <Reveal startFrame={Math.round(df * 0.7)} translateY={20} style={{ position: "absolute", right: 120, top: 150 }}>
        <div
          style={{
            fontFamily: fonts.display,
            fontWeight: 800,
            fontSize: 46,
            textAlign: "right",
            lineHeight: 1.1,
            color: colors.canopyBright,
            textShadow: "0 4px 30px rgba(0,0,0,0.8)",
          }}
        >
          One budget.
          <br />
          Where do we plant?
        </div>
      </Reveal>
    </AbsoluteFill>
  );
};
