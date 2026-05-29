// Height-offset helpers (recipe §4). Pure math + a Mapbox DEM sampler.
// Lets every overlay sit on the photogrammetric ground.

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined

/**
 * Column-major 4x4 matrix that translates by `liftMeters` along +Z.
 * Passed as `modelMatrix` on overlay layers (recipe §4.1).
 */
export function liftMatrix(liftMeters: number): number[] {
  // prettier-ignore
  return [
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, liftMeters, 1,
  ]
}

/**
 * Approximate geoid undulation for Barcelona (EGM2008 ~ +49 m near the city).
 * Constant is fine across a ≤2 km site; the geoid varies slowly.
 */
export const BARCELONA_GEOID_UNDULATION_M = 49

/**
 * Sample Mapbox's raster DEM at one point and decode the elevation (metres).
 * Encoding: height = -10000 + (R*65536 + G*256 + B) * 0.1
 * Returns null if no token or the fetch fails.
 */
export async function fetchDemElevation(lon: number, lat: number): Promise<number | null> {
  if (!MAPBOX_TOKEN) return null
  try {
    const zoom = 14
    const tileSize = 512
    const n = 2 ** zoom
    const worldX = ((lon + 180) / 360) * n * tileSize
    const latRad = (lat * Math.PI) / 180
    const worldY =
      ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n * tileSize
    const tx = Math.floor(worldX / tileSize)
    const ty = Math.floor(worldY / tileSize)
    const px = Math.floor(worldX - tx * tileSize)
    const py = Math.floor(worldY - ty * tileSize)
    const url = `https://api.mapbox.com/v4/mapbox.mapbox-terrain-dem-v1/${zoom}/${tx}/${ty}@2x.pngraw?access_token=${MAPBOX_TOKEN}`
    const resp = await fetch(url)
    if (!resp.ok) return null
    const blob = await resp.blob()
    const bmp = await createImageBitmap(blob)
    const canvas = new OffscreenCanvas(bmp.width, bmp.height)
    const ctx = canvas.getContext('2d')
    if (!ctx) return null
    ctx.drawImage(bmp, 0, 0)
    const sx = Math.min(bmp.width - 1, Math.floor((px * bmp.width) / tileSize))
    const sy = Math.min(bmp.height - 1, Math.floor((py * bmp.height) / tileSize))
    const d = ctx.getImageData(sx, sy, 1, 1).data
    return -10000 + (d[0] * 65536 + d[1] * 256 + d[2]) * 0.1
  } catch {
    return null
  }
}

/**
 * Total lift to place orthometric overlays on the ellipsoid-anchored mesh.
 * Sits 2 m below the mesh so drapes don't z-fight the photogrammetry.
 */
export function computeLiftMeters(orthometricGroundM: number): number {
  return orthometricGroundM + BARCELONA_GEOID_UNDULATION_M - 2
}
