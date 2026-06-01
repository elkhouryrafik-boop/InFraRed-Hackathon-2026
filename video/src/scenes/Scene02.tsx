import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Easing, spring, useVideoConfig } from "remotion";
import { colors, fonts } from "../theme";
import { Kicker, Label } from "../components/kit";

// ── SCENE 02 — "UTCI: Measuring What People Feel" ──
// Defines the film's core metric. Four beats: radiant heat on a silhouette →
// four inputs (air/radiant/wind/humidity) funnel into one UTCI value → a gauge
// needle reads the felt temperature → shade pulls it back below the 26 °C
// comfort threshold. All motion is driven by p = frame/df.
// ── Scene 02 — "UTCI: Measuring What People Feel" (~55s) ──
// 4 beats scaled across df. Transparent root; content above y≈900; side margins ~110px.

const EZ = Easing.bezier(0.16, 1, 0.3, 1);

// A wavy heat ray drawn as an SVG path (sine wiggle) with an arrowhead at the tip.
const WavyArrow: React.FC<{
  x1: number; y1: number; x2: number; y2: number;
  color: string; width: number; amp: number; t: number; phase: number;
}> = ({ x1, y1, x2, y2, color, width, amp, t, phase }) => {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len; // perpendicular
  const ny = dx / len;
  const segs = 26;
  const reach = t; // 0..1 how far the ray has drawn
  let d = "";
  for (let i = 0; i <= segs; i++) {
    const f = (i / segs) * reach;
    const wig = Math.sin(f * Math.PI * 4 + phase) * amp * Math.min(1, f * 3);
    const px = x1 + dx * f + nx * wig;
    const py = y1 + dy * f + ny * wig;
    d += `${i === 0 ? "M" : "L"} ${px.toFixed(1)} ${py.toFixed(1)} `;
  }
  // arrowhead at current tip
  const ang = Math.atan2(dy, dx);
  const tipX = x1 + dx * reach;
  const tipY = y1 + dy * reach;
  const ah = width * 2.4;
  const head =
    reach > 0.18
      ? `M ${tipX} ${tipY} L ${tipX - ah * Math.cos(ang - 0.5)} ${tipY - ah * Math.sin(ang - 0.5)} ` +
        `M ${tipX} ${tipY} L ${tipX - ah * Math.cos(ang + 0.5)} ${tipY - ah * Math.sin(ang + 0.5)}`
      : "";
  return (
    <g opacity={Math.min(1, reach * 2)}>
      <path d={d} stroke={color} strokeWidth={width} fill="none" strokeLinecap="round" />
      {head && <path d={head} stroke={color} strokeWidth={width} fill="none" strokeLinecap="round" />}
    </g>
  );
};

// Translucent standing human silhouette.
const Silhouette: React.FC<{ cx: number; topY: number; h: number; color: string }> = ({ cx, topY, h, color }) => {
  const headR = h * 0.085;
  const bodyTop = topY + headR * 2;
  return (
    <g fill={color} stroke="none">
      <circle cx={cx} cy={topY + headR} r={headR} />
      <path
        d={`M ${cx - h * 0.07} ${bodyTop}
            Q ${cx} ${bodyTop - h * 0.02} ${cx + h * 0.07} ${bodyTop}
            L ${cx + h * 0.05} ${bodyTop + h * 0.5}
            L ${cx + h * 0.045} ${topY + h}
            L ${cx + h * 0.005} ${topY + h}
            L ${cx} ${bodyTop + h * 0.56}
            L ${cx - h * 0.005} ${topY + h}
            L ${cx - h * 0.045} ${topY + h}
            L ${cx - h * 0.05} ${bodyTop + h * 0.5} Z`}
      />
    </g>
  );
};

