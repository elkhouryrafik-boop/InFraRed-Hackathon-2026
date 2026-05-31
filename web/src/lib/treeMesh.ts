// 3D tree spheres for the cinematic "3D view" (Infrared.city-style): a green
// sphere canopy elevated to crown height, sized by the species crown. Uses
// deck.gl SimpleMeshLayer + a luma SphereGeometry. Heights/positions in metres
// (LNGLAT coordinate system → z is metres).

import { SimpleMeshLayer } from '@deck.gl/mesh-layers'
import { SphereGeometry } from '@luma.gl/engine'
import type { Layer } from '@deck.gl/core'
import { foliageColor } from './species'

export interface TreePoint {
  lon: number
  lat: number
  crown_m: number
  species: string
  cell?: string
}

// One shared unit sphere (radius 1), scaled per-tree by crown radius.
const SPHERE = new SphereGeometry({ radius: 1, nlat: 18, nlong: 18 })

export function buildTreeSpheres(
  id: string,
  points: TreePoint[],
  opts?: { selectedCellId?: string | null },
): Layer | null {
  if (!points || points.length === 0) return null
  const selected = opts?.selectedCellId ?? null
  return new SimpleMeshLayer<TreePoint>({
    id,
    data: points,
    mesh: SPHERE,
    // Elevate the sphere centre to ~crown radius + a short trunk gap so it reads
    // as a canopy floating over the ground (matches the reference render).
    getPosition: (d) => [d.lon, d.lat, d.crown_m * 0.5 + 2.0],
    getScale: (d) => {
      const r = Math.max(2, d.crown_m / 2)
      return [r, r, r * 0.85] // slightly squashed = canopy, not a perfect ball
    },
    getColor: (d) => {
      const [r, g, b] = foliageColor(d.species)
      const dim = selected && d.cell && d.cell !== selected
      return (dim ? [r, g, b, 110] : [r, g, b, 255]) as [number, number, number, number]
    },
    updateTriggers: { getColor: [selected] },
    material: {
      ambient: 0.55,
      diffuse: 0.7,
      shininess: 24,
      specularColor: [40, 60, 40],
    },
    pickable: true,
  })
}
