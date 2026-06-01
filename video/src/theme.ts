// theme.ts — global design tokens for the film: the color palette, font stacks,
// canvas size + FPS, the real site's geographic bounds (SITE_BOUNDS, used by
// lib/geo to map lon/lat → pixels), and provenance-tag colors. Everything visual
// imports from here, so one edit restyles the whole video.
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadJetBrains } from "@remotion/google-fonts/JetBrainsMono";

// ── CoolSpend explainer — cinematic climate-documentary palette ──
// Heat (UTCI hot/extreme) → cool canopy green, echoing the app's felt-temperature scale.
export const colors = {
  // base
  bg: "#080B10",
  bgSoft: "#0E131A",
  surface: "#11181F",
  border: "#212C36",
  hairline: "#18212B",

  // heat side (urban heat / danger)
  heat: "#FF5A36",
  ember: "#E8431F",
  amber: "#F5A623",
  heatGlow: "rgba(255,90,54,0.35)",

  // cool / canopy side (the intervention)
  canopy: "#37D08A",
  canopyBright: "#5BE8A6",
  cool: "#4EA8DE",
  teal: "#2FD3C3",
  canopyGlow: "rgba(55,208,138,0.38)",
  coolGlow: "rgba(78,168,222,0.32)",

  // emphasis
  gold: "#F2C14E",

  // gradients
  heatToCool: "linear-gradient(90deg, #E8431F 0%, #F5A623 38%, #37D08A 100%)",
  utciScale:
    "linear-gradient(90deg, #2C6FB0 0%, #4EA8DE 22%, #37D08A 42%, #F5A623 70%, #E8431F 100%)",
  inkFade: "linear-gradient(180deg, rgba(8,11,16,0) 0%, rgba(8,11,16,0.85) 100%)",

  // text
  text: "#F4F7F4",
  textDim: "rgba(244,247,244,0.66)",
  textMuted: "rgba(244,247,244,0.40)",
  textFaint: "rgba(244,247,244,0.22)",
};

export const fonts = {
  display: loadInter("normal", {
    weights: ["400", "500", "600", "700", "800", "900"],
    subsets: ["latin"],
  }).fontFamily,
  mono: loadJetBrains("normal", {
    weights: ["400", "500", "600", "700"],
    subsets: ["latin"],
  }).fontFamily,
};

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

// Real plaza bundle bounds (Plaça dels Àngels showcase) — maps geo → pixels for overlays.
export const SITE_BOUNDS = {
  west: 2.1659135,
  south: 41.3823462,
  east: 2.1676341,
  north: 41.3831634,
};

// Provenance tag → color (honesty architecture)
export const provenance: Record<string, string> = {
  MEASURED: colors.canopy,
  VERIFIED: colors.canopy,
  DECLARED: colors.amber,
  REQUIRES_VERIFICATION: colors.heat,
};
