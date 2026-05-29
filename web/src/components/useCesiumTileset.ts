// Hook: resolve the Cesium tileset URL once, gated on the mount latch.
// Recipe §2.3: latch "ever crossed MIN_ZOOM" at MODULE scope (not useRef) so
// HMR can't change hook counts. Once latched + tiles enabled, keep mounted.

import { useEffect, useState } from 'react'
import { resolveCesiumTilesetUrl, hasCesiumToken } from '../lib/cesium'

export const MIN_ZOOM = 13 // start fading in
export const FULL_ZOOM = 15 // full opacity

// Module-scope latch — survives remounts and HMR.
let everCrossedMinZoom = false

export function markZoom(zoom: number) {
  if (zoom >= MIN_ZOOM) everCrossedMinZoom = true
}

/** Opacity ramp for the photogrammetry between MIN_ZOOM..FULL_ZOOM. */
export function tilesetOpacity(zoom: number): number {
  return Math.min(1, Math.max(0, (zoom - MIN_ZOOM) / (FULL_ZOOM - MIN_ZOOM)))
}

export interface CesiumState {
  url: string | null
  enabled: boolean
  error: string | null
  hasToken: boolean
}

/**
 * Resolve the tileset URL when the token exists and the user has crossed
 * MIN_ZOOM at least once this session. `currentZoom` drives the latch.
 */
export function useCesiumTileset(currentZoom: number): CesiumState {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const hasToken = hasCesiumToken()

  // Update the module-scope latch on every zoom change.
  markZoom(currentZoom)
  const enabled = everCrossedMinZoom

  useEffect(() => {
    if (!hasToken || !enabled || url) return
    let cancelled = false
    resolveCesiumTilesetUrl()
      .then((u) => {
        if (!cancelled) setUrl(u)
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      })
    return () => {
      cancelled = true
    }
  }, [hasToken, enabled, url])

  return { url, enabled, error, hasToken }
}
