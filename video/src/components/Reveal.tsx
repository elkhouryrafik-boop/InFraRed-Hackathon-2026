import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";

type Props = {
  startFrame: number;
  durationInFrames?: number;
  translateY?: number;
  translateX?: number;
  scaleFrom?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
};

export const Reveal: React.FC<Props> = ({
  startFrame,
  durationInFrames = 22,
  translateY = 24,
  translateX = 0,
  scaleFrom = 1,
  children,
  style,
}) => {
  const frame = useCurrentFrame();
  const t = interpolate(
    frame,
    [startFrame, startFrame + durationInFrames],
    [0, 1],
    {
      easing: Easing.bezier(0.16, 1, 0.3, 1),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
  return (
    <div
      style={{
        opacity: t,
        transform: `translate(${(1 - t) * translateX}px, ${(1 - t) * translateY}px) scale(${scaleFrom + (1 - scaleFrom) * t})`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
