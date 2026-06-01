// kit.tsx — the shared styled text/UI atoms used across all scenes: Kicker (small
// uppercase eyebrow), Headline, Chip, Stat, Panel, GlossCard (term + plain
// explainer), Tag (provenance pill), and Label. All pull from theme tokens so
// typography stays consistent.
import React from "react";
import { colors, fonts } from "../theme";

// ── Reusable styled atoms for the CoolSpend explainer (cinematic climate-doc) ──

export const Kicker: React.FC<{ children: React.ReactNode; color?: string }> = ({
  children,
  color = colors.canopy,
}) => (
  <div
    style={{
      fontFamily: fonts.mono,
      fontSize: 22,
      letterSpacing: 6,
      textTransform: "uppercase",
      color,
      fontWeight: 600,
    }}
  >
    {children}
  </div>
);

export const Headline: React.FC<{
  children: React.ReactNode;
  size?: number;
  color?: string;
}> = ({ children, size = 76, color = colors.text }) => (
  <div
    style={{
      fontFamily: fonts.display,
      fontSize: size,
      fontWeight: 800,
      lineHeight: 1.02,
      letterSpacing: -1.5,
      color,
    }}
  >
    {children}
  </div>
);

export const Chip: React.FC<{
  children: React.ReactNode;
  color?: string;
  solid?: boolean;
  size?: number;
}> = ({ children, color = colors.canopy, solid = false, size = 24 }) => (
  <span
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      fontFamily: fonts.mono,
      fontSize: size,
      fontWeight: 600,
      letterSpacing: 0.5,
      color: solid ? colors.bg : color,
      background: solid ? color : "rgba(255,255,255,0.04)",
      border: `1.5px solid ${color}`,
      borderRadius: 999,
      padding: `${size * 0.32}px ${size * 0.7}px`,
      whiteSpace: "nowrap",
    }}
  >
    {children}
  </span>
);

export const Stat: React.FC<{
  value: React.ReactNode;
  label: string;
  color?: string;
  size?: number;
}> = ({ value, label, color = colors.text, size = 92 }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
    <div
      style={{
        fontFamily: fonts.display,
        fontWeight: 800,
        fontSize: size,
        lineHeight: 1,
        letterSpacing: -2,
        color,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {value}
    </div>
    <div
      style={{
        fontFamily: fonts.mono,
        fontSize: size * 0.2,
        letterSpacing: 2,
        textTransform: "uppercase",
        color: colors.textDim,
      }}
    >
      {label}
    </div>
  </div>
);

export const Panel: React.FC<{
  children: React.ReactNode;
  style?: React.CSSProperties;
  glow?: string;
}> = ({ children, style, glow }) => (
  <div
    style={{
      background: "rgba(14,19,26,0.82)",
      border: `1px solid ${colors.border}`,
      borderRadius: 16,
      backdropFilter: "blur(8px)",
      boxShadow: glow ? `0 0 60px ${glow}` : "0 20px 60px rgba(0,0,0,0.45)",
      ...style,
    }}
  >
    {children}
  </div>
);

export const GlossCard: React.FC<{ term: string; plain: string; color?: string }> = ({
  term,
  plain,
  color = colors.canopy,
}) => (
  <Panel style={{ padding: "18px 22px", maxWidth: 560 }} glow={`${color}22`}>
    <div
      style={{
        fontFamily: fonts.mono,
        fontSize: 19,
        fontWeight: 700,
        letterSpacing: 1,
        color,
        marginBottom: 6,
        textTransform: "uppercase",
      }}
    >
      {term}
    </div>
    <div style={{ fontFamily: fonts.display, fontSize: 23, lineHeight: 1.32, color: colors.textDim }}>
      {plain}
    </div>
  </Panel>
);

// provenance pill (VERIFIED / DECLARED / REQUIRES_VERIFICATION / MEASURED)
export const Tag: React.FC<{ kind: string; color: string }> = ({ kind, color }) => (
  <span
    style={{
      fontFamily: fonts.mono,
      fontSize: 16,
      fontWeight: 700,
      letterSpacing: 1.5,
      color,
      border: `1.5px solid ${color}`,
      borderRadius: 6,
      padding: "4px 10px",
      textTransform: "uppercase",
    }}
  >
    {kind}
  </span>
);

export const Label: React.FC<{ children: React.ReactNode; color?: string; size?: number }> = ({
  children,
  color = colors.textDim,
  size = 20,
}) => (
  <span
    style={{
      fontFamily: fonts.mono,
      fontSize: size,
      letterSpacing: 1,
      color,
    }}
  >
    {children}
  </span>
);
