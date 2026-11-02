import { describe, expect, it } from 'vitest'
import { formatHa, formatPct } from './format'

// fr-FR uses a narrow no-break space (U+202F) as thousands separator and a comma for decimals.
const NNBSP = ' '
const NBSP = ' '

describe('formatHa', () => {
  it('formats hectares with French separators and one decimal', () => {
    expect(formatHa(12345.6)).toBe(`12${NNBSP}345,6${NBSP}ha`)
  })

  it('drops decimals for large values', () => {
    expect(formatHa(1234567.89)).toBe(`1${NNBSP}234${NNBSP}568${NBSP}ha`)
  })

  it('shows an em dash for missing values', () => {
    expect(formatHa(null)).toBe('—')
  })
})

describe('formatPct', () => {
  it('formats a ratio as a French percentage with two decimals', () => {
    expect(formatPct(0.01234)).toBe(`1,23${NBSP}%`)
  })
})
