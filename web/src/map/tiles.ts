// Raster tile templates loaded directly by the browser (SPEC §3.5, verified 2026-11-02).

const GFW = 'https://tiles.globalforestwatch.org'
const TILE = '{z}/{x}/{y}.png'

export function hansenLossTiles(opts: {
  startYear: number
  endYear: number
  threshold: number
}): string {
  return (
    `${GFW}/umd_tree_cover_loss/latest/dynamic/${TILE}` +
    `?start_year=${opts.startYear}&end_year=${opts.endYear}` +
    `&tree_cover_density_threshold=${opts.threshold}`
  )
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export function distAlertTiles(opts: {
  today: Date
  threshold: number
  days?: number
  highConfidenceOnly?: boolean
}): string {
  const end = new Date(opts.today)
  const start = new Date(end)
  start.setUTCDate(start.getUTCDate() - (opts.days ?? 90))
  // `alert_confidence` (not `confidence`): low = all alerts, high = high confidence only.
  const confidence = opts.highConfidenceOnly ? 'high' : 'low'
  return (
    `${GFW}/umd_glad_dist_alerts/latest/dynamic/${TILE}` +
    `?start_date=${isoDate(start)}&end_date=${isoDate(end)}&alert_confidence=${confidence}` +
    `&tree_cover_density_threshold=${opts.threshold}`
  )
}

export type Basemap = 'plan' | 'ortho'

const IGN_LAYERS: Record<Basemap, { layer: string; format: string }> = {
  plan: { layer: 'GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2', format: 'image/png' },
  ortho: { layer: 'ORTHOIMAGERY.ORTHOPHOTOS', format: 'image/jpeg' },
}

export function ignBasemap(kind: Basemap): string {
  const { layer, format } = IGN_LAYERS[kind]
  return (
    'https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0' +
    `&LAYER=${layer}&STYLE=normal&FORMAT=${format}&TILEMATRIXSET=PM` +
    '&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}'
  )
}
