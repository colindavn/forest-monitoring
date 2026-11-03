import type { Metric } from './route'
import { formatHa, formatPct } from './format'

export const METRIC_LABELS: Record<Metric, string> = {
  loss_ha: 'Perte de couvert arboré (ha)',
  loss_pct_of_2000: 'Perte (% du couvert 2000)',
  alerts_ha_last_4w: 'Alertes, 4 dernières semaines (ha)',
  trend_slope: 'Tendance de la perte sur 10 ans (ha/an)',
}

/** Metrics that depend on the selected year (the others use the latest data). */
export const YEARLY_METRICS: readonly Metric[] = ['loss_ha', 'loss_pct_of_2000']

const slope = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0, signDisplay: 'always' })

export function formatMetric(metric: Metric, value: number | null | undefined): string {
  if (metric === 'loss_pct_of_2000') return formatPct(value)
  if (metric === 'trend_slope') return value == null ? '—' : `${slope.format(value)} ha/an`
  return formatHa(value)
}
