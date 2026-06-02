// ResultCard — bottom-left contextual surface for phase==='result' (Redesign
// Spec §4.2). Replaces the always-on Hud. ONE hero Cool Score ring gauge, the
// felt-like transition, a 3-up supporting strip, ONE dense meta line (folds the
// old depave-chip), and the docked Growth Slider. No 8-tile KPI grid.

import { useMemo } from 'react'
import './ResultCard.css'
import type { WebBundle } from '../lib/types'
import { rankOne, toKpiView } from '../lib/format'
import { coolScoreView, CITY_AVG_COOL_SCORE } from '../lib/coolScore'
import { useCountUp } from '../lib/useCountUp'
import { GrowthSlider } from './GrowthSlider'
import type { GrowthParams } from '../lib/growth'

interface ResultCardProps {
  bundle: WebBundle
  /** Growth-slider state (docked here). */
  year: number
  setYear: (y: number) => void
  growthParams: GrowthParams
  /** Show the docked growth slider only when there are trees to age. */
  showGrowth: boolean
  onSeeCityPlan: () => void
  /** Persist this run ("make it remember"). Omitted ⇒ no Save button. */
  onSave?: () => void
  /** True while a save is in flight (disables the button). */
  saving?: boolean
}

/** SVG ring gauge: mint arc on a flat track, hero number in the centre. */
function ScoreRing({ score }: { score: number | null }) {
  const animated = useCountUp(score ?? 0, 700, score != null)
  const display = score == null ? null : Math.round(animated)
  const pct = score == null ? 0 : Math.max(0, Math.min(100, animated)) / 100
  const R = 46
  const C = 2 * Math.PI * R
  return (
    <svg className="rc-ring" viewBox="0 0 120 120" width="120" height="120" aria-hidden>
      <circle cx="60" cy="60" r={R} className="rc-ring__track" />
      <circle
        cx="60"
        cy="60"
        r={R}
        className="rc-ring__arc"
        strokeDasharray={C}
        strokeDashoffset={C * (1 - pct)}
        transform="rotate(-90 60 60)"
      />
      <text x="60" y="58" className="rc-ring__num tnum" textAnchor="middle">
        {display == null ? '—' : display}
      </text>
      <text x="60" y="80" className="rc-ring__den" textAnchor="middle">
        /100
      </text>
    </svg>
  )
}

export function ResultCard({
  bundle,
  year,
  setYear,
  growthParams,
  showGrowth,
  onSeeCityPlan,
  onSave,
  saving,
}: ResultCardProps) {
  const top = useMemo(() => rankOne(bundle.decision.configurations), [bundle.decision])
  const kpi = top ? toKpiView(top) : null
  const cs = coolScoreView(bundle.decision, top)

  // Felt-like count-up (peak baseline → intervention).
  const bp = top?.utci_baseline_peak ?? null
  const ip = top?.utci_intervention_peak ?? null
  const feltFrom = useCountUp(bp ?? 0, 420, bp != null)
  const feltTo = useCountUp(ip ?? 0, 420, ip != null)

  // Site name eyebrow — first line of the headline before a comma/colon.
  const siteName = (bundle.decision.headline || 'Selected block')
    .split(/[:,.]/)[0]
    .toUpperCase()
    .slice(0, 32)

  // Dense meta line (folds the old depave-chip): trees · canopy % · species.
  const canopyPct = bundle.canopy ? Math.round(bundle.canopy.cover_fraction * 100) : null
  const speciesShort = (kpi?.species ?? []).slice(0, 3).join(', ')

  // People served — from impervious depave proxy isn't a count; the single-site
  // bundle does not carry a population figure, so omit it rather than fabricate.
  const cooledArea = kpi?.cooledArea ?? '—'
  const rate = kpi?.rate ?? '—'

  return (
    <section className="result-card panel" role="region" aria-label="Cooling results">
      <header className="rc-head">
        <span className="eyebrow">◖ {siteName}</span>
        <span
          className={`rc-badge ${cs.measured ? 'is-measured' : 'is-preview'}`}
          title={
            cs.measured
              ? 'Cooling measured on an Infrared UTCI simulation'
              : 'Preview — placement is real, cooling estimated until run live'
          }
        >
          {cs.measured ? '● MEASURED' : '● PREVIEW'}
        </span>
      </header>

      {/* Hero: Cool Score ring + verdict + vs-city. */}
      <div className="rc-hero">
        <ScoreRing score={cs.score} />
        <div className="rc-hero__meta">
          <div className="rc-hero__label">Cooling score</div>
          <div className="rc-hero__verdict">{cs.verdict}</div>
          <div className="rc-hero__vs">
            <span aria-hidden>▁▂▃▅▇</span> vs city avg{' '}
            <span className="tnum">{CITY_AVG_COOL_SCORE}</span>
          </div>
        </div>
      </div>

      <hr className="rc-rule" />

      {/* Felt-like transition. */}
      <div className="rc-felt">
        <span className="rc-felt__label">Feels like</span>
        {bp != null && ip != null ? (
          <span className="rc-felt__row">
            <span className="rc-felt__from tnum">{feltFrom.toFixed(1)}°</span>
            <span className="rc-felt__arrow" aria-hidden>→</span>
            <span className="rc-felt__to tnum">{feltTo.toFixed(1)}°</span>
            <span className={`rc-felt__delta ${kpi?.isCooling ? 'is-cool' : 'is-warm'}`}>
              {kpi?.delta}
            </span>
          </span>
        ) : (
          <span className="rc-felt__na">peak relief measured only on a live run</span>
        )}
      </div>

      <hr className="rc-rule" />

      {/* 3-up supporting strip. */}
      <dl className="rc-strip">
        <div className="rc-stat">
          <dd className="rc-stat__val tnum">{cooledArea}</dd>
          <dt className="rc-stat__cap">cooled (square metres)</dt>
        </div>
        <div className="rc-stat">
          <dd className="rc-stat__val tnum">{rate}</dd>
          <dt className="rc-stat__cap">per m² cooled</dt>
        </div>
        <div className="rc-stat">
          <dd className="rc-stat__val tnum">{kpi?.trees ?? '—'}</dd>
          <dt className="rc-stat__cap">trees</dt>
        </div>
      </dl>

      <hr className="rc-rule" />

      {/* Dense meta line (folds depave-chip). */}
      <div className="rc-meta">
        {kpi?.trees ?? '—'} trees
        {canopyPct != null && <> · {canopyPct}% canopy</>}
        {speciesShort && <> · {speciesShort}</>}
      </div>

      {/* Docked Growth Slider. */}
      {showGrowth && (
        <div className="rc-growth">
          <GrowthSlider year={year} setYear={setYear} params={growthParams} />
        </div>
      )}

      <div className="rc-actions">
        {onSave && (
          <button
            type="button"
            className="cs-btn cs-btn--primary rc-save"
            onClick={onSave}
            disabled={saving}
          >
            {saving ? 'Saving…' : '⤓ Save this run'}
          </button>
        )}
        <button type="button" className="cs-btn cs-btn--ghost rc-cta" onClick={onSeeCityPlan}>
          See the €1M city plan →
        </button>
      </div>
    </section>
  )
}
