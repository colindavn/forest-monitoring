import { useMemo } from 'react'
import type { AlertPoint } from '../api/client'
import { formatHa } from '../lib/format'
import EChart from './EChart'
import { ANOMALY_COLOR, AXIS, CONFIDENCE_COLORS, INK, ROLLING_COLOR } from './theme'

const dateFmt = new Intl.DateTimeFormat('fr-FR', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})
const axisHa = new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 })

const STACK = [
  { key: 'area_ha_nominal', name: 'Confiance nominale', color: CONFIDENCE_COLORS.nominal },
  { key: 'area_ha_high', name: 'Confiance élevée', color: CONFIDENCE_COLORS.high },
  { key: 'area_ha_highest', name: 'Confiance très élevée', color: CONFIDENCE_COLORS.highest },
] as const

export default function AlertsChart({ series }: { series: AlertPoint[] }) {
  const option = useMemo(() => {
    const weeks = series.map((p) => p.week_start)
    return {
      grid: { left: 52, right: 12, top: 56, bottom: 64 },
      legend: { top: 0, left: 0, textStyle: { color: INK.secondary }, itemGap: 14 },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (items: { dataIndex: number }[]) => {
          const p = series[items[0]?.dataIndex ?? 0]
          if (!p) return ''
          const rows = [
            `<strong>Semaine du ${dateFmt.format(new Date(p.week_start))}</strong>`,
            ...STACK.map((s) => `${s.name} : ${formatHa(p[s.key])}`),
            `Total : ${formatHa(p.area_ha_all)}`,
            `Moyenne mobile 4 semaines : ${formatHa(p.area_ha_4w_rolling / 4)}`,
          ]
          if (p.is_anomaly) rows.push(`▲ Anomalie (z = ${p.z_score?.toFixed(1)})`)
          return rows.join('<br/>')
        },
      },
      xAxis: {
        type: 'category',
        data: weeks,
        ...AXIS,
        axisLabel: {
          color: INK.muted,
          formatter: (v: string) =>
            new Date(v).toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' }),
        },
      },
      yAxis: {
        type: 'value',
        ...AXIS,
        axisLine: { show: false },
        axisLabel: { color: INK.muted, formatter: (v: number) => axisHa.format(v) },
      },
      dataZoom: [
        { type: 'slider', bottom: 8, height: 18, startValue: Math.max(0, weeks.length - 52) },
        { type: 'inside' },
      ],
      series: [
        ...STACK.map((s) => ({
          name: s.name,
          type: 'bar',
          stack: 'alerts',
          data: series.map((p) => p[s.key]),
          itemStyle: { color: s.color, borderColor: INK.surface, borderWidth: 1 },
          barCategoryGap: '20%',
        })),
        {
          // Weekly mean over 4 weeks, so the line shares the bars' scale.
          name: 'Moyenne mobile 4 semaines',
          type: 'line',
          data: series.map((p) => p.area_ha_4w_rolling / 4),
          lineStyle: { color: ROLLING_COLOR, width: 2 },
          itemStyle: { color: ROLLING_COLOR },
          symbol: 'none',
        },
        {
          name: '▲ Anomalie',
          type: 'scatter',
          symbol: 'triangle',
          symbolSize: 10,
          symbolOffset: [0, -8],
          itemStyle: { color: ANOMALY_COLOR, borderColor: INK.surface, borderWidth: 2 },
          data: series.map((p) => (p.is_anomaly ? p.area_ha_all : null)),
          z: 10,
        },
      ],
    }
  }, [series])

  const anomalies = series.filter((p) => p.is_anomaly)
  return (
    <figure className="chart">
      <figcaption>Alertes de perturbation hebdomadaires (DIST-ALERT, en ha)</figcaption>
      <EChart option={option} label="Graphique des alertes hebdomadaires" height={300} />
      <p className="chart-note">
        ▲ Anomalie : semaine dont la surface d’alertes dépasse de plus de 2 écarts-types la
        référence (les 12 semaines précédentes, puis la même semaine des années précédentes dès 2
        ans d’historique) — {anomalies.length} semaine{anomalies.length > 1 ? 's' : ''}.
      </p>
      <details>
        <summary>Voir les données en tableau</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Semaine</th>
                {STACK.map((s) => (
                  <th key={s.key} scope="col">
                    {s.name}
                  </th>
                ))}
                <th scope="col">Total</th>
                <th scope="col">Anomalie</th>
              </tr>
            </thead>
            <tbody>
              {[...series].reverse().map((p) => (
                <tr key={p.week_start}>
                  <th scope="row">{p.week_start}</th>
                  {STACK.map((s) => (
                    <td key={s.key}>{formatHa(p[s.key])}</td>
                  ))}
                  <td>{formatHa(p.area_ha_all)}</td>
                  <td>{p.is_anomaly ? '▲ oui' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  )
}