export const Scene02: React.FC<{ df: number }> = ({ df }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / df; // global progress 0..1

  // Beat windows (fractions of df)
  const b2 = 0.16, b3 = 0.58, b4 = 0.8;

  // Beat 1: radiant heat establishes
  const b1Heat = spring({ frame: frame - df * 0.03, fps, config: { damping: 200 }, durationInFrames: Math.round(df * 0.13) });

  // Beat 2: inputs funnel to UTCI chip (0 at b2 → 1 at b3)
  const funnel = interpolate(p, [b2, b3 - 0.06], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EZ });
  const utciLand = interpolate(p, [b3 - 0.14, b3 - 0.02], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EZ });

  // Beat 3: gauge sweep + needle
  const gaugeSweep = interpolate(p, [b3, b3 + 0.1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EZ });
  const needleSet = interpolate(p, [b3 + 0.08, b4 - 0.02], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EZ });

  // Beat 4: shade + needle eases down
  const shade = interpolate(p, [b4, b4 + 0.1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EZ });
  const cooldown = interpolate(p, [b4 + 0.05, 0.98], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EZ });

  // Stage opacities so beats hand off cleanly
  const stage1op = interpolate(p, [0, 0.02, b2 + 0.02, b2 + 0.1], [0, 1, 1, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const stage2op = interpolate(p, [b2, b2 + 0.05, b3, b3 + 0.06], [0, 1, 1, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const stage3op = interpolate(p, [b3 - 0.02, b3 + 0.05, b4, b4 + 0.06], [0, 1, 1, 0.18], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  const stage4op = interpolate(p, [b4 - 0.02, b4 + 0.06, 1], [0, 1, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

  // Header opacity
  const headIn = interpolate(frame, [6, 22], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

  // Shared plaza geometry
  const plazaY = 760;
  const silTop = 430;
  const silH = 330;
  const silCx = 560;

  // Needle angle for beat 3/4 (gauge is vertical, value 22..34 °C; tick at 26)
  const gaugeX = 1530, gTop = 300, gBot = 840;
  const valToY = (v: number) => interpolate(v, [22, 34], [gBot, gTop]);
  const tick26Y = valToY(26);
  const warmPeak = 30.2;
  const needleVal = 22 + (warmPeak - 22) * needleSet - (warmPeak - 26.4) * cooldown;
  const needleY = valToY(needleVal);

  // Funnel target (UTCI chip center)
  const cX = 960, cY = 540;

  // Input source positions for beat 2 (start spread, funnel to center)
  const inputs = [
    { key: "air", label: "AIR TEMP", color: colors.amber, x0: 300, y0: 250, w: 8, big: false },
    { key: "rad", label: "RADIANT HEAT", color: colors.heat, x0: 320, y0: 760, w: 18, big: true },
    { key: "wind", label: "WIND", color: colors.cool, x0: 1560, y0: 280, w: 7, big: false },
    { key: "hum", label: "HUMIDITY", color: colors.teal, x0: 1580, y0: 760, w: 7, big: false },
  ];

  return (
    <AbsoluteFill style={{ fontFamily: fonts.display }}>
      {/* Header (kept above content) */}
      <div style={{ position: "absolute", top: 80, left: 110, opacity: headIn }}>
        <Kicker color={colors.cool}>THE METRIC</Kicker>
        <div style={{ height: 12 }} />
        <div style={{ fontFamily: fonts.display, fontWeight: 800, fontSize: 54, letterSpacing: -1.4, color: colors.text }}>
          UTCI<span style={{ color: colors.textDim, fontWeight: 600 }}> · measuring what people feel</span>
        </div>
      </div>

      {/* ── BEAT 1: thermometer + silhouette + radiant heat dominant ── */}
      <AbsoluteFill style={{ opacity: stage1op }}>
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
          {/* plaza tile ground */}
          <rect x={140} y={plazaY} width={1640} height={14} rx={4} fill={colors.ember} opacity={0.5} />
          <rect x={140} y={plazaY + 14} width={1640} height={70} fill={colors.ember} opacity={0.12} />
          {/* side wall */}
          <rect x={140} y={300} width={16} height={plazaY - 300} rx={4} fill={colors.ember} opacity={0.4} />

          {/* radiant heat UP from pavement (big, bold) */}
          {[0, 1, 2].map((i) => (
            <WavyArrow key={`up${i}`} x1={silCx - 90 + i * 90} y1={plazaY} x2={silCx - 90 + i * 90} y2={silTop + 120}
              color={colors.heat} width={16} amp={14} t={b1Heat} phase={frame * 0.18 + i * 1.4} />
          ))}
          {/* radiant heat IN from side wall */}
          {[0, 1].map((i) => (
            <WavyArrow key={`side${i}`} x1={170} y1={520 + i * 110} x2={silCx - 110} y2={500 + i * 90}
              color={colors.heat} width={13} amp={10} t={b1Heat} phase={frame * 0.16 + i} />
          ))}
          {/* small wind arrow */}
          <WavyArrow x1={1020} y1={470} x2={silCx + 130} y2={500} color={colors.cool} width={6} amp={8} t={b1Heat} phase={frame * 0.22} />
          {/* humidity droplet */}
          <g opacity={b1Heat}>
            <path d={`M 1060 590 q -22 26 0 46 q 22 -20 0 -46 Z`} fill={colors.teal} />
          </g>

          <Silhouette cx={silCx} topY={silTop} h={silH} color="rgba(244,247,244,0.30)" />
        </svg>

        {/* thermometer reading calm air temp */}
        <div style={{ position: "absolute", left: 230, top: 360, transform: `scale(${0.85 + 0.15 * b1Heat})`, transformOrigin: "left center" }}>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 16 }}>
            <div style={{ position: "relative", width: 34, height: 230 }}>
              <div style={{ position: "absolute", inset: 0, borderRadius: 17, background: "rgba(244,247,244,0.10)", border: `2px solid ${colors.textMuted}` }} />
              <div style={{ position: "absolute", left: 7, right: 7, bottom: 8, height: `${interpolate(b1Heat, [0, 1], [20, 150])}px`, borderRadius: 12, background: colors.amber }} />
              <div style={{ position: "absolute", left: 0, bottom: -14, width: 56, height: 56, marginLeft: -11, borderRadius: "50%", background: colors.amber }} />
            </div>
            <div style={{ fontFamily: fonts.display, fontWeight: 800, fontSize: 56, color: colors.amber, letterSpacing: -1.5 }}>
              31°C
              <div style={{ fontFamily: fonts.mono, fontSize: 18, letterSpacing: 1.5, color: colors.textDim, fontWeight: 500 }}>AIR TEMP</div>
            </div>
          </div>
        </div>

        {/* dominant-input labels */}
        <div style={{ position: "absolute", left: 690, top: 690, opacity: b1Heat }}>
          <span style={{ fontFamily: fonts.mono, fontSize: 30, fontWeight: 700, letterSpacing: 2, color: colors.heat }}>RADIANT HEAT</span>
        </div>
        <div style={{ position: "absolute", left: 1040, top: 440, opacity: b1Heat }}><Label color={colors.cool} size={20}>WIND</Label></div>
        <div style={{ position: "absolute", left: 1090, top: 600, opacity: b1Heat }}><Label color={colors.teal} size={20}>HUMIDITY</Label></div>
      </AbsoluteFill>

      {/* ── BEAT 2: four inputs funnel → UTCI chip ── */}
      <AbsoluteFill style={{ opacity: stage2op }}>
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
          {inputs.map((inp) => {
            const ix = interpolate(funnel, [0, 1], [inp.x0, cX]);
            const iy = interpolate(funnel, [0, 1], [inp.y0, cY]);
            return (
              <WavyArrow key={inp.key} x1={inp.x0} y1={inp.y0} x2={ix} y2={iy}
                color={inp.color} width={inp.w} amp={inp.big ? 12 : 7} t={1} phase={frame * 0.15} />
            );
          })}
        </svg>

        {/* moving input chips */}
        {inputs.map((inp) => {
          const ix = interpolate(funnel, [0, 1], [inp.x0, cX]);
          const iy = interpolate(funnel, [0, 1], [inp.y0, cY]);
          const fade = interpolate(funnel, [0.7, 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={inp.key} style={{ position: "absolute", left: ix, top: iy, transform: "translate(-50%,-50%)", opacity: fade }}>
              <span style={{
                fontFamily: fonts.mono, fontSize: inp.big ? 28 : 20, fontWeight: 700, letterSpacing: 1.5,
                color: inp.color, border: `${inp.big ? 2.5 : 1.5}px solid ${inp.color}`,
                background: "rgba(8,11,16,0.6)", borderRadius: 999, padding: inp.big ? "10px 22px" : "6px 14px", whiteSpace: "nowrap",
              }}>{inp.label}</span>
            </div>
          );
        })}

        {/* UTCI chip lands at center */}
        <div style={{
          position: "absolute", left: cX, top: cY, transform: `translate(-50%,-50%) scale(${interpolate(utciLand, [0, 1], [0.4, 1])})`,
          opacity: utciLand, textAlign: "center",
        }}>
          <div style={{
            display: "inline-block", padding: "26px 64px", borderRadius: 28,
            background: "rgba(14,19,26,0.9)", border: `2.5px solid ${colors.heat}`,
            boxShadow: `0 0 80px ${colors.heatGlow}`,
          }}>
            <div style={{ fontFamily: fonts.display, fontWeight: 900, fontSize: 120, lineHeight: 1, letterSpacing: 2, color: colors.text }}>UTCI</div>
            <div style={{ fontFamily: fonts.mono, fontSize: 28, letterSpacing: 1, color: colors.amber, marginTop: 8 }}>°C = what a body feels</div>
          </div>
        </div>
      </AbsoluteFill>

      {/* ── BEAT 3 & 4: vertical UTCI gauge + needle + plaza/shade ── */}
      <AbsoluteFill style={{ opacity: Math.max(stage3op, stage4op) }}>
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
          {/* gauge track */}
          {(() => {
            const fillTop = interpolate(gaugeSweep, [0, 1], [gBot, gTop]);
            return (
              <g>
                <rect x={gaugeX - 26} y={gTop} width={52} height={gBot - gTop} rx={26} fill="rgba(244,247,244,0.06)" stroke={colors.border} strokeWidth={2} />
                {/* cool lower band */}
                <rect x={gaugeX - 24} y={Math.max(fillTop, tick26Y)} width={48} height={Math.max(0, gBot - Math.max(fillTop, tick26Y))} rx={22} fill={colors.cool} opacity={0.55} />
                {/* warm upper band */}
                {fillTop < tick26Y && (
                  <rect x={gaugeX - 24} y={fillTop} width={48} height={tick26Y - fillTop} rx={22} fill={colors.heat} opacity={0.7} />
                )}
                {/* hard tick at 26 */}
                <line x1={gaugeX - 52} y1={tick26Y} x2={gaugeX + 52} y2={tick26Y} stroke={colors.gold} strokeWidth={4} opacity={gaugeSweep} />
                {/* needle */}
                <g opacity={Math.min(1, needleSet * 3)}>
                  <polygon
                    points={`${gaugeX - 70},${needleY} ${gaugeX - 30},${needleY - 13} ${gaugeX - 30},${needleY + 13}`}
                    fill={colors.text}
                  />
                  <line x1={gaugeX - 30} y1={needleY} x2={gaugeX + 30} y2={needleY} stroke={colors.text} strokeWidth={3} />
                </g>
              </g>
            );
          })()}

          {/* ── BEAT 4 plaza scene under the gauge story ── */}
          <g opacity={stage4op}>
            <rect x={200} y={plazaY} width={1100} height={14} rx={4} fill={colors.ember} opacity={interpolate(shade, [0, 1], [0.5, 0.32])} />
            {/* tree canopy slides in */}
            <g transform={`translate(${interpolate(shade, [0, 1], [-260, 0])}, 0)`} opacity={shade}>
              <rect x={406} y={430} width={18} height={330} fill={colors.canopy} opacity={0.85} />
              <ellipse cx={415} cy={400} rx={170} ry={120} fill={colors.canopy} />
              <ellipse cx={415} cy={400} rx={170} ry={120} fill={colors.canopyBright} opacity={0.25} />
              {/* cast shadow on ground */}
              <ellipse cx={520} cy={plazaY + 8} rx={210} ry={26} fill="rgba(8,11,16,0.55)" />
            </g>
            {/* radiant arrows under shadow dim/shorten */}
            {[0, 1, 2].map((i) => {
              const sx = 470 + i * 70;
              const dim = interpolate(shade, [0, 1], [1, 0.28]);
              const shorten = interpolate(shade, [0, 1], [0, 0.55]);
              return (
                <WavyArrow key={`b4up${i}`} x1={sx} y1={plazaY} x2={sx} y2={interpolate(shorten, [0, 1], [silTop + 130, plazaY - 110])}
                  color={colors.heat} width={14} amp={12} t={1} phase={frame * 0.18 + i} />
              );
            })}
            {/* wind + humidity persist (right of silhouette) */}
            <WavyArrow x1={1010} y1={470} x2={760} y2={500} color={colors.cool} width={6} amp={8} t={1} phase={frame * 0.22} />
            <g opacity={0.9}><path d={`M 1050 590 q -22 26 0 46 q 22 -20 0 -46 Z`} fill={colors.teal} /></g>
            <Silhouette cx={640} topY={silTop} h={silH} color="rgba(244,247,244,0.32)" />
          </g>
        </svg>

        {/* gauge band labels */}
        <div style={{ position: "absolute", left: gaugeX - 360, top: tick26Y - 86, textAlign: "right", width: 320, opacity: gaugeSweep }}>
          <div style={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 30, color: colors.heat }}>moderate heat stress</div>
        </div>
        <div style={{ position: "absolute", left: gaugeX - 360, top: tick26Y + 40, textAlign: "right", width: 320, opacity: gaugeSweep }}>
          <div style={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 30, color: colors.cool }}>no thermal stress</div>
        </div>
        {/* hard 26 label */}
        <div style={{ position: "absolute", left: gaugeX + 70, top: tick26Y - 34, opacity: gaugeSweep }}>
          <span style={{ fontFamily: fonts.display, fontWeight: 800, fontSize: 48, color: colors.gold, letterSpacing: -1 }}>26 °C</span>
        </div>

        {/* provenance stamp */}
        <div style={{ position: "absolute", left: gaugeX - 120, top: 870, transform: "translateX(-50%)", opacity: interpolate(needleSet, [0.2, 0.6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
          <span style={{
            fontFamily: fonts.mono, fontSize: 20, letterSpacing: 1, color: colors.textDim,
            border: `1px solid ${colors.border}`, borderRadius: 8, padding: "6px 14px", background: "rgba(14,19,26,0.7)",
          }}>July 09:00–17:00 · 1.1 m</span>
        </div>

        {/* BEAT 4 end label */}
        <div style={{ position: "absolute", left: 200, top: 300, opacity: interpolate(shade, [0.4, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
          <span style={{ fontFamily: fonts.display, fontWeight: 800, fontSize: 46, letterSpacing: -1, color: colors.canopyBright }}>
            SHADE <span style={{ color: colors.textDim }}>→</span> <span style={{ color: colors.heat }}>radiant heat</span>
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
