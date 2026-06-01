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

// ── SCENE 05 — "The Greedy Shade-Gain Engine" ──
// The technical centerpiece. PICKS[] is the pre-baked greedy result, but every
// number is animated from its source on screen. See the 4-act breakdown below.
// The technical heart of the film: the SHIPPED placement method =
// budgeted weighted-maximum-coverage GREEDY with ray-cast shade-gain and the
// submodular (1 − 1/e) guarantee. Four acts laid across the full df.
//
// Top-down schematic of a small plaza. A 16×12 grid of ground cells.
//   ACT 1 (0–28%)  THE DEMAND FIELD — three condition chips stamp on; surviving
//                  cells glow on a heat ramp; hottest cells float weight = UTCI−26.
//   ACT 2 (28–55%) SHADE-GAIN — drop one tree, sweep a low July sun arc across the
//                  south, cast shadow ellipses NORTH, tally shade-gain 0→0.6, then
//                  slide the tree SOUTH of the hotspot for a higher capture.
//   ACT 3 (55–80%) THE GREEDY — ghost candidates with gain/euro chips; best pulses
//                  and is placed; captured cells dim to "already cooled"; next gain
//                  shrinks; a live concave curve = "submodular".
//   ACT 4 (80–100%) GUARANTEE + STOP — dashed OPTIMUM line + 63% band + formula +
//                  cite; two real stop conditions vs a struck-through fixed cap.

// ── plaza geometry (top-down board) ──
const GRID_COLS = 16;
const GRID_ROWS = 12;
const BOARD = { x: 110, y: 250, w: 1180, h: 600 }; // demand field board (left)
const CELL_W = BOARD.w / GRID_COLS;
const CELL_H = BOARD.h / GRID_ROWS;

const cx = (c: number) => BOARD.x + (c + 0.5) * CELL_W;
const cy = (r: number) => BOARD.y + (r + 0.5) * CELL_H;

// Deterministic pseudo-random so the field is stable across renders.
const rnd = (seed: number) => {
  const s = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
};

// Synthesize a per-cell UTCI field with a clear hot cluster, plus masks.
type Cell = {
  c: number;
  r: number;
  utci: number; // felt temperature
  impervious: boolean; // paved (depavable) vs already green
  preShaded: boolean; // already under existing canopy
};

const CELLS: Cell[] = (() => {
  const out: Cell[] = [];
  // hot cluster centred slightly north-of-centre so shadows have room to fall north
  const hotC = 9.5;
  const hotR = 6.2;
  for (let r = 0; r < GRID_ROWS; r++) {
    for (let c = 0; c < GRID_COLS; c++) {
      const d = Math.hypot((c - hotC) / 5.2, (r - hotR) / 4.0);
      const base = 33.5 - d * 9.5 + (rnd(c * 13 + r * 7) - 0.5) * 2.2;
      const utci = Math.max(21, Math.min(34, base));
      const impervious = rnd(c * 5 + r * 17) > 0.16; // mostly paved plaza
      const preShaded = rnd(c * 31 + r * 3) > 0.9; // a few cells under old trees
      out.push({ c, r, utci, impervious, preShaded });
    }
  }
  return out;
})();

const isDemand = (cell: Cell) => cell.utci > 26 && cell.impervious && !cell.preShaded;
const weight = (cell: Cell) => cell.utci - 26;

// Greedy picks (south-of-cluster, gains diminishing) — pre-baked but each derived
// number is animated from its source on screen.
const PICKS = [
  { c: 9.4, r: 9.0, gain: 0.62, eur: 0.41, cooled: 31 },
  { c: 6.2, r: 8.4, gain: 0.41, eur: 0.27, cooled: 52 },
  { c: 12.4, r: 8.7, gain: 0.30, eur: 0.20, cooled: 67 },
  { c: 9.0, r: 6.0, gain: 0.18, eur: 0.12, cooled: 76 },
  { c: 4.6, r: 6.3, gain: 0.10, eur: 0.067, cooled: 82 },
];

