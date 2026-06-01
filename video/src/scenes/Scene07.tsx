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

// ── SCENE 07 — "Decades of Canopy, Counted in Euros" ──
// Growth + cost. ACT 1 animates two real Chapman-Richards crown-growth curves;
// ACT 2 itemises CapEx/OpEx and discounts 40 years of value to a per-tree PV.
// Two linked acts across df.
//   ACT 1 (0–48%)  GROWTH — an age×crown axis. Two real Chapman-Richards sigmoids
//                  rise from a shared planting crown of 1.5 m: a FAST green curve
//                  (Tipuana tipu, k≈0.204, A=10, 95% by age 20) and a SLOW teal
//                  curve (Cercis siliquastrum, k≈0.102, A=5, 95% by age 40). A
//                  glowing tracer rides each curve; top-down canopy discs grow in
//                  step; equation chip + "fast fills its crown ~2× faster".
//   ACT 2 (48–100%) COST — curves shrink to a thumbnail (left); an itemised CapEx
//                  ledger animates line-by-line summing to EUR 2,200; an OpEx
//                  callout resolves the fraction 12,658,229 / 206,556 = 61.28
//                  (VERIFIED); a 40-year timeline drops shrinking coins (3.5%
//                  discount) collapsing into a locked Counter: PV ~ EUR 3,481/tree,
//                  underlined "auditable".

// ── growth chart geometry ──
const CHART = { x: 620, y: 250, w: 760, h: 520 }; // act-1 centred chart
const AGE_MAX = 40;
const CROWN_MAX = 11; // y-axis top (m)

// Chapman-Richards: crown(age) = max(1.5, A·(1 − e^(−k·age))³)
const crown = (age: number, A: number, k: number) =>
  Math.max(1.5, A * Math.pow(1 - Math.exp(-k * age), 3));

const FAST = { A: 10, k: 0.204, color: colors.canopyBright, name: "Tipuana tipu" };
const SLOW = { A: 5, k: 0.102, color: colors.teal, name: "Cercis siliquastrum" };

// CapEx ledger items (sum = 2,200)
const CAPEX = [
  { label: "nursery stock", eur: 600 },
  { label: "pit excavation", eur: 500 },
  { label: "structural soil", eur: 600 },
  { label: "guarding + stake", eur: 200 },
  { label: "planting labour", eur: 300 },
];
const CAPEX_TOTAL = 2200;

export const Scene07: React.FC<{ df: number }> = ({ df }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  void fps;

  const a1 = df * 0.48; // growth → cost handoff

  const intro = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // In act 2 the growth chart slides left and shrinks to a thumbnail.
  const shrink = interpolate(frame, [a1, a1 + 30], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ fontFamily: fonts.display }}>
      {/* ── persistent header ── */}
      <div style={{ position: "absolute", top: 80, left: 110, opacity: intro }}>
        <Kicker color={colors.canopy}>DECADES OF CANOPY · COUNTED IN EUROS</Kicker>
        <div style={{ height: 14 }} />
        <ActTitle frame={frame} a1={a1} />
      </div>

      {/* ── the growth chart (shared; shrinks in act 2) ── */}
      <GrowthChart frame={frame} df={df} a1={a1} shrink={shrink} />

      {/* ── ACT 2 cost overlays ── */}
      <CostAct frame={frame} df={df} a1={a1} />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
