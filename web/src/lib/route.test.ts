import { describe, expect, it } from 'vitest'
import { DEFAULT_VIEW, parseView, viewToUrl } from './route'

describe('parseView', () => {
  it('maps the root path to France with defaults', () => {
    expect(parseView('/', '')).toEqual(DEFAULT_VIEW)
  })

  it('reads a région path', () => {
    expect(parseView('/r/84', '')).toMatchObject({ level: 'region', code: '84' })
  })

  it('reads a département path with query parameters, keeping codes as strings', () => {
    expect(parseView('/d/2A', '?year=2024&metric=loss_pct_of_2000&threshold=50')).toEqual({
      level: 'department',
      code: '2A',
      year: 2024,
      metric: 'loss_pct_of_2000',
      threshold: 50,
    })
    expect(parseView('/d/01', '').code).toBe('01')
  })

  it('ignores invalid query values', () => {
    const view = parseView('/r/84', '?year=abc&metric=volume&threshold=40')
    expect(view.year).toBeNull()
    expect(view.metric).toBe(DEFAULT_VIEW.metric)
    expect(view.threshold).toBe(30)
  })

  it('falls back to France for unknown paths', () => {
    expect(parseView('/x/1', '')).toMatchObject({ level: 'france', code: 'FR' })
  })
})

describe('viewToUrl', () => {
  it('omits default parameters', () => {
    expect(viewToUrl(DEFAULT_VIEW)).toBe('/')
    expect(viewToUrl({ ...DEFAULT_VIEW, level: 'region', code: '84' })).toBe('/r/84')
  })

  it('serialises non-default parameters', () => {
    expect(
      viewToUrl({
        level: 'department',
        code: '38',
        year: 2024,
        metric: 'loss_pct_of_2000',
        threshold: 30,
      }),
    ).toBe('/d/38?year=2024&metric=loss_pct_of_2000')
  })

  it('round-trips', () => {
    const url = '/d/2B?year=2010&metric=trend_slope&threshold=10'
    const [path, search] = url.split('?')
    expect(viewToUrl(parseView(path, `?${search}`))).toBe(url)
  })
})
