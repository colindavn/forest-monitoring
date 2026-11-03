import type { AreaKpis } from '../api/client'
import { formatHa, formatPct } from '../lib/format'
import { formatMetric } from '../lib/labels'

function Card({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

export default function KpiCards({ area }: { area: AreaKpis }) {
  const slope = area.trend_slope_ha_per_year
  const arrow = slope > 0 ? '↑ en hausse' : slope < 0 ? '↓ en baisse' : '→ stable'
  return (
    <div className="kpis">
      <Card label="Couvert arboré 2000" value={formatHa(area.forest_2000_ha)} />
      <Card
        label={`Perte ${area.latest_year}`}
        value={formatHa(area.loss_latest_ha)}
        sub={`${formatPct(area.loss_latest_pct)} du couvert 2000`}
      />
      <Card
        label={`Perte totale 2001–${area.latest_year}`}
        value={formatHa(area.loss_total_ha)}
        sub={`${formatPct(area.loss_total_pct)} du couvert 2000`}
      />
      <Card label="Tendance 10 ans" value={arrow} sub={formatMetric('trend_slope', slope)} />
      <Card
        label="Alertes, 4 dernières semaines"
        value={formatHa(area.alerts_last_4w_ha)}
        sub={area.latest_alert_week ? `jusqu’à la semaine du ${area.latest_alert_week}` : undefined}
      />
    </div>
  )
}
