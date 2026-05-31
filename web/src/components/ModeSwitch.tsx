// ModeSwitch — top-center floating pill (Redesign Spec §4.3). Switches between
// the Design flow and the Citywide €1M plan. role="tablist"; animated thumb
// slides under the active segment. Lives out of both data zones (top-center).

import './ModeSwitch.css'

export type SwitchMode = 'design' | 'citywide'

interface ModeSwitchProps {
  mode: SwitchMode
  onChange: (m: SwitchMode) => void
}

const SEGMENTS: { id: SwitchMode; label: string }[] = [
  { id: 'design', label: 'Design' },
  { id: 'citywide', label: 'Citywide €1M' },
]

export function ModeSwitch({ mode, onChange }: ModeSwitchProps) {
  const activeIndex = SEGMENTS.findIndex((s) => s.id === mode)
  return (
    <div className="mode-switch panel" role="tablist" aria-label="View mode">
      <span
        className="mode-switch__thumb"
        style={{ transform: `translateX(${activeIndex * 100}%)` }}
        aria-hidden
      />
      {SEGMENTS.map((s) => (
        <button
          key={s.id}
          type="button"
          role="tab"
          id={`mode-tab-${s.id}`}
          aria-selected={mode === s.id}
          aria-controls={`mode-panel-${s.id}`}
          className={`mode-switch__seg ${mode === s.id ? 'is-active' : ''}`}
          onClick={() => onChange(s.id)}
        >
          {s.label}
        </button>
      ))}
    </div>
  )
}
