// deck.gl MapboxOverlay control. OVERLAID (interleaved:false): deck owns its own
// canvas above the map. interleaved was only needed for Tile3DLayer depth, which
// is disabled — and interleaved corrupted GL state when the basemap STYLE or the
// layer-set swapped on the 2D/3D toggle (IconLayer/GeoJsonLayer assertion crashes,
// blank overlay). Overlaid is robust across style/layer swaps. Trade-off: deck
// meshes are not depth-occluded by Mapbox 3D buildings (trees draw on top) —
// acceptable for the cinematic view.

import { useControl } from 'react-map-gl'
import { MapboxOverlay } from '@deck.gl/mapbox'
import type { PickingInfo } from '@deck.gl/core'
import { useEffect } from 'react'
import type { Layer } from '@deck.gl/core'

interface DeckOverlayProps {
  layers: Layer[]
  /** Fired when the user clicks a pickable layer (e.g. a tree). */
  onClick?: (info: PickingInfo) => void
}

export function DeckOverlay({ layers, onClick }: DeckOverlayProps) {
  const overlay = useControl(
    () => new MapboxOverlay({ interleaved: false, layers: [] }),
  )
  useEffect(() => {
    overlay.setProps({ layers, onClick })
  }, [overlay, layers, onClick])
  return null
}
