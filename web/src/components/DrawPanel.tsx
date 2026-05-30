// DrawPanel — the floating control panel for the "design anywhere" flow:
// pick a draw tool, see the live area (vs the cap), detect buildings in the
// selection, then Evaluate to run the real cooling pipeline.

import { useCallback, useEffect, useRef, useState } from 'react'
import type { DrawMode, LngLat, AreaStatus } from '../lib/draw'
import { MAX_AREA_M2 } from '../lib/draw'
import {
  fetchBuildings,
  fetchEvaluate,
  evaluateResponseToBundle,
  type BuildingsPreview,
} from '../lib/api'
import type { WebBundle } from '../lib/types'

interface DrawPanelProps {
  mode: DrawMode | null
  setMode: (m: DrawMode | null) => void
  clear: () => void
  ring: LngLat[] | null
  area: number
  status: AreaStatus | null
  budgetEur: number
  setBudgetEur: (v: number) => void
  onEvaluated: (bundle: WebBundle) => void
}

const TOOLS: { id: DrawMode; label: string; icon: string }[] = [
  { id: 'rectangle', label: 'Rectangle', icon: '▭' },
  { id: 'circle', label: 'Circle', icon: '◯' },
  { id: 'polygon', label: 'Polygon', icon: '⬡' },
]

function fmtArea(m2: number): string {
  if (m2 >= 10_000) return `${(m2 / 10_000).toFixed(2)} ha`
  return `${Math.round(m2).toLocaleString()} m²`
}

export function DrawPanel({
  mode,
  setMode,
  clear,
  ring,
  area,
  status,
  budgetEur,
  setBudgetEur,
  onEvaluated,
}: DrawPanelProps) {
  const [preview, setPreview] = useState<BuildingsPreview | null>(null)
  const [detecting, setDetecting] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const reqId = useRef(0)

  // When a ring is committed (status ok), auto-detect buildings in it.
  useEffect(() => {
    setPreview(null)
    setError(null)
    if (!ring || status !== 'ok') return
    const id = ++reqId.current
    setDetecting(true)
    fetchBuildings(ring)
      .then((p) => {
        if (id === reqId.current) setPreview(p)
      })
      .catch((e: unknown) => {
        if (id === reqId.current) setError(e instanceof Error ? e.message : String(e))
      })
      .finally(() => {
        if (id === reqId.current) setDetecting(false)
      })
  }, [ring, status])

  const onEvaluate = useCallback(async () => {
    if (!ring || status !== 'ok') return
    setEvaluating(true)
    setError(null)
    try {
      const resp = await fetchEvaluate({ polygon: ring, budget_eur: budgetEur })
      onEvaluated(evaluateResponseToBundle(resp))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setEvaluating(false)
    }
  }, [ring, status, budgetEur, onEvaluated])

  const canEvaluate = !!ring && status === 'ok' && !evaluating

  return (
    <div className="draw-panel">
      <div className="draw-panel__title">Design anywhere in Barcelona</div>

      <div className="draw-panel__tools">
        {TOOLS.map((t) => (
          <button
            key={t.id}
            className={`draw-tool ${mode === t.id ? 'is-active' : ''}`}
            onClick={() => setMode(mode === t.id ? null : t.id)}
            title={t.label}
          >
            <span className="draw-tool__icon">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      <div className="draw-panel__hint">
        {mode === 'polygon'
          ? 'Click each corner; double-click to finish.'
          : mode
            ? 'Click a corner, then the opposite corner.'
            : ring
              ? 'Adjust budget, then Evaluate.'
              : 'Pick a tool to select an area.'}
      </div>

      {(mode || ring) && (
        <div className={`draw-panel__area draw-panel__area--${status ?? 'none'}`}>
          <span>Area</span>
          <strong>{fmtArea(area)}</strong>
          <span className="draw-panel__cap">/ {fmtArea(MAX_AREA_M2)} max</span>
        </div>
      )}
      {status === 'too_large' && (
        <div className="draw-panel__warn">Too large — draw a smaller area.</div>
      )}
      {status === 'too_small' && (
        <div className="draw-panel__warn">Too small — draw a bigger area.</div>
      )}

      {ring && status === 'ok' && (
        <div className="draw-panel__detect">
          {detecting && <span>Detecting buildings…</span>}
          {preview && (
            <span>
              {preview.buildings_available
                ? `~${preview.context_building_count} buildings in this tile (their shadows are in the sim)`
                : 'No live buildings (set backend=live)'}
            </span>
          )}
          {preview?.impervious?.available && (
            <span className="draw-panel__depave">
              🔥 {Math.round(preview.impervious.impervious_m2).toLocaleString()} m² impervious
              pavement ({Math.round(preview.impervious.impervious_fraction * 100)}%) — depave
              candidates
            </span>
          )}
        </div>
      )}

      {ring && (
        <label className="draw-panel__budget">
          Budget: €{budgetEur.toLocaleString()}
          <input
            type="range"
            min={50_000}
            max={2_000_000}
            step={50_000}
            value={budgetEur}
            onChange={(e) => setBudgetEur(Number(e.target.value))}
          />
        </label>
      )}

      <div className="draw-panel__actions">
        <button className="btn btn--primary" disabled={!canEvaluate} onClick={onEvaluate}>
          {evaluating ? 'Evaluating… (live sim ~30s)' : 'Evaluate'}
        </button>
        <button className="btn btn--ghost" onClick={clear} disabled={evaluating}>
          Clear
        </button>
      </div>

      {error && <div className="draw-panel__error">{error}</div>}
    </div>
  )
}
