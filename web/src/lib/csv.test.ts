import { describe, expect, it } from 'vitest'
import { toCsv } from './csv'

describe('toCsv', () => {
  it('writes a header and one line per row in column order, with a BOM for Excel', () => {
    const csv = toCsv(
      [
        { year: 2001, loss_ha: 15.5, extra: 'x' },
        { year: 2002, loss_ha: null, extra: 'y' },
      ],
      ['year', 'loss_ha'],
    )
    expect(csv).toBe('﻿year,loss_ha\r\n2001,15.5\r\n2002,\r\n')
  })

  it('quotes values containing separators, quotes or newlines', () => {
    const csv = toCsv([{ name: 'Provence-Alpes-Côte d\'Azur, "PACA"' }], ['name'])
    expect(csv).toBe('﻿name\r\n"Provence-Alpes-Côte d\'Azur, ""PACA"""\r\n')
  })
})
