import { describe, expect, it } from 'vitest'
import { distAlertTiles, hansenLossTiles, ignBasemap } from './tiles'

describe('hansenLossTiles', () => {
  it('builds the GFW dynamic loss tile template for a year range and threshold', () => {
    expect(hansenLossTiles({ startYear: 2001, endYear: 2024, threshold: 30 })).toBe(
      'https://tiles.globalforestwatch.org/umd_tree_cover_loss/latest/dynamic/{z}/{x}/{y}.png' +
        '?start_year=2001&end_year=2024&tree_cover_density_threshold=30',
    )
  })
})

describe('distAlertTiles', () => {
  it('uses alert_confidence=low for all alerts and the last 90 days by default', () => {
    const url = distAlertTiles({ today: new Date('2026-11-02T12:00:00Z'), threshold: 50 })
    expect(url).toBe(
      'https://tiles.globalforestwatch.org/umd_glad_dist_alerts/latest/dynamic/{z}/{x}/{y}.png' +
        '?start_date=2026-08-04&end_date=2026-11-02&alert_confidence=low' +
        '&tree_cover_density_threshold=50',
    )
  })

  it('maps "haute confiance" to alert_confidence=high', () => {
    const url = distAlertTiles({
      today: new Date('2026-11-02T12:00:00Z'),
      threshold: 30,
      highConfidenceOnly: true,
    })
    expect(url).toContain('alert_confidence=high')
  })
})

describe('ignBasemap', () => {
  it('builds WMTS templates for Plan IGN and orthophotos', () => {
    expect(ignBasemap('plan')).toContain('LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2')
    expect(ignBasemap('plan')).toContain('FORMAT=image/png')
    expect(ignBasemap('ortho')).toContain('LAYER=ORTHOIMAGERY.ORTHOPHOTOS')
    expect(ignBasemap('ortho')).toContain('FORMAT=image/jpeg')
    expect(ignBasemap('plan')).toContain('TILEMATRIX={z}&TILEROW={y}&TILECOL={x}')
  })
})
