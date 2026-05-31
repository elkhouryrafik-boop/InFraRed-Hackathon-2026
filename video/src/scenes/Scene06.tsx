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
import { Kicker, Headline, Chip, Stat, Panel, GlossCard, Tag, Label } from "../components/kit";
import { Reveal } from "../components/Reveal";
import { Counter } from "../components/Counter";

// ── SCENE 06 — "No Invasives, No London Plane" ───────────────────────────────
// A hard PLANTABILITY GATE removes invasive + over-represented species BEFORE
// optimisation; survivors get an ecological HEALTH SCORE; a 40% anti-monoculture
// cap protects the plan. Three beats across the full df.
//
//   BEAT 1 (0–40%)  THE GATE — a 12-row species table; a scanning bar sweeps
//                   top→bottom; 3 invasives flash "VETOED" and slide out;
//                   London plane gets an amber PHASE-DOWN tag; counter 12→8;
//                   the 8 survivors snap into a clean green palette grid.
//   BEAT 2 (40–72%) HEALTH SCORE — zoom one survivor card; a stacked weight bar
//                   assembles labelled benefits (sum 1.0); grey penalty notches
//                   subtract; an invasive's bar is driven to 0 by a −0.30 veto.
//   BEAT 3 (72–100%) THE 40% CAP — nine tree icons drop; a MAX 40% ceiling line;
//                   after a 4-tree grace the cap binds and a 5th-same icon is
//                   swapped to another species. End card over the 8 palette.

// ── the 12 candidate species (Latin) — 3 invasive, 1 over-represented ──
type Sp = {
  name: string;
  status: "ok" | "invasive" | "phasedown";
  hue: string; // survivor palette colour
};

const SPECIES: Sp[] = [
  { name: "Celtis australis", status: "ok", hue: colors.canopy },
  { name: "Robinia pseudoacacia", status: "invasive", hue: colors.heat },
  { name: "Cercis siliquastrum", status: "ok", hue: colors.canopyBright },
  { name: "Ligustrum lucidum", status: "invasive", hue: colors.heat },
  { name: "Brachychiton populneus", status: "ok", hue: colors.teal },
  { name: "Platanus × acerifolia", status: "phasedown", hue: colors.amber },
  { name: "Styphnolobium japonicum", status: "ok", hue: colors.canopy },
  { name: "Tipuana tipu", status: "ok", hue: colors.cool },
  { name: "Ulmus pumila", status: "invasive", hue: colors.heat },
  { name: "Jacaranda mimosifolia", status: "ok", hue: colors.canopyBright },
  { name: "Melia azedarach", status: "ok", hue: colors.teal },
  { name: "Tilia × europaea", status: "ok", hue: colors.cool },
];

const SURVIVORS = SPECIES.filter((s) => s.status === "ok");

// benefit segments (sum to 1.00) + grey penalty notches
const BENEFITS = [
  { label: "drought", w: 0.3, color: colors.amber },
  { label: "biodiversity", w: 0.2, color: colors.canopy },
  { label: "pollinator", w: 0.2, color: colors.canopyBright },
  { label: "longevity", w: 0.15, color: colors.teal },
  { label: "native", w: 0.15, color: colors.cool },
];
const PENALTIES = [
  { label: "allergen", w: 0.15 },
  { label: "pest", w: 0.1 },
  { label: "water", w: 0.1 },
  { label: "maint", w: 0.1 },
];

const TABLE = { x: 110, y: 250, w: 980, rowH: 50 };
const rowY = (i: number) => TABLE.y + i * TABLE.rowH;

export const Scene06: React.FC<{ df: number }> = ({ df }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  void fps;

  const b1 = df * 0.4;
  const b2 = df * 0.72;

  const intro = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ fontFamily: fonts.display }}>
      {/* persistent header */}
      <div style={{ position: "absolute", top: 80, left: 110, opacity: intro }}>
        <Kicker color={colors.heat}>THE PLANTABILITY GATE</Kicker>
        <div style={{ height: 14 }} />
        <BeatTitle frame={frame} b1={b1} b2={b2} />
      </div>

      <GateBeat frame={frame} df={df} b1={b1} />
      <HealthBeat frame={frame} df={df} b1={b1} b2={b2} />
      <CapBeat frame={frame} df={df} b2={b2} />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
