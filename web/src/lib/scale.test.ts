import { describe, expect, it } from 'vitest'
import { PALETTE, classify, quantileBreaks } from './scale'

describe('quantileBreaks', () => {
  it('splits values into 6 classes of equal count', () => {
    const values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    expect(quantileBreaks(values, 6)).toEqual([3, 5, 7, 9, 11])
  })

  it('removes duplicate breaks when values repeat', () => {
    expect(quantileBreaks([0, 0, 0, 0, 0, 10], 6)).toEqual([0, 10])
  })

  it('ignores missing values and returns no breaks for empty input', () => {
    expect(quantileBreaks([null, Number.NaN], 6)).toEqual([])
    expect(quantileBreaks([null, 1, 2], 2)).toEqual([2])
  })
})

describe('classify', () => {
  const breaks = [3, 5, 7, 9, 11]

  it('returns the class index, upper-inclusive breaks start the next class', () => {
    expect(classify(1, breaks)).toBe(0)
    expect(classify(3, breaks)).toBe(1)
    expect(classify(10, breaks)).toBe(4)
    expect(classify(100, breaks)).toBe(5)
  })

  it('returns -1 for missing values', () => {
    expect(classify(null, breaks)).toBe(-1)
  })
})

describe('PALETTE', () => {
  it('has 6 sequential colours', () => {
    expect(PALETTE).toHaveLength(6)
  })
})
