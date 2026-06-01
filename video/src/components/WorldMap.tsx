// WorldMap.tsx — animated world map with pulsing city pins and arcs drawn
// between them (lat/lon projected equirectangularly onto an SVG-masked map).
// Reusable kit component for "scales to any city"-style beats.
import React from "react";
import { staticFile, Easing, interpolate, useCurrentFrame } from "remotion";

export type City = { name: string; lat: number; lon: number; start?: number };

type Props = {
  cities: City[];
  pinColor: string;
  pinGlowColor: string;
  arcColor: string;
  bgColor: string;
  baseStart?: number;
  mapFillGradient?: string;
};

const MAP_W = 2754;
const MAP_H = 1398;

const project = (lat: number, lon: number) => ({
  x: ((lon + 180) / 360) * 100,
  y: ((90 - lat) / 180) * 100,
});

const Pin: React.FC<{
  city: City;
  baseStart: number;
  pinColor: string;
  pinGlowColor: string;
  bgColor: string;
}> = ({ city, baseStart, pinColor, pinGlowColor, bgColor }) => {
  const frame = useCurrentFrame();
  const p = project(city.lat, city.lon);
  const start = baseStart + (city.start ?? 0);
  const t = interpolate(frame, [start, start + 20], [0, 1], {
    easing: Easing.bezier(0.4, 0, 0.2, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const pulse = 1 + Math.sin((frame - start) * 0.12) * 0.18;
  const ringPulse = ((frame - start) % 60) / 60;
  return (
    <div
      style={{
        position: "absolute",
        left: `${p.x}%`,
        top: `${p.y}%`,
        transform: `translate(-50%, -50%) scale(${t})`,
        opacity: t,
      }}
    >
      {t > 0.5 && (
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: 14 + ringPulse * 80,
            height: 14 + ringPulse * 80,
            marginLeft: -(14 + ringPulse * 80) / 2,
            marginTop: -(14 + ringPulse * 80) / 2,
            borderRadius: "50%",
            border: `1.5px solid ${pinColor}`,
            opacity: 1 - ringPulse,
          }}
        />
      )}
      <div
        style={{
          width: 16 * pulse,
          height: 16 * pulse,
          borderRadius: "50%",
          background: pinColor,
          boxShadow: `0 0 18px ${pinColor}, 0 0 50px ${pinGlowColor}`,
          position: "relative",
          zIndex: 2,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 22,
          left: "50%",
          transform: "translateX(-50%)",
          fontSize: 14,
          color: "#fff",
          letterSpacing: 3,
          textTransform: "uppercase",
          whiteSpace: "nowrap",
          textShadow: `0 0 12px ${bgColor}`,
          fontWeight: 700,
        }}
      >
        {city.name}
      </div>
    </div>
  );
};

const Arc: React.FC<{
  from: City;
  to: City;
  start: number;
  arcColor: string;
}> = ({ from, to, start, arcColor }) => {
  const frame = useCurrentFrame();
  const a = project(from.lat, from.lon);
  const b = project(to.lat, to.lon);
  const t = interpolate(frame, [start, start + 30], [0, 1], {
    easing: Easing.bezier(0.4, 0, 0.2, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const midX = (a.x + b.x) / 2;
  const midY = Math.min(a.y, b.y) - 6;
  const pathLen = 200;
  const path = `M ${a.x} ${a.y} Q ${midX} ${midY} ${b.x} ${b.y}`;
  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
      }}
    >
      <path
        d={path}
        stroke={arcColor}
        strokeWidth={0.25}
        fill="none"
        strokeDasharray={pathLen}
        strokeDashoffset={pathLen * (1 - t)}
        opacity={0.85}
        style={{ filter: `drop-shadow(0 0 1.5px ${arcColor})` }}
      />
    </svg>
  );
};

export const WorldMap: React.FC<Props> = ({
  cities,
  pinColor,
  pinGlowColor,
  arcColor,
  bgColor,
  baseStart = 0,
  mapFillGradient,
}) => {
  const frame = useCurrentFrame();
  const mapFade = interpolate(frame, [baseStart, baseStart + 30], [0, 1], {
    easing: Easing.bezier(0.4, 0, 0.2, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const fillGradient =
    mapFillGradient ??
    `linear-gradient(135deg, ${pinColor}55 0%, ${arcColor}55 50%, ${pinColor}66 100%)`;

  const sortedCities = [...cities].sort((a, b) => (a.start ?? 0) - (b.start ?? 0));

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        aspectRatio: `${MAP_W} / ${MAP_H}`,
        maxWidth: 1500,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: mapFade,
          WebkitMaskImage: `url(${staticFile("maps/world.svg")})`,
          maskImage: `url(${staticFile("maps/world.svg")})`,
          WebkitMaskSize: "contain",
          maskSize: "contain",
          WebkitMaskRepeat: "no-repeat",
          maskRepeat: "no-repeat",
          WebkitMaskPosition: "center",
          maskPosition: "center",
          background: fillGradient,
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: mapFade * 0.4,
          WebkitMaskImage: `url(${staticFile("maps/world.svg")})`,
          maskImage: `url(${staticFile("maps/world.svg")})`,
          WebkitMaskSize: "contain",
          maskSize: "contain",
          WebkitMaskRepeat: "no-repeat",
          maskRepeat: "no-repeat",
          WebkitMaskPosition: "center",
          maskPosition: "center",
          background: "repeating-linear-gradient(0deg, transparent 0 3px, rgba(255,255,255,0.06) 3px 4px)",
        }}
      />
      {sortedCities.length >= 2 &&
        sortedCities.slice(0, -1).map((from, i) => {
          const to = sortedCities[i + 1];
          return (
            <Arc
              key={`${from.name}-${to.name}`}
              from={from}
              to={to}
              start={baseStart + 50 + i * 6}
              arcColor={arcColor}
            />
          );
        })}
      {sortedCities.map((c) => (
        <Pin
          key={c.name}
          city={c}
          baseStart={baseStart + 36}
          pinColor={pinColor}
          pinGlowColor={pinGlowColor}
          bgColor={bgColor}
        />
      ))}
    </div>
  );
};
