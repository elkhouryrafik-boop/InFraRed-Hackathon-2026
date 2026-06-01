import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  spring,
  useVideoConfig,
  Sequence,
} from "remotion";
import { colors, fonts, FPS } from "../theme";
import { Kicker, Headline, Chip, Panel, Label } from "../components/kit";
import { Reveal } from "../components/Reveal";
import { Counter } from "../components/Counter";

// ── SCENE 03 — "Four Real Maps of a Real City" ──
// Establishes the data foundation: four independent real layers (satellite
// vulnerability grid, OSM geometry, arbrat-viari tree inventory, Padró
// population). Beats: cards fan→stack into a BCN outline → the 494-cell
// vulnerability grid → OSM footprints + species table → Padró population/barris.
// CoolSpend stands on four real, independently sourced layers of Barcelona.

const EASE = Easing.bezier(0.16, 1, 0.3, 1);

// A small stylised Barcelona outline (Eixample wedge + coastline), normalised 0..1.
const BCN_OUTLINE =
  "M0.18,0.10 L0.78,0.04 L0.95,0.30 L0.90,0.62 L0.66,0.92 " +
  "L0.30,0.97 L0.06,0.70 L0.02,0.34 Z";

const LAYERS = [
  { n: 1, name: "Satellite vulnerability grid", color: colors.heat },
  { n: 2, name: "OpenStreetMap geometry", color: colors.cool },
  { n: 3, name: "arbrat viari inventory", color: colors.canopy },
  { n: 4, name: "Padró register", color: colors.gold },
];

// ── One translucent fanned/stacked map-layer card ──
const LayerCard: React.FC<{
  index: number;
  appear: number; // 0..1 stack progress
  fanned: boolean;
}> = ({ index, appear, fanned }) => {
  const L = LAYERS[index];
  // fanned spread vs. stacked-to-outline
  const fanX = (index - 1.5) * 70;
  const fanY = (index - 1.5) * 26;
  const fanR = (index - 1.5) * 7;
  const stackX = index * 10;
  const stackY = index * 14;
  const x = interpolate(appear, [0, 1], [fanX - 40, fanned ? fanX : stackX], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(appear, [0, 1], [fanY + 60, fanned ? fanY : stackY], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rot = interpolate(appear, [0, 1], [fanR + 6, fanned ? fanR : 0]);
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: 360,
        height: 240,
        transform: `translate(${x}px, ${y}px) rotate(${rot}deg)`,
        opacity: appear,
      }}
    >
      <svg width={360} height={240} viewBox="0 0 1 1" preserveAspectRatio="none">
        <path
          d={BCN_OUTLINE}
          fill={`${L.color}1F`}
          stroke={L.color}
          strokeWidth={0.008}
          strokeLinejoin="round"
        />
      </svg>
      <div
        style={{
          position: "absolute",
          left: 14,
          bottom: 12,
          display: "flex",
          alignItems: "center",
          gap: 10,
          fontFamily: fonts.mono,
          fontSize: 18,
          color: L.color,
          fontWeight: 700,
        }}
      >
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 26,
            height: 26,
            borderRadius: 6,
            border: `1.5px solid ${L.color}`,
            fontSize: 15,
          }}
        >
          {L.n}
        </span>
        {L.name}
      </div>
    </div>
  );
};