export const Scene05: React.FC<{ df: number }> = ({ df }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  void fps;

  // Act boundaries in frames.
  const a1 = df * 0.28;
  const a2 = df * 0.55;
  const a3 = df * 0.8;

  // Global progress eased in.
  const intro = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ fontFamily: fonts.display }}>
      {/* ── persistent header ── */}
      <div style={{ position: "absolute", top: 80, left: 110, opacity: intro }}>
        <Kicker color={colors.heat}>THE PLACEMENT ENGINE</Kicker>
        <div style={{ height: 14 }} />
        <ActTitle frame={frame} a1={a1} a2={a2} a3={a3} df={df} />
      </div>

      {/* ── the board itself is shared across acts ── */}
      <DemandField frame={frame} df={df} a1={a1} a2={a2} a3={a3} />

      {/* ── ACT 2 overlay: sun arc + tree + shade ── */}
      <ShadeGainAct frame={frame} df={df} a1={a1} a2={a2} />

      {/* ── ACT 3 overlay: ghost candidates + placed trees + curve ── */}
      <GreedyAct frame={frame} df={df} a2={a2} a3={a3} />

      {/* ── ACT 4 overlay: guarantee band + stop conditions ── */}
      <GuaranteeAct frame={frame} df={df} a3={a3} />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Header act title that swaps per act.
