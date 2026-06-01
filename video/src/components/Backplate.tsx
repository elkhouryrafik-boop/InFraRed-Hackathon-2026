// Backplate.tsx — reusable cinematic background layer: a video or image with a
// slow Ken-Burns zoom/pan plus optional tint, vignette, and top/bottom gradient.
// (Utility kit component; scenes that use b-roll often roll their own inline.)
import React from "react";
import { AbsoluteFill, Img, staticFile, Easing, interpolate, useCurrentFrame } from "remotion";
import { Video } from "@remotion/media";

type Props = {
  videoSrc?: string;
  imageSrc?: string;
  zoom?: number;
  pan?: { x: number; y: number };
  durationInFrames: number;
  vignette?: boolean;
  tintOverlay?: string;
  tintOpacity?: number;
  opacity?: number;
  bgColor?: string;
};

export const Backplate: React.FC<Props> = ({
  videoSrc,
  imageSrc,
  zoom = 0.08,
  pan = { x: 20, y: 10 },
  durationInFrames,
  vignette = true,
  tintOverlay,
  tintOpacity = 0.4,
  opacity = 0.7,
  bgColor = "#0B111E",
}) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });
  const scale = 1 + zoom * t;
  const translateX = pan.x * t;
  const translateY = pan.y * t;

  return (
    <AbsoluteFill style={{ background: bgColor, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          transform: `scale(${scale}) translate(${translateX}px, ${translateY}px)`,
          opacity,
        }}
      >
        {videoSrc ? (
          <Video src={staticFile(videoSrc)} muted loop style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : imageSrc ? (
          <Img src={staticFile(imageSrc)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : null}
      </AbsoluteFill>
      {tintOverlay && (
        <AbsoluteFill
          style={{
            background: tintOverlay,
            mixBlendMode: "color",
            opacity: tintOpacity,
          }}
        />
      )}
      {vignette && (
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at 50% 50%, transparent 35%, ${bgColor} 95%)`,
            pointerEvents: "none",
          }}
        />
      )}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, ${bgColor}66 0%, transparent 30%, transparent 70%, ${bgColor}88 100%)`,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