const BeatTitle: React.FC<{ frame: number; b1: number; b2: number }> = ({
  frame,
  b1,
  b2,
}) => {
  const titles = [
    { at: 0, text: "12 → 8 SPECIES", color: colors.heat },
    { at: b1, text: "HEALTH SCORE", color: colors.canopyBright },
    { at: b2, text: "MAX 40% ONE SPECIES", color: colors.gold },
  ];
  let idx = 0;
  for (let i = 0; i < titles.length; i++) if (frame >= titles[i].at) idx = i;
  const t = titles[idx];
  const since = frame - t.at;
  const op = interpolate(since, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const dy = interpolate(since, [0, 18], [16, 0], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div style={{ opacity: op, transform: `translateY(${dy}px)` }}>
      <Headline size={64} color={t.color}>
        {t.text}
      </Headline>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BEAT 1 — the gate: scan, veto, phase-down, 12→8, survivor palette grid.
const GateBeat: React.FC<{ frame: number; df: number; b1: number }> = ({
  frame,
  df,
  b1,
}) => {
  const active = frame < b1 + 40;
  const op = interpolate(frame, [b1 + 8, b1 + 36], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (!active) return null;

  // table reveal
  const tableOp = interpolate(frame, [10, 26], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // scanning gate bar sweeps top→bottom over most of the beat
  const scanStart = 36;
  const scanEnd = b1 * 0.78;
  const scanT = interpolate(frame, [scanStart, scanEnd], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scanRow = scanT * SPECIES.length; // continuous row index the bar is at
  const scanYpos = TABLE.y + scanRow * TABLE.rowH;

  // a flagged row "fires" once the scan bar has passed its centre
  const firedAt = (i: number) =>
    scanStart + ((i + 0.5) / SPECIES.length) * (scanEnd - scanStart);

  // counter 12→8 morph window (right after the scan completes)
  const countStart = scanEnd + 6;
  const countDur = 22;

  // survivor palette grid assembles after the count
  const gridStart = countStart + countDur + 8;

  return (
    <AbsoluteFill style={{ opacity: op }}>
      {/* the table (left) */}
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, opacity: tableOp }}>
        {SPECIES.map((sp, i) => {
          const fAt = firedAt(i);
          const fired = frame >= fAt;
          const flagged = sp.status !== "ok";

          // slide-out for vetoed, dim-out for phase-down
          const exitT = fired
            ? interpolate(frame - fAt, [12, 32], [0, 1], {
                easing: Easing.in(Easing.cubic),
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            : 0;
          const slideX = sp.status === "invasive" ? exitT * 520 : 0;
          const rowOp = flagged
            ? sp.status === "invasive"
              ? 1 - exitT
              : 1 - exitT * 0.62
            : 1;

          // row reveal stagger
          const rev = interpolate(frame, [12 + i * 2, 26 + i * 2], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          // is the scan bar currently over this row?
          const hot = Math.abs(scanRow - (i + 0.5)) < 0.6 ? 1 : 0;
          const y = rowY(i);

          const stampColor =
            sp.status === "invasive" ? colors.heat : sp.status === "phasedown" ? colors.amber : sp.hue;

          return (
            <g key={i} opacity={rev * rowOp} transform={`translate(${slideX} 0)`}>
              <rect
                x={TABLE.x}
                y={y + 4}
                width={TABLE.w}
                height={TABLE.rowH - 8}
                rx={9}
                fill={fired && flagged ? `${stampColor}1f` : "rgba(255,255,255,0.025)"}
                stroke={fired && flagged ? stampColor : hot ? colors.canopy : colors.hairline}
                strokeWidth={hot || (fired && flagged) ? 1.8 : 1}
              />
              {/* tiny leaf glyph */}
              <Leaf x={TABLE.x + 30} y={y + TABLE.rowH / 2} color={flagged && fired ? stampColor : sp.hue} />
              {/* latin name */}
              <text
                x={TABLE.x + 56}
                y={y + TABLE.rowH / 2 + 8}
                fill={fired && flagged ? stampColor : colors.text}
                fontFamily={fonts.display}
                fontStyle="italic"
                fontSize={26}
                fontWeight={500}
                style={{
                  textDecoration: sp.status === "invasive" && fired ? "line-through" : "none",
                }}
              >
                {sp.name}
              </text>

              {/* stamps */}
              {sp.status === "invasive" && fired && (
                <g
                  opacity={interpolate(frame - fAt, [0, 8], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })}
                >
                  <rect
                    x={TABLE.x + 470}
                    y={y + 11}
                    width={486}
                    height={TABLE.rowH - 22}
                    rx={7}
                    fill={colors.heat}
                  />
                  <text
                    x={TABLE.x + 470 + 243}
                    y={y + TABLE.rowH / 2 + 6}
                    fill={colors.bg}
                    fontFamily={fonts.mono}
                    fontSize={19}
                    fontWeight={700}
                    textAnchor="middle"
                    letterSpacing={1}
                  >
                    EXOTIC-INVASIVE — VETOED
                  </text>
                </g>
              )}
              {sp.status === "phasedown" && fired && (
                <g
                  opacity={interpolate(frame - fAt, [0, 8], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })}
                >
                  <rect
                    x={TABLE.x + 360}
                    y={y + 11}
                    width={596}
                    height={TABLE.rowH - 22}
                    rx={7}
                    fill="rgba(245,166,35,0.16)"
                    stroke={colors.amber}
                    strokeWidth={1.4}
                  />
                  <text
                    x={TABLE.x + 360 + 16}
                    y={y + TABLE.rowH / 2 + 6}
                    fill={colors.amber}
                    fontFamily={fonts.mono}
                    fontSize={16}
                    fontWeight={700}
                  >
                    PHASE-DOWN — ≈25% of BCN street trees, high allergy/disease
                  </text>
                </g>
              )}
            </g>
          );
        })}

        {/* scanning GATE bar */}
        {scanT > 0 && scanT < 1 && (
          <g>
            <rect
              x={TABLE.x - 16}
              y={scanYpos - 3}
              width={TABLE.w + 32}
              height={6}
              rx={3}
              fill={colors.canopyBright}
              opacity={0.9}
            />
            <rect
              x={TABLE.x - 16}
              y={scanYpos - 22}
              width={TABLE.w + 32}
              height={44}
              rx={6}
              fill={colors.canopyGlow}
              opacity={0.4}
            />
            <text
              x={TABLE.x - 24}
              y={scanYpos + 6}
              fill={colors.canopyBright}
              fontFamily={fonts.mono}
              fontSize={18}
              fontWeight={700}
              textAnchor="end"
            >
              GATE
            </text>
          </g>
        )}
      </svg>

      {/* 12 → 8 counter (right) */}
      <div style={{ position: "absolute", top: 280, left: 1240, width: 560 }}>
        <Reveal startFrame={Math.round(b1 * 0.1)} translateY={18}>
          <Panel style={{ padding: "26px 30px" }} glow={colors.heatGlow}>
            <Label color={colors.textDim} size={20}>
              CANDIDATE SPECIES
            </Label>
            <div style={{ height: 12 }} />
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 22,
                fontFamily: fonts.display,
                fontWeight: 800,
                fontSize: 110,
                lineHeight: 1,
                letterSpacing: -3,
              }}
            >
              <span style={{ color: colors.heat }}>
                <Counter
                  from={12}
                  to={8}
                  startFrame={Math.round(countStart)}
                  durationInFrames={countDur}
                  decimals={0}
                />
              </span>
              <span style={{ fontSize: 44, color: colors.textMuted, letterSpacing: 0 }}>
                survive
              </span>
            </div>
            <div style={{ height: 14 }} />
            <Tag kind="3 INVASIVES VETOED" color={colors.heat} />
            <div style={{ height: 10 }} />
            <Label color={colors.amber} size={18}>
              LONDON PLANE ≈ 25% → PHASED DOWN
            </Label>
          </Panel>
        </Reveal>

        <Sequence from={Math.round(b1 * 0.18)} durationInFrames={Math.round(df)}>
          <div style={{ marginTop: 22 }}>
            <Reveal startFrame={0} translateY={18}>
              <GlossCard
                term="HARD VETO"
                plain="Invasive or over-represented species are dropped BEFORE optimisation. The cooling engine never even gets to consider them."
                color={colors.heat}
              />
            </Reveal>
          </div>
        </Sequence>
      </div>

      {/* survivor palette grid snaps in after the count */}
      <SurvivorGrid frame={frame} start={gridStart} />
    </AbsoluteFill>
  );
};

// the 8 survivors snapping into a clean green palette grid (bottom band)
const SurvivorGrid: React.FC<{ frame: number; start: number }> = ({ frame, start }) => {
  const cols = 4;
  const cellW = 240;
  const cellH = 88;
  const gx = 110;
  const gy = 700;
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {SURVIVORS.map((sp, i) => {
        const at = start + i * 4;
        const sp2 = interpolate(frame, [at, at + 16], [0, 1], {
          easing: Easing.out(Easing.back(1.8)),
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const col = i % cols;
        const r = Math.floor(i / cols);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: gx + col * (cellW + 16),
              top: gy + r * (cellH + 14),
              width: cellW,
              height: cellH,
              opacity: sp2,
              transform: `translateY(${(1 - sp2) * 22}px) scale(${0.9 + sp2 * 0.1})`,
              borderRadius: 12,
              border: `1.5px solid ${sp.hue}`,
              background: `${sp.hue}16`,
              display: "flex",
              alignItems: "center",
              gap: 14,
              padding: "0 18px",
              boxSizing: "border-box",
            }}
          >
            <svg width={26} height={26} viewBox="-13 -13 26 26">
              <Leaf x={0} y={0} color={sp.hue} />
            </svg>
            <span
              style={{
                fontFamily: fonts.display,
                fontStyle: "italic",
                fontSize: 19,
                fontWeight: 600,
                color: colors.text,
                lineHeight: 1.1,
              }}
            >
              {sp.name}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BEAT 2 — health score: stacked benefit bar, penalty notches, invasive → 0.
const HealthBeat: React.FC<{ frame: number; df: number; b1: number; b2: number }> = ({
  frame,
  df,
  b1,
  b2,
}) => {
  const active = frame >= b1 - 6 && frame < b2 + 30;
  const op = interpolate(frame, [b1 - 6, b1 + 18, b2, b2 + 26], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (!active) return null;

  const local = frame - b1;
  const span = b2 - b1;

  // bar geometry
  const barX = 130;
  const barY = 360;
  const barW = 1080;
  const barH = 92;

  // benefit segments assemble left→right
  const segStart = 16;
  const segGap = 14;
  const segDur = 16;

  // penalty notches subtract after benefits land
  const penStart = segStart + BENEFITS.length * segGap + 30;

  // running x cursor for benefit segments
  let cursor = 0;

  // final benefit total (1.0) and penalty total
  const penTotal = PENALTIES.reduce((s, p) => s + p.w, 0);

  return (
    <AbsoluteFill style={{ opacity: op }}>
      <div style={{ position: "absolute", top: 256, left: 130 }}>
        <Label color={colors.canopyBright} size={22}>
          ZOOM · Celtis australis — ecological HEALTH SCORE
        </Label>
      </div>

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* track */}
        <rect x={barX} y={barY} width={barW} height={barH} rx={12} fill="rgba(255,255,255,0.03)" stroke={colors.border} strokeWidth={1.5} />

        {/* benefit segments */}
        {BENEFITS.map((b, i) => {
          const segAt = segStart + i * segGap;
          const grow = interpolate(local, [segAt, segAt + segDur], [0, 1], {
            easing: Easing.out(Easing.cubic),
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const x0 = barX + cursor * barW;
          const fullW = b.w * barW;
          cursor += b.w;
          const w = fullW * grow;
          return (
            <g key={b.label} opacity={grow > 0 ? 1 : 0}>
              <rect x={x0} y={barY + 2} width={Math.max(0, w - 2)} height={barH - 4} rx={6} fill={b.color} opacity={0.9} />
              {grow > 0.5 && (
                <>
                  <text
                    x={x0 + fullW / 2}
                    y={barY + barH / 2 - 4}
                    fill={colors.bg}
                    fontFamily={fonts.mono}
                    fontSize={17}
                    fontWeight={700}
                    textAnchor="middle"
                  >
                    {b.label}
                  </text>
                  <text
                    x={x0 + fullW / 2}
                    y={barY + barH / 2 + 18}
                    fill={colors.bg}
                    fontFamily={fonts.mono}
                    fontSize={20}
                    fontWeight={700}
                    textAnchor="middle"
                  >
                    {b.w.toFixed(2)}
                  </text>
                </>
              )}
            </g>
          );
        })}

        {/* penalty notches subtract from the right end */}
        {PENALTIES.map((p, i) => {
          const penAt = penStart + i * 12;
          const grow = interpolate(local, [penAt, penAt + 14], [0, 1], {
            easing: Easing.out(Easing.cubic),
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          // place notches just below the bar as grey deductions
          const slotW = (barW * penTotal) / PENALTIES.length;
          const x0 = barX + barW - barW * penTotal + i * slotW;
          return (
            <g key={p.label} opacity={grow}>
              <rect
                x={x0 + 3}
                y={barY + barH + 16}
                width={(slotW - 6)}
                height={26}
                rx={5}
                fill="rgba(244,247,244,0.10)"
                stroke={colors.textMuted}
                strokeWidth={1.2}
              />
              <text
                x={x0 + slotW / 2}
                y={barY + barH + 16 + 18}
                fill={colors.textDim}
                fontFamily={fonts.mono}
                fontSize={15}
                fontWeight={600}
                textAnchor="middle"
              >
                −{p.label} {p.w.toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* benefits sum = 1.00 bracket */}
        {local > segStart + BENEFITS.length * segGap && (
          <g
            opacity={interpolate(local, [penStart - 14, penStart], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })}
          >
            <text x={barX + barW / 2} y={barY - 18} fill={colors.canopyBright} fontFamily={fonts.mono} fontSize={20} fontWeight={700} textAnchor="middle">
              benefits sum = 1.00
            </text>
          </g>
        )}

        {/* CONTRAST: an invasive species' bar driven to zero by a −0.30 veto */}
        <g
          opacity={interpolate(local, [span * 0.55, span * 0.55 + 16], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })}
        >
          <text x={barX} y={barY + 220} fill={colors.heat} fontFamily={fonts.mono} fontSize={20} fontWeight={700}>
            Robinia pseudoacacia (invasive)
          </text>
          {/* its would-be bar collapses to zero */}
          {(() => {
            const collapse = interpolate(local, [span * 0.6, span * 0.78], [1, 0], {
              easing: Easing.in(Easing.cubic),
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const fullW = 0.6 * barW;
            return (
              <>
                <rect x={barX} y={barY + 238} width={barW} height={60} rx={10} fill="rgba(255,255,255,0.03)" stroke={colors.border} strokeWidth={1.5} />
                <rect x={barX + 2} y={barY + 240} width={Math.max(0, fullW * collapse - 2)} height={56} rx={8} fill={colors.heat} opacity={0.55} />
                {/* the −0.30 veto block driving it down */}
                <rect x={barX + 2} y={barY + 240} width={Math.max(0, fullW * collapse - 2)} height={56} rx={8} fill="url(#none)" />
                <rect
                  x={barX + fullW + 24}
                  y={barY + 240}
                  width={300}
                  height={56}
                  rx={9}
                  fill={colors.heat}
                  opacity={interpolate(local, [span * 0.58, span * 0.66], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })}
                />
                <text
                  x={barX + fullW + 24 + 150}
                  y={barY + 240 + 36}
                  fill={colors.bg}
                  fontFamily={fonts.mono}
                  fontSize={22}
                  fontWeight={700}
                  textAnchor="middle"
                  opacity={interpolate(local, [span * 0.58, span * 0.66], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })}
                >
                  −0.30 INVASIVE VETO
                </text>
                {collapse < 0.06 && (
                  <text x={barX + 20} y={barY + 240 + 36} fill={colors.text} fontFamily={fonts.mono} fontSize={26} fontWeight={800}>
                    SCORE → 0
                  </text>
                )}
              </>
            );
          })()}
        </g>
      </svg>

      {/* readout panel (right) */}
      <div style={{ position: "absolute", top: 256, left: 1280, width: 520 }}>
        <Reveal startFrame={Math.round(b1 + 8)} translateY={18}>
          <Panel style={{ padding: "24px 28px" }} glow={colors.canopyGlow}>
            <Label color={colors.canopyBright} size={19}>
              WEIGHTING
            </Label>
            <div style={{ height: 10 }} />
            <div style={{ fontFamily: fonts.mono, fontSize: 20, lineHeight: 1.7, color: colors.text }}>
              drought 0.30 · biodiversity 0.20 · pollinator 0.20 · longevity 0.15 · native 0.15
            </div>
            <div style={{ height: 16 }} />
            <Tag kind="INVASIVE = −0.30 HARD VETO" color={colors.heat} />
          </Panel>
        </Reveal>
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BEAT 3 — the 40% cap: nine icons drop, ceiling line, swap the 5th-same.
const CapBeat: React.FC<{ frame: number; df: number; b2: number }> = ({
  frame,
  df,
  b2,
}) => {
  const active = frame >= b2 - 6;
  if (!active) return null;
  const op = interpolate(frame, [b2 - 6, b2 + 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const local = frame - b2;
  const span = df - b2;

  // nine slots in a row
  const N = 9;
  const rowX = 200;
  const rowY3 = 480;
  const gap = 160;
  const slotX = (i: number) => rowX + i * gap;

  // first 4 are the same species (within the 40% grace), then cap binds.
  // the 5th would be the same but is SWAPPED to a different species.
  const sameHue = colors.canopy;
  const swapHue = colors.cool;

  const dropAt = (i: number) => 14 + i * 9;

  // ceiling line appears
  const ceilT = interpolate(local, [span * 0.34, span * 0.34 + 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // the swap animates on the 5th icon (index 4)
  const swapT = interpolate(local, [span * 0.5, span * 0.5 + 20], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const endSp = spring({
    frame: local - span * 0.7,
    fps: FPS,
    config: { damping: 14, stiffness: 110 },
  });

  return (
    <AbsoluteFill style={{ opacity: op }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* MAX 40% ceiling line above the row */}
        <g opacity={ceilT}>
          <line
            x1={rowX - 50}
            y1={rowY3 - 110}
            x2={slotX(N - 1) + 50}
            y2={rowY3 - 110}
            stroke={colors.gold}
            strokeWidth={2.5}
            strokeDasharray="10 7"
          />
          <text x={rowX - 50} y={rowY3 - 122} fill={colors.gold} fontFamily={fonts.mono} fontSize={22} fontWeight={700}>
            MAX 40% · one species
          </text>
        </g>

        {/* the nine tree icons */}
        {Array.from({ length: N }).map((_, i) => {
          const drop = interpolate(local, [dropAt(i), dropAt(i) + 18], [0, 1], {
            easing: Easing.out(Easing.bounce),
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const y = rowY3 - (1 - drop) * 160;
          const x = slotX(i);

          // index 4 is the would-be-5th-of-same; colour morphs same→swap
          const isSwap = i === 4;
          const hue = isSwap ? mix(sameHue, swapHue, swapT) : i < 4 ? sameHue : swapHue;

          return (
            <g key={i} transform={`translate(${x} ${y})`} opacity={drop}>
              <TreeIcon color={hue} scale={isSwap ? 1 + swapT * 0.06 : 1} />
              {isSwap && swapT > 0.2 && (
                <g opacity={swapT}>
                  <circle cx={0} cy={-86} r={3} fill={colors.gold} />
                </g>
              )}
            </g>
          );
        })}

        {/* callout on the swapped icon */}
        <g
          opacity={interpolate(local, [span * 0.58, span * 0.58 + 16], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })}
        >
          <line x1={slotX(4)} y1={rowY3 + 70} x2={slotX(4)} y2={rowY3 + 120} stroke={colors.gold} strokeWidth={1.6} />
          <rect x={slotX(4) - 250} y={rowY3 + 120} width={500} height={68} rx={10} fill="rgba(8,11,16,0.9)" stroke={colors.gold} strokeWidth={1.6} />
          <text x={slotX(4)} y={rowY3 + 120 + 28} fill={colors.gold} fontFamily={fonts.mono} fontSize={19} fontWeight={700} textAnchor="middle">
            MAX 40% ONE SPECIES
          </text>
          <text x={slotX(4)} y={rowY3 + 120 + 52} fill={colors.textDim} fontFamily={fonts.mono} fontSize={16} textAnchor="middle">
            after a 4-tree grace → 5th swapped to another species
          </text>
        </g>
      </svg>

      {/* end card */}
      <div
        style={{
          position: "absolute",
          top: 740,
          left: 110,
          width: 1700,
          opacity: Math.min(1, endSp),
          transform: `translateY(${(1 - Math.min(1, endSp)) * 20}px)`,
        }}
      >
        <Headline size={54} color={colors.text}>
          <span style={{ color: colors.canopyBright }}>ECOLOGY-REAL</span>, not just{" "}
          <span style={{ color: colors.cool }}>cool</span>.
        </Headline>
        <div style={{ height: 18 }} />
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {SURVIVORS.map((sp, i) => {
            const ch = interpolate(local, [span * 0.72 + i * 3, span * 0.72 + i * 3 + 12], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <div key={i} style={{ opacity: ch, transform: `translateY(${(1 - ch) * 10}px)` }}>
                <Chip color={sp.hue} size={18}>
                  {sp.name}
                </Chip>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// little SVG atoms

// tiny leaf glyph (drawn around given centre x,y)
const Leaf: React.FC<{ x: number; y: number; color: string }> = ({ x, y, color }) => (
  <g transform={`translate(${x} ${y})`}>
    <path
      d="M 0 -9 C 7 -6 7 6 0 10 C -7 6 -7 -6 0 -9 Z"
      fill={color}
      opacity={0.85}
    />
    <line x1={0} y1={-2} x2={0} y2={9} stroke={colors.bg} strokeWidth={1.2} opacity={0.5} />
  </g>
);

// simple kinetic tree icon (canopy circle + trunk)
const TreeIcon: React.FC<{ color: string; scale?: number }> = ({ color, scale = 1 }) => (
  <g transform={`scale(${scale})`}>
    <rect x={-6} y={4} width={12} height={34} rx={3} fill={mix(color, colors.bg, 0.45)} />
    <circle cx={0} cy={-22} r={40} fill={`${color}22`} />
    <circle cx={0} cy={-22} r={30} fill={`${color}55`} />
    <circle cx={0} cy={-22} r={20} fill={color} stroke={colors.bg} strokeWidth={2} />
  </g>
);

// ─────────────────────────────────────────────────────────────────────────────
// linear blend of two hex/rgba colours → rgba string
function mix(a: string, b: string, t: number): string {
  const pa = parseColor(a);
  const pb = parseColor(b);
  const r = Math.round(pa[0] + (pb[0] - pa[0]) * t);
  const g = Math.round(pa[1] + (pb[1] - pa[1]) * t);
  const bl = Math.round(pa[2] + (pb[2] - pa[2]) * t);
  const al = pa[3] + (pb[3] - pa[3]) * t;
  return `rgba(${r},${g},${bl},${al.toFixed(3)})`;
}

function parseColor(s: string): [number, number, number, number] {
  if (s.startsWith("#")) {
    const h = s.slice(1);
    return [
      parseInt(h.slice(0, 2), 16),
      parseInt(h.slice(2, 4), 16),
      parseInt(h.slice(4, 6), 16),
      1,
    ];
  }
  const m = s.match(/rgba?\(([^)]+)\)/);
  if (m) {
    const parts = m[1].split(",").map((p) => parseFloat(p.trim()));
    return [parts[0], parts[1], parts[2], parts[3] ?? 1];
  }
  return [255, 255, 255, 1];
}