const ActTitle: React.FC<{ frame: number; a1: number }> = ({ frame, a1 }) => {
  const isCost = frame >= a1;
  const t = isCost
    ? { text: "EVERY EURO, ITEMISED", color: colors.gold }
    : { text: "CROWN GROWS ON AN S-CURVE", color: colors.canopyBright };
  const at = isCost ? a1 : 0;
  const since = frame - at;
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
      <Headline size={62} color={t.color}>
        {t.text}
      </Headline>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ACT 1 — the growth chart. Lives at full size in act 1, then slides/shrinks.
const GrowthChart: React.FC<{
  frame: number;
  df: number;
  a1: number;
  shrink: number;
}> = ({ frame, df, a1, shrink }) => {
  // chart appears
  const boardOp = interpolate(frame, [10, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // act-1 internal progress drives the curve draw + tracer.
  const drawStart = 30;
  const drawEnd = a1 - 24;
  const grow = interpolate(frame, [drawStart, drawEnd], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // age currently revealed along the x axis (0..40)
  const ageNow = grow * AGE_MAX;

  // ── shrink-to-thumbnail transform (act 2) ──
  // thumbnail destination (top-left), scaled down.
  const thumb = { x: 130, y: 300, scale: 0.42 };
  const tx = interpolate(shrink, [0, 1], [0, thumb.x - CHART.x]);
  const ty = interpolate(shrink, [0, 1], [0, thumb.y - CHART.y]);
  const sc = interpolate(shrink, [0, 1], [1, thumb.scale]);

  // pixel mappers
  const px = (age: number) => CHART.x + (age / AGE_MAX) * CHART.w;
  const py = (cr: number) => CHART.y + CHART.h - (cr / CROWN_MAX) * CHART.h;

  // build a sampled path for a curve up to ageNow
  const buildPath = (A: number, k: number) => {
    const pts: string[] = [];
    const N = 120;
    for (let i = 0; i <= N; i++) {
      const age = (i / N) * Math.min(ageNow, AGE_MAX);
      const x = px(age);
      const y = py(crown(age, A, k));
      pts.push(`${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`);
      if (age >= ageNow) break;
    }
    return pts.join(" ");
  };

  const fastPath = buildPath(FAST.A, FAST.k);
  const slowPath = buildPath(SLOW.A, SLOW.k);

  // tracer positions ride the head of each curve
  const fastTip = { x: px(ageNow), y: py(crown(ageNow, FAST.A, FAST.k)) };
  const slowTip = { x: px(ageNow), y: py(crown(ageNow, SLOW.A, SLOW.k)) };

  // 95%-of-mature plateau lines (fast plateaus near age 20, slow near age 40)
  const fast95 = FAST.A * 0.95;
  const slow95 = SLOW.A * 0.95;

  // top-down canopy discs (grow in step with current crown) — only in act 1
  const discOp = interpolate(shrink, [0, 0.5], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fastCrownNow = crown(ageNow, FAST.A, FAST.k);
  const slowCrownNow = crown(ageNow, SLOW.A, SLOW.k);
  const discScale = (CHART.h / CROWN_MAX) * 0.5; // px per metre of crown radius-ish

  // equation chip + side caption timing
  const eqOp = interpolate(frame, [drawStart + 6, drawStart + 26], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const capOp = interpolate(frame, [drawEnd - 60, drawEnd - 36], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeCaptions = interpolate(shrink, [0, 0.4], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, opacity: boardOp }}>
        <g transform={`translate(${tx} ${ty}) scale(${sc})`} style={{ transformOrigin: `${CHART.x}px ${CHART.y}px` }}>
          {/* chart frame */}
          <rect
            x={CHART.x - 56}
            y={CHART.y - 24}
            width={CHART.w + 96}
            height={CHART.h + 96}
            rx={16}
            fill="rgba(14,19,26,0.62)"
            stroke={colors.border}
            strokeWidth={1.5}
          />

          {/* y gridlines */}
          {[0, 2, 4, 6, 8, 10].map((cr) => (
            <g key={`gy${cr}`}>
              <line
                x1={CHART.x}
                y1={py(cr)}
                x2={CHART.x + CHART.w}
                y2={py(cr)}
                stroke={colors.hairline}
                strokeWidth={1}
              />
              <text x={CHART.x - 14} y={py(cr) + 6} fill={colors.textMuted} fontFamily={fonts.mono} fontSize={18} textAnchor="end">
                {cr}
              </text>
            </g>
          ))}
          {/* x ticks */}
          {[0, 10, 20, 30, 40].map((age) => (
            <g key={`gx${age}`}>
              <line
                x1={px(age)}
                y1={CHART.y + CHART.h}
                x2={px(age)}
                y2={CHART.y + CHART.h + 8}
                stroke={colors.textMuted}
                strokeWidth={1.5}
              />
              <text x={px(age)} y={CHART.y + CHART.h + 30} fill={colors.textMuted} fontFamily={fonts.mono} fontSize={18} textAnchor="middle">
                {age}
              </text>
            </g>
          ))}

          {/* axes */}
          <line x1={CHART.x} y1={CHART.y} x2={CHART.x} y2={CHART.y + CHART.h} stroke={colors.textDim} strokeWidth={2} />
          <line x1={CHART.x} y1={CHART.y + CHART.h} x2={CHART.x + CHART.w} y2={CHART.y + CHART.h} stroke={colors.textDim} strokeWidth={2} />
          {/* axis labels */}
          <text x={CHART.x + CHART.w / 2} y={CHART.y + CHART.h + 62} fill={colors.textDim} fontFamily={fonts.mono} fontSize={22} textAnchor="middle">
            tree age (years, 0–40)
          </text>
          <text
            x={CHART.x - 44}
            y={CHART.y + CHART.h / 2}
            fill={colors.textDim}
            fontFamily={fonts.mono}
            fontSize={22}
            textAnchor="middle"
            transform={`rotate(-90 ${CHART.x - 44} ${CHART.y + CHART.h / 2})`}
          >
            crown diameter (m)
          </text>

          {/* 95% plateau guides */}
          <g opacity={interpolate(grow, [0.5, 0.75], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}>
            <line x1={CHART.x} y1={py(fast95)} x2={CHART.x + CHART.w} y2={py(fast95)} stroke={FAST.color} strokeWidth={1.5} strokeDasharray="7 7" opacity={0.5} />
            <text x={CHART.x + CHART.w} y={py(fast95) - 8} fill={FAST.color} fontFamily={fonts.mono} fontSize={16} textAnchor="end">
              95% mature · age 20
            </text>
            <line x1={CHART.x} y1={py(slow95)} x2={CHART.x + CHART.w} y2={py(slow95)} stroke={SLOW.color} strokeWidth={1.5} strokeDasharray="7 7" opacity={0.5} />
            <text x={CHART.x + CHART.w} y={py(slow95) - 8} fill={SLOW.color} fontFamily={fonts.mono} fontSize={16} textAnchor="end">
              95% mature · age 40
            </text>
          </g>

          {/* shared origin dot: planting crown 1.5 m at age 0 */}
          <circle cx={px(0)} cy={py(1.5)} r={7} fill={colors.text} stroke={colors.canopyBright} strokeWidth={2} />
          <text x={px(0) + 16} y={py(1.5) + 6} fill={colors.textDim} fontFamily={fonts.mono} fontSize={17}>
            planting crown 1.5 m
          </text>

          {/* SLOW curve (drawn first, behind) */}
          <path d={slowPath} fill="none" stroke={SLOW.color} strokeWidth={4} strokeLinecap="round" opacity={0.92} />
          {/* FAST curve */}
          <path d={fastPath} fill="none" stroke={FAST.color} strokeWidth={4.5} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 8px ${colors.canopyGlow})` }} />

          {/* tracers ride the heads */}
          {grow > 0.001 && grow < 0.999 && (
            <>
              <circle cx={fastTip.x} cy={fastTip.y} r={9} fill={FAST.color} />
              <circle cx={fastTip.x} cy={fastTip.y} r={18} fill={FAST.color} opacity={0.22} />
              <circle cx={slowTip.x} cy={slowTip.y} r={8} fill={SLOW.color} />
              <circle cx={slowTip.x} cy={slowTip.y} r={16} fill={SLOW.color} opacity={0.22} />
            </>
          )}

          {/* curve end labels */}
          <g opacity={interpolate(grow, [0.7, 0.95], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}>
            <text x={fastTip.x - 14} y={fastTip.y - 16} fill={FAST.color} fontFamily={fonts.mono} fontSize={18} fontWeight={700} textAnchor="end">
              FAST {FAST.name}
            </text>
            <text x={slowTip.x - 14} y={slowTip.y + 30} fill={SLOW.color} fontFamily={fonts.mono} fontSize={18} fontWeight={700} textAnchor="end">
              SLOW {SLOW.name}
            </text>
          </g>

          {/* top-down canopy discs growing in step (under each curve head) */}
          <g opacity={discOp}>
            <circle cx={CHART.x + CHART.w - 80} cy={CHART.y + 70} r={Math.max(6, (fastCrownNow / 2) * discScale * 0.18)} fill={FAST.color} opacity={0.28} />
            <circle cx={CHART.x + CHART.w - 80} cy={CHART.y + 70} r={Math.max(3, (fastCrownNow / 2) * discScale * 0.1)} fill={FAST.color} opacity={0.55} />
            <circle cx={CHART.x + CHART.w - 80} cy={CHART.y + 190} r={Math.max(6, (slowCrownNow / 2) * discScale * 0.18)} fill={SLOW.color} opacity={0.28} />
            <circle cx={CHART.x + CHART.w - 80} cy={CHART.y + 190} r={Math.max(3, (slowCrownNow / 2) * discScale * 0.1)} fill={SLOW.color} opacity={0.55} />
          </g>
        </g>
      </svg>

      {/* equation chip — left column in act 1 */}
      <div style={{ position: "absolute", top: 270, left: 110, width: 470, opacity: eqOp * fadeCaptions }}>
        <Panel style={{ padding: "22px 26px" }} glow={colors.canopyGlow}>
          <Label color={colors.canopyBright} size={19}>
            Chapman-Richards
          </Label>
          <div style={{ height: 12 }} />
          <div style={{ fontFamily: fonts.mono, fontSize: 27, fontWeight: 600, color: colors.text, lineHeight: 1.3 }}>
            crown(age) = max(1.5, A·(1 − e^(−k·age))³)
          </div>
          <div style={{ height: 16 }} />
          <div style={{ display: "flex", gap: 12 }}>
            <Chip color={FAST.color} size={20}>
              fast k~0.204
            </Chip>
            <Chip color={SLOW.color} size={20}>
              slow k~0.102
            </Chip>
          </div>
        </Panel>
      </div>

      {/* side caption — left column, lower */}
      <div style={{ position: "absolute", top: 540, left: 110, width: 470, opacity: capOp * fadeCaptions }}>
        <GlossCard
          term="fast fills its crown ~2× faster"
          plain="Same S-curve, different k. Tipuana reaches 95% of its mature crown by age 20; Cercis only at age 40 — species choice changes the whole cooling timeline."
          color={colors.canopyBright}
        />
      </div>
    </>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ACT 2 — itemised cost: CapEx bars, OpEx fraction, discounted coins → PV.
const CostAct: React.FC<{ frame: number; df: number; a1: number }> = ({ frame, df, a1 }) => {
  const active = frame >= a1 - 4;
  if (!active) return null;
  const local = frame - a1;
  const span = df - a1;

  return (
    <AbsoluteFill>
      <CapExLedger local={local} span={span} />
      <OpExCallout local={local} span={span} />
      <DiscountTimeline local={local} span={span} />
    </AbsoluteFill>
  );
};

// ── CapEx rising bars summing to EUR 2,200 ──
const CapExLedger: React.FC<{ local: number; span: number }> = ({ local, span }) => {
  const start = 30;
  const gap = 12;
  const ledger = { x: 700, y: 250, w: 520, rowH: 56 };
  const maxEur = 600;
  const barMaxW = 300;

  // fade ledger out when the timeline takes over (last third)
  const fade = interpolate(local, [span * 0.6, span * 0.7], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ position: "absolute", top: ledger.y, left: ledger.x, width: ledger.w, opacity: fade }}>
      <Label color={colors.gold} size={22}>
        CAPEX · one-time, per tree
      </Label>
      <div style={{ height: 16 }} />
      {CAPEX.map((item, i) => {
        const at = start + i * gap;
        const t = interpolate(local, [at, at + 16], [0, 1], {
          easing: Easing.out(Easing.cubic),
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const bw = (item.eur / maxEur) * barMaxW * t;
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 16, height: ledger.rowH, opacity: t }}>
            <div style={{ width: 180, fontFamily: fonts.mono, fontSize: 21, color: colors.textDim }}>{item.label}</div>
            <div
              style={{
                height: 26,
                width: bw,
                background: colors.gold,
                borderRadius: 6,
                boxShadow: `0 0 18px ${colors.gold}55`,
              }}
            />
            <div style={{ fontFamily: fonts.mono, fontSize: 21, fontWeight: 700, color: colors.text }}>
              € {item.eur}
            </div>
          </div>
        );
      })}

      {/* total */}
      {(() => {
        const at = start + CAPEX.length * gap + 8;
        const t = interpolate(local, [at, at + 18], [0, 1], {
          easing: Easing.out(Easing.cubic),
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div style={{ opacity: t, transform: `translateY(${(1 - t) * 14}px)`, marginTop: 14, borderTop: `1.5px solid ${colors.border}`, paddingTop: 18 }}>
            <Stat
              value={
                <span>
                  CapEx €{" "}
                  <Counter from={0} to={CAPEX_TOTAL} startFrame={at} durationInFrames={20} format={(n) => Math.round(n).toLocaleString("en-US")} />
                </span>
              }
              label="600 + 500 + 600 + 200 + 300"
              color={colors.gold}
              size={64}
            />
          </div>
        );
      })()}
    </div>
  );
};

// ── OpEx EUR 60/tree/yr — fraction resolves to 61.28 (VERIFIED) ──
const OpExCallout: React.FC<{ local: number; span: number }> = ({ local, span }) => {
  const at = span * 0.32;
  const op = interpolate(local, [at, at + 16], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // typed-fraction reveal: numerator → denominator → result
  const numW = interpolate(local, [at + 6, at + 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const denW = interpolate(local, [at + 18, at + 32], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const resOp = interpolate(local, [at + 34, at + 48], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fade = interpolate(local, [span * 0.62, span * 0.72], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div style={{ position: "absolute", top: 300, left: 1300, width: 510, opacity: op * fade }}>
      <Panel style={{ padding: "26px 30px" }} glow={colors.canopyGlow}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Stat value="€ 60" label="OpEx / tree / yr" color={colors.gold} size={72} />
          <div style={{ marginTop: 6 }}>
            <Tag kind="VERIFIED" color={colors.canopy} />
          </div>
        </div>
        <div style={{ height: 22 }} />
        <Label color={colors.textDim} size={19}>
          derived from the live maintenance ledger
        </Label>
        <div style={{ height: 12 }} />
        {/* resolving fraction */}
        <div style={{ fontFamily: fonts.mono, fontSize: 26, fontWeight: 600, color: colors.text, display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <span style={{ overflow: "hidden", whiteSpace: "nowrap", display: "inline-block", width: `${(numW * 100).toFixed(1)}%`, maxWidth: "max-content" }}>
            12,658,229
          </span>
          <span style={{ opacity: numW }}>/</span>
          <span style={{ opacity: denW }}>206,556</span>
          <span style={{ opacity: resOp, color: colors.canopyBright, fontWeight: 700 }}>= 61.28</span>
        </div>
        <div style={{ height: 8 }} />
        <Label color={colors.textMuted} size={16}>
          total annual € / trees served — rounds to € 60/tree/yr
        </Label>
      </Panel>
    </div>
  );
};

// ── 40-year discounted timeline: shrinking coins → PV ~ EUR 3,481/tree ──
const DiscountTimeline: React.FC<{ local: number; span: number }> = ({ local, span }) => {
  const start = span * 0.62;
  const active = local >= start - 6;
  if (!active) return null;
  const op = interpolate(local, [start - 6, start + 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const lane = { x: 150, y: 560, w: 1620, h: 120 };
  const YEARS = 40;
  const rate = 0.035;

  // sweep reveals years left→right over ~60% of the remaining span
  const sweepEnd = start + (span - start) * 0.62;
  const sweepT = interpolate(local, [start + 8, sweepEnd], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const yearsShown = sweepT * YEARS;

  // counter lock timing
  const counterStart = Math.round(sweepEnd + 4);
  const lockT = interpolate(local, [sweepEnd + 24, sweepEnd + 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const yx = (yr: number) => lane.x + (yr / YEARS) * lane.w;

  return (
    <AbsoluteFill style={{ opacity: op }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* timeline axis */}
        <line x1={lane.x} y1={lane.y + lane.h} x2={lane.x + lane.w} y2={lane.y + lane.h} stroke={colors.textDim} strokeWidth={2} />
        {[0, 10, 20, 30, 40].map((yr) => (
          <g key={`ty${yr}`}>
            <line x1={yx(yr)} y1={lane.y + lane.h} x2={yx(yr)} y2={lane.y + lane.h + 8} stroke={colors.textMuted} strokeWidth={1.5} />
            <text x={yx(yr)} y={lane.y + lane.h + 30} fill={colors.textMuted} fontFamily={fonts.mono} fontSize={17} textAnchor="middle">
              yr {yr}
            </text>
          </g>
        ))}

        {/* coins drop per year, SHRINKING as they recede (discount metaphor) */}
        {Array.from({ length: YEARS }).map((_, i) => {
          const yr = i + 1;
          if (yr > yearsShown) return null;
          const appear = interpolate(yearsShown - yr, [0, 1.2], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const discount = Math.pow(1 + rate, -yr); // 1.0 → ~0.25 over 40 yr
          const rad = 4 + discount * 16; // shrinks toward the future
          const cyBase = lane.y + lane.h - 14;
          const drop = interpolate(appear, [0, 1], [-30, 0], { easing: Easing.out(Easing.cubic) });
          return (
            <g key={`coin${i}`} opacity={appear} transform={`translate(${yx(yr)} ${cyBase + drop})`}>
              <circle r={rad} fill={colors.gold} opacity={0.85} />
              <circle r={rad} fill="none" stroke={colors.amber} strokeWidth={1.2} opacity={0.6} />
            </g>
          );
        })}

        {/* "40 yr @ 3.5%" label over the lane */}
        <text x={lane.x + lane.w / 2} y={lane.y - 14} fill={colors.gold} fontFamily={fonts.mono} fontSize={24} fontWeight={700} textAnchor="middle">
          40 yr @ 3.5% — each future euro discounted
        </text>
      </svg>

      {/* the locking PV headline counter */}
      <div
        style={{
          position: "absolute",
          top: 720,
          left: 0,
          width: 1920,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div
          style={{
            fontFamily: fonts.display,
            fontWeight: 900,
            fontSize: 110,
            lineHeight: 1,
            letterSpacing: -3,
            color: colors.gold,
            fontVariantNumeric: "tabular-nums",
            textShadow: `0 0 50px ${colors.gold}40`,
          }}
        >
          PV ~ €{" "}
          <Counter
            from={0}
            to={3481}
            startFrame={counterStart}
            durationInFrames={26}
            format={(n) => Math.round(n).toLocaleString("en-US")}
          />
          <span style={{ fontSize: 48, fontWeight: 700, letterSpacing: 0, color: colors.textDim }}>
            {" "}
            / tree
          </span>
        </div>
        {/* underline grows on lock */}
        <div
          style={{
            marginTop: 14,
            height: 5,
            width: `${lockT * 560}px`,
            background: colors.gold,
            borderRadius: 4,
            boxShadow: `0 0 20px ${colors.gold}`,
          }}
        />
        <div style={{ height: 16, opacity: lockT, transform: `translateY(${(1 - lockT) * 10}px)` }}>
          <Chip color={colors.canopy} solid size={26}>
            auditable
          </Chip>
        </div>
      </div>
    </AbsoluteFill>
  );
};
