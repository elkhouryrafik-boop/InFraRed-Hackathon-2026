import React from "react";
import {
  AbsoluteFill,
  Img,
  staticFile,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";
import { colors, fonts, provenance } from "../theme";
import { Counter } from "../components/Counter";
import { Reveal } from "../components/Reveal";
import { Kicker, Tag, Label, Panel } from "../components/kit";

// ── SCENE 09 — "Spend €1,000,000 across the city" ──
// The citywide rollup over a Ken-Burns screenshot of the live app: a big
// committed-budget counter (€900k of €1M) plus stat chips (trees, sites, m²
// cooled, residents served) — the measured multi-site portfolio.
export const Scene09: React.FC<{ df: number }> = ({ df }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [0, df], [0, 1], { extrapolateRight: "clamp", easing: Easing.bezier(0.4, 0, 0.2, 1) });
  const scale = 1.06 + 0.1 * t;
  const panAtF = Math.round(df * 0.4);

  const chips = [
    { to: 90, suffix: "", lab: "trees", c: colors.canopyBright },
    { to: 6, suffix: "", lab: "sites", c: colors.canopy },
    { to: 20609, suffix: " m²", lab: "cooled", c: colors.teal, fmt: true },
    { to: 26745, suffix: "", lab: "residents", c: colors.cool, fmt: true },
  ];

  return (
    <AbsoluteFill style={{ background: colors.bg }}>
      {/* real captured citywide UI, Ken Burns */}
      <AbsoluteFill style={{ transform: `scale(${scale}) translateX(${t * 40}px)` }}>
        <Img src={staticFile("app/live-citywide.png")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(90deg, rgba(6,9,13,0.92) 0%, rgba(6,9,13,0.72) 34%, transparent 62%)",
        }}
      />

      {/* left panel */}
      <div style={{ position: "absolute", left: 110, top: 120, width: 880 }}>
        <Reveal startFrame={10}>
          <Kicker color={colors.canopy}>Spend €1,000,000 across the city</Kicker>
        </Reveal>
        <Reveal startFrame={18}>
          <Label size={22} color={colors.textDim}>
            494 vulnerability cells ranked · live-evaluated · per-site cap €150,000
          </Label>
        </Reveal>

        {/* big committed counter */}
        <Reveal startFrame={28}>
          <div style={{ marginTop: 28, display: "flex", alignItems: "baseline", gap: 16 }}>
            <div style={{ fontFamily: fonts.display, fontWeight: 900, fontSize: 116, color: colors.gold, letterSpacing: -3 }}>
              €<Counter to={900000} startFrame={30} durationInFrames={50} format={(n) => Math.round(n).toLocaleString("en-US")} />
            </div>
          </div>
          <Label size={24} color={colors.textDim}>committed — of a €1,000,000 budget</Label>
        </Reveal>

        {/* stat chips */}
        <div style={{ marginTop: 30, display: "flex", gap: 20, flexWrap: "wrap" }}>
          {chips.map((c, i) => (
            <Reveal key={i} startFrame={panAtF + i * 10}>
              <Panel style={{ padding: "16px 22px", minWidth: 150 }}>
                <div style={{ fontFamily: fonts.display, fontWeight: 800, fontSize: 50, color: c.c, fontVariantNumeric: "tabular-nums" }}>
                  <Counter
                    to={c.to}
                    startFrame={panAtF + i * 10}
                    durationInFrames={28}
                    suffix={c.suffix}
                    format={c.fmt ? (n) => Math.round(n).toLocaleString("en-US") : undefined}
                  />
                </div>
                <Label size={19}>{c.lab}</Label>
              </Panel>
            </Reveal>
          ))}
        </div>

        <Reveal startFrame={panAtF + 50}>
          <div style={{ marginTop: 28, display: "flex", alignItems: "center", gap: 16 }}>
            <Tag kind="MEASURED" color={provenance.MEASURED} />
            <span style={{ fontFamily: fonts.mono, fontSize: 22, color: colors.canopyBright }}>€44 / m² cooled</span>
            <span style={{ fontFamily: fonts.mono, fontSize: 20, color: colors.textDim }}>· de-duplicated 300 m catchments</span>
          </div>
        </Reveal>

        <Reveal startFrame={panAtF + 64}>
          <div style={{ marginTop: 18, display: "flex", gap: 14, flexWrap: "wrap" }}>
            <span style={{ fontFamily: fonts.mono, fontSize: 21, color: colors.amber }}>€100,000 left uncommitted — by design</span>
            <span style={{ fontFamily: fonts.mono, fontSize: 21, color: colors.canopy }}>· zero invasive · zero London plane</span>
          </div>
        </Reveal>
      </div>
    </AbsoluteFill>
  );
};
