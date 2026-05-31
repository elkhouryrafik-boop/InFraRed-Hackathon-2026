// Pure UTCI colour-scale logic. NO deck.gl import — unit-testable headless.
//
// The exporter already colorises the UTCI rasters into RGBA PNGs, so the app
// does not re-colour pixels at runtime. This module exists so the HUD legend
// and any client-side colorisation share ONE source of truth, and so the scale
// can be tested headless.

export type RGB = [number, number, number]

/** A single stop on a perceptual UTCI ramp: value in °C -> colour. */
export interface ColorStop {
  /** UTCI value in °C this colour anchors. */
  value: number
  color: RGB
  /** Short human label for the legend. */
  label: string
}

/**
 * UTCI thermal-comfort ramp (cool -> hot). Anchored on the standard UTCI
 * heat-stress categories so the legend reads like the literature.
 *   < 26  : no thermal stress
 *   26-32 : moderate heat stress
 *   32-38 : strong heat stress
 *   38-46 : very strong heat stress
 *   > 46  : extreme heat stress
 *
 * Colours are the Redesign Spec v4 §2 CVD-SAFE, MONOTONIC-LIGHTNESS ramp:
 * hot = bright, cool = dark, so the scale survives deuteran/protan/tritan
 * colour-vision deficiency and pure greyscale (B1 release-blocker). The
 * value/label anchors (26/32/38/46) are preserved so the legend still reads
 * like the UTCI literature.
 */
export const UTCI_STOPS: ColorStop[] = [
  { value: 18, color: [13, 33, 73], label: 'Comfortable' }, // --t-20 (dark indigo)
  { value: 26, color: [58, 77, 160], label: 'No stress' }, // --t-24
  { value: 32, color: [181, 73, 122], label: 'Moderate' }, // --t-32 (magenta)
  { value: 38, color: [249, 168, 37], label: 'Strong' }, // --t-38 (amber)
  { value: 46, color: [252, 232, 79], label: 'Extreme' }, // --t-40 (bright yellow)
]

export const UTCI_MIN = UTCI_STOPS[0].value
export const UTCI_MAX = UTCI_STOPS[UTCI_STOPS.length - 1].value

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

function lerpColor(a: RGB, b: RGB, t: number): RGB {
  return [
    Math.round(lerp(a[0], b[0], t)),
    Math.round(lerp(a[1], b[1], t)),
    Math.round(lerp(a[2], b[2], t)),
  ]
}

/** Clamp a number into [lo, hi]. */
export function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v))
}

/**
 * Map a UTCI value (°C) to an RGB colour by linear interpolation between the
 * category stops. Values outside the range clamp to the end stops.
 */
export function utciColor(value: number): RGB {
  if (!Number.isFinite(value)) return [128, 128, 128]
  const v = clamp(value, UTCI_MIN, UTCI_MAX)
  for (let i = 0; i < UTCI_STOPS.length - 1; i++) {
    const lo = UTCI_STOPS[i]
    const hi = UTCI_STOPS[i + 1]
    if (v >= lo.value && v <= hi.value) {
      const span = hi.value - lo.value
      const t = span === 0 ? 0 : (v - lo.value) / span
      return lerpColor(lo.color, hi.color, t)
    }
  }
  return UTCI_STOPS[UTCI_STOPS.length - 1].color
}

/** CSS rgb() string for a UTCI value — handy for the legend gradient. */
export function utciCssColor(value: number): string {
  const [r, g, b] = utciColor(value)
  return `rgb(${r}, ${g}, ${b})`
}

/**
 * Build a CSS linear-gradient string spanning the full UTCI ramp, sampled at
 * `steps` points. Used by the HUD legend bar.
 */
export function utciGradientCss(steps = 24): string {
  const parts: string[] = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const value = lerp(UTCI_MIN, UTCI_MAX, t)
    parts.push(`${utciCssColor(value)} ${(t * 100).toFixed(1)}%`)
  }
  return `linear-gradient(90deg, ${parts.join(', ')})`
}

/**
 * Alpha-by-intensity (Redesign Spec §4.9-3): comfortable cells ≈0.35, extreme
 * cells ≈0.9. Danger glows; safe zones let the city show through. This is the
 * single change that "kills the flat blob". Input is a 0..1 intensity (e.g. a
 * normalised composite score or normalised UTCI); output is 0..1 alpha.
 */
export function alphaByIntensity(t: number): number {
  const v = clamp(t, 0, 1)
  return 0.35 + 0.55 * v
}

/** UTCI °C → 0..1 intensity across the ramp range (for alphaByIntensity). */
export function utciIntensity(value: number): number {
  if (!Number.isFinite(value)) return 0
  return (clamp(value, UTCI_MIN, UTCI_MAX) - UTCI_MIN) / (UTCI_MAX - UTCI_MIN)
}

/** UTCI °C → [r,g,b,a] with alpha ramped by intensity (luminous thermal field). */
export function utciRgba(value: number): [number, number, number, number] {
  const [r, g, b] = utciColor(value)
  return [r, g, b, Math.round(alphaByIntensity(utciIntensity(value)) * 255)]
}

/** Muted olive colour for pre-existing trees (per app spec). */
export const EXISTING_TREE_COLOR: RGB = [115, 140, 107]
