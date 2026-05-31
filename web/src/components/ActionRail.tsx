// ActionRail — right-edge vertical icon rail (Redesign Spec §4.4). Replaces the
// fat DrawPanel. Icon buttons (Draw / Polygon / Clear / Map options), each
// ≥44×44 with an aria-label. The area readout + Evaluate appear as a single
// inline popover only once a ring exists (status==='ok'). Map options (opacity
// + baseline/intervention) live in a small "Map" popover. The Design/Citywide
// switch moved to the top-center ModeSwitch — this rail is Design-only chrome.

import { useCallback, useEffect, useRef, useState } from 'react'
import './ActionRail.css'
import type { DrawMode, LngLat, AreaStatus } from '../lib/draw'
import { MAX_AREA_M2 } from '../lib/draw'
import {
  fetchBuildings,
  fetchEvaluate,
  evaluateResponseToBundle,
  type BuildingsPreview,
} from '../lib/api'
import type { WebBundle, UtciScenario } from '../lib/types'

interface ActionRailProps {
  mode: DrawMode | null
  setMode: (m: DrawMode | null) => void
  clear: () => void
  ring: LngLat[] | null
  area: number
  status: AreaStatus | null
  budgetEur: number
  setBudgetEur: (v: number) => void
  onEvaluated: (bundle: WebBundle) => void
  onEvaluatingChange?: (evaluating: boolean) => void
  // Map options (demoted from the old Hud, §3.2).
  scenario: UtciScenario
  onScenarioChange: (s: UtciScenario) => void
  rasterOpacity: number
  onRasterOpacityChange: (v: number) => void
}

function fmtArea(m2: number): string {
  if (m2 >= 10_000) return `${(m2 / 10_000).toFixed(2)} ha`
  return `${Math.round(m2).toLocaleString()} m²`
}

