// CitywidePanel — bottom-left contextual surface for phase==='citywide'
// (Redesign Spec §4.6). Mirrors the Result Card: hero strip (people protected +
// €1M + ha greened) then a ranked leaderboard with rank medallions and per-site
// mint spend bars. Each row is a real <button> (C4) that flies to + spotlights
// the site. All numbers come from citywide_plan.json (real, measured).

import { useMemo } from 'react'
import './CitywidePanel.css'
import type { CityPlan, CityPlanSite } from '../lib/types'
import { formatEuro } from '../lib/format'

interface CitywidePanelProps {
  plan: CityPlan | null
  loading: boolean
  /** Fly to + spotlight this funded site (by index in the sorted list). */
  onSelectSite: (site: CityPlanSite, index: number) => void
  /** Cross-highlight a row's pin on hover. */
  onHoverSite: (index: number | null) => void
  selectedIndex: number | null
  onCoolOwnBlock: () => void
  onReplayStory: () => void
}

function titleCase(s: string): string {
  return s
    .toLowerCase()
    .replace(/\b\w/g, (m) => m.toUpperCase())
    .replace(/\bI\b/g, 'i')
}

export function CitywidePanel({
  plan,
  loading,
  onSelectSite,
  onHoverSite,
  selectedIndex,
  onCoolOwnBlock,
  onReplayStory,
}: CitywidePanelProps) {
  const sites = useMemo(
    () => (plan ? [...plan.allocated_cells].sort((a, b) => a.rank - b.rank) : []),
    [plan],
  )
  const maxSpend = useMemo(
    () => sites.reduce((m, s) => Math.max(m, s.cost_eur), 1),
    [sites],
  )

  if (loading && !plan) {
    return (
      <section className="city-panel panel" role="region" aria-label="Citywide plan">
        <div className="cp-loading" aria-live="polite">
          <span className="spinner" aria-hidden /> Scanning Barcelona…
        </div>
      </section>
    )
  }
  if (!plan) return null

  const measured = plan.cooling_is_measured && plan.cooling_source === 'measured_utci'
  const canopyM2 = Math.round(plan.total_canopy_m2).toLocaleString()

  return (
    <section className="city-panel panel" role="region" aria-label="Citywide €1M plan">
      <header className="cp-head">
        <span className="eyebrow">◖ CITYWIDE PLAN</span>
        <span className="cp-budget tnum">● {formatEuro(plan.budget_eur)}</span>
      </header>

      {/* Hero strip: people / funded / canopy. */}
      <div className="cp-hero">
        <div className="cp-hero__stat">
          <div className="cp-hero__val tnum">
            {plan.total_people_served ? plan.total_people_served.toLocaleString() : '—'}
          </div>
          <div className="cp-hero__cap">people served</div>
        </div>
        <div className="cp-hero__stat">
          <div className="cp-hero__val tnum">{plan.allocated_count}</div>
          <div className="cp-hero__cap">sites funded</div>
        </div>
        <div className="cp-hero__stat">
          <div className="cp-hero__val tnum">{canopyM2}</div>
          <div className="cp-hero__cap">m² new canopy</div>
        </div>
      </div>

      <div className={`cp-credibility ${measured ? 'is-measured' : 'is-preview'}`}>
        {measured ? '● MEASURED' : '● PREVIEW'} ·{' '}
        {Math.round(
          plan.total_cooled_footprint_m2 || plan.total_cooled_m2_proxy || 0,
        ).toLocaleString()}{' '}
        m² cooled{measured ? '' : ' (est.)'} · {plan.total_trees} trees
      </div>

      <hr className="cp-rule" />

      {/* Ranked leaderboard. */}
      <ol className="cp-board">
        {sites.map((s, i) => (
          <li key={s.cell_id}>
            <button
              type="button"
              className={`cp-row ${selectedIndex === i ? 'is-selected' : ''}`}
              onClick={() => onSelectSite(s, i)}
              onMouseEnter={() => onHoverSite(i)}
              onMouseLeave={() => onHoverSite(null)}
              onFocus={() => onHoverSite(i)}
              onBlur={() => onHoverSite(null)}
            >
              <span className="cp-row__rank" aria-hidden>
                {i + 1}
              </span>
              <span className="cp-row__body">
                <span className="cp-row__name">
                  {titleCase(s.district)} · {titleCase(s.barri)}
                </span>
                <span className="cp-row__bar" aria-hidden>
                  <span
                    className={`cp-row__fill ${s.partial ? 'is-partial' : ''}`}
                    style={{ width: `${(s.cost_eur / maxSpend) * 100}%` }}
                  />
                </span>
              </span>
              <span className="cp-row__spend tnum">{formatEuro(s.cost_eur)}</span>
              <span className="cp-row__chev" aria-hidden>▸</span>
            </button>
          </li>
        ))}
      </ol>

      <hr className="cp-rule" />
      <div className="cp-foot">
        {plan.total_cells_scanned ?? 494} blocks scanned · funded the{' '}
        {plan.allocated_count} hottest first · {formatEuro(plan.budget_eur - plan.total_allocated_eur)} left
      </div>
      {plan.placement_audit && (
        <div className={`cp-audit ${plan.placement_audit.all_on_valid_ground ? 'is-ok' : 'is-warn'}`}>
          {plan.placement_audit.all_on_valid_ground ? '✓ ' : '⚠ '}
          {plan.placement_audit.trees_checked - plan.placement_audit.on_building}/
          {plan.placement_audit.trees_checked} trees verified on valid ground ·{' '}
          {plan.placement_audit.on_building} on buildings · {plan.placement_audit.clumps_under_min_spacing} clumped
          <span className="cp-audit__how"> (independent OSM re-check)</span>
        </div>
      )}

      {/* CTA (Scene 8 footer). */}
      <div className="cp-cta">
        <button type="button" className="cs-btn cs-btn--primary" onClick={onCoolOwnBlock}>
          Cool your own block →
        </button>
        <button type="button" className="cs-btn cs-btn--ghost" onClick={onReplayStory}>
          Replay the story
        </button>
      </div>
    </section>
  )
}
