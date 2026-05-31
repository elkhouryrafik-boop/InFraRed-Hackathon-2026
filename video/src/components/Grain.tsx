import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

const NOISE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.95" numOctaves="2" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(#n)" opacity="0.55"/></svg>`;

export const Grain: React.FC<{ intensity?: number }> = ({ intensity = 0.08 }) => {
  const frame = useCurrentFrame();
  const offset = (frame * 7) % 320;
  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        mixBlendMode: "overlay",
        opacity: intensity,
        backgroundImage: `url("data:image/svg+xml;utf8,${encodeURIComponent(NOISE_SVG)}")`,
        backgroundSize: "320px 320px",
        backgroundPosition: `${offset}px ${(offset * 1.3) % 320}px`,
      }}
    />
  );
};
