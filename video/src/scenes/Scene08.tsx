import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { colors, fonts, provenance } from "../theme";
import { BeforeAfterHeatmap } from "../dataviz/BeforeAfterHeatmap";
import { Counter } from "../components/Counter";
import { Reveal } from "../components/Reveal";
import { Kicker, Tag, Label } from "../components/kit";

// ── SCENE 08 — "Optimise, then validate" ──
// The single-site payoff: a before/after UTCI heatmap (BeforeAfterHeatmap) plays
// the optimise→validate pipeline while a stats column counts up the MEASURED
// results (trees, m² cooled by band, mean/peak felt-temp drop, €/m² cooled).
const STEPS = [
  "measured baseline UTCI",
  "greedy place",
  "live before / after",
  "measured grid difference",
];

export const Scene08: React.FC<{ df: number }> = ({ df }) => {
  const frame = useCurrentFrame();
  const treesAtF = Math.round(df * 0.08);
  const revealAtF = Math.round(df * 0.5);
  const statsAtF = Math.round(df * 0.62);

  // active pipeline step
  const stepBounds = [0.0, 0.16, 0.32, 0.55, 0.78];
  const prog = frame / df;
  let active = 0;
  for (let i = 0; i < STEPS.length; i++) if (prog >= stepBounds[i]) active = i;

  return (
    <AbsoluteFill>
      {/* heatmap centerpiece, nudged left to leave a stats column */}
      <AbsoluteFill style={{ transform: "translateX(-220px) translateY(10px) scale(0.92)" }}>
        <BeforeAfterHeatmap revealAtF={revealAtF} treesAtF={treesAtF} />
      </AbsoluteFill>

      {/* title + pipeline ribbon, top */}
      <div style={{ position: "absolute", top: 64, left: 120, right: 120 }}>
        <Reveal startFrame={10}>
          <Kicker color={colors.canopy}>Optimise, then validate</Kicker>
        </Reveal>
        <Reveal startFrame={18}>
          <div
            style={{
              marginTop: 8,
              display: "flex",
              gap: 10,
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            {STEPS.map((s, i) => (
              <React.Fragment key={i}>
                <div
                  style={{
                    fontFamily: fonts.mono,
                    fontSize: 19,
                    padding: "6px 12px",
                    borderRadius: 8,
                    border: `1.5px solid ${i <= active ? colors.canopy : colors.border}`,
                    color: i <= active ? colors.canopy : colors.textMuted,
                    background: i === active ? "rgba(55,208,138,0.12)" : "transparent",
                    transition: "none",
                  }}
                >
                  {s}
                </div>
                {i < STEPS.length - 1 && (
                  <span style={{ color: colors.textMuted, fontSize: 18 }}>→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </Reveal>
      </div>

      {/* stats column, right */}
      <div
        style={{
          position: "absolute",
          right: 96,
          top: 250,
          width: 430,
          display: "flex",
          flexDirection: "column",
          gap: 18,
        }}
      >
        <Reveal startFrame={statsAtF}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
            <div style={{ fontFamily: fonts.display, fontWeight: 900, fontSize: 70, color: colors.text }}>
              <Counter to={20} startFrame={statsAtF} durationInFrames={24} />
            </div>
            <Label size={24}>trees placed</Label>
          </div>
        </Reveal>

        {[
          { to: 2779, lab: "m² cooled ≥ 0.5 °C", c: colors.canopyBright, big: true },
          { to: 2239, lab: "m² cooled ≥ 1 °C", c: colors.canopy },
          { to: 1491, lab: "m² cooled ≥ 2 °C", c: colors.teal },
        ].map((r, i) => (
          <Reveal key={i} startFrame={statsAtF + 14 + i * 12}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
              <div
                style={{
                  fontFamily: fonts.display,
                  fontWeight: 800,
                  fontSize: r.big ? 60 : 46,
                  color: r.c,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                <Counter to={r.to} startFrame={statsAtF + 14 + i * 12} durationInFrames={26} format={(n) => Math.round(n).toLocaleString("en-US")} />
              </div>
              <Label size={20}>{r.lab}</Label>
            </div>
          </Reveal>
        ))}

        <Reveal startFrame={statsAtF + 56}>
          <div style={{ display: "flex", gap: 22, marginTop: 6 }}>
            <div>
              <div style={{ fontFamily: fonts.display, fontWeight: 800, fontSize: 40, color: colors.cool }}>
                −1.48 °C
              </div>
              <Label size={17}>mean felt-temp drop</Label>
            </div>
            <div>
              <div style={{ fontFamily: fonts.display, fontWeight: 800, fontSize: 40, color: colors.amber }}>
                31.0→30.6
              </div>
              <Label size={17}>peak felt °C</Label>
            </div>
          </div>
        </Reveal>

        <Reveal startFrame={statsAtF + 72}>
          <div
            style={{
              marginTop: 10,
              display: "flex",
              alignItems: "center",
              gap: 16,
            }}
          >
            <div style={{ fontFamily: fonts.display, fontWeight: 900, fontSize: 64, color: colors.gold }}>
              €<Counter to={72} startFrame={statsAtF + 72} durationInFrames={24} />
            </div>
            <Label size={22}>/ m² cooled</Label>
          </div>
        </Reveal>

        <Reveal startFrame={statsAtF + 88}>
          <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 4 }}>
            <Tag kind="MEASURED" color={provenance.MEASURED} />
            <Label size={20} color={colors.textDim}>live Infrared UTCI · not estimated</Label>
          </div>
        </Reveal>
      </div>
    </AbsoluteFill>
  );
};