export function ActionRail({
  mode,
  setMode,
  clear,
  ring,
  area,
  status,
  budgetEur,
  setBudgetEur,
  onEvaluated,
  onEvaluatingChange,
  scenario,
  onScenarioChange,
  rasterOpacity,
  onRasterOpacityChange,
}: ActionRailProps) {
  const [preview, setPreview] = useState<BuildingsPreview | null>(null)
  const [detecting, setDetecting] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mapOpen, setMapOpen] = useState(false)
  const reqId = useRef(0)

  useEffect(() => {
    onEvaluatingChange?.(evaluating)
  }, [evaluating, onEvaluatingChange])

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
      // Genuinely unplantable area → clean message, keep the current scene.
      if (resp.empty || !resp.decision) {
        setError(
          resp.headline ||
            'No plantable spots found in this area. Try a larger or less built-up block.',
        )
        return
      }
      onEvaluated(evaluateResponseToBundle(resp))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setEvaluating(false)
    }
  }, [ring, status, budgetEur, onEvaluated])

  const canEvaluate = !!ring && status === 'ok' && !evaluating
  const hasRing = !!ring

  return (
    <div className="action-rail-wrap">
      {/* The icon rail itself. */}
      <nav className="action-rail panel" aria-label="Cooling design tools">
        <button
          type="button"
          className={`rail-btn ${mode === 'rectangle' || mode === 'circle' ? 'is-active' : ''}`}
          aria-label="Draw cooling area"
          aria-pressed={mode === 'rectangle'}
          title="Draw a rectangular cooling area"
          onClick={() => setMode(mode === 'rectangle' ? null : 'rectangle')}
        >
          <span className="rail-btn__icon" aria-hidden>✏</span>
        </button>
        <button
          type="button"
          className={`rail-btn ${mode === 'polygon' ? 'is-active' : ''}`}
          aria-label="Polygon tool"
          aria-pressed={mode === 'polygon'}
          title="Draw a polygon (click corners, double-click to finish)"
          onClick={() => setMode(mode === 'polygon' ? null : 'polygon')}
        >
          <span className="rail-btn__icon" aria-hidden>⬡</span>
        </button>
        <button
          type="button"
          className="rail-btn"
          aria-label="Clear selection"
          title="Clear the drawn area"
          disabled={!hasRing && !mode}
          onClick={clear}
        >
          <span className="rail-btn__icon" aria-hidden>⌫</span>
        </button>
        <button
          type="button"
          className={`rail-btn ${mapOpen ? 'is-active' : ''}`}
          aria-label="Map options"
          aria-expanded={mapOpen}
          title="Heatmap opacity & baseline/with-trees"
          onClick={() => setMapOpen((v) => !v)}
        >
          <span className="rail-btn__icon" aria-hidden>▦</span>
        </button>
      </nav>

      {/* Map options popover (opacity + baseline/intervention), demoted from Hud. */}
      {mapOpen && (
        <div className="rail-popover panel" role="group" aria-label="Map options">
          <div className="rail-popover__title">Heatmap</div>
          <div className="rail-toggle" role="group" aria-label="Heatmap scenario">
            <button
              type="button"
              className={`rail-toggle__btn ${scenario === 'baseline' ? 'is-active' : ''}`}
              aria-pressed={scenario === 'baseline'}
              onClick={() => onScenarioChange('baseline')}
            >
              Baseline
            </button>
            <button
              type="button"
              className={`rail-toggle__btn ${scenario === 'intervention' ? 'is-active' : ''}`}
              aria-pressed={scenario === 'intervention'}
              onClick={() => onScenarioChange('intervention')}
            >
              With trees
            </button>
          </div>
          <label className="rail-opacity" htmlFor="rail-raster-opacity">
            <span>Opacity</span>
            <input
              id="rail-raster-opacity"
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={rasterOpacity}
              onChange={(e) => onRasterOpacityChange(Number(e.target.value))}
            />
            <span className="tnum">{Math.round(rasterOpacity * 100)}%</span>
          </label>
        </div>
      )}

      {/* Draw-complete popover anchored to the rail (§4.4). */}
      {hasRing && (
        <div className="rail-eval panel" role="group" aria-label="Evaluate cooling">
          <div className={`rail-eval__area rail-eval__area--${status ?? 'none'}`}>
            <strong className="tnum">{fmtArea(area)}</strong>
            <span className="rail-eval__cap">
              {status === 'ok'
                ? `within ${fmtArea(MAX_AREA_M2)} cap ✓`
                : status === 'too_large'
                  ? 'too large — draw smaller'
                  : 'too small — draw bigger'}
            </span>
          </div>

          <div className="rail-eval__detect" aria-live="polite">
            {detecting && <span>Detecting plantable spots…</span>}
            {preview && (
              <span>
                {preview.buildings_available
                  ? `~${preview.context_building_count} buildings — their shadows are in the sim`
                  : 'Using OpenStreetMap buildings for placement (keep trees off roofs); live backend adds Infrared shadows'}
              </span>
            )}
            {preview?.impervious?.available && (
              <span className="rail-eval__depave">
                {Math.round(preview.impervious.impervious_m2).toLocaleString()} m² impervious (
                {Math.round(preview.impervious.impervious_fraction * 100)}%) — depave candidates
              </span>
            )}
          </div>

          <label className="rail-eval__budget" htmlFor="rail-budget">
            <span>Budget €{budgetEur.toLocaleString()}</span>
            <input
              id="rail-budget"
              type="range"
              min={50_000}
              max={2_000_000}
              step={50_000}
              value={budgetEur}
              onChange={(e) => setBudgetEur(Number(e.target.value))}
            />
          </label>

          <button
            type="button"
            className="cs-btn cs-btn--primary rail-eval__go"
            disabled={!canEvaluate}
            onClick={onEvaluate}
          >
            {evaluating ? 'Evaluating… live Infrared UTCI (~60–90s)' : '▸ Evaluate cooling'}
          </button>

          {error && (
            <div className="rail-eval__error" role="alert">
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
