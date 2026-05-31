// Map lon/lat → pixel within a bounds-aligned frame (linear Web-Mercator-lite;
// the site span is tiny so a linear map is visually exact at this scale).
import { SITE_BOUNDS } from "../theme";

export function lonLatToPct(
  lon: number,
  lat: number,
  bounds = SITE_BOUNDS,
): { xPct: number; yPct: number } {
  const xPct = ((lon - bounds.west) / (bounds.east - bounds.west)) * 100;
  const yPct = ((bounds.north - lat) / (bounds.north - bounds.south)) * 100;
  return { xPct, yPct };
}

// metres-per-degree at Barcelona latitude → crown radius (m) to % of frame width
export function metresToPctX(
  metres: number,
  bounds = SITE_BOUNDS,
): number {
  const midLat = (bounds.north + bounds.south) / 2;
  const spanM =
    (bounds.east - bounds.west) * 111320 * Math.cos((midLat * Math.PI) / 180);
  return (metres / spanM) * 100;
}

export type TreeFeature = {
  geometry: { coordinates: [number, number] };
  properties: {
    kind: "proposed" | "existing";
    species: string;
    common: string;
    scientific: string;
    color: [number, number, number];
    crown_diameter_m: number;
    crown_area_m2: number;
    height_m: number;
    cooling_score: number;
    leaf_cycle: string;
    shade_density: string;
    ecology?: Record<string, number | string>;
  };
};

export function rgb(c: [number, number, number], a = 1): string {
  return `rgba(${c[0]},${c[1]},${c[2]},${a})`;
}
