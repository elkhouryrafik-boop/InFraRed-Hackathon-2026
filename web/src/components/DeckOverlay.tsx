// deck.gl MapboxOverlay control (recipe §1). interleaved:true is mandatory for
// depth-correct compositing with Tile3DLayer.

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
    () => new MapboxOverlay({ interleaved: true, layers: [] }),
  )
  useEffect(() => {
    overlay.setProps({ layers, onClick })
  }, [overlay, layers, onClick])
  return null
}
