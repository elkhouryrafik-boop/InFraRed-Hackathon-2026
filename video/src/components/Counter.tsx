import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";

// Counter — animated number that eases from `from` to `to` over its frame window
// (interpolated on useCurrentFrame). `format` (or `decimals`) controls display;
// tabular-nums keeps digit width stable so the value doesn't jitter while ticking.
type Props = {
  from?: number;
  to: number;
  startFrame: number;
  durationInFrames: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  style?: React.CSSProperties;
  format?: (n: number) => string;
};

export const Counter: React.FC<Props> = ({
  from = 0,
  to,
  startFrame,
  durationInFrames,
  prefix = "",
  suffix = "",
  decimals = 0,
  style,
  format,
}) => {
  const frame = useCurrentFrame();
  const v = interpolate(
    frame,
    [startFrame, startFrame + durationInFrames],
    [from, to],
    {
      easing: Easing.bezier(0.16, 1, 0.3, 1),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
  const formatted = format ? format(v) : v.toFixed(decimals);
  return (
    <span style={{ fontVariantNumeric: "tabular-nums", ...style }}>
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
};
