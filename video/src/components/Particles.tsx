import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

type ParticleHue = "primary" | "accent" | "neutral";

type Particle = {
  x: number;
  y: number;
  size: number;
  speed: number;
  phase: number;
  hue: ParticleHue;
  depth: number;
};

type Props = {
  primaryColor: string;
  accentColor: string;
  bgColor: string;
  bgSoftColor?: string;
  tint?: "primary" | "accent" | "mixed";
  intensity?: number;
  count?: number;
};

const seed = (i: number, salt: number) => {
  const x = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453;
  return x - Math.floor(x);
};

const generateParticles = (count: number): Particle[] =>
  Array.from({ length: count }, (_, i) => {
    const r = seed(i, 1);
    const hue: ParticleHue = r < 0.4 ? "primary" : r < 0.8 ? "accent" : "neutral";
    return {
      x: seed(i, 2) * 1920,
      y: seed(i, 3) * 1080,
      size: 1 + seed(i, 4) * 3.5,
      speed: 6 + seed(i, 5) * 18,
      phase: seed(i, 6) * Math.PI * 2,
      depth: 0.3 + seed(i, 7) * 0.7,
      hue,
    };
  });

export const Particles: React.FC<Props> = ({
  primaryColor,
  accentColor,
  bgColor,
  bgSoftColor,
  tint = "mixed",
  intensity = 1,
  count = 90,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const soft = bgSoftColor ?? bgColor;

  const particles = React.useMemo(() => generateParticles(count), [count]);

  return (
    <AbsoluteFill style={{ background: bgColor, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 50%, ${soft} 0%, ${bgColor} 70%)`,
        }}
      />
      {particles.map((p, i) => {
        const drift = Math.sin(t * 0.4 + p.phase) * 30;
        const driftY = Math.cos(t * 0.3 + p.phase) * 20;
        const y = ((p.y - t * p.speed + driftY) % 1080 + 1080) % 1080;
        const x = (p.x + drift + 1920) % 1920;

        let color = "rgba(255,255,255,0.55)";
        if (tint === "primary" && p.hue !== "neutral") color = primaryColor;
        else if (tint === "accent" && p.hue !== "neutral") color = accentColor;
        else if (tint === "mixed") {
          color =
            p.hue === "primary"
              ? primaryColor
              : p.hue === "accent"
                ? accentColor
                : "rgba(255,255,255,0.55)";
        }

        const opacity = 0.18 * p.depth * intensity + 0.05;
        const size = p.size * p.depth;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: size,
              height: size,
              borderRadius: "50%",
              background: color,
              opacity,
              boxShadow: `0 0 ${size * 4}px ${color}`,
              filter: `blur(${(1 - p.depth) * 1.2}px)`,
            }}
          />
        );
      })}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, transparent 30%, ${bgColor} 95%)`,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
