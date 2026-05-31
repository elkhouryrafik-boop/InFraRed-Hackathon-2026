import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";
import { colors, fonts } from "../theme";
import { Kicker, Headline, Label, Tag } from "../components/kit";
import { Reveal } from "../components/Reveal";

// ── SCENE 04 — "Where a Tree Can Actually Go" ──────────────────────────────
// The optimiser never works in open space. It first builds a finite set of
// pre-validated candidate slots via geometry constraints + 8 m spacing, then
// each surviving slot becomes a planter or an in-ground pit.
//
// All motion driven by frame in [0, df]. 4 beats: lattice → elimination →
// standards converge → mode cards. Top-down stylised plaza.

// Plaza geometry (px, in the 1920×1080 canvas, content kept above y≈900).
const PLAZA = { x: 130, y: 250, w: 860, h: 560, r: 28 };
const BUILDING = { x: 130, y: 250, w: 860, h: 150 }; // top edge block
const ROAD = { x: 130, y: 720, w: 860, h: 90 }; // bottom edge strip
const GRID_STEP = 64; // visual 4 m
const FACADE_CLEAR = 70; // façade clearance ring depth (px)

type Dot = {
  col: number;
  row: number;
  x: number;
  y: number;
  // classification
  inBuilding: boolean;
  onRoad: boolean;
  nearFacade: boolean;
  survivesGeom: boolean;
};

// Build the 4 m lattice once (row-major).
function buildLattice(): Dot[] {
  const dots: Dot[] = [];
  const x0 = PLAZA.x + GRID_STEP * 0.7;
  const y0 = PLAZA.y + GRID_STEP * 0.7;
  let row = 0;
  for (let y = y0; y < PLAZA.y + PLAZA.h - 18; y += GRID_STEP) {
    let col = 0;
    for (let x = x0; x < PLAZA.x + PLAZA.w - 18; x += GRID_STEP) {
      const inBuilding =
        y < BUILDING.y + BUILDING.h + 4 && y > BUILDING.y;
      const onRoad = y > ROAD.y - 4;
      const nearFacade =
        !inBuilding &&
        !onRoad &&
        y < BUILDING.y + BUILDING.h + FACADE_CLEAR;
      dots.push({
        col,
        row,
        x,
        y,
        inBuilding,
        onRoad,
        nearFacade,
        survivesGeom: !inBuilding && !onRoad && !nearFacade,
      });
      col++;
    }
    row++;
  }
  return dots;
}

const LATTICE = buildLattice();
const N = LATTICE.length;

// Greedy 8 m spacing pass over geometry survivors (row-major order).
// Returns set of dot-indices that are KEPT (accepted) after spacing.
const SPACING_PX = 116; // visual 8 m radius
function computeSpacingKeep(): { kept: number[]; kepByIdx: boolean[] } {
  const kept: number[] = [];
  const kepByIdx = new Array(N).fill(false);
  LATTICE.forEach((d, i) => {
    if (!d.survivesGeom) return;
    const clash = kept.some((ki) => {
      const k = LATTICE[ki];
      const dx = k.x - d.x;
      const dy = k.y - d.y;
      return Math.hypot(dx, dy) < SPACING_PX;
    });
    if (!clash) {
      kept.push(i);
      kepByIdx[i] = true;
    }
  });
  return { kept, kepByIdx };
}

const SPACING = computeSpacingKeep();

