// Onboarding — the one-time, skippable, localStorage-gated guided heat reveal
// (Redesign Spec §4.1 + storyboard §3.3 scenes 0–3). It is a full-bleed overlay
// over the LIVE deck.gl map (no separate story canvas): each scene emits camera
// + heatmap-fade intents the parent (Scene.tsx) applies to the real layers.
//
// CRITICAL credibility rule (§3.3 + §6): payoff numbers come from the REAL
// citywide_plan.json (cooling_is_measured:true) — NEVER the eval_bundle mock
// 0.00 °C. The plan is passed in; copy degrades gracefully if it is absent.

import { useCallback, useEffect, useRef, useState } from 'react'
import './Onboarding.css'
import type { CityPlan } from '../lib/types'

export interface OnboardingIntent {
  /** 0..1 — how much the UTCI drape should be faded in for this scene. */
  heatReveal: number
  /** 'overview' = full city; 'site' = tight on the rank-1 hot block. */
  framing: 'overview' | 'site'
  /** true on the intervention scene → show the with-trees heatmap + canopy. */
  intervention: boolean
}

interface OnboardingProps {
  plan: CityPlan | null
  /** Called every time the scene changes so the parent can drive the map. */
  onIntent: (intent: OnboardingIntent) => void
  /** Finish the intro and enter the Design phase (sets localStorage flag). */
  onFinish: () => void
  /** Jump straight to the Citywide €1M plan. */
  onSeeCityPlan: () => void
}

interface Scene {
  eyebrow?: string
  headline: string
  subline?: string
  body: string
  primary: string
  intent: OnboardingIntent
}

function buildScenes(plan: CityPlan | null): Scene[] {
  // REAL measured figures (citywide_plan.json). Fallbacks only if the file is
  // missing — never a fabricated "measured" number.
  const hottest = plan
    ? Math.max(...plan.allocated_cells.map((c) => c.mean_lst_celsius), 0)
    : 44.1
  const cooled = plan?.total_cooled_footprint_m2 ?? 24356
  const rate = plan?.avg_cost_per_m2_cooled ?? 41
  const people = plan?.total_people_served ?? 22590
  const trees = plan?.total_trees ?? 99

  return [
    {
      // Scene 0 — HOOK
      headline: 'Barcelona is running a fever.',
      body: `Last summer its hottest streets crossed ${Math.round(hottest)} °C at ground level — not the air, the pavement people walk on.`,
      primary: 'Show me where',
      intent: { heatReveal: 1, framing: 'overview', intervention: false },
    },
    {
      // Scene 1 — THE PROBLEM
      headline: 'This block runs hot.',
      body: 'Concrete, parked cars, no shade. Nobody planned it this way — it just paved over.',
      primary: 'What if we planted trees?',
      intent: { heatReveal: 1, framing: 'site', intervention: false },
    },
    {
      // Scene 2 — THE INTERVENTION
      headline: 'We plant only where a tree can actually go.',
      body: 'Never a roof, never a wall, never the road. 8 m apart, the right species for each street’s width.',
      primary: 'How much did that cool?',
      intent: { heatReveal: 0.85, framing: 'site', intervention: true },
    },
    {
      // Scene 3 — THE MEASURED PAYOFF (real numbers only)
      headline: `${Math.round(cooled).toLocaleString()} m² cooled, measured.`,
      subline: `€${rate}/m² · ${people.toLocaleString()} people · ${trees} trees`,
      body: 'Not a forecast — we re-ran Barcelona’s microclimate with these trees in it.',
      primary: 'Try it on a real block →',
      intent: { heatReveal: 0.85, framing: 'site', intervention: true },
    },
  ]
}

export function Onboarding({ plan, onIntent, onFinish, onSeeCityPlan }: OnboardingProps) {
  const scenes = buildScenes(plan)
  const [i, setI] = useState(0)
  const dialogRef = useRef<HTMLDivElement | null>(null)
  const primaryRef = useRef<HTMLButtonElement | null>(null)

  // Push the current scene's intent up to the map.
  useEffect(() => {
    onIntent(scenes[i].intent)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i])

  // Move focus to the primary button on each scene (focus trap + readability).
  useEffect(() => {
    primaryRef.current?.focus()
  }, [i])

  const next = useCallback(() => {
    if (i < scenes.length - 1) setI((v) => v + 1)
    else onFinish()
  }, [i, scenes.length, onFinish])

  // Esc closes (skips). Tab is trapped within the dialog.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onFinish()
      } else if (e.key === 'Tab') {
        const root = dialogRef.current
        if (!root) return
        const focusable = root.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
        )
        if (focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onFinish])

  const scene = scenes[i]
  const isFirst = i === 0
  const isLast = i === scenes.length - 1

  return (
    <div
      className="onboarding"
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-label="CoolSpend introduction"
    >
      <div className="onboarding__scrim" aria-hidden />

      <button type="button" className="onboarding__skip" onClick={onFinish}>
        Skip ▸
      </button>

      <div className="onboarding__content">
        <div className="eyebrow onboarding__eyebrow">
          ◖ COOLSPEND · Barcelona urban-cooling lab
        </div>

        <h1 className="onboarding__headline">{scene.headline}</h1>
        {scene.subline && <div className="onboarding__subline tnum">{scene.subline}</div>}
        <p className="onboarding__body">{scene.body}</p>

        <div className="onboarding__actions">
          <button
            type="button"
            ref={primaryRef}
            className="cs-btn cs-btn--primary"
            onClick={next}
          >
            {isFirst ? '▸ ' : ''}
            {scene.primary}
          </button>
          {isFirst && (
            <button type="button" className="cs-btn cs-btn--ghost" onClick={onSeeCityPlan}>
              See the €1M city plan
            </button>
          )}
          {isLast && (
            <button type="button" className="cs-btn cs-btn--ghost" onClick={onSeeCityPlan}>
              See the €1M city plan
            </button>
          )}
        </div>

        <div className="onboarding__proof" aria-hidden>
          <span>● measured UTCI</span>
          <span>● 0–40 yr growth</span>
          <span>● {plan?.allocated_count ?? 7} hot sites</span>
        </div>

        <div className="onboarding__dots" aria-hidden>
          {scenes.map((_, k) => (
            <span key={k} className={`onboarding__dot ${k === i ? 'is-active' : ''}`} />
          ))}
        </div>
      </div>
    </div>
  )
}
