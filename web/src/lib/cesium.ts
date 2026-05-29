// Resolves the Google Photorealistic 3D Tiles tileset URL via Cesium Ion.
// Recipe §2.1: resolve ONCE per session, cache for the page lifetime.

const CESIUM_ION_TOKEN = import.meta.env.VITE_CESIUM_ION_TOKEN as string | undefined
const GOOGLE_3D_TILES_ASSET_ID = 2275207

// Module-scope cache — survives component remounts / HMR, one fetch per page.
let cachedUrlPromise: Promise<string> | null = null

export function hasCesiumToken(): boolean {
  return typeof CESIUM_ION_TOKEN === 'string' && CESIUM_ION_TOKEN.trim().length > 0
}

interface CesiumEndpoint {
  url?: string
  options?: { url?: string }
}

/**
 * Resolve the tileset URL. External 3D Tiles assets (Google) put the URL at
 * `options.url` with the Google Maps key pre-embedded; there is no separate
 * accessToken. Resolves at most once per page lifetime.
 */
export function resolveCesiumTilesetUrl(): Promise<string> {
  if (!hasCesiumToken()) {
    return Promise.reject(new Error('No Cesium Ion token configured'))
  }
  if (cachedUrlPromise) return cachedUrlPromise

  cachedUrlPromise = (async () => {
    const r = await fetch(
      `https://api.cesium.com/v1/assets/${GOOGLE_3D_TILES_ASSET_ID}/endpoint`,
      { headers: { Authorization: `Bearer ${CESIUM_ION_TOKEN}` } },
    )
    if (!r.ok) throw new Error(`Cesium Ion endpoint ${r.status}`)
    const data = (await r.json()) as CesiumEndpoint
    const url = data.options?.url ?? data.url
    if (!url) throw new Error('Cesium Ion: missing tileset URL')
    return url
  })()

  // If it fails, clear the cache so a later retry can re-attempt.
  cachedUrlPromise.catch(() => {
    cachedUrlPromise = null
  })

  return cachedUrlPromise
}