export const Scene04: React.FC<{ df: number }> = ({ df }) => {
  const frame = useCurrentFrame();

  // Beat windows (fractions of df).
  const b1 = 0.22 * df; // lattice complete
  const b2s = 0.22 * df;
  const b2e = 0.56 * df; // elimination + spacing complete
  const b3s = 0.56 * df;
  const b3e = 0.76 * df;
  const b4s = 0.76 * df;

  // ── BEAT 1: lattice flood-in (row-major) ──
  const latticeProg = interpolate(frame, [4, b1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const dotsShown = Math.floor(latticeProg * N);

  // ── BEAT 2: elimination sweeps ──
  // Phase a: buildings cull, Phase b: road cull, Phase c: façade ring sweep,
  // Phase d: spacing bloom.
  const elimA = interpolate(frame, [b2s, b2s + (b2e - b2s) * 0.18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const elimB = interpolate(
    frame,
    [b2s + (b2e - b2s) * 0.18, b2s + (b2e - b2s) * 0.34],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const facadeSweep = interpolate(
    frame,
    [b2s + (b2e - b2s) * 0.34, b2s + (b2e - b2s) * 0.56],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const spacingProg = interpolate(
    frame,
    [b2s + (b2e - b2s) * 0.56, b2e],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  // façade ring x-position sweeps left→right across plaza
  const ringX = PLAZA.x + facadeSweep * PLAZA.w;
  const spacingKeptCount = Math.floor(spacingProg * SPACING.kept.length);
  const spacingActiveSet = new Set(
    SPACING.kept.slice(0, spacingKeptCount),
  );

  // Determine per-dot visual state at the current frame.
  function dotState(d: Dot, i: number) {
    if (i >= dotsShown && frame < b2s) return { show: false } as const;
    // Building cull
    if (d.inBuilding && elimA > 0) {
      const fade = 1 - elimA;
      return { show: fade > 0.02, color: colors.heat, opacity: fade, r: 4 };
    }
    // Road cull
    if (d.onRoad && elimB > 0) {
      const fade = 1 - elimB;
      return { show: fade > 0.02, color: colors.amber, opacity: fade, r: 4 };
    }
    // Façade clearance cull — culled once ring sweeps past
    if (d.nearFacade) {
      const culled = d.x < ringX && facadeSweep > 0;
      const fade = culled ? 0 : 1;
      return {
        show: fade > 0.02,
        color: colors.heat,
        opacity: 0.55 * fade,
        r: 4,
      };
    }
    // Geometry survivors
    if (d.survivesGeom) {
      const accepted = spacingActiveSet.has(i);
      // dots not yet accepted but eliminated by an accepted neighbour
      let greyed = false;
      if (spacingProg > 0 && !accepted) {
        greyed = SPACING.kept.slice(0, spacingKeptCount).some((ki) => {
          const k = LATTICE[ki];
          return Math.hypot(k.x - d.x, k.y - d.y) < SPACING_PX;
        });
      }
      if (greyed) {
        return { show: true, color: colors.textFaint, opacity: 0.35, r: 3 };
      }
      const isKept = SPACING.kepByIdx[i];
      const col =
        spacingProg > 0
          ? accepted
            ? colors.canopy
            : isKept
              ? colors.canopy
              : colors.canopy
          : facadeSweep > 0.4 || elimB > 0.2
            ? colors.canopy
            : colors.textDim;
      const op = accepted ? 1 : spacingProg > 0 && !isKept ? 0.4 : 0.85;
      return {
        show: true,
        color: col,
        opacity: op,
        r: accepted ? 6 : 4,
      };
    }
    return { show: false } as const;
  }

  // 8 m bloom ring for the most-recently accepted slot
  const lastAccepted =
    spacingKeptCount > 0 ? LATTICE[SPACING.kept[spacingKeptCount - 1]] : null;
  const bloomFrac = spacingProg * SPACING.kept.length - (spacingKeptCount - 1);

  // Two chosen slots for the mode cards (first two accepted survivors).
  const slotA = SPACING.kept.length > 0 ? LATTICE[SPACING.kept[0]] : null;
  const slotB =
    SPACING.kept.length > 1
      ? LATTICE[SPACING.kept[Math.min(2, SPACING.kept.length - 1)]]
      : null;

  // ── BEAT 4: mode card flip ──
  const cardProg = interpolate(frame, [b4s, b4s + 0.1 * df], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  // tag pulse (once)
  const pulseAt = b4s + 0.16 * df;
  const pulse =
    frame > pulseAt
      ? 1 +
        0.12 *
          Math.max(
            0,
            Math.sin(((frame - pulseAt) / 10) * Math.PI),
          ) *
          (frame < pulseAt + 10 ? 1 : 0)
      : 1;

  // plaza fades back for beat 4 to let cards breathe
  const plazaDim = interpolate(frame, [b4s, b4s + 0.07 * df], [1, 0.22], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ fontFamily: fonts.display }}>
      {/* ── Title ── */}
      <div style={{ position: "absolute", left: 130, top: 110 }}>
        <Reveal startFrame={2} durationInFrames={20}>
          <Kicker>Candidate generation</Kicker>
        </Reveal>
        <Reveal startFrame={8} durationInFrames={22}>
          <Headline size={64}>WHERE A TREE CAN ACTUALLY GO</Headline>
        </Reveal>
      </div>

      {/* ── Plaza diagram (BEATS 1–2) ── */}
      <svg
        width={1920}
        height={1080}
        style={{ position: "absolute", left: 0, top: 0, opacity: plazaDim }}
      >
        {/* plaza ground */}
        <rect
          x={PLAZA.x}
          y={PLAZA.y}
          width={PLAZA.w}
          height={PLAZA.h}
          rx={PLAZA.r}
          fill="rgba(78,168,222,0.04)"
          stroke={colors.border}
          strokeWidth={1.5}
        />
        {/* building block */}
        <rect
          x={BUILDING.x}
          y={BUILDING.y}
          width={BUILDING.w}
          height={BUILDING.h}
          rx={PLAZA.r}
          fill="rgba(33,44,54,0.85)"
          stroke={colors.hairline}
          strokeWidth={1}
        />
        <text
          x={BUILDING.x + 22}
          y={BUILDING.y + 38}
          fill={colors.textMuted}
          fontFamily={fonts.mono}
          fontSize={20}
          letterSpacing={2}
        >
          BUILDING
        </text>
        {/* road strip */}
        <rect
          x={ROAD.x}
          y={ROAD.y}
          width={ROAD.w}
          height={ROAD.h}
          rx={18}
          fill="rgba(245,166,35,0.06)"
          stroke="rgba(245,166,35,0.25)"
          strokeWidth={1}
          strokeDasharray="2 10"
        />
        <text
          x={ROAD.x + 22}
          y={ROAD.y + ROAD.h / 2 + 7}
          fill="rgba(245,166,35,0.6)"
          fontFamily={fonts.mono}
          fontSize={18}
          letterSpacing={2}
        >
          ROADWAY
        </text>

        {/* façade clearance ring sweep */}
        {facadeSweep > 0 && facadeSweep < 1 && (
          <line
            x1={ringX}
            y1={BUILDING.y + BUILDING.h}
            x2={ringX}
            y2={BUILDING.y + BUILDING.h + FACADE_CLEAR}
            stroke={colors.heat}
            strokeWidth={2}
            opacity={0.8}
          />
        )}
        {/* façade clearance band guide */}
        {facadeSweep > 0 && (
          <rect
            x={PLAZA.x}
            y={BUILDING.y + BUILDING.h}
            width={PLAZA.w}
            height={FACADE_CLEAR}
            fill="rgba(255,90,54,0.05)"
          />
        )}

        {/* lattice dots */}
        {LATTICE.map((d, i) => {
          const s = dotState(d, i);
          if (!s.show) return null;
          return (
            <circle
              key={i}
              cx={d.x}
              cy={d.y}
              r={s.r}
              fill={s.color}
              opacity={s.opacity}
            />
          );
        })}

        {/* 8 m spacing bloom on most recent accept */}
        {lastAccepted && spacingProg > 0 && spacingProg < 1 && (
          <circle
            cx={lastAccepted.x}
            cy={lastAccepted.y}
            r={SPACING_PX * Math.min(1, bloomFrac)}
            fill="none"
            stroke={colors.canopy}
            strokeWidth={1.5}
            opacity={0.5 * (1 - Math.min(1, bloomFrac))}
          />
        )}

        {/* 4 m caliper (BEAT 1) */}
        {latticeProg > 0.25 && frame < b2s + (b2e - b2s) * 0.34 && (
          <g opacity={interpolate(frame, [b1 * 0.4, b1 * 0.7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}>
            <line
              x1={PLAZA.x + GRID_STEP * 0.7}
              y1={PLAZA.y + BUILDING.h + FACADE_CLEAR + 40}
              x2={PLAZA.x + GRID_STEP * 0.7 + GRID_STEP}
              y2={PLAZA.y + BUILDING.h + FACADE_CLEAR + 40}
              stroke={colors.textDim}
              strokeWidth={1.5}
            />
            <line x1={PLAZA.x + GRID_STEP * 0.7} y1={PLAZA.y + BUILDING.h + FACADE_CLEAR + 34} x2={PLAZA.x + GRID_STEP * 0.7} y2={PLAZA.y + BUILDING.h + FACADE_CLEAR + 46} stroke={colors.textDim} strokeWidth={1.5} />
            <line x1={PLAZA.x + GRID_STEP * 0.7 + GRID_STEP} y1={PLAZA.y + BUILDING.h + FACADE_CLEAR + 34} x2={PLAZA.x + GRID_STEP * 0.7 + GRID_STEP} y2={PLAZA.y + BUILDING.h + FACADE_CLEAR + 46} stroke={colors.textDim} strokeWidth={1.5} />
            <text
              x={PLAZA.x + GRID_STEP * 0.7 + GRID_STEP / 2}
              y={PLAZA.y + BUILDING.h + FACADE_CLEAR + 28}
              fill={colors.textDim}
              fontFamily={fonts.mono}
              fontSize={20}
              textAnchor="middle"
            >
              4 m
            </text>
          </g>
        )}

        {/* 8 m caliper (BEAT 2 spacing) */}
        {spacingProg > 0.35 && slotA && slotB && frame < b3s && (
          <g opacity={interpolate(spacingProg, [0.35, 0.6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}>
            <line x1={slotA.x} y1={slotA.y} x2={slotA.x + SPACING_PX} y2={slotA.y} stroke={colors.canopy} strokeWidth={1.5} strokeDasharray="4 4" />
            <text x={slotA.x + SPACING_PX / 2} y={slotA.y - 12} fill={colors.canopy} fontFamily={fonts.mono} fontSize={20} textAnchor="middle">
              8 m
            </text>
          </g>
        )}
      </svg>

      {/* ── elimination running labels (BEAT 2) ── */}
      <div style={{ position: "absolute", left: 1040, top: 280, display: "flex", flexDirection: "column", gap: 18 }}>
        {([
          ["off buildings", colors.heat, elimA],
          ["off roadway", colors.amber, elimB],
          ["clear of façades", colors.heat, facadeSweep],
          ["8 m minimum spacing", colors.canopy, spacingProg],
        ] as const).map(([txt, c, p], k) => (
          <div
            key={k}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              opacity: interpolate(p, [0.01, 0.3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) * plazaDim,
            }}
          >
            <div style={{ width: 12, height: 12, borderRadius: 12, background: c }} />
            <Label color={p >= 0.999 ? colors.text : c} size={26}>
              {txt}
            </Label>
            {p >= 0.999 && <Label color={colors.canopy} size={26}>✓</Label>}
          </div>
        ))}
      </div>

      {/* ── BEAT 3: three standards converge inset ── */}
      {frame >= b3s - 6 && frame < b4s + 4 && (
        <StandardsInset frame={frame} b3s={b3s} b3e={b3e} />
      )}

      {/* ── BEAT 4: mode cards ── */}
      {frame >= b4s - 4 && (
        <div
          style={{
            position: "absolute",
            left: 130,
            top: 330,
            display: "flex",
            gap: 56,
            opacity: cardProg,
          }}
        >
          {/* PLANTER */}
          <ModeCard
            flip={cardProg}
            title="PLANTER"
            accent={colors.cool}
            delay={0}
          >
            <svg width={520} height={300}>
              {/* pavement */}
              <rect x={20} y={210} width={480} height={60} fill="rgba(33,44,54,0.5)" stroke={colors.hairline} />
              {/* wall on left */}
              <rect x={20} y={40} width={20} height={170} fill="rgba(33,44,54,0.9)" />
              {/* planter box on pavement */}
              <rect x={150} y={150} width={140} height={62} rx={6} fill="rgba(78,168,222,0.12)" stroke={colors.cool} strokeWidth={2} />
              {/* tree mass */}
              <circle cx={220} cy={120} r={42} fill="rgba(55,208,138,0.25)" stroke={colors.canopy} strokeWidth={2} />
              {/* 0.6 m clearance tick to the wall */}
              <line x1={40} y1={181} x2={150} y2={181} stroke={colors.cool} strokeWidth={1.5} />
              <line x1={40} y1={175} x2={40} y2={187} stroke={colors.cool} strokeWidth={1.5} />
              <line x1={150} y1={175} x2={150} y2={187} stroke={colors.cool} strokeWidth={1.5} />
              <text x={95} y={170} fill={colors.cool} fontFamily={fonts.mono} fontSize={18} textAnchor="middle">0.6 m</text>
            </svg>
            <div style={{ display: "flex", gap: 12, marginTop: 4 }}>
              <Label color={colors.cool} size={22}>0.6 m wall</Label>
              <Label color={colors.textMuted} size={22}>·</Label>
              <Label color={colors.textDim} size={22}>no de-paving</Label>
            </div>
          </ModeCard>

          {/* IN-GROUND */}
          <ModeCard
            flip={cardProg}
            title="IN-GROUND"
            accent={colors.canopy}
            delay={0.08 * df}
          >
            <svg width={520} height={300}>
              {/* building edge (left) */}
              <rect x={20} y={40} width={70} height={230} fill="rgba(33,44,54,0.9)" stroke={colors.hairline} />
              <text x={55} y={30} fill={colors.textMuted} fontFamily={fonts.mono} fontSize={15} textAnchor="middle">BLDG</text>
              {/* pavement */}
              <rect x={90} y={210} width={410} height={60} fill="rgba(33,44,54,0.5)" stroke={colors.hairline} />
              {/* de-paved pit */}
              <rect x={300} y={205} width={120} height={70} rx={6} fill="rgba(8,11,16,0.9)" stroke={colors.canopy} strokeWidth={2} strokeDasharray="6 4" />
              <circle cx={360} cy={120} r={46} fill="rgba(55,208,138,0.28)" stroke={colors.canopy} strokeWidth={2} />
              {/* 6 m setback line to building */}
              <line x1={90} y1={186} x2={300} y2={186} stroke={colors.canopy} strokeWidth={1.5} />
              <line x1={90} y1={180} x2={90} y2={192} stroke={colors.canopy} strokeWidth={1.5} />
              <line x1={300} y1={180} x2={300} y2={192} stroke={colors.canopy} strokeWidth={1.5} />
              <text x={195} y={175} fill={colors.canopy} fontFamily={fonts.mono} fontSize={18} textAnchor="middle">6 m setback</text>
              {/* unknown utility line beneath (dashed, faint) */}
              <line x1={100} y1={252} x2={490} y2={252} stroke={colors.amber} strokeWidth={1.5} strokeDasharray="3 7" opacity={0.55} />
              <text x={150} y={272} fill="rgba(245,166,35,0.6)" fontFamily={fonts.mono} fontSize={14}>?? utility</text>
            </svg>
            <div style={{ display: "flex", gap: 14, marginTop: 4, alignItems: "center" }}>
              <Label color={colors.canopy} size={22}>6 m setback</Label>
              <Label color={colors.textMuted} size={22}>·</Label>
              <Label color={colors.textDim} size={22}>pit cost</Label>
              <div style={{ transform: `scale(${pulse})`, transformOrigin: "left center", marginLeft: 6 }}>
                <Tag kind="requires_utility_survey" color={colors.amber} />
              </div>
            </div>
          </ModeCard>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ── Mode card shell with a subtle 3D flip-in ──
const ModeCard: React.FC<{
  flip: number;
  title: string;
  accent: string;
  delay: number;
  children: React.ReactNode;
}> = ({ flip, title, accent, children }) => {
  const rot = (1 - flip) * 22;
  return (
    <div
      style={{
        background: "rgba(14,19,26,0.9)",
        border: `1px solid ${colors.border}`,
        borderRadius: 18,
        padding: "26px 30px",
        boxShadow: `0 0 50px ${accent}22`,
        transform: `perspective(1400px) rotateY(${rot}deg)`,
        transformOrigin: "left center",
      }}
    >
      <div
        style={{
          fontFamily: fonts.mono,
          fontSize: 26,
          fontWeight: 700,
          letterSpacing: 3,
          color: accent,
          marginBottom: 14,
        }}
      >
        {title}
      </div>
      {children}
    </div>
  );
};

// ── BEAT 3 inset: three bracketed ranges aligning on the 8 m tick ──
const StandardsInset: React.FC<{
  frame: number;
  b3s: number;
  b3e: number;
}> = ({ frame, b3s, b3e }) => {
  const enter = interpolate(frame, [b3s - 6, b3s + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const exit = interpolate(frame, [b3e - 8, b3e + 4], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const conv = interpolate(frame, [b3s + 16, b3e - 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  // x-axis: metres 5..11 mapped to px. Shared tick at 8 m.
  const axX = 1060;
  const axW = 720;
  const mToX = (m: number) => axX + ((m - 5) / 6) * axW;
  const tick8 = mToX(8);

  // ranges: [min,max, label, color, initialOffsetPx]
  const ranges: [number, number, string, string, number][] = [
    [6, 9, "NACTO 6–9 m", colors.cool, -90],
    [8, 10, "climate 8–10 m", colors.canopy, 70],
    [6, 10, "de-paving 6–10 m", colors.amber, -40],
  ];

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 360,
        width: 1920,
        opacity: enter * exit,
      }}
    >
      <div style={{ position: "absolute", left: axX, top: -54 }}>
        <Label color={colors.textDim} size={24}>three standards converge</Label>
      </div>
      <svg width={1920} height={360}>
        {/* shared 8 m tick */}
        <line x1={tick8} y1={6} x2={tick8} y2={250} stroke={colors.canopy} strokeWidth={1.5} strokeDasharray="3 5" opacity={0.7} />
        <text x={tick8} y={278} fill={colors.canopy} fontFamily={fonts.mono} fontSize={22} textAnchor="middle">8 m</text>

        {ranges.map(([lo, hi, label, c, off], i) => {
          const y = 40 + i * 64;
          const dx = (1 - conv) * off;
          const x1 = mToX(lo) + dx;
          const x2 = mToX(hi) + dx;
          return (
            <g key={i}>
              {/* bracket */}
              <line x1={x1} y1={y} x2={x2} y2={y} stroke={c} strokeWidth={3} />
              <line x1={x1} y1={y - 12} x2={x1} y2={y + 12} stroke={c} strokeWidth={3} />
              <line x1={x2} y1={y - 12} x2={x2} y2={y + 12} stroke={c} strokeWidth={3} />
              <text x={x1} y={y - 20} fill={c} fontFamily={fonts.mono} fontSize={22}>
                {label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
