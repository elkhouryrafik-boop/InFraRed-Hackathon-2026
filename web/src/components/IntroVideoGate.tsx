import { useEffect, useRef, useState } from 'react'
import './IntroVideoGate.css'

const VIDEOS = {
  short: '/coolspend-2min.mp4',
  long: '/coolspend-explainer.mp4',
} as const
type Choice = keyof typeof VIDEOS

/**
 * First-visit front door. Shows a choice — a 2-minute brief, the 10-minute
 * deep-dive, or skip — then plays the chosen film full-screen (autoplay muted,
 * one tap to unmute, skippable). On end/skip it calls onDone, revealing the app.
 */
export function IntroVideoGate({ onDone }: { onDone: () => void }) {
  const ref = useRef<HTMLVideoElement | null>(null)
  const [choice, setChoice] = useState<Choice | null>(null)
  const [muted, setMuted] = useState(true)
  const [progress, setProgress] = useState(0)
  const [leaving, setLeaving] = useState(false)

  const finish = () => {
    if (leaving) return
    setLeaving(true)
    window.setTimeout(onDone, 480)
  }

  useEffect(() => {
    if (!choice) return
    const v = ref.current
    if (!v) return
    v.play().catch(() => {
      /* autoplay may be blocked; the unmute/skip affordances still drive it */
    })
    const onTime = () => v.duration && setProgress(v.currentTime / v.duration)
    const onEnd = () => finish()
    v.addEventListener('timeupdate', onTime)
    v.addEventListener('ended', onEnd)
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') finish()
      if (e.key === ' ') {
        e.preventDefault()
        if (v.paused) v.play()
        else v.pause()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => {
      v.removeEventListener('timeupdate', onTime)
      v.removeEventListener('ended', onEnd)
      window.removeEventListener('keydown', onKey)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [choice])

  const unmute = () => {
    const v = ref.current
    if (!v) return
    v.muted = false
    v.volume = 1
    setMuted(false)
    if (v.paused) v.play().catch(() => {})
  }

  // ── Choice screen ──
  if (!choice) {
    return (
      <div className={`introgate introgate--choose ${leaving ? 'introgate--leaving' : ''}`}>
        <div className="ig-choose">
          <div className="ig-choose__brand">● COOLSPEND · BARCELONA</div>
          <h1 className="ig-choose__title">Where each euro buys the most cooling.</h1>
          <p className="ig-choose__sub">Watch how the platform works — pick your depth.</p>

          <div className="ig-choose__opts">
            <button className="ig-opt" onClick={() => setChoice('short')}>
              <span className="ig-opt__time">2 min</span>
              <span className="ig-opt__name">Brief intro</span>
              <span className="ig-opt__desc">Fast and to the point — the idea and the result.</span>
            </button>
            <button className="ig-opt ig-opt--feature" onClick={() => setChoice('long')}>
              <span className="ig-opt__time">10 min</span>
              <span className="ig-opt__name">Full deep-dive</span>
              <span className="ig-opt__desc">Every detail of how it's designed — data, method, honesty.</span>
            </button>
          </div>

          <button className="ig-choose__skip" onClick={finish}>
            Skip — go straight to the app →
          </button>
        </div>
      </div>
    )
  }

  // ── Playback ──
  return (
    <div className={`introgate ${leaving ? 'introgate--leaving' : ''}`}>
      <video
        ref={ref}
        className="introgate__video"
        src={VIDEOS[choice]}
        autoPlay
        muted
        playsInline
        preload="auto"
      />

      {muted && (
        <button className="introgate__unmute" onClick={unmute} aria-label="Unmute">
          <span className="introgate__unmute-icon">🔊</span>
          <span>Tap for sound</span>
        </button>
      )}

      <button className="introgate__skip" onClick={finish}>
        Skip intro →
      </button>

      <div className="introgate__caption">
        CoolSpend · {choice === 'short' ? '2-min brief' : '10-min deep-dive'}
      </div>

      <div className="introgate__bar">
        <div className="introgate__bar-fill" style={{ width: `${progress * 100}%` }} />
      </div>
    </div>
  )
}
