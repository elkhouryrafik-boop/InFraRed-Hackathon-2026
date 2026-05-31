// useCountUp — animates a number from 0 (or a previous value) to `target` over
// `duration` ms with an ease-out curve. Respects prefers-reduced-motion: when
// reduced, it lands on the target instantly (Redesign Spec §4.2 / §6 D1).

import { useEffect, useRef, useState } from 'react'
import { prefersReducedMotion } from './useReducedMotion'

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)

export function useCountUp(target: number, duration = 420, enabled = true): number {
  const [value, setValue] = useState(enabled ? 0 : target)
  const fromRef = useRef(0)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    if (!enabled || prefersReducedMotion() || !Number.isFinite(target)) {
      setValue(target)
      return
    }
    const from = fromRef.current
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const v = from + (target - from) * easeOut(t)
      setValue(v)
      if (t < 1) rafRef.current = requestAnimationFrame(tick)
      else fromRef.current = target
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current)
    }
  }, [target, duration, enabled])

  return value
}
