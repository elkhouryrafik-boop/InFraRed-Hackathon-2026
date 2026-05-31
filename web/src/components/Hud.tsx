// Glassy HUD panel (top-left): headline, rank-1 KPIs, scenario toggle, legend.

import './Hud.css'
import type { Decision, UtciScenario } from '../lib/types'
import { rankOne, toKpiView } from '../lib/format'
import { Legend } from './Legend'

interface HudProps {
  decision: Decision
  scenario: UtciScenario
  onScenarioChange: (s: UtciScenario) => void
  rasterOpacity: number
  onRasterOpacityChange: (v: number) => void
}

export function Hud({
  decision,
  scenario,
  onScenarioChange,
  rasterOpacity,
  onRasterOpacityChange,
}: HudProps) {
  const top = rankOne(decision.configurations)
  const kpi = top ? toKpiView(top) : null

  return (
    <div className="hud" role="region" aria-label="Cooling scenario summary">
      <div className="hud__brand">
        <span className="hud__brand-dot" aria-hidden />
        CoolSpend · Barcelona
      </div>

      <h1 className="hud__headline">{decision.headline}</h1>
      {(() => {
        const measured = decision.backend === 'live' || decision.backend === 'cached'
        return (
          <div
            className={`hud__backend ${measured ? 'is-measured' : 'is-preview'}`}
            title={
              measured
                ? 'Cooling measured on Infrared UTCI simulation'
                : 'Synthetic preview — placement real, cooling estimated until run live'
            }
          >
            {measured ? `✓ measured UTCI (${decision.backend})` : '≈ preview (synthetic cooling)'}
          </div>
        )
      })()}

      {kpi && (
        <>
          <div className="hud__label">
            {kpi.label}
            <span className="hud__rank">RANK {kpi.rank}</span>
          </div>

          <div className="kpis">
            <div className="kpi">
              <div className="kpi__value">{kpi.trees}</div>
              <div className="kpi__caption">Trees</div>
            </div>
            <div className="kpi">
              <div className="kpi__value">{kpi.cost}</div>
              <div className="kpi__caption">Budget</div>
            </div>
            <div className="kpi">
              <div className="kpi__value">{kpi.cooledArea}</div>
              <div className="kpi__caption">Cooled footprint</div>
            </div>
            <div className="kpi">
              <div className="kpi__value">{kpi.rate}</div>
              <div className="kpi__caption">Cost efficiency</div>
            </div>

            <div className="kpi kpi--wide">
              <div className="felt">
                <span className="felt__from">{kpi.baselinePeak}</span>
                <span className="felt__arrow" aria-hidden>
                  →
                </span>
                <span className="felt__to">{kpi.interventionPeak}</span>
                <span
                  className={
                    'felt__delta ' +
                    (kpi.isCooling ? 'felt__delta--cool' : 'felt__delta--warm')
                  }
                >
                  {kpi.delta}
                </span>
              </div>
              <div className="kpi__caption">Feels-like peak °C · baseline → intervention</div>
            </div>

            {kpi.depth && (
              <div className="kpi kpi--wide">
                <div className="kpi__value kpi__value--depth">{kpi.depth}</div>
                <div className="kpi__caption">
                  Cooling depth · {kpi.heatStressRelieved} lifted out of heat stress
                </div>
              </div>
            )}
          </div>

          {kpi.species.length > 0 && (
            <div className="species" aria-label="Species selected">
              {kpi.species.map((s) => (
                <span className="species__chip" key={s}>
                  {s}
                </span>
              ))}
            </div>
          )}
        </>
      )}

      {/* Scenario toggle */}
      <div className="toggle" role="group" aria-label="Heatmap scenario">
        <button
          type="button"
          className={
            'toggle__btn ' + (scenario === 'baseline' ? 'toggle__btn--active' : '')
          }
          onClick={() => onScenarioChange('baseline')}
          aria-pressed={scenario === 'baseline'}
        >
          Baseline
        </button>
        <button
          type="button"
          className={
            'toggle__btn ' +
            (scenario === 'intervention' ? 'toggle__btn--active' : '')
          }
          onClick={() => onScenarioChange('intervention')}
          aria-pressed={scenario === 'intervention'}
        >
          With trees
        </button>
      </div>

      {/* Opacity */}
      <div className="opacity-row">
        <label htmlFor="raster-opacity">Heatmap</label>
        <input
          id="raster-opacity"
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={rasterOpacity}
          onChange={(e) => onRasterOpacityChange(Number(e.target.value))}
        />
        <span>{Math.round(rasterOpacity * 100)}%</span>
      </div>

      <Legend />

      <div className="hud__disclaimer">{decision.disclaimer}</div>
    </div>
  )
}
