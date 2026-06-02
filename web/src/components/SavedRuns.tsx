// SavedRuns — the "memory" surface (IAAC Day-2 slides, Part 2). A compact
// gallery of previously-saved evaluations, shown in the design phase. Click one
// to reload it: the app fetches the stored bundle and re-renders it through the
// same path a fresh Evaluate uses. This is the visible half of "make it
// remember" — the runs survive a page refresh because they live in the DB.

import { useCallback, useEffect, useState } from 'react'
import './SavedRuns.css'
import { listRuns, getRun, type RunSummary } from '../lib/api'
import type { EvaluateResponse } from '../lib/api'

interface SavedRunsProps {
  /** Bumped by the parent after a save, to trigger a refetch. */
  version: number
  /** Reload a picked run (already fetched) into the scene. */
  onPick: (resp: EvaluateResponse) => void
}

function fmtDate(iso: string): string {
  // iso like 2026-06-02T11:38:38+00:00 — show date + HH:MM, locale-agnostic slice.
  return iso.replace('T', ' ').slice(0, 16)
}

export function SavedRuns({ version, onPick }: SavedRunsProps) {
  const [runs, setRuns] = useState<RunSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loadingId, setLoadingId] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    listRuns()
      .then((r) => !cancelled && setRuns(r))
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [version])

  const pick = useCallback(
    async (id: number) => {
      setLoadingId(id)
      setError(null)
      try {
        const resp = await getRun(id)
        onPick(resp)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : String(e))
      } finally {
        setLoadingId(null)
      }
    },
    [onPick],
  )

  // Hide the panel entirely until the first run is saved, so it never clutters a
  // clean first-run canvas. (Errors still surface so a backend fault is visible.)
  if (!error && (runs == null || runs.length === 0)) return null

  return (
    <section className="saved-runs panel" aria-label="Saved runs">
      <header className="sr-head">
        <span className="sr-title">⤓ Saved runs</span>
        {runs && <span className="sr-count tnum">{runs.length}</span>}
      </header>

      {error && (
        <div className="sr-error" role="alert">
          {error}
        </div>
      )}

      <ul className="sr-list">
        {(runs ?? []).map((r) => (
          <li key={r.id}>
            <button
              type="button"
              className="sr-item"
              onClick={() => pick(r.id)}
              disabled={loadingId != null}
              title={`Reload "${r.name}"`}
            >
              <span className="sr-item__name">{r.name}</span>
              <span className="sr-item__meta">
                {r.delta_utci_c != null && (
                  <span className="sr-chip is-cool tnum">{r.delta_utci_c.toFixed(1)}°</span>
                )}
                {r.eur_per_m2 != null && (
                  <span className="sr-chip tnum">€{Math.round(r.eur_per_m2)}/m²</span>
                )}
                {r.n_trees != null && <span className="sr-chip tnum">{r.n_trees}🌳</span>}
              </span>
              <span className="sr-item__date">{fmtDate(r.created_at)}</span>
              {loadingId === r.id && <span className="sr-item__loading">loading…</span>}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
