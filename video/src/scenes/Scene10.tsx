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
import { colors, fonts, FPS, provenance } from "../theme";
import { Kicker, Headline, Chip, Stat, Panel, GlossCard, Tag, Label } from "../components/kit";
import { Reveal } from "../components/Reveal";
import { Counter } from "../components/Counter";

// ── SCENE 10 — "Never Report a Number We Didn't Compute" (~45s) ──────────────
// The honesty architecture: a three-tier backend (MOCK | CACHED | LIVE) selected
// by ONE setting, that never lets a synthetic number masquerade as measured.
// A vertical tier-switch occupies centre stage; a single glowing toggle slides
// between three lanes; each beat lights its lane and plays its story.
//
//   BEAT 1 (0–28%)  MOCK   — flat synthetic tile + red "NOT MEASURED DATA" stamp
//                            + struck-through globe "ZERO NETWORK CALLS".
//   BEAT 2 (28–58%) CACHED — geometry → hash; magnifier finds a match → replays a
//                            real heatmap; then a cache-MISS → hard red ERROR card,
//                            an X blocking the arrow back to MOCK.
//   BEAT 3 (58–80%) LIVE   — arrow → Infrared engine → real UTCI grid → return
//                            arrow deposits a card back into the cache store.
//   FINALE (80–100%)       — zoom out; provenance pills on every label; a MEASURED
//                            badge stays dark over mock, ILLUMINATES over live;
//                            close on the headline lockup + "MOCK · CACHED · LIVE".

// ── tier-switch geometry (centre stage) ──
const LANES = [
  { key: "MOCK", color: colors.heat },
  { key: "CACHED", color: colors.amber },
  { key: "LIVE", color: colors.canopy },
];
const SWITCH = { x: 150, y: 250, w: 360, laneH: 150, gap: 26 };
const laneY = (i: number) => SWITCH.y + i * (SWITCH.laneH + SWITCH.gap);
const laneMidY = (i: number) => laneY(i) + SWITCH.laneH / 2;
const TOGGLE_X = SWITCH.x - 64;

export const Scene10: React.FC<{ df: number }> = ({ df }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  void fps;

  // beat boundaries (frames)
  const b1 = df * 0.28;
  const b2 = df * 0.58;
  const b3 = df * 0.8;

  // which lane is selected right now → drives toggle slide + lane glow
  let selected = 0;
  if (frame >= b3) selected = 2;
  else if (frame >= b2) selected = 1;
  else if (frame >= b1) selected = 1; // cached lane stays lit through its beat
  else selected = 0;

  const intro = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ fontFamily: fonts.display }}>
      {/* ── header ── */}
      <div style={{ position: "absolute", top: 80, left: 110, opacity: intro }}>
        <Kicker color={colors.canopy}>THE HONESTY ARCHITECTURE</Kicker>
        <div style={{ height: 14 }} />
        <Headline size={58} color={colors.text}>
          Selected by <span style={{ color: colors.canopyBright }}>one setting</span>.
        </Headline>
        <div style={{ height: 8 }} />
        <Label color={colors.textDim} size={24}>
          MOCK · CACHED · LIVE
        </Label>
      </div>

      {/* ── the shared tier switch (all beats) ── */}
      <TierSwitch frame={frame} df={df} selected={selected} b1={b1} b2={b2} b3={b3} />

      {/* ── BEAT 1 — MOCK ── */}
      <MockBeat frame={frame} df={df} b1={b1} />

      {/* ── BEAT 2 — CACHED ── */}
      <CachedBeat frame={frame} df={df} b1={b1} b2={b2} />

      {/* ── BEAT 3 — LIVE ── */}
      <LiveBeat frame={frame} df={df} b2={b2} b3={b3} />

      {/* ── FINALE ── */}
      <Finale frame={frame} df={df} b3={b3} />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Shared vertical tier switch with the sliding glowing toggle.