// ── BEAT 2: tessellated vulnerability grid (22×22), pulsing warm→cool ──
const VulnGrid: React.FC<{ t: number }> = ({ t }) => {
  const N = 22;
  const cells: React.ReactNode[] = [];
  const px = 460 / N;
  for (let r = 0; r < N; r++) {
    for (let c = 0; c < N; c++) {
      const idx = (r * N + c) / (N * N - 1);
      // pseudo "composite score" gradient between heat and cool
      const wave = 0.5 + 0.5 * Math.sin(idx * 9 + t * 4);
      const score = idx * 0.7 + wave * 0.3;
      const heatC = [255, 90, 54];
      const coolC = [78, 168, 222];
      const mix = (a: number, b: number) => Math.round(a + (b - a) * score);
      const fill = `rgb(${mix(coolC[0], heatC[0])},${mix(coolC[1], heatC[1])},${mix(
        coolC[2],
        heatC[2],
      )})`;
      const appear = interpolate(t, [0, 0.4], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      const cellDelay = idx * 0.5;
      const o = interpolate(appear, [cellDelay, cellDelay + 0.5], [0, 0.92], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      cells.push(
        <div
          key={`${r}-${c}`}
          style={{
            position: "absolute",
            left: c * px,
            top: r * px,
            width: px - 1.5,
            height: px - 1.5,
            background: fill,
            opacity: o,
            borderRadius: 2,
          }}
        />,
      );
    }
  }
  return (
    <div style={{ position: "relative", width: 460, height: 460 }}>
      {cells}
      {/* ~400 m caliper */}
      <div
        style={{
          position: "absolute",
          left: 0,
          bottom: -34,
          width: px * 4,
          height: 2,
          background: colors.text,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: px * 4 + 10,
          bottom: -46,
          fontFamily: fonts.mono,
          fontSize: 18,
          color: colors.textDim,
        }}
      >
        ~400 m
      </div>
    </div>
  );
};

// ── A source chip with an animated signal swatch ──
const SourceChip: React.FC<{
  t: number;
  delay: number;
  title: string;
  caption: string;
  color: string;
  kind: "heat" | "fill" | "ndvi";
}> = ({ t, delay, title, caption, color, kind }) => {
  const p = interpolate(t, [delay, delay + 0.4], [0, 1], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  let swatch: React.ReactNode;
  if (kind === "heat") {
    const heat = interpolate(p, [0, 1], [0, 1]);
    swatch = (
      <div
        style={{
          width: 56,
          height: 40,
          borderRadius: 6,
          background: `linear-gradient(90deg, ${colors.cool}, rgb(${Math.round(
            78 + heat * 177,
          )},${Math.round(168 - heat * 78)},${Math.round(222 - heat * 168)}))`,
        }}
      />
    );
  } else if (kind === "fill") {
    swatch = (
      <div
        style={{
          width: 56,
          height: 40,
          borderRadius: 6,
          border: `1.5px solid ${color}`,
          overflow: "hidden",
        }}
      >
        <div style={{ width: `${p * 100}%`, height: "100%", background: color }} />
      </div>
    );
  } else {
    // low NDVI = nearly-empty bar
    const ndvi = p * 0.18;
    swatch = (
      <div
        style={{
          width: 56,
          height: 40,
          borderRadius: 6,
          border: `1.5px solid ${color}`,
          display: "flex",
          alignItems: "flex-end",
        }}
      >
        <div style={{ width: "100%", height: `${ndvi * 100}%`, background: color }} />
      </div>
    );
  }
  return (
    <div
      style={{
        opacity: p,
        transform: `translateY(${(1 - p) * 18}px)`,
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "12px 16px",
        background: "rgba(14,19,26,0.82)",
        border: `1px solid ${colors.border}`,
        borderRadius: 12,
      }}
    >
      {swatch}
      <div>
        <div style={{ fontFamily: fonts.mono, fontSize: 18, color, fontWeight: 700 }}>
          {title}
        </div>
        <div style={{ fontFamily: fonts.mono, fontSize: 15, color: colors.textDim }}>
          {caption}
        </div>
      </div>
    </div>
  );
};

export const Scene03: React.FC<{ df: number }> = ({ df }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = FPS; // 30, keeps the linter from flagging the import

  // beat boundaries (fractions of df)
  const b1 = df * 0.18;
  const b2 = df * 0.48;
  const b3 = df * 0.72;

  // BEAT 1 — fan → stack
  const fan = spring({ frame, fps: fps || f, config: { damping: 200 }, durationInFrames: 40 });
  const stack = interpolate(frame, [b1 * 0.55, b1], [0, 1], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fanned = frame < b1 * 0.55;

  // BEAT 2 — grid local time
  const t2 = interpolate(frame, [b1, b2], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const stampP = interpolate(frame, [b2 - df * 0.06, b2 - df * 0.01], [0, 1], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // BEAT 3 — OSM geometry
  const t3 = interpolate(frame, [b2, b3], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // BEAT 4 — Padró
  const t4 = interpolate(frame, [b3, df], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const SPECIES = [
    "Platanus × hispanica",
    "Celtis australis",
    "Tilia tomentosa",
    "Melia azedarach",
    "Sophora japonica",
    "Cercis siliquastrum",
  ];

  return (
    <AbsoluteFill style={{ fontFamily: fonts.display }}>
      {/* ── Persistent header ── */}
      <div style={{ position: "absolute", left: 110, top: 80 }}>
        <Reveal startFrame={0} translateY={18}>
          <Kicker color={colors.cool}>FOUR REAL MAPS</Kicker>
        </Reveal>
        <Reveal startFrame={6} translateY={22}>
          <div style={{ marginTop: 14 }}>
            <Headline size={70}>Four real maps of a real city</Headline>
          </div>
        </Reveal>
      </div>

      {/* ── BEAT 1: layer cards fan → stack into Barcelona outline ── */}
      <Sequence from={0} durationInFrames={Math.ceil(b2)}>
        <div style={{ position: "absolute", left: 200, top: 360 }}>
          {LAYERS.map((_, i) => {
            const appear = fanned ? fan : stack;
            return <LayerCard key={i} index={i} appear={appear} fanned={fanned} />;
          })}
        </div>
      </Sequence>

      {/* ── BEAT 2: vulnerability grid + 494 + source chips ── */}
      <Sequence from={Math.floor(b1)} durationInFrames={Math.ceil(b2 - b1) + 8}>
        <div style={{ position: "absolute", left: 110, top: 300 }}>
          <VulnGrid t={t2} />
        </div>

        <div style={{ position: "absolute", left: 660, top: 300, width: 760 }}>
          <Label color={colors.heat} size={22}>
            VULNERABILITY GRID
          </Label>
          <div
            style={{
              fontFamily: fonts.display,
              fontSize: 132,
              fontWeight: 800,
              color: colors.text,
              letterSpacing: -4,
              lineHeight: 1,
              marginTop: 6,
            }}
          >
            <Counter
              startFrame={Math.floor(b1) + 4}
              durationInFrames={36}
              to={494}
            />
          </div>
          <Label color={colors.textDim} size={24}>
            494 cells · ~400 m
          </Label>

          <div
            style={{
              display: "flex",
              gap: 14,
              marginTop: 28,
              flexWrap: "wrap",
            }}
          >
            <SourceChip
              t={t2}
              delay={0.30}
              title="Landsat"
              caption="land-surface temperature"
              color={colors.heat}
              kind="heat"
            />
            <SourceChip
              t={t2}
              delay={0.42}
              title="Sentinel-1"
              caption="sealed surface"
              color={colors.amber}
              kind="fill"
            />
            <SourceChip
              t={t2}
              delay={0.54}
              title="Sentinel-2"
              caption="low NDVI = little vegetation"
              color={colors.canopy}
              kind="ndvi"
            />
          </div>

          <div style={{ marginTop: 22 }}>
            <Chip color={colors.cool} size={20}>
              Landsat · Sentinel-1 · Sentinel-2
            </Chip>
          </div>

          {/* glossary + honesty stamp */}
          <div
            style={{
              marginTop: 26,
              opacity: stampP,
              transform: `translateY(${(1 - stampP) * 16}px)`,
            }}
          >
            <Panel style={{ padding: "16px 20px", maxWidth: 640 }} glow={`${colors.amber}33`}>
              <div
                style={{
                  fontFamily: fonts.mono,
                  fontSize: 18,
                  color: colors.canopy,
                  fontWeight: 700,
                }}
              >
                NDVI = greenness
              </div>
              <div
                style={{
                  fontFamily: fonts.display,
                  fontSize: 26,
                  fontWeight: 700,
                  color: colors.amber,
                  marginTop: 8,
                }}
              >
                WHERE to look, not how much cooling
              </div>
            </Panel>
          </div>
        </div>
      </Sequence>

      {/* ── BEAT 3: OSM geometry + species table ── */}
      <Sequence from={Math.floor(b2)} durationInFrames={Math.ceil(b3 - b2) + 8}>
        {/* OSM footprints / roads / furniture over the outline */}
        <div style={{ position: "absolute", left: 110, top: 320 }}>
          <Label color={colors.cool} size={22}>
            OpenStreetMap
          </Label>
          <svg width={520} height={460} style={{ display: "block", marginTop: 10 }}>
            {/* road centerlines */}
            {[
              "M40,90 L480,60",
              "M30,210 L470,240",
              "M60,360 L460,330",
              "M120,30 L150,440",
              "M300,20 L320,450",
            ].map((d, i) => {
              const dr = interpolate(t3, [0.0 + i * 0.04, 0.3 + i * 0.04], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              return (
                <path
                  key={`r${i}`}
                  d={d}
                  stroke={colors.cool}
                  strokeWidth={3}
                  fill="none"
                  strokeDasharray={600}
                  strokeDashoffset={600 * (1 - dr)}
                  opacity={0.85}
                />
              );
            })}
            {/* building footprints */}
            {Array.from({ length: 16 }).map((_, i) => {
              const col = i % 4;
              const row = Math.floor(i / 4);
              const bx = 60 + col * 110;
              const by = 110 + row * 90;
              const a = interpolate(t3, [0.25 + i * 0.025, 0.5 + i * 0.025], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              return (
                <rect
                  key={`b${i}`}
                  x={bx}
                  y={by}
                  width={70}
                  height={56}
                  rx={4}
                  fill={`${colors.cool}22`}
                  stroke={colors.cool}
                  strokeWidth={1.5}
                  opacity={a}
                />
              );
            })}
            {/* furniture dots */}
            {Array.from({ length: 8 }).map((_, i) => {
              const a = interpolate(t3, [0.55 + i * 0.02, 0.7 + i * 0.02], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              return (
                <circle
                  key={`f${i}`}
                  cx={80 + (i % 4) * 120}
                  cy={i < 4 ? 80 : 400}
                  r={5}
                  fill={colors.teal}
                  opacity={a}
                />
              );
            })}
          </svg>

          {/* tree icon bounces OFF a rooftop */}
          {(() => {
            const bp = interpolate(t3, [0.6, 0.78], [0, 1], {
              easing: EASE,
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const bounceY = -Math.sin(bp * Math.PI) * 90;
            return (
              <div
                style={{
                  position: "absolute",
                  left: 130,
                  top: 150,
                  transform: `translateY(${bounceY}px)`,
                  opacity: bp,
                  fontSize: 38,
                }}
              >
                <svg width={40} height={48}>
                  <rect x={17} y={30} width={6} height={16} fill={colors.amber} />
                  <circle cx={20} cy={20} r={16} fill={colors.canopy} />
                </svg>
              </div>
            );
          })()}
          <div
            style={{
              position: "absolute",
              left: 180,
              top: 110,
              fontFamily: fonts.mono,
              fontSize: 17,
              color: colors.textDim,
              opacity: interpolate(t3, [0.7, 0.85], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            no roofs, no traffic
          </div>
        </div>

        {/* arbrat viari species table */}
        <div style={{ position: "absolute", left: 720, top: 330, width: 700 }}>
          <div
            style={{
              opacity: interpolate(t3, [0.2, 0.4], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            <Panel style={{ padding: "22px 26px" }} glow={`${colors.canopy}2A`}>
              <div
                style={{
                  fontFamily: fonts.mono,
                  fontSize: 22,
                  fontWeight: 700,
                  color: colors.canopy,
                  letterSpacing: 1,
                  borderBottom: `1px solid ${colors.border}`,
                  paddingBottom: 12,
                  marginBottom: 10,
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <span>arbrat viari · 12 species</span>
                <span style={{ color: colors.textDim }}>street-tree inventory</span>
              </div>
              {SPECIES.map((sp, i) => {
                const a = interpolate(t3, [0.35 + i * 0.06, 0.5 + i * 0.06], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                });
                return (
                  <div
                    key={sp}
                    style={{
                      opacity: a,
                      transform: `translateX(${(1 - a) * 16}px)`,
                      display: "flex",
                      justifyContent: "space-between",
                      fontFamily: fonts.mono,
                      fontSize: 21,
                      color: colors.text,
                      padding: "7px 0",
                    }}
                  >
                    <span>
                      <span style={{ color: colors.canopy, marginRight: 12 }}>
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      {sp}
                    </span>
                    <span style={{ color: colors.textDim }}>plantable</span>
                  </div>
                );
              })}
              <div
                style={{
                  fontFamily: fonts.mono,
                  fontSize: 20,
                  color: colors.textMuted,
                  paddingTop: 8,
                  opacity: interpolate(t3, [0.85, 1], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  }),
                }}
              >
                … 12 species
              </div>
            </Panel>
          </div>
        </div>
      </Sequence>

      {/* ── BEAT 4: Padró population + 73 barris + re-stack ── */}
      <Sequence from={Math.floor(b3)} durationInFrames={Math.ceil(df - b3) + 2}>
        <div style={{ position: "absolute", left: 110, top: 340, width: 820 }}>
          <Label color={colors.gold} size={22}>
            PADRÓ REGISTER
          </Label>
          <div
            style={{
              fontFamily: fonts.display,
              fontSize: 128,
              fontWeight: 800,
              color: colors.text,
              letterSpacing: -4,
              lineHeight: 1,
              marginTop: 8,
              textShadow: `0 0 60px ${colors.gold}33`,
            }}
          >
            <Counter
              startFrame={Math.floor(b3) + 4}
              durationInFrames={48}
              to={1702814}
              format={(v) => Math.round(v).toLocaleString("en-US")}
            />
          </div>
          <div style={{ marginTop: 6 }}>
            <Label color={colors.textDim} size={26}>
              Padró: 1,702,814 residents
            </Label>
          </div>

          {/* 73 barris dots */}
          <div
            style={{
              marginTop: 34,
              display: "grid",
              gridTemplateColumns: "repeat(15, 1fr)",
              gap: 12,
              width: 560,
            }}
          >
            {Array.from({ length: 73 }).map((_, i) => {
              const a = interpolate(t4, [0.25 + (i / 73) * 0.45, 0.4 + (i / 73) * 0.45], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              return (
                <div
                  key={i}
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: 999,
                    background: colors.gold,
                    opacity: a * 0.9,
                    transform: `scale(${0.4 + a * 0.6})`,
                  }}
                />
              );
            })}
          </div>
          <div style={{ marginTop: 16 }}>
            <Chip color={colors.gold} size={20}>
              73 barris
            </Chip>
          </div>
        </div>

        {/* re-stacked four layers + closing line */}
        <div style={{ position: "absolute", left: 1080, top: 360 }}>
          {LAYERS.map((_, i) => {
            const a = interpolate(t4, [0.45 + i * 0.06, 0.6 + i * 0.06], [0, 1], {
              easing: EASE,
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <div key={i} style={{ opacity: a }}>
                <LayerCard index={i} appear={1} fanned={false} />
              </div>
            );
          })}
        </div>
        <div
          style={{
            position: "absolute",
            left: 1080,
            top: 700,
            opacity: interpolate(t4, [0.78, 0.95], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          <Headline size={48}>Four maps. One real city.</Headline>
        </div>
      </Sequence>
    </AbsoluteFill>
  );
};