const ActTitle: React.FC<{
  frame: number;
  a1: number;
  a2: number;
  a3: number;
  df: number;
}> = ({ frame, a1, a2, a3 }) => {
  const titles = [
    { at: 0, text: "THE DEMAND FIELD", color: colors.heat },
    { at: a1, text: "SHADE-GAIN", color: colors.canopyBright },
    { at: a2, text: "GAIN PER EURO", color: colors.gold },
    { at: a3, text: "STOPS ON A REAL CONDITION", color: colors.cool },
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
// ACT 1 + shared board: the demand field.
const DemandField: React.FC<{
  frame: number;
  df: number;
  a1: number;
  a2: number;
  a3: number;
}> = ({ frame, df, a1, a2, a3 }) => {
  // condition chips tick on in sequence during act 1
  const condStart = 24;
  const condGap = (a1 - condStart - 30) / 3;
  const conds = [
    { label: "UTCI > 26 °C", at: condStart },
    { label: "impervious", at: condStart + condGap },
    { label: "not already shaded", at: condStart + condGap * 2 },
  ];

  // how many conditions are "active" (used to mask cells progressively)
  const activeConds = conds.filter((c) => frame >= c.at + 10).length;

  // board appears
  const boardOp = interpolate(frame, [12, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // capture sets from acts 2/3 to dim "already cooled" cells later
  const cooledCells = useCooledCells(frame, df, a2, a3);

  return (
    <>
      {/* condition chips above the board */}
      <div
        style={{
          position: "absolute",
          top: 196,
          left: 110,
          display: "flex",
          gap: 14,
        }}
      >
        {conds.map((cd, i) => {
          const on = frame >= cd.at;
          const sp = on
            ? interpolate(frame - cd.at, [0, 10], [0, 1], {
                easing: Easing.out(Easing.back(1.6)),
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            : 0;
          // fade chips out once we leave act 1
          const fade = interpolate(frame, [a1, a1 + 24], [1, 0.32], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={i}
              style={{
                opacity: sp * fade,
                transform: `translateY(${(1 - sp) * 12}px) scale(${0.9 + sp * 0.1})`,
              }}
            >
              <Chip color={colors.amber} solid={frame >= cd.at + 10} size={22}>
                {cd.label}
              </Chip>
            </div>
          );
        })}
      </div>

      {/* the board */}
      <svg
        width={1920}
        height={1080}
        style={{ position: "absolute", inset: 0, opacity: boardOp }}
      >
        {/* board frame */}
        <rect
          x={BOARD.x - 12}
          y={BOARD.y - 12}
          width={BOARD.w + 24}
          height={BOARD.h + 24}
          rx={14}
          fill="rgba(14,19,26,0.55)"
          stroke={colors.border}
          strokeWidth={1.5}
        />
        {/* compass: N up */}
        <g opacity={0.7}>
          <text
            x={BOARD.x + BOARD.w + 30}
            y={BOARD.y + 8}
            fill={colors.textDim}
            fontFamily={fonts.mono}
            fontSize={20}
          >
            N
          </text>
          <line
            x1={BOARD.x + BOARD.w + 34}
            y1={BOARD.y + 20}
            x2={BOARD.x + BOARD.w + 34}
            y2={BOARD.y + 70}
            stroke={colors.textMuted}
            strokeWidth={1.5}
          />
          <path
            d={`M ${BOARD.x + BOARD.w + 34} ${BOARD.y + 16} l -5 10 l 10 0 z`}
            fill={colors.textDim}
          />
        </g>

        {/* cells */}
        {CELLS.map((cell, i) => {
          const x = BOARD.x + cell.c * CELL_W;
          const y = BOARD.y + cell.r * CELL_H;
          // staggered reveal by distance from corner
          const delay = 12 + (cell.c + cell.r) * 0.5;
          const rev = interpolate(frame, [delay, delay + 14], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          const demand = isDemand(cell);
          // a cell "passes" only the conditions that are currently active
          const passUtci = cell.utci > 26;
          const passImperv = cell.impervious;
          const passShade = !cell.preShaded;
          const passes =
            (activeConds < 1 || passUtci) &&
            (activeConds < 2 || passImperv) &&
            (activeConds < 3 || passShade);

          // heat ramp intensity from weight
          const w = weight(cell);
          const heatT = interpolate(w, [0, 8], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const lit = demand && passes && activeConds >= 1;

          // is this cell now "already cooled" (acts 2-3)?
          const coolT = cooledCells.get(i) ?? 0;

          const baseFill = lit
            ? heatRamp(heatT)
            : "rgba(255,255,255,0.018)";
          const fill = coolT > 0 ? mix(baseFill, colors.canopy, coolT * 0.85) : baseFill;

          // glow for hottest demand cells
          const glow = lit ? 0.35 + heatT * 0.45 : 0.06;

          return (
            <g key={i} opacity={rev}>
              <rect
                x={x + 1.5}
                y={y + 1.5}
                width={CELL_W - 3}
                height={CELL_H - 3}
                rx={4}
                fill={fill}
                stroke={lit ? heatRamp(Math.min(1, heatT + 0.25)) : colors.hairline}
                strokeWidth={lit ? 1.2 : 1}
                style={{ filter: lit ? `brightness(${1 + glow * 0.3})` : undefined }}
              />
            </g>
          );
        })}

        {/* floating weight labels on the few hottest cells */}
        {hottestCells(3).map((cell, i) => {
          const labelAt = a1 - 60 + i * 12;
          const op = interpolate(frame, [labelAt, labelAt + 14, a1 + 10, a1 + 30], [0, 1, 1, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const u = Math.round(cell.utci);
          const w = u - 26;
          return (
            <g key={`w${i}`} opacity={op}>
              <rect
                x={cx(cell.c) - 78}
                y={cy(cell.r) - 18}
                width={156}
                height={34}
                rx={8}
                fill="rgba(8,11,16,0.86)"
                stroke={colors.heat}
                strokeWidth={1.2}
              />
              <text
                x={cx(cell.c)}
                y={cy(cell.r) + 5}
                fill={colors.text}
                fontFamily={fonts.mono}
                fontSize={18}
                fontWeight={600}
                textAnchor="middle"
              >
                weight = {u}−26 = {w}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Act 1 explainer caption (right column) */}
      <Sequence from={Math.round(a1 * 0.45)} durationInFrames={Math.round(a1)}>
        <div style={{ position: "absolute", top: 300, left: 1340, width: 470 }}>
          <Reveal startFrame={0} translateY={20}>
            <GlossCard
              term="DEMAND CELL"
              plain="Every ground cell that is genuinely hot, paved, and not already in shade. Only these can be 'cooled' — the rest are noise."
              color={colors.heat}
            />
          </Reveal>
          <div style={{ height: 18 }} />
          <Reveal startFrame={16} translateY={20}>
            <GlossCard
              term="weight = UTCI − 26"
              plain="Each demand cell is worth how far its felt-temperature exceeds the 26 °C comfort threshold. Hotter ground earns more weight."
              color={colors.amber}
            />
          </Reveal>
        </div>
      </Sequence>
    </>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ACT 2 — shade-gain: one tree, sun arc, shadow north, tally, slide south.
const ShadeGainAct: React.FC<{
  frame: number;
  df: number;
  a1: number;
  a2: number;
}> = ({ frame, df, a1, a2 }) => {
  const active = frame >= a1 - 10 && frame < a2 + 30;
  const op = interpolate(frame, [a1 - 10, a1 + 16, a2, a2 + 28], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (!active) return null;

  const local = frame - a1; // frames since act 2 start
  const span = a2 - a1;

  // the tree starts near the cluster centre, then SLIDES south at ~62% of act
  const slideStart = span * 0.6;
  const slideT = interpolate(local, [slideStart, slideStart + 26], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const treeC = 9.5;
  const treeR0 = 5.6; // inside the hot cluster (too far north → shadow misses)
  const treeR1 = 8.9; // south of the cluster → shadow falls onto the hot cells
  const treeR = treeR0 + (treeR1 - treeR0) * slideT;
  const tx = cx(treeC);
  const ty = cy(treeR);

  // sun sweeps low across the south (bottom). azimuth from SE → SW over the act.
  const sweepT = interpolate(local, [10, span * 0.55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const sunAngle = Math.PI * (0.18 + sweepT * 0.64); // 0..π across the bottom
  const arcR = 430;
  const arcCx = cx(treeC);
  const arcCy = BOARD.y + BOARD.h + 40; // arc centre below the board (south)
  const sunX = arcCx - Math.cos(sunAngle) * arcR;
  const sunY = arcCy - Math.sin(sunAngle) * arcR * 0.5;

  // shadow is opposite the sun → falls NORTH (above) the trunk
  const shadowLen = 92 + (1 - Math.sin(sunAngle)) * 70;
  const shDX = (tx - sunX) * 0.0;
  void shDX;
  const shadowAngle = Math.atan2(ty - sunY, tx - sunX);
  const shX = tx + Math.cos(shadowAngle) * shadowLen;
  const shY = ty + Math.sin(shadowAngle) * shadowLen;

  // shade-gain fraction climbs 0 → 0.6 over the act, jumps after the slide
  const baseGain = interpolate(local, [span * 0.12, span * 0.5], [0, 0.34], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const slideBoost = interpolate(slideT, [0, 1], [0, 0.28], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  void baseGain;
  void slideBoost;

  const treePop = interpolate(local, [4, 22], [0, 1], {
    easing: Easing.out(Easing.back(2)),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // which demand cells the shadow ellipse currently touches → light canopy
  const touched = CELLS.map((cell) => {
    if (!isDemand(cell)) return 0;
    const ex = cx(cell.c);
    const ey = cy(cell.r);
    const d = Math.hypot((ex - shX) / 96, (ey - shY) / 58);
    return d < 1 ? interpolate(d, [0, 1], [1, 0]) : 0;
  });

  const punch = interpolate(local, [slideStart - 8, slideStart + 8], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: op }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* sun arc track across the south */}
        <path
          d={describeArc(arcCx, arcCy, arcR, arcR * 0.5)}
          fill="none"
          stroke="rgba(245,166,35,0.28)"
          strokeWidth={2}
          strokeDasharray="6 8"
        />
        {/* sun */}
        <g>
          <circle cx={sunX} cy={sunY} r={26} fill={colors.amber} opacity={0.95} />
          <circle cx={sunX} cy={sunY} r={46} fill={colors.amber} opacity={0.16} />
          {/* sun ray to tree */}
          <line
            x1={sunX}
            y1={sunY}
            x2={tx}
            y2={ty}
            stroke="rgba(245,166,35,0.4)"
            strokeWidth={1.5}
            strokeDasharray="4 6"
          />
        </g>

        {/* canopy shadow ellipse (north of trunk) */}
        <ellipse
          cx={shX}
          cy={shY}
          rx={96}
          ry={58}
          fill={colors.canopyGlow}
          stroke={colors.canopy}
          strokeWidth={1.5}
          opacity={0.55}
        />

        {/* touched demand cells light canopy green */}
        {CELLS.map((cell, i) => {
          const t = touched[i];
          if (t <= 0) return null;
          return (
            <rect
              key={`tc${i}`}
              x={BOARD.x + cell.c * CELL_W + 1.5}
              y={BOARD.y + cell.r * CELL_H + 1.5}
              width={CELL_W - 3}
              height={CELL_H - 3}
              rx={4}
              fill={colors.canopy}
              opacity={0.18 + t * 0.55}
              stroke={colors.canopyBright}
              strokeWidth={1}
            />
          );
        })}

        {/* the candidate tree */}
        <g transform={`translate(${tx} ${ty}) scale(${treePop})`}>
          <circle r={30} fill={colors.canopy} opacity={0.25} />
          <circle r={20} fill={colors.canopyBright} opacity={0.5} />
          <circle r={9} fill={colors.canopy} stroke={colors.canopyBright} strokeWidth={2} />
        </g>

        {/* "July sun angles" label near the arc */}
        <text
          x={arcCx - arcR + 40}
          y={arcCy - 30}
          fill={colors.amber}
          fontFamily={fonts.mono}
          fontSize={20}
          opacity={0.9}
        >
          July sun angles · low from the south
        </text>
      </svg>

      {/* shade-gain readout panel (right) */}
      <div style={{ position: "absolute", top: 300, left: 1340, width: 470 }}>
        <Panel style={{ padding: "26px 30px" }} glow={colors.canopyGlow}>
          <Label color={colors.canopyBright} size={20}>
            SHADE-GAIN  (ray-cast)
          </Label>
          <div style={{ height: 10 }} />
          <div
            style={{
              fontFamily: fonts.display,
              fontWeight: 800,
              fontSize: 96,
              lineHeight: 1,
              letterSpacing: -2,
              color: colors.canopyBright,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            <Counter
              from={0}
              to={slideT > 0.05 ? 0.6 : 0.34}
              startFrame={Math.round(a1 + span * 0.12)}
              durationInFrames={Math.round(span * 0.7)}
              decimals={2}
            />
          </div>
          <div style={{ height: 6 }} />
          <Label color={colors.textDim} size={19}>
            fraction of demand-weight a tree's shadow actually covers
          </Label>
        </Panel>

        <div style={{ height: 18, opacity: punch }}>
          <div style={{ height: 18 }} />
          <Panel style={{ padding: "18px 22px" }} glow={colors.canopyGlow}>
            <div
              style={{
                fontFamily: fonts.display,
                fontSize: 28,
                fontWeight: 700,
                color: colors.text,
                lineHeight: 1.2,
              }}
            >
              shade falls north →{" "}
              <span style={{ color: colors.canopyBright }}>plant SOUTH of the hotspot</span>
            </div>
          </Panel>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ACT 3 — the greedy: ghost candidates, pick best gain/euro, dim cooled, curve.
const GreedyAct: React.FC<{
  frame: number;
  df: number;
  a2: number;
  a3: number;
}> = ({ frame, df, a2, a3 }) => {
  const active = frame >= a2 - 6 && frame < a3 + 30;
  const op = interpolate(frame, [a2 - 6, a2 + 18, a3, a3 + 26], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (!active) return null;

  const local = frame - a2;
  const span = a3 - a2;
  const perPick = span / (PICKS.length + 0.4);

  // index of pick currently being evaluated / placed
  const placedCount = Math.min(PICKS.length, Math.floor(local / perPick));

  return (
    <AbsoluteFill style={{ opacity: op }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* ghost candidates with gain/euro chips for the CURRENT round */}
        {placedCount < PICKS.length &&
          (() => {
            const roundStart = placedCount * perPick;
            const evalT = interpolate(local, [roundStart, roundStart + perPick * 0.45], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            // show this round's winner plus two faded alternatives
            const winner = PICKS[placedCount];
            if (!winner) return null;
            const alts = [
              { c: winner.c - 3.4, r: winner.r - 1.6, eur: winner.eur * 0.6 },
              { c: winner.c + 3.2, r: winner.r + 0.8, eur: winner.eur * 0.74 },
            ];
            const pulse = 0.6 + 0.4 * Math.sin(local * 0.4);
            return (
              <g opacity={evalT}>
                {alts.map((a, i) => (
                  <g key={`alt${i}`} opacity={0.4}>
                    <circle cx={cx(a.c)} cy={cy(a.r)} r={16} fill="none" stroke={colors.textMuted} strokeWidth={1.5} strokeDasharray="3 4" />
                    <GainChipSvg x={cx(a.c)} y={cy(a.r) - 30} value={a.eur} color={colors.textMuted} />
                  </g>
                ))}
                {/* winner pulses */}
                <circle
                  cx={cx(winner.c)}
                  cy={cy(winner.r)}
                  r={22 + pulse * 6}
                  fill="none"
                  stroke={colors.gold}
                  strokeWidth={2.5}
                  opacity={pulse}
                />
                <GainChipSvg x={cx(winner.c)} y={cy(winner.r) - 34} value={winner.eur} color={colors.gold} highlight />
              </g>
            );
          })()}

        {/* placed trees + their captured (now dimmed "already cooled") footprint */}
        {PICKS.slice(0, placedCount).map((p, i) => {
          const placedAt = i * perPick + perPick * 0.5;
          const pop = interpolate(local, [placedAt, placedAt + 16], [0, 1], {
            easing: Easing.out(Easing.back(2)),
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const dim = interpolate(local, [placedAt + 6, placedAt + 24], [0.6, 0.22], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <g key={`p${i}`}>
              {/* captured footprint dims to 'already cooled' */}
              <ellipse
                cx={cx(p.c)}
                cy={cy(p.r) - 24}
                rx={92}
                ry={56}
                fill={colors.canopy}
                opacity={dim * pop}
              />
              <g transform={`translate(${cx(p.c)} ${cy(p.r)}) scale(${pop})`}>
                <circle r={18} fill={colors.canopyBright} opacity={0.4} />
                <circle r={8} fill={colors.canopy} stroke={colors.canopyBright} strokeWidth={2} />
              </g>
            </g>
          );
        })}
      </svg>

      {/* live diminishing-returns curve (top-right corner) */}
      <DiminishingCurve frame={frame} a2={a2} a3={a3} placedCount={placedCount} local={local} perPick={perPick} />

      {/* gain-per-euro readout */}
      <div style={{ position: "absolute", top: 760, left: 130, display: "flex", gap: 16, alignItems: "center" }}>
        <Chip color={colors.gold} solid size={24}>
          gain per euro
        </Chip>
        <Label color={colors.textDim} size={22}>
          pick the highest · place it · its cells can't be cooled twice
        </Label>
      </div>
    </AbsoluteFill>
  );
};

// gain/euro chip drawn inside the SVG
const GainChipSvg: React.FC<{ x: number; y: number; value: number; color: string; highlight?: boolean }> = ({
  x,
  y,
  value,
  color,
  highlight,
}) => (
  <g>
    <rect
      x={x - 56}
      y={y - 17}
      width={112}
      height={32}
      rx={16}
      fill={highlight ? color : "rgba(8,11,16,0.82)"}
      stroke={color}
      strokeWidth={1.5}
    />
    <text
      x={x}
      y={y + 5}
      fill={highlight ? colors.bg : color}
      fontFamily={fonts.mono}
      fontSize={17}
      fontWeight={700}
      textAnchor="middle"
    >
      {value.toFixed(2)} m²/€
    </text>
  </g>
);

// live concave curve of cumulative cooled area vs trees placed
const DiminishingCurve: React.FC<{
  frame: number;
  a2: number;
  a3: number;
  placedCount: number;
  local: number;
  perPick: number;
}> = ({ a3, placedCount, local, perPick }) => {
  const chart = { x: 1360, y: 470, w: 450, h: 320 };
  // cumulative cooled fraction after each pick (concave)
  const cum = [0, ...PICKS.map((p) => p.cooled / 100)];
  const maxN = PICKS.length;

  const px = (n: number) => chart.x + (n / maxN) * chart.w;
  const py = (v: number) => chart.y + chart.h - v * chart.h;

  // how far along the curve we've drawn (continuous)
  const drawN = Math.min(maxN, local / perPick);

  // build polyline up to drawN
  const pts: [number, number][] = [];
  for (let n = 0; n <= Math.floor(drawN); n++) pts.push([px(n), py(cum[n])]);
  if (drawN > Math.floor(drawN) && Math.floor(drawN) < maxN) {
    const f = drawN - Math.floor(drawN);
    const n0 = Math.floor(drawN);
    const ix = px(n0) + (px(n0 + 1) - px(n0)) * f;
    const iy = py(cum[n0]) + (py(cum[n0 + 1]) - py(cum[n0])) * f;
    pts.push([ix, iy]);
  }
  const path = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p[0]} ${p[1]}`).join(" ");

  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
      <rect
        x={chart.x - 24}
        y={chart.y - 56}
        width={chart.w + 56}
        height={chart.h + 96}
        rx={14}
        fill="rgba(14,19,26,0.78)"
        stroke={colors.border}
        strokeWidth={1.5}
      />
      <text x={chart.x - 4} y={chart.y - 26} fill={colors.gold} fontFamily={fonts.mono} fontSize={20} fontWeight={600}>
        cumulative cooled area
      </text>
      {/* axes */}
      <line x1={chart.x} y1={chart.y} x2={chart.x} y2={chart.y + chart.h} stroke={colors.textMuted} strokeWidth={1.5} />
      <line
        x1={chart.x}
        y1={chart.y + chart.h}
        x2={chart.x + chart.w}
        y2={chart.y + chart.h}
        stroke={colors.textMuted}
        strokeWidth={1.5}
      />
      <text
        x={chart.x + chart.w / 2}
        y={chart.y + chart.h + 34}
        fill={colors.textDim}
        fontFamily={fonts.mono}
        fontSize={17}
        textAnchor="middle"
      >
        trees placed →
      </text>

      {/* concave curve */}
      <path d={path} fill="none" stroke={colors.canopyBright} strokeWidth={3} strokeLinejoin="round" />
      {/* dots at each placed pick */}
      {PICKS.slice(0, placedCount).map((p, i) => (
        <circle key={i} cx={px(i + 1)} cy={py(cum[i + 1])} r={5} fill={colors.canopy} stroke={colors.canopyBright} strokeWidth={2} />
      ))}

      {/* "submodular" tag once a couple of picks land */}
      {placedCount >= 2 && (
        <g opacity={interpolate(local, [perPick * 2, perPick * 2 + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}>
          <text x={chart.x + chart.w - 6} y={chart.y + 40} fill={colors.cool} fontFamily={fonts.mono} fontSize={22} fontWeight={700} textAnchor="end">
            submodular
          </text>
          <text x={chart.x + chart.w - 6} y={chart.y + 64} fill={colors.textDim} fontFamily={fonts.mono} fontSize={15} textAnchor="end">
            each tree adds less than the last
          </text>
        </g>
      )}
      {/* dashed projection of where the next (smaller) gain lands */}
      {placedCount >= 1 && placedCount < maxN && (
        <line
          x1={px(placedCount)}
          y1={py(cum[placedCount])}
          x2={px(placedCount + 1)}
          y2={py(cum[placedCount + 1])}
          stroke={colors.textMuted}
          strokeWidth={2}
          strokeDasharray="4 5"
          opacity={0.6}
        />
      )}
    </svg>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ACT 4 — guarantee band + stop conditions.
const GuaranteeAct: React.FC<{ frame: number; df: number; a3: number }> = ({
  frame,
  df,
  a3,
}) => {
  const active = frame >= a3 - 6;
  if (!active) return null;
  const op = interpolate(frame, [a3 - 6, a3 + 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const local = frame - a3;
  const span = df - a3;

  const chart = { x: 1360, y: 470, w: 450, h: 320 };
  const optY = chart.y + chart.h * 0.12; // optimum line near top
  const bandY = chart.y + chart.h - (chart.h * 0.88) * 0.63; // 63% of optimum height

  const bandGrow = interpolate(local, [10, 40], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const formulaSp = spring({
    frame: local - 38,
    fps: FPS,
    config: { damping: 12, stiffness: 120 },
  });

  // stop conditions blink on
  const stop1 = interpolate(local, [span * 0.5, span * 0.5 + 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const stop2 = interpolate(local, [span * 0.62, span * 0.62 + 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const capX = interpolate(local, [span * 0.72, span * 0.72 + 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const closing = interpolate(local, [span * 0.8, span * 0.8 + 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: op }}>
      {/* overlay band onto the existing curve chart */}
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* filled 63% band */}
        <rect
          x={chart.x}
          y={bandY}
          width={chart.w}
          height={(chart.y + chart.h - bandY) * bandGrow}
          fill={colors.canopyGlow}
          opacity={0.5}
          style={{ transformOrigin: `${chart.x}px ${chart.y + chart.h}px` }}
        />
        {/* dashed OPTIMUM line */}
        <line
          x1={chart.x}
          y1={optY}
          x2={chart.x + chart.w}
          y2={optY}
          stroke={colors.gold}
          strokeWidth={2}
          strokeDasharray="8 6"
        />
        <text x={chart.x + chart.w} y={optY - 8} fill={colors.gold} fontFamily={fonts.mono} fontSize={18} textAnchor="end">
          OPTIMUM
        </text>
        {/* 63% marker line */}
        <line
          x1={chart.x}
          y1={bandY}
          x2={chart.x + chart.w}
          y2={bandY}
          stroke={colors.canopyBright}
          strokeWidth={2}
          strokeDasharray="4 4"
          opacity={bandGrow}
        />
      </svg>

      {/* formula snap-in */}
      <div
        style={{
          position: "absolute",
          top: 300,
          left: 130,
          width: 1080,
          opacity: Math.min(1, formulaSp),
          transform: `scale(${0.92 + formulaSp * 0.08})`,
        }}
      >
        <Panel style={{ padding: "30px 38px" }} glow={colors.canopyGlow}>
          <div
            style={{
              fontFamily: fonts.mono,
              fontSize: 64,
              fontWeight: 700,
              color: colors.canopyBright,
              letterSpacing: -1,
            }}
          >
            (1 − 1/e) = 63% of optimum
          </div>
          <div style={{ height: 12 }} />
          <Label color={colors.textDim} size={22}>
            greedy on a submodular gain is provably within 63% of the best possible placement — guaranteed, not hoped
          </Label>
          <div style={{ height: 14 }} />
          <Label color={colors.textMuted} size={17}>
            Nemhauser 1978 · cost-benefit Leskovec 2007
          </Label>
        </Panel>
      </div>

      {/* stop conditions end card */}
      <div style={{ position: "absolute", top: 600, left: 130, width: 1120 }}>
        <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
          <div style={{ opacity: stop1, transform: `translateY(${(1 - stop1) * 12}px)` }}>
            <Chip color={colors.canopy} size={26}>
              ✓ no positive-gain affordable slot
            </Chip>
          </div>
          <div style={{ opacity: stop2, transform: `translateY(${(1 - stop2) * 12}px)` }}>
            <Chip color={colors.canopy} size={26}>
              ✓ budget exhausted
            </Chip>
          </div>
          <div style={{ opacity: 0.4 + capX * 0.0, position: "relative" }}>
            <Chip color={colors.textMuted} size={26}>
              fixed iteration cap
            </Chip>
            {/* strike-through */}
            <div
              style={{
                position: "absolute",
                top: "50%",
                left: 0,
                height: 3,
                width: `${capX * 100}%`,
                background: colors.heat,
                transformOrigin: "left center",
              }}
            />
          </div>
        </div>

        <div style={{ height: 28 }} />
        <div style={{ opacity: closing, transform: `translateY(${(1 - closing) * 16}px)` }}>
          <Headline size={48} color={colors.text}>
            stops on a{" "}
            <span style={{ color: colors.canopyBright }}>real condition</span>, never a{" "}
            <span style={{ color: colors.heat }}>fixed cap</span>.
          </Headline>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// helpers

// which cells are "already cooled" (green dim) at the current frame, returns
// map index→intensity. Driven by acts 2 (single tree) and 3 (greedy picks).
function useCooledCells(frame: number, df: number, a2: number, a3: number): Map<number, number> {
  const map = new Map<number, number>();
  if (frame < a2) return map;
  const local = frame - a2;
  const span = a3 - a2;
  const perPick = span / (PICKS.length + 0.4);
  const placedCount = frame >= a3 ? PICKS.length : Math.min(PICKS.length, Math.floor(local / perPick));
  for (let pi = 0; pi < placedCount; pi++) {
    const p = PICKS[pi];
    const fpx = cx(p.c);
    const fpy = cy(p.r) - 24; // footprint north of trunk
    CELLS.forEach((cell, i) => {
      if (!isDemand(cell)) return;
      const ex = cx(cell.c);
      const ey = cy(cell.r);
      const d = Math.hypot((ex - fpx) / 96, (ey - fpy) / 58);
      if (d < 1) map.set(i, Math.max(map.get(i) ?? 0, 1 - d * 0.5));
    });
  }
  return map;
}

// heat ramp amber→ember→heat by intensity 0..1
function heatRamp(t: number): string {
  const c = Math.max(0, Math.min(1, t));
  if (c < 0.5) return mix(colors.amber, colors.ember, c / 0.5);
  return mix(colors.ember, colors.heat, (c - 0.5) / 0.5);
}

// linear blend of two hex/rgba colors
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

// the n hottest demand cells, for floating weight labels
function hottestCells(n: number): Cell[] {
  return CELLS.filter(isDemand)
    .slice()
    .sort((a, b) => b.utci - a.utci)
    .filter((_, i) => i % 3 === 0) // spread them out a bit
    .slice(0, n);
}

// describe a flattened half-arc (ellipse top) for the sun track
function describeArc(cxc: number, cyc: number, rx: number, ry: number): string {
  const x0 = cxc - rx;
  const x1 = cxc + rx;
  return `M ${x0} ${cyc} A ${rx} ${ry} 0 0 1 ${x1} ${cyc}`;
}
