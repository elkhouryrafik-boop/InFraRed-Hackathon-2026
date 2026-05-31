// A top-down tree-canopy sprite for deck.gl IconLayer (mask mode). The sprite is
// WHITE with the canopy shape + leaf-clump texture encoded in ALPHA, so IconLayer
// `getColor` tints it per species (white × green = leafy green with soft shading).
// A soft radial falloff gives an organic edge — reads as foliage from above, not a
// hard flat disk. Laid flat (billboard:false) so it sits on the ground like a real
// canopy footprint.

const CANOPY_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <defs>
    <radialGradient id="c" cx="50%" cy="46%" r="52%">
      <stop offset="0%" stop-color="#fff" stop-opacity="1"/>
      <stop offset="72%" stop-color="#fff" stop-opacity="0.96"/>
      <stop offset="90%" stop-color="#fff" stop-opacity="0.7"/>
      <stop offset="100%" stop-color="#fff" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="lo" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#fff" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#fff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <!-- base canopy with a soft organic edge -->
  <circle cx="64" cy="64" r="60" fill="url(#c)"/>
  <!-- leaf clumps: overlapping soft lobes give a textured, lumpy crown -->
  <circle cx="46" cy="50" r="26" fill="url(#lo)"/>
  <circle cx="82" cy="54" r="24" fill="url(#lo)"/>
  <circle cx="58" cy="82" r="24" fill="url(#lo)"/>
  <circle cx="84" cy="82" r="18" fill="url(#lo)"/>
  <circle cx="40" cy="76" r="16" fill="url(#lo)"/>
  <!-- bright highlight near the crown top (sun-side) -->
  <circle cx="56" cy="46" r="12" fill="#fff" fill-opacity="0.5"/>
</svg>`.trim()

export const CANOPY_ICON = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(CANOPY_SVG)}`

// IconLayer mapping for the single shared canopy sprite (mask:true → tinted by color).
export const CANOPY_ICON_MAPPING = {
  canopy: { x: 0, y: 0, width: 128, height: 128, anchorX: 64, anchorY: 64, mask: true },
} as const
