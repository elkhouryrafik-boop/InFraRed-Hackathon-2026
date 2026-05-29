import { describe, it, expect } from 'vitest'
import {
  liftMatrix,
  computeLiftMeters,
  BARCELONA_GEOID_UNDULATION_M,
} from './elevation'

describe('liftMatrix', () => {
  it('builds a column-major Z-translation matrix', () => {
    expect(liftMatrix(10)).toEqual([
      1, 0, 0, 0,
      0, 1, 0, 0,
      0, 0, 1, 0,
      0, 0, 10, 1,
    ])
  })
})

describe('computeLiftMeters', () => {
  it('adds geoid undulation and a -2m mesh offset', () => {
    expect(computeLiftMeters(12)).toBe(12 + BARCELONA_GEOID_UNDULATION_M - 2)
  })
})
