import { useEffect, useRef, useState } from 'react'
import './IntroVideoGate.css'

const VIDEO_SRC = '/coolspend-explainer.mp4'

/**
 * Full-screen explainer that plays when the app opens (first visit). It autoplays
 * muted (browser policy), invites one click to unmute, and can be skipped. On end
 * or skip it calls onDone — which marks it seen and reveals the live app.
 */
export function IntroVideoGate({ onDone }: { onDone: () => void }) {
  const ref = useRef<HTMLVideoElement | null>(null)
  const [muted, setMuted] = useState(true)
  const [progress, setProgress] = useState(0)
  const [leaving, setLeaving] = useState(false)

  const finish = () => {
    if (leaving) return
    setLeaving(true)
    window.setTimeout(onDone, 480)
  }

  useEffect(() => {
    const v = ref.current
    if (!v) return
    v.play().catch(() => {
      /* autoplay may be blocked; the poster + Play affordance still let the user start it */
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
  }, [])

  const unmute = () => {
    const v = ref.current
    if (!v) return
    v.muted = false
    v.volume = 1
    setMuted(false)
    if (v.paused) v.play().catch(() => {})
  }

  return (
    <div className={`introgate ${leaving ? 'introgate--leaving' : ''}`}>
      <video
        ref={ref}
        className="introgate__video"
        src={VIDEO_SRC}
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

      <div className="introgate__caption">CoolSpend · how it works</div>

      <div className="introgate__bar">
        <div className="introgate__bar-fill" style={{ width: `${progress * 100}%` }} />
      </div>
    </div>
  )
}
