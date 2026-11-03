import type { Level, Metric, Threshold } from '../lib/route'

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'

export interface AreaKpis {
  level: Level
  code: string
  name: string
  parent_code: string | null
  forest_2000_ha: number | null
  latest_year: number
  loss_latest_ha: number | null
  loss_latest_pct: number | null
  loss_5y_avg_ha: number | null
  loss_total_ha: number | null
  loss_total_pct: number | null
  trend_slope_ha_per_year: number
  alerts_last_4w_ha: number
  latest_alert_week: string | null
  rank_in_parent: number | null
}

export interface AreaRef {
  level: Level
  code: string
  name: string
}

export interface AreaResponse {
  area: AreaKpis
  parent?: AreaRef
  children?: AreaKpis[]
}

export interface LossPoint {
  year: number
  forest_2000_ha: number
  loss_ha: number
  loss_pct_of_2000: number | null
  cum_loss_ha: number
  loss_ha_5y_avg: number
  yoy_change_pct: number | null
}

export interface AlertPoint {
  week_start: string
  area_ha: number
  area_ha_nominal: number
  area_ha_high: number
  area_ha_highest: number
  area_ha_high_conf: number
  area_ha_all: number
  area_ha_4w_rolling: number
  z_score: number | null
  is_anomaly: boolean
}

export interface Choropleth {
  level: 'region' | 'department'
  metric: Metric
  year: number
  threshold: Threshold
  values: Record<string, number | null>
}

export interface Health {
  status: string
  latest_loss_year: number | null
  latest_alert_date: string | null
  synthetic: boolean
}

export interface Source {
  id: string
  name: string
  provider: string
  url: string
  licence: string
}

export interface Meta {
  sources: Source[]
  versions: Record<string, string[]>
  updated: Record<string, string | null>
  thresholds: number[]
  default_threshold: number
  latest_loss_year: number | null
  latest_alert_date: string | null
  synthetic: boolean
  dbt_docs_url: string
}

async function get<T>(path: string, params: Record<string, string | number | null> = {}) {
  const query = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== null) query.set(k, String(v))
  const qs = query.toString()
  const resp = await fetch(`${BASE}${path}${qs ? `?${qs}` : ''}`)
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText} — ${path}`)
  return (await resp.json()) as T
}

const AREA_PATH: Record<Level, (code: string) => string> = {
  france: () => '/areas/france',
  region: (code) => `/areas/regions/${encodeURIComponent(code)}`,
  department: (code) => `/areas/departments/${encodeURIComponent(code)}`,
}

export const api = {
  health: () => get<Health>('/health'),
  meta: () => get<Meta>('/meta'),
  area: (level: Level, code: string, threshold: Threshold) =>
    get<AreaResponse>(AREA_PATH[level](code), { threshold }),
  loss: (level: Level, code: string, threshold: Threshold) =>
    get<{ series: LossPoint[] }>('/loss', { level, code, threshold }),
  alerts: (level: Level, code: string, threshold: Threshold) =>
    get<{ series: AlertPoint[] }>('/alerts', { level, code, threshold }),
  choropleth: (
    level: 'region' | 'department',
    metric: Metric,
    threshold: Threshold,
    year: number | null,
    parent: string | null = null,
  ) => get<Choropleth>('/choropleth', { level, metric, threshold, year, parent }),
}
