import React from "react";
import {
  AbsoluteFill,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { Video } from "@remotion/media";
import { colors, fonts } from "../theme";
import { Reveal } from "../components/Reveal";
import { Kicker } from "../components/kit";

// ── SCENE 11 — "What We Don't Yet Know — and Why That's the Point" ──
// Dusk b-roll closer: lists the honest limitations (buried pipes, cautious
// setback, uncommitted budget, one city/one July) and lands the thesis
// "Fidelity, not novelty" + the CoolSpend · Barcelona lockup.
// Scene 11 — "What We Don't Yet Know — and Why That's the Point" (dusk closer).
export const Scene11: React.FC<{ df: number }> = ({ df }) => {
  const frame = useCurrentFrame();
  const scale = 1 + 0.1 * interpolate(frame, [0, df], [0, 1], { extrapolateRight: "clamp" });

  const limitations = [
    "Can't see buried pipes — every in-ground slot flagged for survey",
    "6 m setback, deliberately cautious",
    "Shade-gain only guides placement — cooling comes from the live sim",
    "€100,000 of €1,000,000 left uncommitted, by design",
    "One city, one July",
  ];

  return (
    <AbsoluteFill style={{ background: "#07090d" }}>
      <AbsoluteFill style={{ transform: `scale(${scale})` }}>
        <Video
          src={staticFile("clips/clip11_dusk_pit.mp4")}
          muted
          loop
          playbackRate={0.5}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(8,11,16,0.55) 0%, rgba(8,11,16,0.25) 40%, rgba(7,9,13,0.92) 100%)",
        }}
      />
      <AbsoluteFill
        style={{ background: "radial-gradient(ellipse at 50% 50%, transparent 45%, rgba(7,9,13,0.7) 100%)" }}
      />

      <div style={{ position: "absolute", left: 120, top: 130, maxWidth: 1100 }}>
        <Reveal startFrame={12}>
          <Kicker color={colors.amber}>What we don't yet know</Kicker>
        </Reveal>
        <div style={{ marginTop: 28, display: "flex", flexDirection: "column", gap: 16 }}>
          {limitations.map((t, i) => (
            <Reveal key={i} startFrame={24 + i * 12} translateX={-18}>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 2,
                    background: colors.amber,
                    transform: "rotate(45deg)",
                    flexShrink: 0,
                  }}
                />
                <span
                  style={{
                    fontFamily: fonts.display,
                    fontSize: 30,
                    color: colors.textDim,
                    textShadow: "0 2px 16px rgba(0,0,0,0.8)",
                  }}
                >
                  {t}
                </span>
              </div>
            </Reveal>
          ))}
        </div>
      </div>

      {/* Final thesis lockup */}
      <Reveal
        startFrame={Math.round(df * 0.62)}
        translateY={26}
        style={{ position: "absolute", left: 0, right: 0, bottom: 250, textAlign: "center" }}
      >
        <div
          style={{
            fontFamily: fonts.display,
            fontWeight: 900,
            fontSize: 92,
            letterSpacing: -2,
            color: colors.text,
            textShadow: "0 6px 50px rgba(0,0,0,0.85)",
          }}
        >
          Fidelity, not novelty.
        </div>
        <div
          style={{
            marginTop: 16,
            fontFamily: fonts.mono,
            fontSize: 26,
            letterSpacing: 3,
            color: colors.canopyBright,
          }}
        >
          C O O L S P E N D · BARCELONA
        </div>
      </Reveal>
    </AbsoluteFill>
  );
};
