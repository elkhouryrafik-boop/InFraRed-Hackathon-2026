// useAreaDraw — interaction state for drawing a selection (rectangle / circle /
// polygon) on the Mapbox map, plus the deck.gl preview layers for it.
//
// Drawing model:
//   rectangle / circle : 2 clicks (anchor, then opposite corner / radius edge),
//                        with a live rubber-band that follows the cursor between.
//   polygon            : click each vertex, double-click to finish.
// While a draw mode is active, map drag-pan is disabled so clicks place points
// instead of panning.

import { useCallback, useMemo, useState } from 'react'
import { PolygonLayer, ScatterplotLayer } from '@deck.gl/layers'
import type { Layer } from '@deck.gl/core'
import {
  ringAreaM2,
  rectRing,
  circleRing,
  areaStatus,
  closeRing,
  type DrawMode,
  type LngLat,
  type AreaStatus,
} from '../lib/draw'

export interface AreaDraw {
  mode: DrawMode | null
  setMode: (m: DrawMode | null) => void
  /** The committed selection ring (closed), or null. */
  ring: LngLat[] | null
  /** Live ring being drawn (committed, or rubber-band preview), or null. */
  previewRing: LngLat[] | null
  area: number
  status: AreaStatus | null
  clear: () => void
  drawLayers: Layer[]
  /** True while actively drawing — caller should disable map dragPan. */
  drawing: boolean
  onMapClick: (lngLat: LngLat) => void
  onMapMouseMove: (lngLat: LngLat) => void
  onMapDblClick: () => void
}

const PREVIEW_OK: [number, number, number, number] = [43, 200, 188, 60]
const PREVIEW_BAD: [number, number, number, number] = [255, 110, 90, 70]
const LINE_OK: [number, number, number, number] = [43, 200, 188, 240]
const LINE_BAD: [number, number, number, number] = [255, 110, 90, 240]

export function useAreaDraw(): AreaDraw {
  const [mode, setModeRaw] = useState<DrawMode | null>(null)
  const [anchor, setAnchor] = useState<LngLat | null>(null)
  const [hover, setHover] = useState<LngLat | null>(null)
  const [verts, setVerts] = useState<LngLat[]>([]) // polygon vertices
  const [ring, setRing] = useState<LngLat[] | null>(null)

  const clear = useCallback(() => {
    setAnchor(null)
    setHover(null)
    setVerts([])
    setRing(null)
  }, [])

  const setMode = useCallback(
    (m: DrawMode | null) => {
      clear()
      setModeRaw(m)
    },
    [clear],
  )

  const onMapClick = useCallback(
    (lngLat: LngLat) => {
      if (!mode) return
      if (mode === 'polygon') {
        setVerts((v) => [...v, lngLat])
        return
      }
      // rectangle / circle: first click = anchor, second = commit.
      if (!anchor) {
        setAnchor(lngLat)
        setHover(lngLat)
        return
      }
      const built = mode === 'rectangle' ? rectRing(anchor, lngLat) : circleRing(anchor, lngLat)
      setRing(built)
      setAnchor(null)
      setModeRaw(null) // finished — leave draw mode so the map is interactive again
    },
    [mode, anchor],
  )

  const onMapMouseMove = useCallback(
    (lngLat: LngLat) => {
      if (mode && (anchor || mode === 'polygon')) setHover(lngLat)
    },
    [mode, anchor],
  )

  const onMapDblClick = useCallback(() => {
    if (mode === 'polygon' && verts.length >= 3) {
      setRing(closeRing(verts))
      setVerts([])
      setModeRaw(null)
    }
  }, [mode, verts])

  // The ring currently shown: committed ring, or a live rubber-band preview.
  const previewRing = useMemo<LngLat[] | null>(() => {
    if (ring) return ring
    if (mode === 'polygon' && verts.length > 0) {
      const live = hover ? [...verts, hover] : verts
      return live.length >= 3 ? closeRing(live) : null
    }
    if ((mode === 'rectangle' || mode === 'circle') && anchor && hover) {
      return mode === 'rectangle' ? rectRing(anchor, hover) : circleRing(anchor, hover)
    }
    return null
  }, [ring, mode, verts, anchor, hover])

  const area = useMemo(() => (previewRing ? ringAreaM2(previewRing) : 0), [previewRing])
  const status = useMemo<AreaStatus | null>(
    () => (previewRing ? areaStatus(area) : null),
    [previewRing, area],
  )

  const drawing = mode !== null

  const drawLayers = useMemo<Layer[]>(() => {
    const out: Layer[] = []
    const bad = status === 'too_large' || status === 'too_small'
    if (previewRing && previewRing.length >= 3) {
      out.push(
        new PolygonLayer({
          id: 'draw-preview',
          data: [{ polygon: previewRing }],
          getPolygon: (d: { polygon: LngLat[] }) => d.polygon,
          filled: true,
          stroked: true,
          getFillColor: bad ? PREVIEW_BAD : PREVIEW_OK,
          getLineColor: bad ? LINE_BAD : LINE_OK,
          getLineWidth: 2,
          lineWidthUnits: 'pixels',
          lineWidthMinPixels: 2,
        }),
      )
    }
    // Placed vertices / anchor dots.
    const dots: LngLat[] = ring
      ? []
      : mode === 'polygon'
        ? verts
        : anchor
          ? [anchor]
          : []
    if (dots.length > 0) {
      out.push(
        new ScatterplotLayer({
          id: 'draw-dots',
          data: dots,
          getPosition: (d: LngLat) => d,
          getFillColor: [43, 200, 188, 255],
          getRadius: 4,
          radiusUnits: 'pixels',
          radiusMinPixels: 4,
        }),
      )
    }
    return out
  }, [previewRing, status, ring, mode, verts, anchor])

  return {
    mode,
    setMode,
    ring,
    previewRing,
    area,
    status,
    clear,
    drawLayers,
    drawing,
    onMapClick,
    onMapMouseMove,
    onMapDblClick,
  }
}
