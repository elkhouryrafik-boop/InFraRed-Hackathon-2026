// deck.gl MapboxOverlay control (recipe §1). interleaved:true is mandatory for
// depth-correct compositing with Tile3DLayer.

import { useControl } from 'react-map-gl'
import { MapboxOverlay } from '@deck.gl/mapbox'
import { useEffect } from 'react'
import type { Layer } from '@deck.gl/core'

export function DeckOverlay({ layers }: { layers: Layer[] }) {
  const overlay = useControl(
    () => new MapboxOverlay({ interleaved: true, layers: [] }),
  )
  useEffect(() => {
    overlay.setProps({ layers })
  }, [overlay, layers])
  return null
}
