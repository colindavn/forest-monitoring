import { useMemo } from 'react'
import type { LossPoint } from '../api/client'
import { formatHa, formatPct } from '../lib/format'
import EChart from './EChart'
import { AXIS, INK, LOSS_COLORS } from './theme'

const axisHa = new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 })

export default function LossChart({ series }: { series: LossPoint[] }) {
  const option = useMemo(
    () => ({
      grid: { left: 52, right: 12, top: 36, bottom: 28 },
      legend: { top: 0, left: 0, textStyle: { color: INK.secondary }, itemGap: 16 },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: INK.axis } },
        valueFormatter: (v: number) => formatHa(v),
      },
      xAxis: { type: 'category', data: series.map((p) => p.year), ...AXIS },
      yAxis: {
        type: 'value',
        ...AXIS,
        axisLine: { show: false },
        axisLabel: { color: INK.muted, formatter: (v: number) => axisHa.format(v) },
      },
      series: [
        {
          name: 'Perte annuelle',
          type: 'bar',
          data: series.map((p) => p.loss_ha),
          itemStyle: { color: LOSS_COLORS.bars, borderRadius: [4, 4, 0, 0] },
          barCategoryGap: '30%',
        },
        {
          name: 'Moyenne sur 5 ans',
          type: 'line',
          data: series.map((p) => p.loss_ha_5y_avg),
          lineStyle: { color: LOSS_COLORS.avg, width: 2 },
          itemStyle: { color: LOSS_COLORS.avg },
          symbol: 'none',
          smooth: false,
        },
      ],
    }),
    [series],
  )

  return (
    <figure className="chart">
      <figcaption>Perte annuelle de couvert arboré (Hansen, en ha)</figcaption>
      <EChart option={option} label="Graphique de la perte annuelle de couvert arboré" />
      <details>
        <summary>Voir les données en tableau</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Année</th>
                <th scope="col">Perte</th>
                <th scope="col">% du couvert 2000</th>
                <th scope="col">Moyenne 5 ans</th>
                <th scope="col">Cumul</th>
              </tr>
            </thead>
            <tbody>
              {series.map((p) => (
                <tr key={p.year}>
                  <th scope="row">{p.year}</th>
                  <td>{formatHa(p.loss_ha)}</td>
                  <td>{formatPct(p.loss_pct_of_2000)}</td>
                  <td>{formatHa(p.loss_ha_5y_avg)}</td>
                  <td>{formatHa(p.cum_loss_ha)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  )
}
