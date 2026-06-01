import React from "react";
import {
  AbsoluteFill,
  Img,
  staticFile,
  interpolate,
  useCurrentFrame,
  Easing,
} from "remotion";
import { colors, fonts, SITE_BOUNDS } from "../theme";
import { lonLatToPct, metresToPctX, rgb, TreeFeature } from "../lib/geo";
import trees from "../data/trees.json";
import boundary from "../data/boundary.json";

// BeforeAfterHeatmap — the data viz at the heart of Scene 08. It stacks the two
// real Infrared UTCI rasters (baseline + intervention) and crossfades them at
// revealAtF, draws the real site boundary, and grows the proposed trees in from
// data/trees.json — each placed by lon/lat via lonLatToPct (see lib/geo), with
// crown size from crown_diameter_m via metresToPctX so dots match the raster 1:1.

// Panel sized to the real bbox aspect (≈1.59:1) so raster + trees align 1:1.
const PANEL_W = 1180;
const PANEL_H = Math.round(PANEL_W / 1.59);

type Props = {
  // frame (local) at which the heatmap flips baseline → intervention
  revealAtF: number;
  // frame at which proposed trees start growing in
  treesAtF: number;
  showTrees?: boolean;
};

const feats = (trees as { features: TreeFeature[] }).features;
const ring = (boundary as {
  features: { geometry: { coordinates: number[][][] } }[];
}).features[0].geometry.coordinates[0];

export const BeforeAfterHeatmap: React.FC<Props> = ({
  revealAtF,
  treesAtF,
  showTrees = true,
}) => {
  const frame = useCurrentFrame();
  const flip = interpolate(frame, [revealAtF, revealAtF + 26], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });
  const grow = interpolate(frame, [treesAtF, treesAtF + 34], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const ringPath =
    ring
      .map((c) => {
        const { xPct, yPct } = lonLatToPct(c[0], c[1]);
        return `${xPct},${yPct}`;
      })
      .join(" ");

  return (
    <AbsoluteFill
      style={{ alignItems: "center", justifyContent: "center" }}
    >
      <div
        style={{
          position: "relative",
          width: PANEL_W,
          height: PANEL_H,
          borderRadius: 14,
          overflow: "hidden",
          boxShadow: "0 30px 90px rgba(0,0,0,0.6)",
          border: `1px solid ${colors.border}`,
          background: colors.bgSoft,
        }}
      >
        {/* baseline raster */}
        <Img
          src={staticFile("app/utci_baseline.png")}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "fill",
            imageRendering: "auto",
          }}
        />
        {/* intervention raster crossfades in */}
        <Img
          src={staticFile("app/utci_intervention.png")}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "fill",
            opacity: flip,
          }}
        />

        {/* site boundary + trees in bounds space */}
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
        >
          <polygon
            points={ringPath}
            fill="none"
            stroke={colors.text}
            strokeOpacity={0.7}
            strokeWidth={0.35}
            strokeDasharray="1.4 1.0"
          />
        </svg>

        {showTrees &&
          feats.map((f, i) => {
            const [lon, lat] = f.geometry.coordinates;
            const { xPct, yPct } = lonLatToPct(lon, lat);
            const proposed = f.properties.kind === "proposed";
            const rPct = metresToPctX(f.properties.crown_diameter_m / 2);
            const appear = proposed ? grow : 1;
            const c = f.properties.color ?? [55, 208, 138];
            const stagger = interpolate(
              frame,
              [treesAtF + i * 1.2, treesAtF + i * 1.2 + 18],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            );
            const a = proposed ? stagger : 1;
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: `${xPct}%`,
                  top: `${yPct}%`,
                  width: `${rPct * 2}%`,
                  aspectRatio: "1 / 1",
                  transform: `translate(-50%,-50%) scale(${proposed ? appear : 1})`,
                  borderRadius: "50%",
                  background: proposed
                    ? `radial-gradient(circle, ${rgb(c, 0.55)} 0%, ${rgb(c, 0.28)} 60%, ${rgb(c, 0)} 100%)`
                    : "radial-gradient(circle, rgba(120,150,90,0.5) 0%, rgba(120,150,90,0) 70%)",
                  border: proposed
                    ? `1.5px solid ${rgb(c, 0.9)}`
                    : "1px dashed rgba(180,200,150,0.6)",
                  opacity: a,
                }}
              />
            );
          })}

        {/* heat→cool legend */}
        <div
          style={{
            position: "absolute",
            bottom: 14,
            left: 16,
            right: 16,
            display: "flex",
            alignItems: "center",
            gap: 10,
            fontFamily: fonts.mono,
            fontSize: 13,
            color: colors.textDim,
          }}
        >
          <span>cool</span>
          <div
            style={{
              flex: 1,
              height: 7,
              borderRadius: 4,
              background: colors.utciScale,
            }}
          />
          <span>extreme</span>
        </div>
      </div>

      {/* state label */}
      <div
        style={{
          marginTop: 22,
          fontFamily: fonts.mono,
          fontSize: 20,
          letterSpacing: 2,
          color: flip > 0.5 ? colors.canopy : colors.heat,
          fontWeight: 600,
        }}
      >
        {flip > 0.5 ? "WITH 20 TREES — LIVE INFRARED UTCI" : "BASELINE — LIVE INFRARED UTCI"}
      </div>
    </AbsoluteFill>
  );
};