const TierSwitch: React.FC<{
  frame: number;
  df: number;
  selected: number;
  b1: number;
  b2: number;
  b3: number;
}> = ({ frame, df, selected, b1, b2, b3 }) => {
  void df;
  const appear = interpolate(frame, [10, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // smoothed toggle position (spring toward selected lane mid)
  const target = laneMidY(selected);
  // ease between lane changes using beat boundaries as anchors
  const togY = smoothToggle(frame, b1, b2, b3);
  void target;

  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, opacity: appear }}>
      {/* switch rail */}
      <rect
        x={TOGGLE_X - 16}
        y={laneY(0) - 6}
        width={36}
        height={laneY(2) + SWITCH.laneH - laneY(0) + 12}
        rx={18}
        fill="rgba(14,19,26,0.7)"
        stroke={colors.border}
        strokeWidth={1.5}
      />
      {/* the glowing toggle knob */}
      <g>
        <circle cx={TOGGLE_X + 2} cy={togY} r={26} fill={LANES[selected].color} opacity={0.22} />
        <circle cx={TOGGLE_X + 2} cy={togY} r={14} fill={LANES[selected].color} />
        <circle cx={TOGGLE_X + 2} cy={togY} r={14} fill="none" stroke={colors.text} strokeWidth={1.5} opacity={0.5} />
      </g>

      {/* three lanes */}
      {LANES.map((lane, i) => {
        const lit = i === selected;
        const litT = interpolate(
          frame,
          [laneOnAt(i, b1, b2, b3), laneOnAt(i, b1, b2, b3) + 14],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        );
        const glow = lit ? litT : 0;
        return (
          <g key={lane.key}>
            <rect
              x={SWITCH.x}
              y={laneY(i)}
              width={SWITCH.w}
              height={SWITCH.laneH}
              rx={14}
              fill={lit ? hexA(lane.color, 0.1 + glow * 0.08) : "rgba(14,19,26,0.55)"}
              stroke={lit ? lane.color : colors.border}
              strokeWidth={lit ? 2.5 : 1.5}
              style={{ filter: lit ? `drop-shadow(0 0 ${10 + glow * 22}px ${hexA(lane.color, 0.5)})` : undefined }}
            />
            {/* connector from toggle to lane */}
            <line
              x1={TOGGLE_X + 16}
              y1={laneMidY(i)}
              x2={SWITCH.x}
              y2={laneMidY(i)}
              stroke={lit ? lane.color : colors.hairline}
              strokeWidth={lit ? 2.5 : 1.2}
              opacity={lit ? 0.8 : 0.4}
            />
            {/* lane label */}
            <text
              x={SWITCH.x + 26}
              y={laneMidY(i) + 12}
              fill={lit ? lane.color : colors.textMuted}
              fontFamily={fonts.mono}
              fontSize={40}
              fontWeight={700}
              letterSpacing={4}
            >
              {lane.key}
            </text>
            {/* sub-status */}
            <text
              x={SWITCH.x + 26}
              y={laneMidY(i) + 42}
              fill={lit ? colors.textDim : colors.textFaint}
              fontFamily={fonts.mono}
              fontSize={17}
            >
              {i === 0 ? "synthetic" : i === 1 ? "replay" : "real Infrared"}
            </text>
          </g>
        );
      })}
    </svg>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BEAT 1 — MOCK: flat synthetic tile + "NOT MEASURED DATA" stamp + struck globe.
const MockBeat: React.FC<{ frame: number; df: number; b1: number }> = ({ frame, df, b1 }) => {
  const active = frame < b1 + 28;
  if (!active) return null;
  const op = interpolate(frame, [8, 26, b1, b1 + 26], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  void df;

  const STAGE = { x: 700, y: 280, w: 520, h: 360 };

  // flat synthetic tile fills in
  const fillT = interpolate(frame, [20, 50], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // rubber stamp slams in (scale-in + slight rotate)
  const stampSp = spring({ frame: frame - 54, fps: FPS, config: { damping: 9, stiffness: 200 } });
  const stampScale = interpolate(stampSp, [0, 1], [2.4, 1]);
  const stampOp = interpolate(frame, [54, 60], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const stampRot = -8 + interpolate(stampSp, [0, 1], [6, 0]);

  return (
    <AbsoluteFill style={{ opacity: op }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* flat synthetic plaza tile — uniform, obviously fake */}
        <rect
          x={STAGE.x}
          y={STAGE.y}
          width={STAGE.w}
          height={STAGE.h}
          rx={12}
          fill={hexA(colors.heat, 0.12 * fillT)}
          stroke={colors.heat}
          strokeWidth={1.5}
          opacity={0.6 + fillT * 0.4}
        />
        {/* a flat synthetic grid — every cell identical (no real variation) */}
        {Array.from({ length: 6 * 4 }).map((_, k) => {
          const c = k % 6;
          const r = Math.floor(k / 6);
          const cw = STAGE.w / 6;
          const ch = STAGE.h / 4;
          const rev = interpolate(frame, [22 + k * 0.6, 30 + k * 0.6], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <rect
              key={k}
              x={STAGE.x + c * cw + 3}
              y={STAGE.y + r * ch + 3}
              width={cw - 6}
              height={ch - 6}
              rx={5}
              fill={hexA(colors.heat, 0.16)}
              opacity={rev * 0.8}
            />
          );
        })}
        {/* placeholder synthetic number — flat, fixed */}
        <text
          x={STAGE.x + STAGE.w / 2}
          y={STAGE.y + STAGE.h / 2 + 6}
          fill={colors.textMuted}
          fontFamily={fonts.mono}
          fontSize={22}
          textAnchor="middle"
          opacity={fillT * 0.7}
        >
          ΔUTCI = -2.0 °C  (placeholder)
        </text>

        {/* the red rubber-stamp */}
        <g
          transform={`translate(${STAGE.x + STAGE.w / 2} ${STAGE.y + STAGE.h / 2}) rotate(${stampRot}) scale(${stampScale})`}
          opacity={stampOp}
        >
          <rect x={-220} y={-44} width={440} height={88} rx={8} fill="none" stroke={colors.heat} strokeWidth={5} />
          <text
            x={0}
            y={12}
            fill={colors.heat}
            fontFamily={fonts.mono}
            fontSize={40}
            fontWeight={700}
            letterSpacing={2}
            textAnchor="middle"
          >
            NOT MEASURED DATA
          </text>
        </g>
      </svg>

      {/* struck-through network globe + ZERO NETWORK CALLS */}
      <div style={{ position: "absolute", top: 690, left: 700, width: 540 }}>
        <Reveal startFrame={64} translateY={16}>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <NetGlobe size={56} />
            <div>
              <Label color={colors.heat} size={26}>
                ZERO NETWORK CALLS
              </Label>
              <div style={{ height: 4 }} />
              <Label color={colors.textDim} size={18}>
                MOCK = NOT MEASURED DATA
              </Label>
            </div>
          </div>
        </Reveal>
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BEAT 2 — CACHED: geometry → hash, magnifier match → heatmap replay, then MISS.
const CachedBeat: React.FC<{ frame: number; df: number; b1: number; b2: number }> = ({
  frame,
  df,
  b1,
  b2,
}) => {
  const active = frame >= b1 - 8 && frame < b2 + 28;
  if (!active) return null;
  const op = interpolate(frame, [b1 - 8, b1 + 16, b2, b2 + 26], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  void df;

  const local = frame - b1;
  const span = b2 - b1;

  const STAGE = { x: 700, y: 280, w: 520, h: 220 };

  // 1) polygon morphs into a hash string
  const morphT = interpolate(local, [6, 36], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 2) magnifier scans a row of cached cards, snaps onto a match
  const scanStart = span * 0.3;
  const scanT = interpolate(local, [scanStart, scanStart + 30], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const cards = 4;
  const matchIdx = 2;
  const cardW = STAGE.w / cards;
  const magX = STAGE.x + cardW * (0.5 + scanT * matchIdx);
  const magY = STAGE.y + STAGE.h + 70;
  const matched = scanT > 0.95;

  // 3) the matched card replays a real heatmap (utciScale gradient grid)
  const replayT = interpolate(local, [scanStart + 32, scanStart + 60], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 4) FAILURE branch — a non-matching hash, magnifier finds nothing → ERROR
  const missStart = span * 0.74;
  const missT = interpolate(local, [missStart, missStart + 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: op }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* geometry polygon → hash */}
        <g opacity={1 - morphT} transform={`translate(${STAGE.x + 90} ${STAGE.y - 6})`}>
          <polygon
            points="0,40 60,0 130,28 110,96 30,86"
            fill="none"
            stroke={colors.cool}
            strokeWidth={2.5}
          />
        </g>
        <text
          x={STAGE.x + 30}
          y={STAGE.y + 30}
          fill={colors.amber}
          fontFamily={fonts.mono}
          fontSize={30}
          fontWeight={700}
          opacity={morphT}
        >
          hash: a13ccde…
        </text>

        {/* row of cached cards */}
        {Array.from({ length: cards }).map((_, i) => {
          const isMatch = i === matchIdx && matched;
          const x = STAGE.x + i * cardW + 8;
          const y = STAGE.y + 70;
          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={cardW - 16}
                height={STAGE.h - 80}
                rx={8}
                fill={isMatch ? hexA(colors.canopy, 0.12) : "rgba(14,19,26,0.7)"}
                stroke={isMatch ? colors.canopy : colors.border}
                strokeWidth={isMatch ? 2.5 : 1.2}
              />
              <text
                x={x + 12}
                y={y + 26}
                fill={isMatch ? colors.canopy : colors.textMuted}
                fontFamily={fonts.mono}
                fontSize={15}
              >
                {["b808462", "545bb6e", "a13ccde", "1962b50"][i]}
              </text>
              {/* the matched card replays a small REAL heatmap */}
              {isMatch &&
                Array.from({ length: 5 * 3 }).map((__, k) => {
                  const cc = k % 5;
                  const rr = Math.floor(k / 5);
                  const t = (cc + rr) / 6; // sample across utciScale
                  const cw = (cardW - 36) / 5;
                  const chh = (STAGE.h - 130) / 3;
                  return (
                    <rect
                      key={k}
                      x={x + 12 + cc * cw}
                      y={y + 40 + rr * chh}
                      width={cw - 2}
                      height={chh - 2}
                      rx={2}
                      fill={utciSample(t)}
                      opacity={replayT}
                    />
                  );
                })}
            </g>
          );
        })}

        {/* magnifier glass */}
        <g opacity={interpolate(local, [scanStart - 6, scanStart + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}>
          <circle cx={magX} cy={magY} r={28} fill="none" stroke={matched ? colors.canopy : colors.textDim} strokeWidth={3.5} />
          <line
            x1={magX + 20}
            y1={magY + 20}
            x2={magX + 42}
            y2={magY + 42}
            stroke={matched ? colors.canopy : colors.textDim}
            strokeWidth={4}
            strokeLinecap="round"
          />
        </g>

        {/* FAILURE branch: arrow back to MOCK lane, blocked by an explicit X */}
        {missT > 0 && (
          <g opacity={missT}>
            {/* arrow from cache stage pointing left/down toward the MOCK lane */}
            <line
              x1={STAGE.x - 20}
              y1={STAGE.y + STAGE.h + 30}
              x2={SWITCH.x + SWITCH.w + 30}
              y2={laneMidY(0)}
              stroke={colors.heat}
              strokeWidth={2.5}
              strokeDasharray="7 7"
            />
            {/* the blocking X — drawn explicitly over the arrow midpoint */}
            {(() => {
              const mx = (STAGE.x - 20 + SWITCH.x + SWITCH.w + 30) / 2;
              const my = (STAGE.y + STAGE.h + 30 + laneMidY(0)) / 2;
              const s = 26 * Math.min(1, missT * 1.4);
              return (
                <g>
                  <circle cx={mx} cy={my} r={34} fill="rgba(8,11,16,0.9)" stroke={colors.heat} strokeWidth={2.5} />
                  <line x1={mx - s} y1={my - s} x2={mx + s} y2={my + s} stroke={colors.heat} strokeWidth={5} strokeLinecap="round" />
                  <line x1={mx + s} y1={my - s} x2={mx - s} y2={my + s} stroke={colors.heat} strokeWidth={5} strokeLinecap="round" />
                </g>
              );
            })()}
          </g>
        )}
      </svg>

      {/* matched / replay caption */}
      {matched && (
        <Sequence from={Math.round(b1 + scanStart + 30)}>
          <div style={{ position: "absolute", top: 540, left: 700, width: 540 }}>
            <Reveal startFrame={Math.round(b1 + scanStart + 30)} translateY={14}>
              <Chip color={colors.canopy} size={22}>
                cache HIT → replay real UTCI
              </Chip>
            </Reveal>
          </div>
        </Sequence>
      )}

      {/* what "cached" means, in plain words */}
      <div style={{ position: "absolute", top: 506, left: 1280, width: 520 }}>
        <Reveal startFrame={Math.round(b1 + 18)} translateY={18}>
          <GlossCard
            term="CACHED = REPLAY OF A REAL RUN"
            plain="Same geometry → same hash → the exact UTCI a live run already produced. A miss is an error, never a fabricated number."
            color={colors.amber}
          />
        </Reveal>
      </div>

      {/* the hard red ERROR card */}
      {missT > 0 && (
        <div
          style={{
            position: "absolute",
            top: 620,
            left: 700,
            width: 560,
            opacity: missT,
            transform: `translateY(${(1 - missT) * 16}px)`,
          }}
        >
          <Panel style={{ padding: "22px 26px", border: `2px solid ${colors.heat}` }} glow={colors.heatGlow}>
            <Label color={colors.heat} size={28}>
              CACHE MISS → ERROR, NOT MOCK
            </Label>
            <div style={{ height: 8 }} />
            <Label color={colors.textDim} size={20}>
              never silently falls to mock
            </Label>
          </Panel>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BEAT 3 — LIVE: arrow → Infrared engine → real UTCI grid → return arrow → cache.
const LiveBeat: React.FC<{ frame: number; df: number; b2: number; b3: number }> = ({
  frame,
  df,
  b2,
  b3,
}) => {
  const active = frame >= b2 - 8 && frame < b3 + 30;
  if (!active) return null;
  const op = interpolate(frame, [b2 - 8, b2 + 16, b3, b3 + 28], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  void df;

  const local = frame - b2;
  const span = b3 - b2;

  const ENGINE = { x: 700, y: 300, w: 240, h: 150 };
  const GRID = { x: 1010, y: 290, w: 300, h: 220 };

  // arrow from LIVE lane hits the engine box
  const arrowT = interpolate(local, [8, 28], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // engine "computes" (pulse)
  const compute = 0.6 + 0.4 * Math.sin(local * 0.35);
  // real red-blue UTCI grid renders
  const gridT = interpolate(local, [span * 0.35, span * 0.65], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // return arrow deposits a card back into the cache store
  const returnT = interpolate(local, [span * 0.7, span * 0.92], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: op }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* arrow from LIVE lane → engine */}
        <line
          x1={SWITCH.x + SWITCH.w + 10}
          y1={laneMidY(2)}
          x2={ENGINE.x - 8}
          y2={ENGINE.y + ENGINE.h / 2}
          stroke={colors.canopy}
          strokeWidth={2.5}
          strokeDasharray="8 6"
          opacity={arrowT}
        />
        <polygon
          points={`${ENGINE.x - 8},${ENGINE.y + ENGINE.h / 2} ${ENGINE.x - 22},${ENGINE.y + ENGINE.h / 2 - 8} ${ENGINE.x - 22},${ENGINE.y + ENGINE.h / 2 + 8}`}
          fill={colors.canopy}
          opacity={arrowT}
        />

        {/* the real Infrared engine box */}
        <rect
          x={ENGINE.x}
          y={ENGINE.y}
          width={ENGINE.w}
          height={ENGINE.h}
          rx={12}
          fill="rgba(14,19,26,0.85)"
          stroke={colors.canopy}
          strokeWidth={2.5}
          style={{ filter: `drop-shadow(0 0 ${8 + compute * 18}px ${hexA(colors.canopy, 0.5)})` }}
        />
        <text x={ENGINE.x + ENGINE.w / 2} y={ENGINE.y + 56} fill={colors.canopyBright} fontFamily={fonts.mono} fontSize={24} fontWeight={700} textAnchor="middle">
          INFRARED
        </text>
        <text x={ENGINE.x + ENGINE.w / 2} y={ENGINE.y + 88} fill={colors.textDim} fontFamily={fonts.mono} fontSize={17} textAnchor="middle">
          real engine
        </text>
        {/* compute ticks */}
        {[0, 1, 2].map((k) => (
          <circle
            key={k}
            cx={ENGINE.x + ENGINE.w / 2 - 24 + k * 24}
            cy={ENGINE.y + ENGINE.h - 28}
            r={5}
            fill={colors.canopy}
            opacity={0.3 + 0.7 * Math.abs(Math.sin(local * 0.35 + k))}
          />
        ))}

        {/* genuine red-blue UTCI grid */}
        <g opacity={gridT}>
          {Array.from({ length: 8 * 6 }).map((_, k) => {
            const c = k % 8;
            const r = Math.floor(k / 8);
            const cw = GRID.w / 8;
            const chh = GRID.h / 6;
            // a hot core fading to cool edges → real-looking field
            const d = Math.hypot((c - 3.5) / 4, (r - 2.5) / 3);
            const t = Math.max(0, Math.min(1, 1 - d));
            const rev = interpolate(local, [span * 0.35 + (c + r) * 0.6, span * 0.4 + (c + r) * 0.6], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <rect
                key={k}
                x={GRID.x + c * cw + 1}
                y={GRID.y + r * chh + 1}
                width={cw - 2}
                height={chh - 2}
                fill={utciSample(t)}
                opacity={rev}
              />
            );
          })}
          <text x={GRID.x} y={GRID.y - 12} fill={colors.canopyBright} fontFamily={fonts.mono} fontSize={18} fontWeight={600}>
            real UTCI grid
          </text>
        </g>

        {/* return arrow deposits a card back into the CACHED store */}
        <g opacity={returnT}>
          <path
            d={`M ${GRID.x + GRID.w / 2} ${GRID.y + GRID.h + 14} C ${GRID.x} ${GRID.y + GRID.h + 120}, ${SWITCH.x + SWITCH.w + 120} ${laneMidY(1) - 60}, ${SWITCH.x + SWITCH.w + 30} ${laneMidY(1)}`}
            fill="none"
            stroke={colors.canopy}
            strokeWidth={2.5}
            strokeDasharray="8 6"
          />
          {/* the card travelling along, deposited at the cache lane */}
          {(() => {
            const cardX = interpolate(returnT, [0, 1], [GRID.x + GRID.w / 2 - 20, SWITCH.x + SWITCH.w + 10]);
            const cardY = interpolate(returnT, [0, 1], [GRID.y + GRID.h + 14, laneMidY(1) - 16]);
            return (
              <g>
                <rect x={cardX} y={cardY} width={44} height={32} rx={5} fill={hexA(colors.canopy, 0.18)} stroke={colors.canopy} strokeWidth={2} />
              </g>
            );
          })()}
        </g>
      </svg>

      {/* live cell tally — counts up as the real grid fills */}
      <div style={{ position: "absolute", top: 300, left: 1360, width: 360 }}>
        <Reveal startFrame={Math.round(b2 + span * 0.35)} translateY={16}>
          <Stat
            value={
              <Counter
                from={0}
                to={48}
                startFrame={Math.round(b2 + span * 0.35)}
                durationInFrames={Math.round(span * 0.3)}
                suffix=" cells"
              />
            }
            label="real UTCI samples computed"
            color={colors.canopyBright}
            size={64}
          />
        </Reveal>
      </div>

      {/* live caption */}
      <div style={{ position: "absolute", top: 560, left: 700, width: 620 }}>
        <Reveal startFrame={Math.round(b2 + 8)} translateY={14}>
          <Chip color={colors.canopy} size={24}>
            LIVE → REAL UTCI → WRITES CACHE
          </Chip>
        </Reveal>
        {returnT > 0.4 && (
          <>
            <div style={{ height: 14 }} />
            <Reveal startFrame={Math.round(b2 + span * 0.7)} translateY={12}>
              <Label color={colors.textDim} size={20}>
                writes to cache for replay
              </Label>
            </Reveal>
          </>
        )}
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// FINALE — zoom out, provenance pills, MEASURED badge dark on mock / lit on live,
// closing headline lockup.
const Finale: React.FC<{ frame: number; df: number; b3: number }> = ({ frame, df, b3 }) => {
  const active = frame >= b3 - 6;
  if (!active) return null;
  const op = interpolate(frame, [b3 - 6, b3 + 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const local = frame - b3;
  const span = df - b3;

  // provenance pills cascade in
  const pillsT = interpolate(local, [10, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // MEASURED badge over live lane illuminates; over mock stays dark/locked
  const measuredT = interpolate(local, [span * 0.35, span * 0.55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // closing headline lockup
  const closeSp = spring({ frame: local - Math.round(span * 0.55), fps: FPS, config: { damping: 13, stiffness: 110 } });

  const PILLS: { kind: string; key: keyof typeof provenance | string }[] = [
    { kind: "VERIFIED", key: "VERIFIED" },
    { kind: "DECLARED", key: "DECLARED" },
    { kind: "REQUIRES_VERIFICATION", key: "REQUIRES_VERIFICATION" },
  ];

  return (
    <AbsoluteFill style={{ opacity: op }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {/* MEASURED badge — over MOCK lane: dark/locked */}
        <MeasuredBadge x={SWITCH.x + SWITCH.w + 60} y={laneMidY(0) - 24} lit={0} />
        {/* over LIVE lane: illuminates canopy green */}
        <MeasuredBadge x={SWITCH.x + SWITCH.w + 60} y={laneMidY(2) - 24} lit={measuredT} />
      </svg>

      {/* provenance pills — green VERIFIED, amber DECLARED, grey/red REQUIRES_VERIFICATION */}
      <div style={{ position: "absolute", top: 250, left: 760, display: "flex", flexDirection: "column", gap: 16 }}>
        {PILLS.map((p, i) => {
          const t = interpolate(pillsT, [i * 0.22, i * 0.22 + 0.4], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div key={p.kind} style={{ opacity: t, transform: `translateX(${(1 - t) * 22}px)` }}>
              <Tag kind={p.kind} color={provenance[p.key] ?? colors.textMuted} />
            </div>
          );
        })}
      </div>

      {/* closing centered headline lockup */}
      <div
        style={{
          position: "absolute",
          top: 470,
          left: 0,
          width: 1920,
          textAlign: "center",
          opacity: Math.min(1, closeSp),
          transform: `scale(${0.94 + Math.min(1, closeSp) * 0.06})`,
        }}
      >
        <Headline size={84} color={colors.text}>
          NEVER REPORT A NUMBER
        </Headline>
        <div style={{ height: 6 }} />
        <Headline size={84} color={colors.canopyBright}>
          WE DIDN&apos;T COMPUTE
        </Headline>
        <div style={{ height: 26 }} />
        <Label color={colors.textDim} size={32}>
          MOCK · CACHED · LIVE
        </Label>
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// small parts

// a network-globe icon (optionally struck through)
const NetGlobe: React.FC<{ size: number }> = ({ size }) => {
  const r = size / 2;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={r} cy={r} r={r - 4} fill="none" stroke={colors.textDim} strokeWidth={2} />
      <ellipse cx={r} cy={r} rx={(r - 4) * 0.5} ry={r - 4} fill="none" stroke={colors.textDim} strokeWidth={1.6} />
      <line x1={4} y1={r} x2={size - 4} y2={r} stroke={colors.textDim} strokeWidth={1.6} />
      <line x1={6} y1={r * 0.6} x2={size - 6} y2={r * 0.6} stroke={colors.textDim} strokeWidth={1.2} />
      <line x1={6} y1={r * 1.4} x2={size - 6} y2={r * 1.4} stroke={colors.textDim} strokeWidth={1.2} />
      {/* strikethrough */}
      <line x1={6} y1={size - 6} x2={size - 6} y2={6} stroke={colors.heat} strokeWidth={4} strokeLinecap="round" />
    </svg>
  );
};

// MEASURED badge — dark/locked at lit=0, canopy-illuminated at lit=1
const MeasuredBadge: React.FC<{ x: number; y: number; lit: number }> = ({ x, y, lit }) => {
  const col = lit > 0.02 ? mix(colors.textMuted, colors.canopy, lit) : colors.textMuted;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={210}
        height={48}
        rx={10}
        fill={lit > 0.02 ? hexA(colors.canopy, 0.12 * lit) : "rgba(14,19,26,0.6)"}
        stroke={col}
        strokeWidth={2}
        style={{ filter: lit > 0.4 ? `drop-shadow(0 0 ${lit * 18}px ${hexA(colors.canopy, 0.5)})` : undefined }}
      />
      {/* lock icon when dark */}
      {lit < 0.5 && (
        <g transform={`translate(${x + 22} ${y + 24})`} opacity={1 - lit}>
          <rect x={-9} y={-4} width={18} height={14} rx={3} fill="none" stroke={colors.textMuted} strokeWidth={2} />
          <path d="M -5 -4 V -9 A 5 5 0 0 1 5 -9 V -4" fill="none" stroke={colors.textMuted} strokeWidth={2} />
        </g>
      )}
      <text
        x={x + (lit < 0.5 ? 48 : 105)}
        y={y + 32}
        fill={col}
        fontFamily={fonts.mono}
        fontSize={22}
        fontWeight={700}
        letterSpacing={2}
        textAnchor={lit < 0.5 ? "start" : "middle"}
      >
        MEASURED
      </text>
    </g>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// helpers

// when each lane first lights (frames)
function laneOnAt(i: number, b1: number, b2: number, b3: number): number {
  if (i === 0) return 12;
  if (i === 1) return b1;
  return b3;
}

// smoothed toggle Y across the beats — eases between lane mids on boundaries.
function smoothToggle(frame: number, b1: number, b2: number, b3: number): number {
  // 0:mock → 1:cached (at b1) → stays 1 → 2:live (at b3)
  const toCached = interpolate(frame, [b1 - 12, b1 + 8], [laneMidY(0), laneMidY(1)], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (frame < b3 - 12) return toCached;
  return interpolate(frame, [b3 - 12, b3 + 8], [laneMidY(1), laneMidY(2)], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
}

// sample the utciScale gradient (cool→hot) at t∈[0,1]
function utciSample(t: number): string {
  const c = Math.max(0, Math.min(1, t));
  // stops: #2C6FB0, #4EA8DE, #37D08A, #F5A623, #E8431F at 0,.22,.42,.70,1
  const stops: [number, string][] = [
    [0, "#2C6FB0"],
    [0.22, "#4EA8DE"],
    [0.42, "#37D08A"],
    [0.7, "#F5A623"],
    [1, "#E8431F"],
  ];
  for (let i = 0; i < stops.length - 1; i++) {
    const [p0, c0] = stops[i];
    const [p1, c1] = stops[i + 1];
    if (c >= p0 && c <= p1) {
      return mix(c0, c1, (c - p0) / (p1 - p0));
    }
  }
  return stops[stops.length - 1][1];
}

// hex color + alpha → rgba string
function hexA(hex: string, a: number): string {
  if (!hex.startsWith("#")) return hex;
  const h = hex.slice(1);
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a.toFixed(3)})`;
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
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16), 1];
  }
  const m = s.match(/rgba?\(([^)]+)\)/);
  if (m) {
    const parts = m[1].split(",").map((p) => parseFloat(p.trim()));
    return [parts[0], parts[1], parts[2], parts[3] ?? 1];
  }
  return [255, 255, 255, 1];
}
