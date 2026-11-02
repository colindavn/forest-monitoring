export type Level = 'france' | 'region' | 'department'
export type Metric = 'loss_ha' | 'loss_pct_of_2000' | 'alerts_ha_last_4w' | 'trend_slope'
export type Threshold = 10 | 30 | 50

export interface View {
  level: Level
  code: string
  /** null = latest year */
  year: number | null
  metric: Metric
  threshold: Threshold
}

export const METRICS: readonly Metric[] = [
  'loss_ha',
  'loss_pct_of_2000',
  'alerts_ha_last_4w',
  'trend_slope',
]
export const THRESHOLDS: readonly Threshold[] = [10, 30, 50]

export const DEFAULT_VIEW: View = {
  level: 'france',
  code: 'FR',
  year: null,
  metric: 'loss_ha',
  threshold: 30,
}

const PREFIX: Record<Exclude<Level, 'france'>, string> = { region: 'r', department: 'd' }

export function parseView(pathname: string, search: string): View {
  const params = new URLSearchParams(search)
  const year = Number.parseInt(params.get('year') ?? '', 10)
  const metric = params.get('metric') as Metric | null
  const threshold = Number(params.get('threshold')) as Threshold

  const base: View = {
    ...DEFAULT_VIEW,
    year: Number.isFinite(year) && year > 1999 ? year : null,
    metric: metric && METRICS.includes(metric) ? metric : DEFAULT_VIEW.metric,
    threshold: THRESHOLDS.includes(threshold) ? threshold : DEFAULT_VIEW.threshold,
  }
  const match = /^\/([rd])\/([0-9A-Za-z]{2,3})\/?$/.exec(pathname)
  if (!match) return base
  return { ...base, level: match[1] === 'r' ? 'region' : 'department', code: match[2] }
}

export function viewToUrl(view: View): string {
  const path = view.level === 'france' ? '/' : `/${PREFIX[view.level]}/${view.code}`
  const params = new URLSearchParams()
  if (view.year !== null) params.set('year', String(view.year))
  if (view.metric !== DEFAULT_VIEW.metric) params.set('metric', view.metric)
  if (view.threshold !== DEFAULT_VIEW.threshold) params.set('threshold', String(view.threshold))
  const query = params.toString()
  return query ? `${path}?${query}` : path
}
